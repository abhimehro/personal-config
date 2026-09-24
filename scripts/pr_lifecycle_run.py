#!/usr/bin/env python3
"""Stage runner preflight: print exact action plan + allowed commands.

``--stage 1|2|3`` emits a JSON plan and appends a JSONL run record under
``/tmp/pr-lifecycle/<run>.jsonl``. Updates ``status.json`` on the ledger
branch when ``--write-status`` is set. Classifies failures as TRANSIENT_RETRY
vs LOGIC_STOP.

``--status`` refreshes the pinned "PR pipeline status" GitHub issue.

Calibration stays disabled. Stage 2 never merges. Stage 3 re-reads predicates.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position
import pr_lifecycle_feed as feed_mod
import pr_lifecycle_ledger_cas as cas
import pr_lifecycle_pipeline_health as health
import pr_lifecycle_reconcile as reconcile_mod
from pr_lifecycle_config import validate_config
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

LOG_DIR = Path(tempfile.gettempdir()) / "pr-lifecycle"
STATUS_PATH_ON_BRANCH = "status.json"
PINNED_ISSUE_TITLE = "PR pipeline status"


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def _run_id() -> str:
    """Generate a unique timestamped lifecycle run identifier."""
    stamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSON record to a JSONL file, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _stage_cap(config: dict[str, Any], name: str, default: int) -> int:
    raw = (config.get("lifecycle") or {}).get("stage_caps") or {}
    value = raw.get(name, default)
    if not isinstance(value, int) or value < 1:
        return default
    return value


STAGE2_ENQUEUE_CAP = 5
RESELECT_ENQUEUE_REASON = "CONFLICTING_UNIQUE_RESELECT"


def _wi_source_key(work_item: dict[str, Any]) -> str:
    """Get a feed item's source_key or source_item_key, or an empty string."""
    return str(
        work_item.get("source_key") or work_item.get("source_item_key") or ""
    )


