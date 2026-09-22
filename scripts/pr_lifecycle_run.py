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
    return datetime.now(timezone.utc)


def _run_id() -> str:
    stamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def build_stage_plan(
    stage: int,
    ledger: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build the exact action plan a stage agent may execute."""
    report = health.summarize(ledger)
    allowed: list[str] = []
    actions: list[dict[str, Any]] = []
    stop_class = None
    reason = "OK"

    if stage == 1:
        allowed = [
            "python3 scripts/pr_lifecycle_reconcile.py --json",
            "python3 scripts/pr_lifecycle_feed.py --json",
            "gh pr view / gh pr list (read-only inventory)",
            "routine approve/squash-merge/close per lifecycle predicates",
            "CAS handoff via pr_lifecycle_ledger_cas (schema-aware only)",
        ]
        actions = reconcile_mod.collect_actions(ledger, config, limit=40)
        actions.append(
            {
                "action": "FEED_CHECK",
                "reason": "ensure Stage 2 intake is non-empty when eligible stock exists",
            }
        )
    elif stage == 2:
        allowed = [
            "python3 scripts/pr_lifecycle_feed.py --json",
            "open/update draft salvage PRs only (never merge/approve/close originals)",
            "CAS write complete Stage 2 work items + handoff events",
        ]
        feed = feed_mod.build_feed(ledger, config)
        if feed.get("empty_with_stock"):
            stop_class = "LOGIC_STOP"
            reason = "EMPTY_FEED_WITH_ELIGIBLE_STOCK"
        actions = [
            {"action": "SALVAGE_WI", "wi": wi} for wi in feed.get("work_items") or []
        ]
        actions.insert(
            0,
            {
                "action": "FEED_SUMMARY",
                "feed": {
                    "reason": feed["reason"],
                    "work_item_count": feed["work_item_count"],
                    "eligible_stock_count": feed["eligible_stock_count"],
                },
            },
        )
    elif stage == 3:
        allowed = [
            "python3 scripts/pr_lifecycle_reconcile.py --json",
            "resolve advisory Codacy/qodo/CodeRabbit threads with no human reply",
            "bounded non-security completion / close per Stage 3 predicates",
            "CAS terminal transitions; never force-push",
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
        ]
    else:
        stop_class = "LOGIC_STOP"
        reason = f"invalid stage {stage}"

    return {
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


def write_status_doc(plan: dict[str, Any], run_id: str) -> dict[str, Any]:
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


def update_pinned_issue(status: dict[str, Any]) -> None:
    """Best-effort update of the pinned PR pipeline status issue."""
    body = (
        f"<!-- pr-lifecycle-status -->\n"
        f"updated_at_utc: {status['updated_at_utc']}\n"
        f"run_id: {status.get('run_id')}\n"
        f"stage: {status.get('stage')}\n"
        f"ledger_revision: {status.get('ledger_revision')}\n"
        f"reason: {status.get('reason')}\n"
        f"stop_class: {status.get('stop_class')}\n"
        f"calibration_enabled: false\n"
        f"\n```json\n{json.dumps(status, indent=2, sort_keys=True)}\n```\n"
    )
    # Find existing issue by title; create if missing.
    import subprocess

    listed = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            "abhimehro/personal-config",
            "--search",
            f'in:title "{PINNED_ISSUE_TITLE}"',
            "--json",
            "number,title",
            "--limit",
            "5",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    issue_number = None
    if listed.returncode == 0 and listed.stdout.strip():
        try:
            rows = json.loads(listed.stdout)
        except json.JSONDecodeError:
            rows = []
        for row in rows:
            if row.get("title") == PINNED_ISSUE_TITLE:
                issue_number = row.get("number")
                break
    if issue_number:
        subprocess.run(
            [
                "gh",
                "issue",
                "edit",
                str(issue_number),
                "--repo",
                "abhimehro/personal-config",
                "--body",
                body,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    else:
        subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                "abhimehro/personal-config",
                "--title",
                PINNED_ISSUE_TITLE,
                "--body",
                body,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )


def run_stage(stage: int, *, dry_run: bool, write_status: bool) -> int:
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
        record = {
            "run_id": run_id,
            "stage": stage,
            "stop_class": "TRANSIENT_RETRY",
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
