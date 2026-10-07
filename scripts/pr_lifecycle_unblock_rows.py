"""Backlog decision rows and per-repo action tallies for unblock plans.

Rows combine nonterminal human-owned ledger items and security holds with the
run's ESCALATE proposals; tallies group proposals by action and blocker.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import timedelta
from typing import Any

from pr_lifecycle_unblock_routing import _iso, _parse_datetime

_EXPIRES_RE = re.compile(r"\bExpires\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")


def _backlog_item(item: Any, repo: str) -> bool:
    """True for nonterminal items in repo owned by a human or security hold."""
    if not isinstance(item, dict):
        return False
    if item.get("repository") != repo or item.get("lifecycle_state") == "TERMINAL":
        return False
    return (
        item.get("current_owner") == "human"
        or item.get("guardrail_outcome") == "REVIEW_SECURITY"
    )


def _row_expiry(
    item: dict[str, Any], next_action: str, packet_expiry_days: int
) -> str | None:
    """Return the row's expiry timestamp from next_action or item age."""
    expires_match = _EXPIRES_RE.search(next_action)
    if expires_match:
        return expires_match.group(1)
    updated = _parse_datetime(item.get("updated_at_utc"))
    if updated is None:
        return None
    return _iso(updated + timedelta(days=packet_expiry_days))


def _backlog_row(
    item: dict[str, Any],
    repo: str,
    next_action: str,
    expires: str | None,
    packet_expiry_days: int,
) -> dict[str, Any]:
    """Build one human-decision backlog row from a ledger item."""
    return {
        "repository": repo,
        "pr": item.get("pr"),
        "url": item.get("url"),
        "blocker": item.get("guardrail_outcome") or "human_decision",
        "evidence": next_action[:200],
        "recommended_action": next_action[:200],
        "safe_default": item.get("safe_default")
        or "Leave open; no merge or close without a human decision.",
        "owner": "human",
        "expires": expires,
        "packet_expiry_close_days": packet_expiry_days,
    }


def _human_ledger_rows(
    repo: str, ledger: dict[str, Any], packet_expiry_days: int
) -> list[dict[str, Any]]:
    """Build backlog rows for nonterminal human-owned items and security holds."""
    rows: list[dict[str, Any]] = []
    for item in ledger.get("items") or []:
        if not _backlog_item(item, repo):
            continue
        next_action = str(item.get("next_action") or "")
        rows.append(
            _backlog_row(
                item,
                repo,
                next_action,
                _row_expiry(item, next_action, packet_expiry_days),
                packet_expiry_days,
            )
        )
    return rows


def _rows_for_repo(
    repo: str,
    actions: list[dict[str, Any]],
    ledger: dict[str, Any],
    packet_expiry_days: int,
) -> list[dict[str, Any]]:
    """Combine a repository's ledger decision rows and escalation proposals."""
    rows = _human_ledger_rows(repo, ledger, packet_expiry_days)
    rows.extend(
        {
            **action,
            "packet_expiry_close_days": packet_expiry_days,
        }
        for action in actions
        if action.get("action") == "ESCALATE" and action.get("repository") == repo
    )
    return rows


def _repo_counts(
    actions: list[dict[str, Any]], repositories: list[str]
) -> dict[str, Any]:
    """Count proposals by action and blocker for each requested repository."""
    result: dict[str, Any] = {}
    for repo in repositories:
        repo_actions = [
            action for action in actions if action.get("repository") == repo
        ]
        result[repo] = {
            "by_action": dict(
                Counter(action.get("action", "UNKNOWN") for action in repo_actions)
            ),
            "by_blocker": dict(
                Counter(
                    str(action.get("blocker"))
                    for action in repo_actions
                    if action.get("blocker")
                )
            ),
        }
    return result
