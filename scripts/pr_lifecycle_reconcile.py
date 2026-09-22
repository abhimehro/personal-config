#!/usr/bin/env python3
"""Reconcile non-terminal ledger items against live GitHub PR state.

Dry-run by default. ``--apply`` uses schema-aware CAS via
``pr_lifecycle_ledger_cas.run_commit`` and
``pr_lifecycle_ledger.apply_transition`` (never raw YAML string replace).
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
import pr_lifecycle_ledger as ledger_mod
import pr_lifecycle_ledger_cas as cas
from pr_lifecycle_config import validate_config
from pr_lifecycle_persist import dump_ledger, strip_in_memory_item_fields
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

DEFAULT_EXPIRY_DAYS = 7
STALE_LABEL = "stale-auto-closed"
STALE_COMMENT = (
    "Closing as stale: WAITING_HUMAN BOT packet older than "
    "packet_expiry_close_days with no REVIEW_SECURITY hold "
    "(policy 2026-09-21). Re-open or comment if this should stay open."
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError:
        return None


def _expiry_days(config: dict[str, Any]) -> int:
    lifecycle = config.get("lifecycle") or {}
    raw = lifecycle.get("packet_expiry_close_days", DEFAULT_EXPIRY_DAYS)
    if not isinstance(raw, int) or raw < 1:
        return DEFAULT_EXPIRY_DAYS
    return raw


def _gh_pr_view(repo: str, pr: int) -> dict[str, Any] | None:
    cmd = [
        "gh",
        "pr",
        "view",
        str(pr),
        "--repo",
        repo,
        "--json",
        "state,mergedAt,closedAt,headRefOid,baseRefOid,url",
    ]
    try:
        completed = subprocess.run(
            cmd, check=False, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _item_age_days(item: dict[str, Any], now: datetime) -> float | None:
    stamp = _parse_utc(item.get("updated_at_utc"))
    if stamp is None:
        return None
    return (now - stamp).total_seconds() / 86400.0


def _classify_live_terminal(live_state: str, key: str) -> dict[str, Any] | None:
    if live_state == "MERGED":
        return {
            "action": "TERMINAL_MERGED",
            "key": key,
            "to_state": "TERMINAL",
            "disposition": "MERGED_ROUTINE",
            "reason": "live PR state=MERGED",
        }
    if live_state == "CLOSED":
        return {
            "action": "TERMINAL_CLOSED",
            "key": key,
            "to_state": "TERMINAL",
            "disposition": "CLOSED_NOOP",
            "reason": "live PR state=CLOSED (not merged)",
        }
    return None


def _classify_sha_drift(
    item: dict[str, Any], live_head: str, key: str
) -> dict[str, Any] | None:
    ledger_head = str(item.get("head_sha") or "")
    if not live_head or not ledger_head:
        return None
    if live_head.lower() == ledger_head.lower():
        return None
    return {
        "action": "SHA_DRIFT_REINTAKE",
        "key": key,
        "to_state": "STAGE1_INTAKE",
        "disposition": None,
        "reason": f"head drift ledger={ledger_head[:12]} live={live_head[:12]}",
        "live_head_sha": live_head,
    }


def _classify_stale(
    item: dict[str, Any], *, expiry_days: int, now: datetime, key: str
) -> dict[str, Any] | None:
    stale_candidate = (
        item.get("lifecycle_state") == "WAITING_HUMAN"
        and item.get("author_type") == "BOT"
        and item.get("guardrail_outcome") != "REVIEW_SECURITY"
    )
    if not stale_candidate:
        return None
    age = _item_age_days(item, now)
    if age is None or age <= expiry_days:
        return None
    return {
        "action": "CLOSE_STALE",
        "key": key,
        "to_state": "TERMINAL",
        "disposition": "CLOSED_STALE",
        "reason": (
            f"WAITING_HUMAN BOT non-REVIEW_SECURITY age={age:.1f}d "
            f"> {expiry_days}d"
        ),
        "repository": item.get("repository"),
        "pr": item.get("pr"),
    }


def classify_item(
    item: dict[str, Any],
    live: dict[str, Any] | None,
    *,
    expiry_days: int,
    now: datetime,
) -> dict[str, Any] | None:
    """Return a proposed action, or None when no change is needed."""
    if item.get("lifecycle_state") == "TERMINAL":
        return None
    key = str(item.get("key") or "")
    if live is None:
        return {
            "action": "LIVE_LOOKUP_FAILED",
            "key": key,
            "reason": "gh pr view failed; skip mutation",
        }
    live_state = str(live.get("state") or "").upper()
    live_head = str(live.get("headRefOid") or "")
    return (
        _classify_live_terminal(live_state, key)
        or _classify_sha_drift(item, live_head, key)
        or _classify_stale(item, expiry_days=expiry_days, now=now, key=key)
    )


def _event_id(prefix: str) -> str:
    stamp = _utc_now().strftime("%Y%m%d%H%M%S")
    return f"evt-{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


def build_transition_event(
    item: dict[str, Any],
    action: dict[str, Any],
    *,
    kind: str,
) -> dict[str, Any]:
    to_state = action["to_state"]
    disposition = action.get("disposition")
    reason = str(action.get("reason") or "reconcile")
    event_id = _event_id("reconcile")
    item_key = item["key"]
    from_state = item["lifecycle_state"]
    from_owner = item["current_owner"]
    to_owner = ledger_mod.STATE_OWNERS[to_state]
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


def apply_action_to_ledger(
    ledger: dict[str, Any],
    item: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    """Mutate ledger in memory via apply_transition projection rules."""
    to_state = action["to_state"]
    disposition = action.get("disposition")
    kind = "TERMINAL" if to_state == "TERMINAL" else "HANDOFF"
    event = build_transition_event(item, action, kind=kind)
    projected = {
        "revision": int(item["revision"]),
        "lifecycle_state": item["lifecycle_state"],
        "current_owner": item["current_owner"],
        "next_owner": item["next_owner"],
        "terminal_disposition": item.get("terminal_disposition"),
        "handoffs": list(item.get("handoffs") or []),
        "latest_transition": None,
        "latest_transition_kind": None,
    }
    ledger_mod.apply_transition(event, projected)
    item["revision"] = projected["revision"]
    item["lifecycle_state"] = projected["lifecycle_state"]
    item["current_owner"] = projected["current_owner"]
    item["next_owner"] = projected["next_owner"]
    item["terminal_disposition"] = projected["terminal_disposition"]
    item["handoffs"] = projected["handoffs"]
    item["updated_at_utc"] = event["created_at_utc"]
    if action.get("action") == "SHA_DRIFT_REINTAKE":
        live_head = action.get("live_head_sha")
        if live_head:
            item["next_action"] = (
                f"Re-anchor intake to live head {live_head}; prior evidence void."
            )
    events = ledger.setdefault("events", [])
    events.append(event)
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    return event


def _close_stale_github(action: dict[str, Any]) -> list[str]:
    repo = str(action.get("repository") or "")
    pr = int(action.get("pr") or 0)
    steps: list[str] = []
    if not repo or not pr:
        steps.append("skip github close: missing repository/pr")
        return steps
    comment = subprocess.run(
        ["gh", "pr", "comment", str(pr), "--repo", repo, "--body", STALE_COMMENT],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    steps.append(f"comment exit={comment.returncode}")
    label = subprocess.run(
        ["gh", "pr", "edit", str(pr), "--repo", repo, "--add-label", STALE_LABEL],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    steps.append(f"label exit={label.returncode}")
    close = subprocess.run(
        ["gh", "pr", "close", str(pr), "--repo", repo],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    steps.append(f"close exit={close.returncode}")
    return steps


def collect_actions(
    ledger: dict[str, Any],
    config: dict[str, Any],
    *,
    now: datetime | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    clock = now or _utc_now()
    expiry = _expiry_days(config)
    actions: list[dict[str, Any]] = []
    for item in ledger.get("items") or []:
        action = _action_for_item(item, expiry, clock)
        if action is None:
            continue
        actions.append(action)
        if limit is not None and len(actions) >= limit:
            break
    return actions


def _action_for_item(
    item: Any, expiry: int, clock: datetime
) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    if item.get("lifecycle_state") == "TERMINAL":
        return None
    repo = str(item.get("repository") or "")
    pr = item.get("pr")
    live = _gh_pr_view(repo, int(pr)) if repo and pr else None
    return classify_item(item, live, expiry_days=expiry, now=clock)


def run_reconcile(*, apply: bool, limit: int | None, json_out: bool) -> int:
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    with tempfile.TemporaryDirectory(prefix="pr-lifecycle-reconcile-") as tmp:
        out = Path(tmp) / "ledger.yaml"
        fetch = cas.run_preflight(out)
        ledger = load_yaml(Path(fetch["ledger_path"]))
        actions = collect_actions(ledger, config, limit=limit)
        plan = {
            "dry_run": not apply,
            "ledger_revision": ledger.get("ledger_revision"),
            "action_count": len(actions),
            "actions": actions,
        }
        if not apply:
            _emit(plan, json_out)
            return 0
        items_by_key = {
            item["key"]: item
            for item in ledger.get("items") or []
            if isinstance(item, dict) and "key" in item
        }
        applied: list[dict[str, Any]] = []
        for action in actions:
            if action["action"] == "LIVE_LOOKUP_FAILED":
                continue
            item = items_by_key.get(action["key"])
            if item is None:
                continue
            if action["action"] == "CLOSE_STALE":
                action["github_steps"] = _close_stale_github(action)
            event = apply_action_to_ledger(ledger, item, action)
            applied.append({"action": action, "event_id": event["event_id"]})
        strip_in_memory_item_fields(ledger)
        out.write_text(dump_ledger(ledger), encoding="utf-8")
        result = cas.run_commit(
            out,
            "reconcile: live PR state → ledger transitions",
            bump_revision=False,
        )
        plan["applied"] = applied
        plan["cas"] = result
        _emit(plan, json_out)
    return 0


def _emit(plan: dict[str, Any], json_out: bool) -> None:
    if json_out:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return
    print(f"dry_run={plan['dry_run']}")
    print(f"ledger_revision={plan.get('ledger_revision')}")
    print(f"action_count={plan['action_count']}")
    for action in plan["actions"]:
        print(
            f"action={action['action']} key={action.get('key')} "
            f"reason={action.get('reason')}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile non-terminal ledger items against live GitHub PR state. "
            "Dry-run by default; --apply uses schema-aware CAS."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="CAS-write transitions (default: dry-run plan only)",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_reconcile(apply=args.apply, limit=args.limit, json_out=args.json)
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PR_LIFECYCLE_RECONCILE_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


# Aliases
classify_item = classify_item
collect_actions = collect_actions
