"""Ledger operations and key management for PR lifecycle reconciliation."""

from __future__ import annotations

from typing import Any

from pr_lifecycle_support import SHA_RE


class ReconcileSkip(Exception):
    """One action cannot be applied; the rest of the batch may continue."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _validate_new_key(repository: str, pr: Any, live_head: str) -> str:
    """Validate and construct the new key."""
    return f"{repository}#{pr}@{live_head}"


def _is_other_item_with_key(
    other: dict[str, Any], new_key: str, item: dict[str, Any]
) -> bool:
    """Check if another item has the same key and is not the current item."""
    return (
        isinstance(other, dict)
        and other is not item
        and other.get("key") == new_key
    )


def _is_key_taken(ledger: dict[str, Any], new_key: str, item: dict[str, Any]) -> bool:
    """Check if the new key is already taken in the ledger."""
    for other in ledger.get("items") or []:
        if _is_other_item_with_key(other, new_key, item):
            return True
    return False


def _update_events_for_key(
    ledger: dict[str, Any], old_key: str, new_key: str
) -> None:
    """Update events in the ledger for the new key."""
    for event in ledger.get("events") or []:
        if isinstance(event, dict) and event.get("item_key") == old_key:
            event_id = event.get("event_id")
            event["item_key"] = new_key
            if isinstance(event_id, str) and event_id:
                event["idempotency_key"] = f"{new_key}:{event_id}"


def _update_work_items_for_key(
    ledger: dict[str, Any], old_key: str, new_key: str
) -> None:
    """Update work items in the ledger for the new key."""
    for work in ledger.get("stage2_work_items") or []:
        if isinstance(work, dict) and work.get("source_item_key") == old_key:
            work["source_item_key"] = new_key


def _replace_key(ledger: dict[str, Any], item: dict[str, Any], live_head: str) -> bool:
    """Replace the key in the ledger and update related events."""
    repository = item.get("repository")
    pr = item.get("pr")
    if not repository or pr is None:
        return False
    new_key = _validate_new_key(repository, pr, live_head)
    if _is_key_taken(ledger, new_key, item):
        return False
    old_key = item["key"]
    item["key"] = new_key
    item["head_sha"] = live_head
    _update_events_for_key(ledger, old_key, new_key)
    _update_work_items_for_key(ledger, old_key, new_key)
    return True


def _is_anchor_blocked(item: dict[str, Any], action: dict[str, Any]) -> bool:
    """Check if the anchor is blocked due to security or author type."""
    if action.get("action") not in {"SHA_DRIFT_REINTAKE", "REANCHOR_HEAD"}:
        return False
    if item.get("guardrail_outcome") == "REVIEW_SECURITY":
        return True
    return item.get("author_type") != "BOT"


def _rekey_item_head_if_needed(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> None:
    """Rekey the item head if needed and possible."""
    live_head = str(action.get("live_head_sha") or "")
    if not live_head or live_head == item.get("head_sha"):
        return
    if SHA_RE.fullmatch(live_head) is None:
        raise ReconcileSkip("anchor_invalid_head")
    if not _replace_key(ledger, item, live_head):
        raise ReconcileSkip("anchor_key_taken")


def _prepare_live_head(
    ledger: dict[str, Any], item: dict[str, Any], action: dict[str, Any]
) -> None:
    """Rekey before a transition event is built. Skip leaves the item unchanged."""
    if action.get("action") not in {"SHA_DRIFT_REINTAKE", "REANCHOR_HEAD"}:
        return
    if _is_anchor_blocked(item, action):
        raise ReconcileSkip("sticky_anchor")
    _rekey_item_head_if_needed(ledger, item, action)