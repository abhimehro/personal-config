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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position
import pr_lifecycle_ledger as ledger_mod
import pr_lifecycle_ledger_cas as cas
from pr_identity import classify_pr_identity, identity_policy_from_config
from pr_lifecycle_config import validate_config
from pr_lifecycle_open_inventory import list_open_prs
from pr_lifecycle_persist import dump_ledger, strip_in_memory_item_fields
from pr_lifecycle_support import ROOT, SHA_RE
from pr_lifecycle_yaml import load_yaml

DEFAULT_EXPIRY_DAYS = 7
STALE_LABEL = "stale-auto-closed"
STALE_COMMENT = (
    "Closing as stale: WAITING_HUMAN BOT packet older than "
    "packet_expiry_close_days with no REVIEW_SECURITY hold "
    "(policy 2026-09-21). Re-open or comment if this should stay open."
)


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


def _gh_pr_view(repo: str, pr: int) -> dict[str, Any] | None:
    """Fetch live PR fields, returning None when the command or payload fails.

    Note: base SHA is enriched via REST ``gh api`` rather than folding
    ``baseRefOid`` into the ``--json`` field list, so a missing base SHA
    fails closed as None instead of silently omitting the drift check.
    """
    cmd = [
        "gh",
        "pr",
        "view",
        str(pr),
        "--repo",
        repo,
        "--json",
        "state,mergedAt,closedAt,headRefOid,url,mergedBy,labels",
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
    if not isinstance(payload, dict):
        return None
    # Enrich base SHA via REST — required by SHA-drift classification.
    # Fail closed (None) if either call fails: missing baseRefOid would
    # mis-classify SHA drift.
    base_cmd = [
        "gh",
        "api",
        f"repos/{repo}/pulls/{pr}",
        "--jq",
        ".base.sha",
    ]
    try:
        base = subprocess.run(
            base_cmd, check=False, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if base.returncode != 0:
        return None
    sha = (base.stdout or "").strip()
    if not sha:
        return None
    payload["baseRefOid"] = sha
    return payload


def _gh_pr_files(repo: str, pr: int) -> list[str] | None:
    """Fetch the PR's changed-file paths via REST; None on any failure.

    Paginates so a large diff cannot silently truncate evidence (a hidden
    sensitive path must never downgrade a hold). Renames contribute their
    old path too: `.previous_filename` keeps a file moved OUT of a
    sensitive location from looking clean. An empty result also returns
    None: a real open PR always changes at least one file, so an empty
    list means the evidence could not be trusted.
    """
    cmd = [
        "gh",
        "api",
        f"repos/{repo}/pulls/{pr}/files",
        "--paginate",
        "--jq",
        ".[] | .filename, (.previous_filename // empty)",
    ]
    try:
        completed = subprocess.run(
            cmd, check=False, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    paths = sorted({line for line in completed.stdout.splitlines() if line})
    return paths or None


def _item_age_days(item: dict[str, Any], now: datetime) -> float | None:
    """Return days since the item update, or None for an invalid timestamp."""
    stamp = _parse_utc(item.get("updated_at_utc"))
    if stamp is None:
        return None
    return (now - stamp).total_seconds() / 86400.0


# Only labels that make one disposition unambiguous evidence; other
# unlabeled closures are recorded as CLOSED_NOOP rather than guessed.
_CLOSED_LABEL_DISPOSITIONS = {
    "duplicate": "CLOSED_DUPLICATE",
    "superseded": "CLOSED_SUPERSEDED",
    STALE_LABEL: "CLOSED_STALE",
    "wontfix": "HUMAN_REJECTED",
    "declined": "HUMAN_REJECTED",
}


def _label_names(live: dict[str, Any]) -> list[str]:
    """Sorted label names from a live PR payload."""
    return sorted(
        label["name"]
        for label in live.get("labels") or []
        if isinstance(label, dict) and isinstance(label.get("name"), str)
    )


def _classify_live_merge(
    item: dict[str, Any], live: dict[str, Any], key: str
) -> dict[str, Any] | None:
    merger = str((live.get("mergedBy") or {}).get("login") or "")
    if not merger:
        return _pending_terminal(item, key, "MERGED", "mergedBy unavailable")
    completion_owned = (
        item.get("lifecycle_state") == "STAGE3_RECONCILIATION"
        or item.get("current_owner") == "stage3"
    )
    disposition = "MERGED_BOUNDED_COMPLETION" if completion_owned else "MERGED_ROUTINE"
    return {
        "action": "TERMINAL_MERGED",
        "key": key,
        "to_state": "TERMINAL",
        "disposition": disposition,
        "reason": f"live PR state=MERGED mergedBy={merger}",
        "evidence": {"mergedBy": merger},
    }


def _classify_live_close(
    item: dict[str, Any], live: dict[str, Any], key: str
) -> dict[str, Any] | None:
    """Classify a closed PR by its labels, preserving unlabeled security holds.

    Without a disposition label, return CLOSED_NOOP unless REVIEW_SECURITY
    requires Stage 3 classification. Return None if that security observation
    was already recorded.
    """
    labels = _label_names(live)
    disposition = next(
        (
            _CLOSED_LABEL_DISPOSITIONS[name]
            for name in labels
            if name in _CLOSED_LABEL_DISPOSITIONS
        ),
        None,
    )
    if disposition is None:
        if item.get("guardrail_outcome") == "REVIEW_SECURITY":
            return _pending_terminal(
                item, key, "CLOSED", "no disposition-bearing label"
            )
        return {
            "action": "TERMINAL_CLOSED",
            "key": key,
            "to_state": "TERMINAL",
            "disposition": "CLOSED_NOOP",
            "reason": (
                "live PR state=CLOSED without disposition label; "
                "closed outside lifecycle → CLOSED_NOOP"
            ),
            "evidence": {"labels": labels},
        }
    return {
        "action": "TERMINAL_CLOSED",
        "key": key,
        "to_state": "TERMINAL",
        "disposition": disposition,
        "reason": f"live PR state=CLOSED labels={labels}",
        "evidence": {"labels": labels},
    }


def _pending_terminal(
    item: dict[str, Any], key: str, observed: str, detail: str
) -> dict[str, Any] | None:
    """Route an unclassified merge to Stage 3 when merger evidence is absent.

    Non-Stage-3 items route to Stage 3 for classification; an item already
    Stage-3-owned gets an in-place observation note (same-state handoffs are
    illegal). A prior identical observation is not re-emitted.
    """
    marker = f"Observed {observed} unclassified"
    if marker in str(item.get("next_action") or ""):
        return None
    if item.get("lifecycle_state") != "STAGE3_RECONCILIATION":
        return {
            "action": "TERMINAL_PENDING",
            "key": key,
            "to_state": "STAGE3_RECONCILIATION",
            "disposition": None,
            "observed_state": observed,
            "reason": (
                f"live state={observed} without classifying evidence "
                f"({detail}); route to Stage 3"
            ),
            "evidence": {"observed_state": observed, "detail": detail},
        }
    return {
        "action": "TERMINAL_OBSERVED",
        "key": key,
        "observed_state": observed,
        "reason": f"{marker}: {detail}",
        "evidence": {"observed_state": observed, "detail": detail},
    }


def _classify_live_terminal(
    item: dict[str, Any], live: dict[str, Any], key: str
) -> dict[str, Any] | None:
    """Return a terminal or pending action for a merged/closed live PR."""
    live_state = str(live.get("state") or "").upper()
    if live_state == "MERGED":
        return _classify_live_merge(item, live, key)
    if live_state == "CLOSED":
        return _classify_live_close(item, live, key)
    return None


def _field_drift(ledger_val: object, live_val: object) -> bool:
    ledger = str(ledger_val or "")
    live = str(live_val or "")
    return bool(live and ledger and live.lower() != ledger.lower())


def _drift_fields(item: dict[str, Any], live: dict[str, Any]) -> tuple[str, str, bool]:
    live_head = str(live.get("headRefOid") or "")
    live_base = str(live.get("baseRefOid") or "")
    drifted = _field_drift(item.get("head_sha"), live_head) or _field_drift(
        item.get("base_sha"), live_base
    )
    return live_head, live_base, drifted


def _classify_sha_drift(
    item: dict[str, Any], live: dict[str, Any], key: str
) -> dict[str, Any] | None:
    live_head, live_base, drifted = _drift_fields(item, live)
    if not drifted:
        return None
    if item.get("lifecycle_state") == "STAGE1_INTAKE":
        # Same-state handoffs are not legal transitions; re-anchor in place.
        return {
            "action": "REANCHOR_HEAD",
            "key": key,
            "reason": f"re-anchor intake to live head {live_head[:12]}",
            "live_head_sha": live_head,
            "live_base_sha": live_base,
        }
    ledger_head = str(item.get("head_sha") or "")
    return {
        "action": "SHA_DRIFT_REINTAKE",
        "key": key,
        "to_state": "STAGE1_INTAKE",
        "disposition": None,
        "reason": f"head/base drift ledger={ledger_head[:12]} live={live_head[:12]}",
        "live_head_sha": live_head,
        "live_base_sha": live_base,
    }


def _classify_stale(
    item: dict[str, Any], *, expiry_days: int, now: datetime, key: str
) -> dict[str, Any] | None:
    """Return a stale-close action for an expired eligible bot packet."""
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
            f"WAITING_HUMAN BOT non-REVIEW_SECURITY age={age:.1f}d > {expiry_days}d"
        ),
        "repository": item.get("repository"),
        "pr": item.get("pr"),
    }


def _needs_path_backfill(item: dict[str, Any]) -> bool:
    """True for a nonterminal item whose changed-path evidence is absent."""
    paths = item.get("changed_paths")
    return item.get("lifecycle_state") != "TERMINAL" and not (
        isinstance(paths, list) and paths
    )


def _backfill_eligible(item: dict[str, Any], live: Any) -> bool:
    """True only when a pathless nonterminal item faces an open live PR."""
    return (
        _needs_path_backfill(item)
        and isinstance(live, dict)
        and str(live.get("state") or "").upper() == "OPEN"
        and bool(str(item.get("repository") or ""))
        and _positive_pr_number(item.get("pr"))
    )


def _path_backfill_action(
    item: dict[str, Any], live: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Emit a changed_paths backfill for an open live PR missing path evidence.

    Data-only action: it stamps `changed_paths` so the guardrail evaluator
    can judge the item on real evidence instead of holding it forever on a
    missing list. Fetch failures emit PATH_BACKFILL_FAILED for visibility
    (never applied); non-OPEN live states skip the fetch entirely.
    """
    if not _backfill_eligible(item, live):
        return None
    repo = str(item["repository"])
    pr = int(item["pr"])
    key = str(item.get("key") or "")
    paths = _gh_pr_files(repo, pr)
    if paths is None:
        return {
            "action": "PATH_BACKFILL_FAILED",
            "key": key,
            "repository": repo,
            "pr": pr,
            "reason": "changed-paths fetch failed; item stays unevaluated",
        }
    return {
        "action": "BACKFILL_PATHS",
        "key": key,
        "repository": repo,
        "pr": pr,
        "paths": paths,
        "reason": f"backfill changed_paths ({len(paths)} files) for guardrail evidence",
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
    # A merged or closed PR is done. An already-noted observation returns None;
    # do not fall through into SHA re-intake just because the recorded head
    # differs from the closed head.
    live_state = str(live.get("state") or "").upper()
    if live_state in {"MERGED", "CLOSED"}:
        return _classify_live_terminal(item, live, key)
    return _classify_sha_drift(item, live, key) or _classify_stale(
        item, expiry_days=expiry_days, now=now, key=key
    )


def _event_id(prefix: str) -> str:
    """Generate a unique timestamped event identifier."""
    stamp = _utc_now().strftime("%Y%m%d%H%M%S")
    return f"evt-{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


def build_transition_event(
    item: dict[str, Any],
    action: dict[str, Any],
    *,
    kind: str,
) -> dict[str, Any]:
    """Build a projected ledger transition event for a reconcile action."""
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


class ReconcileSkip(Exception):
    """One action cannot be applied; the rest of the batch may continue."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _anchor_blocked(item: dict[str, Any], action: dict[str, Any]) -> bool:
    """Sticky security and non-bot head moves stay on their recorded anchor.

    REVIEW_SECURITY and human-authored packets are not silently re-intaken.
    """
    if action.get("action") not in {"SHA_DRIFT_REINTAKE", "REANCHOR_HEAD"}:
        return False
    if item.get("guardrail_outcome") == "REVIEW_SECURITY":
        return True
    if item.get("author_type") != "BOT":
        return True
    return False


def _rekey_item_head(
    ledger: dict[str, Any], item: dict[str, Any], live_head: str
) -> bool:
    """Point key at live_head. False if that key is already taken.

    Schema requires key.endswith(head_sha) and
    idempotency_key == f"{item_key}:{event_id}". Rewrite this item's events
    and any stage2 work-item source keys. Do not bump item revision here.
    """
    if not live_head or live_head == item.get("head_sha"):
        return True
    if SHA_RE.fullmatch(live_head) is None:
        return False
    repository = item.get("repository")
    pr = item.get("pr")
    if not repository or pr is None:
        return False
    new_key = f"{repository}#{pr}@{live_head}"
    for other in ledger.get("items") or []:
        taken = (
            isinstance(other, dict)
            and other is not item
            and other.get("key") == new_key
        )
        if taken:
            return False
    old_key = item["key"]
    item["key"] = new_key
    item["head_sha"] = live_head
    for event in ledger.get("events") or []:
        if isinstance(event, dict) and event.get("item_key") == old_key:
            event_id = event.get("event_id")
            event["item_key"] = new_key
            if isinstance(event_id, str) and event_id:
                event["idempotency_key"] = f"{new_key}:{event_id}"
    for work in ledger.get("stage2_work_items") or []:
        if isinstance(work, dict) and work.get("source_item_key") == old_key:
            work["source_item_key"] = new_key
    return True


def _prepare_live_head(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> None:
    """Rekey before a transition event is built. Skip leaves the item unchanged."""
    if action.get("action") not in {"SHA_DRIFT_REINTAKE", "REANCHOR_HEAD"}:
        return
    if _anchor_blocked(item, action):
        raise ReconcileSkip("sticky_anchor")
    live_head = str(action.get("live_head_sha") or "")
    if not live_head or live_head == item.get("head_sha"):
        return
    if SHA_RE.fullmatch(live_head) is None:
        raise ReconcileSkip("anchor_invalid_head")
    if not _rekey_item_head(ledger, item, live_head):
        raise ReconcileSkip("anchor_key_taken")


def _apply_drift_fields(item: dict[str, Any], action: dict[str, Any]) -> None:
    live_head = action.get("live_head_sha")
    # Head moves only via _rekey_item_head so the key still ends with head_sha.
    if live_head and live_head == item.get("head_sha"):
        item["next_action"] = (
            f"Re-anchor intake to live head {live_head}; prior evidence void."
        )
    live_base = action.get("live_base_sha")
    if live_base:
        item["base_sha"] = live_base


def _reanchor_item(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> dict[str, Any]:
    """In-place base note for items already in STAGE1_INTAKE.

    The live head is written by _prepare_live_head. Item revision stays put:
    this path records no transition event, and the projection must match events.
    """
    live_base = action.get("live_base_sha")
    if live_base:
        item["base_sha"] = live_base
    item["updated_at_utc"] = _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    item["next_action"] = (
        f"Re-anchored to live head {item.get('head_sha')}; prior evidence void."
    )
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    return {"event_id": None}


def apply_action_to_ledger(
    ledger: dict[str, Any],
    item: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    """Apply an action in memory and return the appended transition event."""
    _prepare_live_head(ledger, item, action)
    if action.get("action") == "REANCHOR_HEAD":
        return _reanchor_item(ledger, item, action)
    if action.get("action") == "TERMINAL_OBSERVED":
        return _note_observed_terminal(ledger, item, action)
    if action.get("action") == "BACKFILL_PATHS":
        return _backfill_item_paths(ledger, item, action)
    to_state = action["to_state"]
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
        _apply_drift_fields(item, action)
    if action.get("action") == "TERMINAL_PENDING":
        item["next_action"] = (
            f"Observed {action.get('observed_state')} unclassified; "
            "Stage 3 classification required."
        )
    events = ledger.setdefault("events", [])
    events.append(event)
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    return event


def _note_observed_terminal(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> dict[str, Any]:
    """In-place observation note for a Stage-3-owned unclassified terminal.

    Do not bump item revision: this note has no transition event, and the
    projection validator requires revision to match the event chain.
    """
    item["updated_at_utc"] = _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    item["next_action"] = str(action.get("reason") or "Observed unclassified")
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    return {"event_id": None}


def _backfill_item_paths(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> dict[str, Any]:
    """Stamp `changed_paths` in place from a BACKFILL_PATHS action.

    Data-only write: no transition event, no revision bump, and no
    updated_at_utc refresh (a path list is evidence, not activity — the
    staleness clock must not reset on a backfill).
    """
    paths = sorted({str(path) for path in action.get("paths") or [] if str(path)})
    if not paths:
        raise ReconcileSkip("backfill_empty_paths")
    if item.get("changed_paths") == paths:
        raise ReconcileSkip("backfill_noop")
    item["changed_paths"] = paths
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    return {"event_id": None}


def _close_stale_github(action: dict[str, Any]) -> tuple[list[str], bool]:
    """Close the stale PR on GitHub; confirm only when a re-read shows CLOSED."""
    repo = str(action.get("repository") or "")
    pr = int(action.get("pr") or 0)
    steps: list[str] = []
    if not repo or not pr:
        steps.append("skip github close: missing repository/pr")
        return steps, False
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
    if close.returncode != 0:
        return steps, False
    live = _gh_pr_view(repo, pr)
    confirmed = (
        isinstance(live, dict) and str(live.get("state") or "").upper() == "CLOSED"
    )
    steps.append(f"confirm={'closed' if confirmed else 'unconfirmed'}")
    return steps, confirmed


def collect_actions(
    ledger: dict[str, Any],
    config: dict[str, Any],
    *,
    now: datetime | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Collect reconciliation actions for ledger items in item order."""
    clock = now or _utc_now()
    expiry = _expiry_days(config)
    actions: list[dict[str, Any]] = []
    for item in ledger.get("items") or []:
        actions.extend(_action_for_item(item, expiry, clock))
        if limit is not None and len(actions) >= limit:
            del actions[limit:]
            break
    return actions


def build_intake_item(
    live: dict[str, Any], policy: Any, now: datetime
) -> dict[str, Any]:
    """Construct a fail-closed Stage 1 ledger projection for an open PR.

    Use normalized inventory fields and policy to classify the author. Start
    at revision zero with UNKNOWN risk and NOT_RUN guardrails; do not modify
    the PR or ledger. Missing required inventory fields raise KeyError.
    """
    verdict = classify_pr_identity(live, policy)
    author = {
        "login": verdict.login,
        "identity_source": "github_api",
        "app_slug": verdict.app_slug,
    }
    if verdict.method in {
        "allowlist_login",
        "allowlist_app_slug",
        "token_authored_signals",
    }:
        author["identity_provenance"] = {
            "method": verdict.method,
            "signals": list(verdict.signals),
        }
    repository = str(live["repository"])
    pr = int(live["number"])
    head_sha = str(live["headRefOid"])
    url = str(live["url"])
    return {
        "key": f"{repository}#{pr}@{head_sha}",
        "repository": repository,
        "pr": pr,
        "url": url,
        "base_sha": str(live["baseRefOid"]),
        "head_sha": head_sha,
        "author": author,
        "author_type": verdict.author_type,
        "classification": "UNKNOWN",
        "risk_class": "UNKNOWN",
        "sensitive_paths": [],
        "changed_paths": [],
        "guardrail_outcome": "NOT_RUN",
        "lifecycle_state": "STAGE1_INTAKE",
        "current_owner": "stage1",
        "next_owner": "stage1",
        "terminal_disposition": None,
        "safe_default": "Leave open; no merge or close until Stage 1 guardrails run.",
        "next_action": (
            "Stage 1: run guardrails on newly ingested open PR "
            f"(ingested {now.strftime('%Y-%m-%d')} by reconcile)."
        ),
        "evidence_urls": [url],
        "attempts": {"evidence": 0, "recovery": 0, "mutations": 0},
        "handoffs": [],
        "revision": 0,
        "updated_at_utc": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def collect_ingest_actions(
    ledger: dict[str, Any],
    config: dict[str, Any],
    open_prs_by_repo: dict[str, list[dict[str, Any]]],
    *,
    now: datetime,
) -> list[dict[str, Any]]:
    """Plan uncapped intake actions for configured open PRs without changing inputs.

    Skip PRs with any active ledger item, even at an older head. Report invalid
    identity anchors as INGEST_SKIPPED and terminal current heads as
    TERMINAL_BUT_OPEN; otherwise return INGEST_OPEN_PR with an intake item.
    Duplicate inventory entries produce at most one intake item per PR.
    """
    items = [item for item in ledger.get("items") or [] if isinstance(item, dict)]
    ctx = _IngestCtx(items, identity_policy_from_config(config), now)
    actions: list[dict[str, Any]] = []
    for repo in config.get("repos") or []:
        for live in open_prs_by_repo.get(repo, []):
            action = _ingest_action(repo, live, ctx)
            if action is not None:
                actions.append(action)
    return actions


def _author_login_str(author: Any) -> str:
    """Return the stripped author login from a live PR entry."""
    if not isinstance(author, dict):
        return ""
    return str(author.get("login") or "").strip()


def _ingest_skipped(
    repo: str, reason: str, pr_number: Any = None, *, include_pr: bool = False
) -> dict[str, Any]:
    """Build an INGEST_SKIPPED entry, optionally carrying the PR number."""
    action: dict[str, Any] = {
        "action": "INGEST_SKIPPED",
        "repository": repo,
        "reason": reason,
    }
    if include_pr:
        action["pr"] = pr_number
    return action


def _terminal_open(
    key: str, live: dict[str, Any], terminal: dict[str, Any]
) -> dict[str, Any]:
    """Build a TERMINAL_BUT_OPEN entry for a live PR at a terminal head."""
    return {
        "action": "TERMINAL_BUT_OPEN",
        "key": key,
        "repository": live.get("repository"),
        "pr": live.get("number"),
        "url": live.get("url"),
        "terminal_disposition": terminal.get("terminal_disposition"),
        "reason": "PR is open at a head already recorded as terminal",
    }


def _positive_pr_number(value: Any) -> bool:
    """Require a positive int PR number (bool excluded)."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _sha_pair(live: dict[str, Any]) -> bool:
    """Require 40-hex head and base SHAs on a live PR entry."""
    return bool(
        SHA_RE.fullmatch(str(live.get("headRefOid") or ""))
        and SHA_RE.fullmatch(str(live.get("baseRefOid") or ""))
    )


def _https_url(url: Any) -> bool:
    """Require a string URL with an https scheme."""
    return isinstance(url, str) and url.startswith("https://")


def _ingest_skip_reason(live: dict[str, Any]) -> tuple[str, bool] | None:
    """Return (reason, include_pr) for an invalid live entry, or None."""
    if not _positive_pr_number(live.get("number")):
        return "invalid pull request number", False
    if not _sha_pair(live):
        return "invalid base/head SHA", True
    if not _author_login_str(live.get("author")):
        return "empty identity login", True
    if not _https_url(live.get("url")):
        return "invalid pull request URL", True
    return None


def _repo_candidates(
    items: list[dict[str, Any]], repo: str, pr_number: Any
) -> list[dict[str, Any]]:
    """Return ledger items matching this repo and PR number."""
    return [
        item
        for item in items
        if item.get("repository") == repo and item.get("pr") == pr_number
    ]


def _terminal_at(candidates: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    """Return the terminal ledger item recorded at this head key, if any."""
    return next(
        (
            item
            for item in candidates
            if item.get("key") == key and item.get("lifecycle_state") == "TERMINAL"
        ),
        None,
    )


@dataclass(frozen=True)
class _IngestCtx:
    """The shared ingest state: ledger items, identity policy, timestamp."""

    items: list[dict[str, Any]]
    policy: Any
    now: datetime


def _ingest_action(
    repo: str, live: dict[str, Any], ctx: _IngestCtx
) -> dict[str, Any] | None:
    """Classify one live PR: skip/terminal/ingest action, or None when tracked.

    Skip PRs with any active ledger item, even at an older head. New intake
    items are appended to items so duplicate inventory entries dedupe.
    """
    items = ctx.items
    pr_number = live.get("number")
    head_sha = str(live.get("headRefOid") or "")
    skipped = _ingest_skip_reason(live)
    if skipped is not None:
        reason, include_pr = skipped
        return _ingest_skipped(repo, reason, pr_number, include_pr=include_pr)
    candidates = _repo_candidates(items, repo, pr_number)
    if any(item.get("lifecycle_state") != "TERMINAL" for item in candidates):
        return None
    key = f"{repo}#{pr_number}@{head_sha}"
    terminal = _terminal_at(candidates, key)
    if terminal is not None:
        return _terminal_open(key, live, terminal)
    item = build_intake_item(live, ctx.policy, ctx.now)
    items.append(item)
    return {
        "action": "INGEST_OPEN_PR",
        "key": key,
        "repository": repo,
        "pr": pr_number,
        "item": item,
    }


def _action_for_item(item: Any, expiry: int, clock: datetime) -> list[dict[str, Any]]:
    """Look up and classify one nonterminal item; return 0-2 planned actions.

    A changed-paths backfill rides alongside the primary action so the
    guardrail evaluator can adjudicate the item on evidence next pass.
    """
    if not isinstance(item, dict):
        return []
    if item.get("lifecycle_state") == "TERMINAL":
        return []
    repo = str(item.get("repository") or "")
    pr = item.get("pr")
    live = _gh_pr_view(repo, int(pr)) if repo and pr else None
    primary = classify_item(item, live, expiry_days=expiry, now=clock)
    actions = [primary] if primary is not None else []
    backfill = _path_backfill_action(item, live)
    if backfill is not None:
        actions.append(backfill)
    return actions


def run_reconcile(
    *, apply: bool, limit: int | None, json_out: bool, ingest: bool = True
) -> int:
    """Fetch and emit actions, optionally applying and CAS-committing them.

    limit caps existing-item actions; nonpositive limits still allow the first
    eligible action. Open-PR intake is uncapped; ingest=False skips its
    inventory and intake. Inventory OSError failures become INVENTORY_FAILED
    entries; configuration, ledger fetch, and commit errors propagate.
    Apply mode may close stale PRs and persists ledger changes.
    Return zero after emitting the plan, including inventory failure reports.
    """
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    with tempfile.TemporaryDirectory(prefix="pr-lifecycle-reconcile-") as tmp:
        out = Path(tmp) / "ledger.yaml"
        fetch = cas.run_preflight(out)
        ledger = load_yaml(Path(fetch["ledger_path"]))
        actions = collect_actions(ledger, config, limit=limit)
        inventory_failed: list[dict[str, str]] = []
        open_prs_by_repo: dict[str, list[dict[str, Any]]] = {}
        if ingest:
            for repo in config["repos"]:
                try:
                    open_prs_by_repo[repo] = list_open_prs(repo)
                except OSError as exc:
                    inventory_failed.append(
                        {
                            "action": "INVENTORY_FAILED",
                            "repository": repo,
                            "reason": f"{type(exc).__name__}: {exc}"[:200],
                        }
                    )
            ingest_actions = collect_ingest_actions(
                ledger, config, open_prs_by_repo, now=_utc_now()
            )
            actions.extend(ingest_actions)
            actions.extend(inventory_failed)
        else:
            ingest_actions = []
        plan = {
            "dry_run": not apply,
            "ledger_revision": ledger.get("ledger_revision"),
            "action_count": len(actions),
            "actions": actions,
            "ingest_count": sum(
                action["action"] == "INGEST_OPEN_PR" for action in ingest_actions
            ),
            "terminal_but_open_count": sum(
                action["action"] == "TERMINAL_BUT_OPEN" for action in ingest_actions
            ),
            "inventory_failed": inventory_failed,
        }
        if not apply:
            _emit(plan, json_out)
            return 0
        applied = _apply_actions(ledger, actions)
        ingested = _apply_ingest_actions(ledger, actions)
        strip_in_memory_item_fields(ledger)
        out.write_text(dump_ledger(ledger), encoding="utf-8")
        result = cas.run_commit(
            out,
            "reconcile: live PR state → ledger transitions",
            bump_revision=False,
        )
        plan["applied"] = applied
        plan["ingested"] = ingested
        plan["cas"] = result
        _emit(plan, json_out)
    return 0


def _apply_close_stale(action: dict[str, Any]) -> bool:
    steps, closed = _close_stale_github(action)
    action["github_steps"] = steps
    if not closed:
        # Failed/unconfirmed closes must not write terminal records.
        action["close_unconfirmed"] = True
    return closed


def _apply_actions(
    ledger: dict[str, Any], actions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply reconciliation actions to the ledger and return successful events.

    Inventory reports and intake actions are skipped; intake is applied
    separately by the ingestion path.
    """
    items_by_key = {
        item["key"]: item
        for item in ledger.get("items") or []
        if isinstance(item, dict) and "key" in item
    }
    applied: list[dict[str, Any]] = []
    for action in actions:
        if action["action"] in {
            "LIVE_LOOKUP_FAILED",
            "INGEST_OPEN_PR",
            "INGEST_SKIPPED",
            "TERMINAL_BUT_OPEN",
            "INVENTORY_FAILED",
            "PATH_BACKFILL_FAILED",
        }:
            continue
        result = _apply_one(ledger, action, items_by_key)
        if result is not None:
            applied.append(result)
    return applied


def _apply_ingest_actions(
    ledger: dict[str, Any], actions: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Append intake rows in place and return their key/repository summaries.

    Mark duplicate-key actions as skipped. Increment ledger_revision once
    only if at least one item was appended; do not create transition events.
    """
    items = ledger.setdefault("items", [])
    existing = {
        item.get("key")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("key"), str)
    }
    ingested: list[dict[str, str]] = []
    for action in actions:
        if action.get("action") != "INGEST_OPEN_PR":
            continue
        item = action["item"]
        if item["key"] in existing:
            action["skipped"] = "duplicate key"
            continue
        items.append(item)
        existing.add(item["key"])
        ingested.append({"key": item["key"], "repository": item["repository"]})
    if ingested:
        ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    return ingested


def _apply_one(
    ledger: dict[str, Any],
    action: dict[str, Any],
    items_by_key: dict[Any, dict[str, Any]],
) -> dict[str, Any] | None:
    item = items_by_key.get(action["key"])
    if item is None:
        return None
    if action["action"] == "CLOSE_STALE":
        if not _apply_close_stale(action):
            return None
    try:
        event = apply_action_to_ledger(ledger, item, action)
    except ReconcileSkip as exc:
        action["skipped"] = exc.reason
        return None
    return {"action": action, "event_id": event["event_id"]}


def _emit(plan: dict[str, Any], json_out: bool) -> None:
    """Print a reconciliation plan as JSON or concise text."""
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
    """Build the reconciliation command-line parser."""
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
    parser.add_argument(
        "--no-ingest",
        action="store_true",
        help="skip live open-PR inventory and Stage 1 intake planning",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the reconcile CLI, returning 1 for expected operational errors."""
    args = build_parser().parse_args(argv)
    try:
        return run_reconcile(
            apply=args.apply,
            limit=args.limit,
            json_out=args.json,
            ingest=not args.no_ingest,
        )
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PR_LIFECYCLE_RECONCILE_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


# Aliases
classify_item = classify_item
collect_actions = collect_actions
