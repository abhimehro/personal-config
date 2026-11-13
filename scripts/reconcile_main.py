"""Main CLI and orchestration for PR lifecycle reconciliation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pr_lifecycle_config import validate_config
from pr_lifecycle_github_http import OPERATOR_CONFLICT, CasError
from pr_lifecycle_open_inventory import list_open_prs
from pr_lifecycle_persist import dump_ledger
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

from .reconcile_actions import (
    _action_for_item,
    _build_author,
    _build_changed_paths,
    _duplicate_terminal_actions,
    _live_items,
    build_intake_item,
    collect_ingest_actions,
    guards,
    ledger_mod,
)
from .reconcile_github import _gh_pr_view
from .reconcile_ledger import ReconcileSkip, _prepare_live_head


DEFAULT_EXPIRY_DAYS = 7
STALE_LABEL = "stale-auto-closed"
STALE_COMMENT = (
    "Closing as stale: WAITING_HUMAN BOT packet older than "
    "packet_expiry_close_days with no REVIEW_SECURITY hold "
    "(policy 2026-09-21). Re-open or comment if this should stay open."
)
DEFAULT_COMMIT_MESSAGE = "reconcile: apply lifecycle actions"


@dataclass(frozen=True)
class StalePolicy:
    """Inputs shared across stale-item classification."""

    expiry_days: int
    now: datetime
    exclusions: frozenset[tuple[str | None, int]] = frozenset()


@dataclass
class ApplyPlanContext:
    """Context for applying the reconciliation plan."""

    plan: dict[str, Any]
    ledger: dict[str, Any]
    actions: list[dict[str, Any]]
    cap: int
    json_out: bool


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def _parse_utc(value: object) -> datetime | None:
    """Parse a Z-suffixed timestamp as UTC, or return None if invalid."""
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError:
        return None


def _expiry_days(config: dict[str, Any]) -> int:
    """Return the configured positive packet expiry or the default."""
    lifecycle = config.get("lifecycle") or {}
    raw = lifecycle.get("packet_expiry_close_days", DEFAULT_EXPIRY_DAYS)
    if not isinstance(raw, int) or raw < 1:
        return DEFAULT_EXPIRY_DAYS
    return raw


def _event_id(prefix: str) -> str:
    """Generate a unique timestamped event identifier."""
    stamp = _utc_now().strftime("%Y%m%d%H%M%S")
    return f"evt-{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


def _build_transition_projection(item: dict[str, Any]) -> dict[str, Any]:
    """Build the projected state for a transition."""
    return {
        "revision": int(item["revision"]),
        "lifecycle_state": item["lifecycle_state"],
        "current_owner": item["current_owner"],
        "next_owner": item["next_owner"],
        "terminal_disposition": item.get("terminal_disposition"),
        "handoffs": list(item.get("handoffs") or []),
        "latest_transition": None,
        "latest_transition_kind": None,
    }


def _update_item_from_projection(item: dict[str, Any], projected: dict[str, Any]) -> None:
    """Update the item from the projected state."""
    item["revision"] = projected["revision"]
    item["lifecycle_state"] = projected["lifecycle_state"]
    item["current_owner"] = projected["current_owner"]
    item["next_owner"] = projected["next_owner"]
    item["terminal_disposition"] = projected["terminal_disposition"]
    item["handoffs"] = projected["handoffs"]


def _apply_drift_fields_if_needed(item: dict[str, Any], action: dict[str, Any]) -> None:
    """Apply drift fields if the action is SHA_DRIFT_REINTAKE."""
    if action.get("action") == "SHA_DRIFT_REINTAKE":
        _apply_drift_fields(item, action)


def _set_next_action_if_needed(item: dict[str, Any], action: dict[str, Any]) -> None:
    """Set the next action if the action is TERMINAL_PENDING."""
    if action.get("action") == "TERMINAL_PENDING":
        item["next_action"] = (
            f"Observed {action.get('observed_state')} unclassified; "
            "Stage 3 classification required."
        )


def _build_transition_event(
    item: dict[str, Any], action: dict[str, Any], kind: str
) -> dict[str, Any]:
    """Build a projected ledger transition event for a reconcile action."""
    to_state = action["to_state"]
    disposition = action.get("disposition")
    reason = str(action.get("reason") or "reconcile")
    event_id = _event_id("reconcile")
    item_key = item["key"]
    from_state = item["lifecycle_state"]
    from_owner = item["current_owner"]
    to_owner = "stage1" if to_state == "STAGE1_INTAKE" else "stage3"
    next_owner = "none" if to_state == "TERMINAL" else to_owner
    expected = int(item["revision"])
    return {
        "event_id": event_id,
        "kind": kind,
        "item_key": item_key,
        "from_owner": from_owner,
        "to_owner": to_owner,
        "from_state": from_state,
        "to_state": to_state,
        "next_owner": next_owner,
        "terminal_disposition": disposition,
        "parent_event_id": None,
        "expected_item_revision": expected,
        "resulting_item_revision": expected + 1,
        "idempotency_key": f"{item_key}:{event_id}",
        "status": "PROJECTED",
        "created_at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "acknowledged_at_utc": None,
        "reason": reason,
        "successful": None,
        "policy_revision": None,
    }


def _handle_transition_event(
    ledger: dict[str, Any], event: dict[str, Any]
) -> None:
    """Handle the transition event by appending it to the ledger."""
    events = ledger.setdefault("events", [])
    events.append(event)
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1


def _handle_transition(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> dict[str, Any]:
    """Handle transition actions."""
    to_state = action["to_state"]
    kind = "TERMINAL" if to_state == "TERMINAL" else "HANDOFF"
    event = _build_transition_event(item, action, kind)
    projected = _build_transition_projection(item)
    ledger_mod.apply_transition(event, projected)
    _update_item_from_projection(item, projected)
    item["updated_at_utc"] = event["created_at_utc"]
    _apply_drift_fields_if_needed(item, action)
    _set_next_action_if_needed(item, action)
    _handle_transition_event(ledger, event)
    return event


def _keep_sentinel_marker(item: dict[str, Any], text: str) -> str:
    """Keep a stamped Sentinel hold when another action rewrites next_action."""
    prior = str(item.get("next_action") or "")
    if guards.SENTINEL_HOLD_MARKER not in prior:
        return text
    if guards.SENTINEL_HOLD_MARKER in text:
        return text
    return f"{text} {guards.SENTINEL_HOLD_MARKER} remains in effect."


def _apply_drift_fields(item: dict[str, Any], action: dict[str, Any]) -> None:
    live_head = action.get("live_head_sha")
    if live_head and live_head == item.get("head_sha"):
        item["next_action"] = _keep_sentinel_marker(
            item,
            f"Re-anchor intake to live head {live_head}; prior evidence void.",
        )
    live_base = action.get("live_base_sha")
    if live_base:
        item["base_sha"] = live_base


def _handle_reanchor_head(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> dict[str, Any]:
    """Handle the REANCHOR_HEAD action."""
    live_base = action.get("live_base_sha")
    if live_base:
        item["base_sha"] = live_base
    item["updated_at_utc"] = _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    item["next_action"] = _keep_sentinel_marker(
        item,
        f"Re-anchored to live head {item.get('head_sha')}; prior evidence void.",
    )
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    return {"event_id": None}


def _handle_terminal_observed(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> dict[str, Any]:
    """Handle the TERMINAL_OBSERVED action."""
    item["updated_at_utc"] = _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    item["next_action"] = str(action.get("reason") or "Observed unclassified")
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    return {"event_id": None}


def _handle_backfill_paths(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> dict[str, Any]:
    """Handle the BACKFILL_PATHS action."""
    paths = sorted({str(path) for path in action.get("paths") or [] if str(path)})
    if not paths:
        raise ReconcileSkip("backfill_empty_paths")
    if item.get("changed_paths") == paths:
        raise ReconcileSkip("backfill_noop")
    item["changed_paths"] = paths
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    return {"event_id": None}


def _handle_security_action(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> dict[str, Any]:
    """Handle security-related actions."""
    from .reconcile_actions import _reclassify_title_security_item, _hold_sentinel_security_item
    if action.get("action") == "RECLASSIFY_TITLE_SECURITY":
        return _reclassify_title_security_item(ledger, item, action)
    return _hold_sentinel_security_item(ledger, item, action)


def apply_action_to_ledger(
    ledger: dict[str, Any],
    item: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    """Apply an action to the item and ledger in memory.

    Return the appended transition event, or {"event_id": None} for an
    in-place action that leaves item revision unchanged. ReconcileSkip
    propagates when an anchor is blocked or an in-place action has no work.
    """
    _prepare_live_head(ledger, item, action)
    if action.get("action") == "REANCHOR_HEAD":
        return _handle_reanchor_head(ledger, item, action)
    if action.get("action") == "TERMINAL_OBSERVED":
        return _handle_terminal_observed(ledger, item, action)
    if action.get("action") == "BACKFILL_PATHS":
        return _handle_backfill_paths(ledger, item, action)
    if action.get("action") in {
        "RECLASSIFY_TITLE_SECURITY",
        "HOLD_SENTINEL_SECURITY",
    }:
        return _handle_security_action(ledger, item, action)
    return _handle_transition(ledger, item, action)


def _build_inventory_failed(config: dict[str, Any], exc: OSError) -> list[dict[str, Any]]:
    """Build inventory failed actions for each repo."""
    return [
        {
            "action": "INVENTORY_FAILED",
            "repository": repo,
            "reason": f"inventory failed: {type(exc).__name__}",
        }
        for repo in config.get("repos") or []
    ]


def _build_plan(
    config: dict[str, Any],
    out: Path,
    limit: int | None,
    ingest: bool,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Build the reconciliation plan, ledger, and actions."""
    try:
        open_prs_by_repo = list_open_prs(config) if ingest else {}
    except OSError as exc:
        open_prs_by_repo = {}
        inventory_failed = _build_inventory_failed(config, exc)
    else:
        inventory_failed = []

    fetch = cas.run_preflight(out)
    ledger = load_yaml(Path(fetch["ledger_path"]))
    actions = collect_actions(ledger, config, limit=limit)
    if ingest:
        ingest_actions = collect_ingest_actions(ledger, config, open_prs_by_repo, now=_utc_now())
        actions.extend(ingest_actions)
    plan = {
        "dry_run": True,
        "ledger_revision": ledger.get("ledger_revision"),
        "actions": actions,
        "inventory_failed": inventory_failed,
    }
    return plan, ledger, actions