def _filter_never_touch_work_items(
    work_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate feed items by never-touch source, preserving their order."""
    mechanical: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for work_item in work_items:
        if health.is_never_touch_key(_wi_source_key(work_item)):
            skipped.append(work_item)
        else:
            mechanical.append(work_item)
    return mechanical, skipped


def _enqueue_source_paths(
    item: dict[str, Any], signals: health.ReselectSignals, key: str
) -> list[str]:
    """Resolve allowed paths, preferring caller-supplied unique remaining."""
    paths = list(item.get("changed_paths") or [])
    unique = health.signal_value(signals.unique_paths_by_key, key)
    if unique is not None:
        paths = list(unique)
    return health.non_journal_paths([str(path) for path in paths])


def _enqueue_action(
    item: dict[str, Any], key: str, allowed_paths: list[str]
) -> dict[str, Any]:
    """Build one ENQUEUE_STAGE2_WI plan action for a reselect candidate."""
    return {
        "action": "ENQUEUE_STAGE2_WI",
        "source_key": key,
        "repository": item.get("repository"),
        "pr": item.get("pr"),
        "base_sha": item.get("base_sha"),
        "head_sha": item.get("head_sha"),
        "allowed_paths": allowed_paths,
        "reason": RESELECT_ENQUEUE_REASON,
        "next_action": health.MECHANICAL_RESELECT_NA,
        "note": (
            "CAS-write a complete stage2_work_item; "
            "pr_lifecycle_feed.py is read-only verification only"
        ),
    }


def _enqueue_fields_complete(
    item: dict[str, Any], key: str, allowed_paths: list[str]
) -> bool:
    """Return True when the ledger item can yield a complete Stage 2 WI."""
    fields = (
        key,
        item.get("repository"),
        item.get("pr"),
        item.get("base_sha"),
        item.get("head_sha"),
    )
    return all(fields) and bool(allowed_paths)


def plan_stage2_enqueues(
    ledger: dict[str, Any],
    *,
    signals: health.ReselectSignals | None = None,
    limit: int = STAGE2_ENQUEUE_CAP,
) -> dict[str, Any]:
    """Return Stage 2 enqueue action proposals for capped reselect candidates."""
    # Unique-path signals beat changed_paths; journal paths are stripped from
    # allowed_paths. Candidates that cannot form a complete WI land in
    # skipped_incomplete instead, so enqueued_count can trail candidate_count
    # and FEED_CHECK can fail. Actions request later CAS writes; nothing here
    # creates WIs or writes to the ledger.
    signals = signals or health.ReselectSignals()
    # Select unbounded, then cap complete WIs: an early-run of incomplete
    # candidates must not starve a complete one further down ledger order.
    candidates = health.list_reselect_candidates(ledger, signals=signals)
    enqueue_actions: list[dict[str, Any]] = []
    incomplete: list[dict[str, Any]] = []
    for item in candidates:
        if len(enqueue_actions) >= limit:
            break
        key = str(item.get("key") or "")
        allowed_paths = _enqueue_source_paths(item, signals, key)
        if not _enqueue_fields_complete(item, key, allowed_paths):
            incomplete.append({"source_key": key, "reason": "INCOMPLETE_WI_FIELDS"})
            continue
        enqueue_actions.append(_enqueue_action(item, key, allowed_paths))
    return {
        "candidate_count": len(candidates),
        "enqueued_count": len(enqueue_actions),
        "skipped_incomplete": incomplete,
        "enqueue_actions": enqueue_actions,
    }


def plan_stage3_mechanical_handoffs(
    ledger: dict[str, Any],
    *,
    signals: health.ReselectSignals | None = None,
    limit: int = STAGE2_ENQUEUE_CAP,
) -> list[dict[str, Any]]:
    """Propose Stage 2 handoffs for eligible Stage 3 reconciliation items."""
    # The selector accepts CONFLICTING or DIRTY; only stage3-owned items with a
    # salvage outcome produce actions. The limit applies after those filters,
    # so Stage 1 candidates never consume handoff slots. No ledger update here.
    candidates = health.list_reselect_candidates(ledger, signals=signals)
    actions: list[dict[str, Any]] = []
    for item in candidates:
        if item.get("current_owner") != "stage3":
            continue
        if item.get("lifecycle_state") != "STAGE3_RECONCILIATION":
            continue
        if (item.get("guardrail_outcome") or "") not in health.SALVAGE_OUTCOMES:
            continue
        actions.append(
            {
                "action": "HANDOFF_MECHANICAL_TO_STAGE2",
                "source_key": item.get("key"),
                "repository": item.get("repository"),
                "pr": item.get("pr"),
                "reason": RESELECT_ENQUEUE_REASON,
                "next_action": health.MECHANICAL_RESELECT_NA,
                "note": (
                    "CAS complete Stage 2 WI + owner stage2; "
                    "do not leave mechanical CONFLICTING as WAITING_HUMAN"
                ),
            }
        )
        if len(actions) >= limit:
            break
    return actions


def _stage1_plan(
    ledger: dict[str, Any],
    config: dict[str, Any],
    *,
    signals: health.ReselectSignals | None = None,
) -> tuple[list[str], list[dict[str, Any]], str | None, str]:
    """Plan Stage 1 reconciliation and reselect enqueues plus a FEED_CHECK grade."""
    # Signals supply live mergeability, titles, and unique paths for the
    # reselect planner; candidates yielding no enqueue actions grade
    # FEED_CHECK FAIL with LOGIC_STOP.
    allowed = [
        "python3 scripts/pr_lifecycle_reconcile.py --json",
        "python3 scripts/pr_lifecycle_feed.py --json (read-only verification)",
        "gh pr view / gh pr list (read-only inventory)",
        "routine approve/squash-merge/close per lifecycle predicates",
        "CAS handoff via pr_lifecycle_ledger_cas (schema-aware only)",
        "CAS-write ≤5 complete stage2_work_items (ENQUEUE_STAGE2_WI)",
        "CLOSED_NOOP Observed-CLOSED ledger catch-up (bookkeeping; weekly ok)",
    ]
    cap = _stage_cap(config, "stage1_actions", 40)
    actions = reconcile_mod.collect_actions(ledger, config, limit=cap)
    planned = plan_stage2_enqueues(ledger, signals=signals)
    actions.extend(planned["enqueue_actions"])
    stop_class = None
    reason = "OK"
    feed_ok = not (
        planned["candidate_count"] > 0 and not planned["enqueued_count"]
    )
    if not feed_ok:
        stop_class = "LOGIC_STOP"
        reason = "FEED_CHECK_FAIL"
    actions.append(
        {
            "action": "FEED_CHECK",
            "reselect_candidates": planned["candidate_count"],
            "enqueued": planned["enqueued_count"],
            "skipped_incomplete": planned["skipped_incomplete"],
            "grade": "PASS" if feed_ok else "FAIL",
            "reason": (
                "CAS-write complete stage2_work_items when reselect stock exists; "
                "pr_lifecycle_feed.py is read-only — not enqueue"
                if feed_ok
                else (
                    "FEED_CHECK FAIL: reselect candidates > 0 but enqueued == 0 "
                    "(do not leave Stage 2 EMPTY_INTAKE theater)"
                )
            ),
        }
    )
    return allowed, actions, stop_class, reason


def _stage2_plan(
    ledger: dict[str, Any], config: dict[str, Any]
) -> tuple[list[str], list[dict[str, Any]], str | None, str, dict[str, Any]]:
    """Plan Stage 2 work after excluding never-touch feed items."""
    # Empty feed with eligible stock is LOGIC_STOP; no remaining feed items
    # emits SKIP_IF_EMPTY + skip flags, else feed + salvage actions. The result
    # also reports skipped sources and the remaining item count.
    allowed = [
        "python3 scripts/pr_lifecycle_feed.py --json",
        "open/update draft salvage PRs only (never merge/approve/close originals)",
        "CAS write complete Stage 2 work items + handoff events",
        "skip-if-empty: exit success with no docs PR when usable WI==0",
    ]
    feed = feed_mod.build_feed(
        ledger, config, limit=_stage_cap(config, "stage2_salvage_candidates", 10)
    )
    mechanical, never_touch = _filter_never_touch_work_items(
        list(feed.get("work_items") or [])
    )
    extras: dict[str, Any] = {
        "skip_cursor": False,
        "empty_intake_skip": False,
        "mechanical_candidate_count": len(mechanical),
        "never_touch_skipped": [
            {"source_key": _wi_source_key(wi), "reason": "NEVER_TOUCH"}
            for wi in never_touch
        ],
    }
    stop_class = None
    reason = "OK"
    if feed.get("empty_with_stock"):
        stop_class = "LOGIC_STOP"
        reason = "EMPTY_FEED_WITH_ELIGIBLE_STOCK"
    elif not mechanical:
        # True empty or only never-touch leftovers → success skip (no docs PR).
        reason = "EMPTY_INTAKE_SKIP"
        extras["skip_cursor"] = True
        extras["empty_intake_skip"] = True
        actions = [
            {
                "action": "SKIP_IF_EMPTY",
                "reason": (
                    "usable mechanical Stage 2 WI == 0 after never-touch filter; "
                    "exit success; do not open/push docs PR; do not launch "
                    "further agents"
                ),
                "feed_reason": feed.get("reason"),
                "work_item_count": feed.get("work_item_count"),
                "eligible_stock_count": feed.get("eligible_stock_count"),
            }
        ]
        return allowed, actions, stop_class, reason, extras
    actions = [
        {
            "action": "FEED_SUMMARY",
            "feed": {
                "reason": feed["reason"],
                "work_item_count": feed["work_item_count"],
                "eligible_stock_count": feed["eligible_stock_count"],
                "mechanical_candidate_count": len(mechanical),
            },
        }
    ]
    actions.extend(
        {"action": "SALVAGE_WI", "wi": work_item} for work_item in mechanical
    )
    return allowed, actions, stop_class, reason, extras


def _stage3_plan(
    ledger: dict[str, Any],
    *,
    signals: health.ReselectSignals | None = None,
) -> tuple[list[str], list[dict[str, Any]], str | None, str]:
    """Plan Stage 3 reconciliation, deferred CLOSED_NOOP, and handoff actions."""
    allowed = [
        "python3 scripts/pr_lifecycle_reconcile.py --json",
        "resolve advisory Codacy/qodo/CodeRabbit threads with no human reply",
        "bounded non-security completion / close per Stage 3 predicates",
        "CAS terminal transitions; never force-push",
        "HANDOFF_MECHANICAL_TO_STAGE2 for CONFLICTING HOLD_CONTRACT remainder",
        "calibration remains DISABLED — do not reset or enable it",
    ]
    actions = [
        {
            "action": "RECONCILE_REMAINDER",
            "reason": "re-read predicates; builder ≠ merger",
        },
        {
            "action": "ADVISORY_BOT_THREADS",
            "reason": (
                "Codacy/qodo/CodeRabbit threads with no human reply are "
                "advisory; may resolve before /trunk (Abhi 2026-09-21)"
            ),
        },
        {
            "action": "CLOSED_NOOP_DEFERRED",
            "reason": (
                "Observed-CLOSED CLOSED_NOOP is Stage 1 reconcile bookkeeping "
                "or weekly archive — do not spend Stage 3 daily completion cap"
            ),
        },
    ]
    actions.extend(plan_stage3_mechanical_handoffs(ledger, signals=signals))
    return allowed, actions, None, "OK"


def build_stage_plan(
    stage: int,
    ledger: dict[str, Any],
    config: dict[str, Any],
    *,
    signals: health.ReselectSignals | None = None,
) -> dict[str, Any]:
    """Build a stage plan with health, permitted commands, and planned actions."""
    # Signals apply only to Stage 1; an invalid stage yields LOGIC_STOP with no
    # permitted commands or actions.
    report = health.summarize(ledger)
    extras: dict[str, Any] = {}
    if stage == 1:
        allowed, actions, stop_class, reason = _stage1_plan(
            ledger, config, signals=signals
        )
    elif stage == 2:
        allowed, actions, stop_class, reason, extras = _stage2_plan(ledger, config)
    elif stage == 3:
        allowed, actions, stop_class, reason = _stage3_plan(
            ledger, signals=signals
        )
    else:
        allowed, actions = [], []
        stop_class = "LOGIC_STOP"
        reason = f"invalid stage {stage}"

    plan = {
        "stage": stage,
        "generated_at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ledger_revision": ledger.get("ledger_revision"),
        "pipeline_health": {
            "salvage_eligible_count": report.salvage_eligible_count,
            "stage2_work_item_count": report.stage2_work_item_count,
            "starvation": report.starvation,
            "reason": report.reason,
        },
        "allowed_commands": allowed,
        "actions": actions,
        "calibration_enabled": False,
        "stage2_may_merge": False,
        "stop_class": stop_class,
        "reason": reason,
    }
    plan.update(extras)
    return plan


def write_status_doc(plan: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Build the compact status document for a stage plan."""
    return {
        "updated_at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": run_id,
        "stage": plan.get("stage"),
        "ledger_revision": plan.get("ledger_revision"),
        "reason": plan.get("reason"),
        "stop_class": plan.get("stop_class"),
        "pipeline_health": plan.get("pipeline_health"),
        "action_count": len(plan.get("actions") or []),
        "calibration_enabled": False,
    }


def _issue_body(status: dict[str, Any]) -> str:
    """Render the pinned status-issue body for a stage status dict."""
    return (
        f"<!-- pr-lifecycle-status -->\n"
        f"updated_at_utc: {status['updated_at_utc']}\n"
        f"run_id: {status.get('run_id') or ''}\n"
        f"stage: {status.get('stage') or ''}\n"
        f"ledger_revision: {status.get('ledger_revision') or ''}\n"
        f"reason: {status.get('reason') or ''}\n"
        f"stop_class: {status.get('stop_class') or ''}\n"
        f"calibration_enabled: false\n"
        f"\n```json\n{json.dumps(status, indent=2, sort_keys=True)}\n```\n"
    )


def _gh_issue(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", "issue", *cmd, "--repo", "abhimehro/personal-config"],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _find_pinned_issue() -> int | None:
    listed = _gh_issue(
        [
            "list",
            "--search",
            f'in:title "{PINNED_ISSUE_TITLE}"',
            "--json",
            "number,title",
            "--limit",
            "20",
        ]
    )
    if listed.returncode != 0 or not listed.stdout.strip():
        return None
    try:
        rows = json.loads(listed.stdout)
    except json.JSONDecodeError:
        return None
    for row in rows:
        if row.get("title") == PINNED_ISSUE_TITLE:
            number = row.get("number")
            return int(number) if number is not None else None
    return None


def _upsert_pinned_issue(issue_number: int | None, body: str) -> None:
    if issue_number is not None:
        result = _gh_issue(["edit", str(issue_number), "--body", body])
    else:
        result = _gh_issue(["create", "--title", PINNED_ISSUE_TITLE, "--body", body])
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()[:200]
        raise OSError(f"gh issue update failed rc={result.returncode}: {stderr}")


def update_pinned_issue(status: dict[str, Any]) -> None:
    """Best-effort update of the pinned PR pipeline status issue."""
    _upsert_pinned_issue(_find_pinned_issue(), _issue_body(status))


def run_stage(stage: int, *, dry_run: bool, write_status: bool) -> int:
    """Fetch the ledger, emit and log a plan, and optionally write status."""
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    run_id = _run_id()
    log_path = LOG_DIR / f"{run_id}.jsonl"
    try:
        with tempfile.TemporaryDirectory(prefix="pr-lifecycle-run-") as tmp:
            out = Path(tmp) / "ledger.yaml"
            fetch = cas.run_preflight(out)
            ledger = load_yaml(Path(fetch["ledger_path"]))
            plan = build_stage_plan(stage, ledger, config)
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        # OSError covers fetch/service failures (recoverable); data-shape and
        # validation failures are repo-owned and cannot heal by retrying.
        stop_class = "TRANSIENT_RETRY" if isinstance(exc, OSError) else "LOGIC_STOP"
        record = {
            "run_id": run_id,
            "stage": stage,
            "stop_class": stop_class,
            "error": type(exc).__name__,
            "at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _append_jsonl(log_path, record)
        print(json.dumps(record, indent=2, sort_keys=True))
        return 1

    plan["run_id"] = run_id
    plan["dry_run"] = dry_run
    plan["log_path"] = str(log_path)
    _append_jsonl(log_path, {"event": "plan", **plan})
    print(json.dumps(plan, indent=2, sort_keys=True))

    if write_status:
        status = write_status_doc(plan, run_id)
        # Local mirror for agents; live branch update is a Stage ops concern.
        local_status = LOG_DIR / STATUS_PATH_ON_BRANCH
        local_status.parent.mkdir(parents=True, exist_ok=True)
        local_status.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        _append_jsonl(log_path, {"event": "status", **status})

    if plan.get("stop_class") == "LOGIC_STOP":
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the lifecycle stage-runner command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", type=int, choices=[1, 2, 3], help="Stage to preflight"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print plan only (default)",
    )
    parser.add_argument(
        "--write-status",
        action="store_true",
        help="Write /tmp/pr-lifecycle/status.json for this run",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Update the pinned PR pipeline status GitHub issue",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a stage preflight or refresh the pinned status issue."""
    args = build_parser().parse_args(argv)
    try:
        if args.status:
            status = {
                "updated_at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "run_id": _run_id(),
                "stage": None,
                "reason": "manual --status refresh",
                "calibration_enabled": False,
            }
            update_pinned_issue(status)
            print(json.dumps(status, indent=2, sort_keys=True))
            return 0
        if args.stage is None:
            print("PR_LIFECYCLE_RUN_ERROR: --stage is required", file=sys.stderr)
            return 1
        return run_stage(
            args.stage, dry_run=args.dry_run, write_status=args.write_status
        )
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PR_LIFECYCLE_RUN_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
