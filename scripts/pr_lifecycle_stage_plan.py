#!/usr/bin/env python3
"""Stage plan builders for the PR lifecycle runner.

Translates a fetched ledger plus live reselect signals into the permitted
commands, proposed actions, stop class, and reason for each stage. Plans are
proposals only: nothing here executes commands or writes the ledger.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pr_lifecycle_feed as feed_mod  # noqa: E402
import pr_lifecycle_pipeline_health as health  # noqa: E402
import pr_lifecycle_reconcile as reconcile_mod  # noqa: E402
from pr_lifecycle_reselect_signals import SignalsResult  # noqa: E402

STAGE2_ENQUEUE_CAP = 5
RESELECT_ENQUEUE_REASON = "CONFLICTING_UNIQUE_RESELECT"


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def _stage_cap(config: dict[str, Any], name: str, default: int) -> int:
    raw = (config.get("lifecycle") or {}).get("stage_caps") or {}
    value = raw.get(name, default)
    if not isinstance(value, int) or value < 1:
        return default
    return value


def _wi_source_key(work_item: dict[str, Any]) -> str:
    """Get a feed item's source_key or source_item_key, or an empty string."""
    return str(work_item.get("source_key") or work_item.get("source_item_key") or "")


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
    paths = list(item.get("changed_paths") or item.get("paths") or [])
    unique = health.signal_value(signals.unique_paths_by_key, key)
    if unique is not None:
        paths = list(unique)
    return health.non_journal_paths([str(path) for path in paths])