def _apply_actions(
    ledger: dict[str, Any], actions: list[dict[str, Any]], cap: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply actions to the ledger, returning applied and deferred actions."""
    applied = []
    deferred = []
    for action in actions:
        if len(applied) >= cap:
            deferred.append(action)
            continue
        try:
            event = apply_action_to_ledger(ledger, _item_for_action(ledger, action), action)
        except ReconcileSkip:
            continue
        applied.append(action)
    return applied, deferred


def _handle_cas_conflict(ctx: ApplyPlanContext, attempt: int) -> int:
    """Handle CAS conflict and retry if possible."""
    if attempt < 3:
        time.sleep(0.5 * attempt)
        return _apply_plan(ctx)
    ctx.plan["aborted"] = OPERATOR_CONFLICT
    _emit(ctx.plan, ctx.json_out)
    return 4


def _apply_plan(ctx: ApplyPlanContext) -> int:
    """Apply the reconciliation plan and handle CAS commits."""
    attempt = 0
    while True:
        attempt += 1
        with tempfile.TemporaryDirectory(prefix="pr-lifecycle-reconcile-") as tmp:
            out = Path(tmp) / "ledger.yaml"
            applied, deferred = _apply_actions(ctx.ledger, ctx.actions, ctx.cap)
            ctx.plan["deferred_count"] = len(deferred)
            ctx.plan["applied_count"] = len(applied)
            dump_ledger(ctx.ledger, out)
            try:
                cas_result = _commit_cas_with_retry(out, attempt)
            except CasError:
                return _handle_cas_conflict(ctx, attempt)
            ctx.plan["cas"] = cas_result
            _emit(ctx.plan, ctx.json_out)
            return 0


def _item_for_action(ledger: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    """Return the ledger item for an action, or raise ReconcileSkip."""
    key = str(action.get("key") or "")
    for item in ledger.get("items") or []:
        if isinstance(item, dict) and item.get("key") == key:
            return item
    raise ReconcileSkip("item_not_found")


def run_reconcile(
    *,
    apply: bool,
    limit: int | None,
    json_out: bool,
    ingest: bool = True,
) -> int:
    """Fetch and emit actions, optionally applying and CAS-committing them."""
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    cap = guards.max_apply_from_env()

    with tempfile.TemporaryDirectory(prefix="pr-lifecycle-reconcile-") as tmp:
        out = Path(tmp) / "ledger.yaml"
        plan, ledger, actions = _build_plan(config, out, limit, ingest)
        plan["dry_run"] = not apply
        if not apply:
            _emit(plan, json_out)
            return 0
        if plan["inventory_failed"]:
            plan["aborted"] = "INVENTORY_FAILED"
            _emit(plan, json_out)
            return 3
        ctx = ApplyPlanContext(plan, ledger, actions, cap, json_out)
        return _apply_plan(ctx)


def _emit_plan_text(plan: dict[str, Any]) -> None:
    """Emit the plan as concise text."""
    print(f"dry_run={plan['dry_run']} actions={len(plan.get('actions', []))}")
    if plan.get("inventory_failed"):
        print(f"inventory_failed={len(plan['inventory_failed'])}")
    if plan.get("deferred_count"):
        print(f"deferred_count={plan['deferred_count']}")
    if plan.get("applied_count"):
        print(f"applied_count={plan['applied_count']}")
    if plan.get("aborted"):
        print(f"aborted={plan['aborted']}")
    if plan.get("cas"):
        print(f"ledger_commit={plan['cas']['commit_sha'][:12]}")


def _emit(plan: dict[str, Any], json_out: bool) -> None:
    """Print the plan as JSON or concise text."""
    if json_out:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        _emit_plan_text(plan)


def build_parser() -> argparse.ArgumentParser:
    """Build the reconcile command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-ingest", dest="ingest", action="store_false")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the reconcile CLI, returning 1 for expected operational errors."""
    args = build_parser().parse_args(argv)
    try:
        return run_reconcile(
            apply=args.apply, limit=args.limit, json_out=args.json, ingest=args.ingest
        )
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PR_LIFECYCLE_RECONCILE_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())