def _enqueue_action(
    item: dict[str, Any],
    key: str,
    allowed_paths: list[str],
    live_base_sha: str | None = None,
) -> dict[str, Any]:
    """Build one ENQUEUE_STAGE2_WI plan action for a reselect candidate.

    The base anchor prefers the fetched live base (baseRefOid tracks the
    moving tip of the base branch) and falls back to the ledger anchor.
    """
    return {
        "action": "ENQUEUE_STAGE2_WI",
        "source_key": key,
        "repository": item.get("repository"),
        "pr": item.get("pr"),
        "base_sha": live_base_sha or item.get("base_sha"),
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
    # Stage 3 owns its handoff items; Stage 1 must not re-enqueue them.
    stage1_candidates = [
        item for item in candidates if item.get("current_owner") != "stage3"
    ]
    enqueue_actions: list[dict[str, Any]] = []
    incomplete: list[dict[str, Any]] = []
    for item in stage1_candidates:
        if len(enqueue_actions) >= limit:
            break
        key = str(item.get("key") or "")
        allowed_paths = _enqueue_source_paths(item, signals, key)
        if not _enqueue_fields_complete(item, key, allowed_paths):
            incomplete.append({"source_key": key, "reason": "INCOMPLETE_WI_FIELDS"})
            continue
        enqueue_actions.append(
            _enqueue_action(
                item,
                key,
                allowed_paths,
                live_base_sha=health.signal_value(signals.live_base_sha_by_key, key),
            )
        )
    return {
        "candidate_count": len(stage1_candidates),
        "enqueued_count": len(enqueue_actions),
        "skipped_incomplete": incomplete,
        "enqueue_actions": enqueue_actions,
    }


def _stage3_handoff_eligible(item: dict[str, Any]) -> bool:
    """Return True for stage3-owned reconciliation items with a salvage outcome."""
    return (
        item.get("current_owner") == "stage3"
        and item.get("lifecycle_state") == "STAGE3_RECONCILIATION"
        and (item.get("guardrail_outcome") or "") in health.SALVAGE_OUTCOMES
    )


def _handoff_action(
    item: dict[str, Any],
    allowed_paths: list[str],
    live_base_sha: str | None = None,
) -> dict[str, Any]:
    """Build one HANDOFF_MECHANICAL_TO_STAGE2 plan action with WI anchors.

    The base anchor prefers the fetched live base over the ledger anchor.
    """
    return {
        "action": "HANDOFF_MECHANICAL_TO_STAGE2",
        "source_key": item.get("key"),
        "repository": item.get("repository"),
        "pr": item.get("pr"),
        "base_sha": live_base_sha or item.get("base_sha"),
        "head_sha": item.get("head_sha"),
        "allowed_paths": allowed_paths,
        "reason": RESELECT_ENQUEUE_REASON,
        "next_action": health.MECHANICAL_RESELECT_NA,
        "note": (
            "CAS complete Stage 2 WI + owner stage2; "
            "do not leave mechanical CONFLICTING as WAITING_HUMAN"
        ),
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
    # so Stage 1 candidates never consume handoff slots. Handoffs carry the same
    # verified unique paths and SHA anchors as Stage 1 enqueues — an action
    # without them could not assemble the complete WI it requests, so
    # incomplete items stay Stage-3-owned for evidence gathering instead.
    # No ledger update here.
    signals = signals or health.ReselectSignals()
    candidates = health.list_reselect_candidates(ledger, signals=signals)
    actions: list[dict[str, Any]] = []
    for item in candidates:
        if not _stage3_handoff_eligible(item):
            continue
        key = str(item.get("key") or "")
        allowed_paths = _enqueue_source_paths(item, signals, key)
        if not _enqueue_fields_complete(item, key, allowed_paths):
            continue
        actions.append(
            _handoff_action(
                item,
                allowed_paths,
                live_base_sha=health.signal_value(signals.live_base_sha_by_key, key),
            )
        )
        if len(actions) >= limit:
            break
    return actions


def _stage1_plan(
    ledger: dict[str, Any],
    config: dict[str, Any],
    *,
    signals: health.ReselectSignals | None = None,
    signals_status: str | None = None,
) -> tuple[list[str], list[dict[str, Any]], str | None, str]:
    """Plan Stage 1 reconciliation and reselect enqueues plus a FEED_CHECK grade.

    Return permitted commands, action proposals, stop class, and reason.
    If candidate_count > 0 with enqueued_count == 0, yield LOGIC_STOP/FEED_CHECK_FAIL.
    Individual skipped/incomplete candidates are counted in skipped_incomplete
    but do not independently trigger the stop. PARTIAL or DEGRADED signals_status
    annotates the feed check without independently changing its grade or stop class.
    """
    # Signals supply live mergeability, titles, and unique paths for the
    # reselect planner; aggregate candidate_count > 0 with enqueued_count == 0
    # grades FEED_CHECK FAIL with LOGIC_STOP.
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
    feed_ok = not (planned["candidate_count"] > 0 and not planned["enqueued_count"])
    if not feed_ok:
        stop_class = "LOGIC_STOP"
        reason = "FEED_CHECK_FAIL"
    feed_check_action: dict[str, Any] = {
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
    if signals_status is not None:
        feed_check_action["signals_status"] = signals_status
    if signals_status in {"DEGRADED", "PARTIAL"}:
        feed_check_action["condition"] = "SIGNALS_DEGRADED"
    actions.append(feed_check_action)
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
    cap = _stage_cap(config, "stage2_salvage_candidates", 10)
    # Build the complete feed so never-touch entries cannot hide usable salvage
    # items. Apply the candidate cap only after filtering those entries out.
    feed = feed_mod.build_feed(ledger, config)
    mechanical, never_touch = _filter_never_touch_work_items(
        list(feed.get("work_items") or [])
    )
    mechanical = mechanical[:cap]
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
    if not mechanical and feed.get("non_never_touch_stock_count", 0) > 0:
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


def _dispatch_stage_plan(
    stage: int,
    ledger: dict[str, Any],
    config: dict[str, Any],
    signals_result: SignalsResult,
) -> tuple[list[str], list[dict[str, Any]], str | None, str, dict[str, Any]]:
    """Route the stage to its planner; invalid stages fail closed."""
    if stage == 1:
        plan = _stage1_plan(
            ledger,
            config,
            signals=signals_result.signals,
            signals_status=signals_result.status,
        )
    elif stage == 3:
        plan = _stage3_plan(ledger, signals=signals_result.signals)
    elif stage == 2:
        return _stage2_plan(ledger, config)
    else:
        plan = ([], [], "LOGIC_STOP", f"invalid stage {stage}")
    return (*plan, {})


def _cause_clauses(result: SignalsResult) -> list[str]:
    """Accumulate one clause per degradation cause actually present.

    Causes co-occur (failed queries burn the budget; a hard abort leaves
    survivors unqueried; view successes can coincide with a total `gh api`
    outage), so first-match-wins would hide whichever cause sorts second.
    """
    clauses: list[str] = []
    if result.failed_keys:
        clauses.append(
            "ledger fallbacks in effect, title-gated items invisible for failed keys"
        )
    if result.timed_out:
        clauses.append(
            "live scan truncated by total budget after "
            f"{result.queried_count} attempted queries, unqueried keys use "
            "ledger values"
        )
    if result.status == "DEGRADED":
        clauses.append("scan aborted, all unqueried keys use ledger values")
    scanned_ok = result.queried_count - len(result.failed_keys)
    if scanned_ok > 0 and result.base_enriched_count == 0:
        clauses.append(
            f"live base anchors missing (0/{scanned_ok} enriched), "
            "no view failures among them"
        )
    return clauses


def _degraded_note(result: SignalsResult) -> str:
    """Join the degradation causes into the SIGNALS_DEGRADED action note."""
    clauses = _cause_clauses(result)
    if clauses:
        return " | ".join(clauses)
    return "live signal query unavailable; all keys use ledger values"


def _has_degraded_action(actions: list[dict[str, Any]]) -> bool:
    """Whether the plan already carries a SIGNALS_DEGRADED action."""
    return any(
        isinstance(a, dict) and a.get("action") == "SIGNALS_DEGRADED" for a in actions
    )


def _annotate_degraded_signals(
    actions: list[dict[str, Any]], result: SignalsResult
) -> None:
    """Append the informational SIGNALS_DEGRADED action once per plan."""
    if result.status not in {"DEGRADED", "PARTIAL"} or _has_degraded_action(actions):
        return
    actions.append(
        {
            "action": "SIGNALS_DEGRADED",
            "status": result.status,
            "note": _degraded_note(result),
        }
    )


def build_stage_plan(
    stage: int,
    ledger: dict[str, Any],
    config: dict[str, Any],
    *,
    signals_result: SignalsResult | None = None,
) -> dict[str, Any]:
    """Build a stage plan with health, permitted commands, and planned actions.

    signals_result informs the health reselect count and Stage 1/3 action
    selection. Its status is descriptive: PARTIAL/DEGRADED adds an
    informational action and condition without changing stop classification
    or discarding supplied signals. Invalid stages return LOGIC_STOP.
    Proposed commands and actions are not executed.
    """
    # Signals apply only to Stage 1 and Stage 3; an invalid stage yields
    # LOGIC_STOP with no permitted commands or actions.
    result = signals_result or SignalsResult(status="SKIPPED")
    signals_status = result.status
    report = health.summarize(ledger, signals=result.signals)
    allowed, actions, stop_class, reason, extras = _dispatch_stage_plan(
        stage, ledger, config, result
    )
    _annotate_degraded_signals(actions, result)

    plan = {
        "stage": stage,
        "generated_at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ledger_revision": ledger.get("ledger_revision"),
        "pipeline_health": {
            "salvage_eligible_count": report.salvage_eligible_count,
            "stage2_work_item_count": report.stage2_work_item_count,
            "reselect_candidate_count": getattr(report, "reselect_candidate_count", 0),
            "starvation": report.starvation,
            "reason": report.reason,
        },
        "allowed_commands": allowed,
        "actions": actions,
        "calibration_enabled": False,
        "stage2_may_merge": False,
        "signals_status": signals_status,
        "stop_class": stop_class,
        "reason": reason,
    }
    if signals_status in {"DEGRADED", "PARTIAL"}:
        plan["condition"] = "SIGNALS_DEGRADED"
    plan.update(extras)
    return plan
