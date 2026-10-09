"""Check-state normalization for open-PR inventory.

CheckRun and StatusContext contexts become name/state pairs; a statusCheckRollup
connection becomes a check list plus a truncation flag. Pure functions only —
no GitHub or subprocess calls live here.
"""

from __future__ import annotations

from typing import Any

from pr_lifecycle_inventory_check_states import (
    _TRUNCATED_CHECK,
    _check_state,
)


def _nodes(connection: Any, label: str) -> list[dict[str, Any]]:
    """Return connection nodes or raise OSError for malformed node lists."""
    if not isinstance(connection, dict) or not isinstance(
        connection.get("nodes"), list
    ):
        raise OSError(f"malformed {label}")
    nodes = connection["nodes"]
    if not all(isinstance(node, dict) for node in nodes):
        raise OSError(f"malformed {label}")
    return nodes


def _checks_truncated(connection: Any) -> bool:
    """True when the contexts pageInfo is absent or reports a next page."""
    page_info = connection.get("pageInfo") if isinstance(connection, dict) else None
    if isinstance(page_info, dict) and isinstance(page_info.get("hasNextPage"), bool):
        return page_info["hasNextPage"]
    return True


def _normalized_commit(commit: Any) -> list[dict[str, Any]]:
    """Return the single-commit normalized list, raising on malformed input."""
    if not isinstance(commit, dict):
        raise OSError("malformed commit")
    commit_author = commit.get("author") or {}
    if not isinstance(commit_author, dict):
        raise OSError("malformed commit author")
    return [{"commit": {"author": {"email": commit_author.get("email")}}}]


def _commit_checks(
    raw: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], bool]:
    """Return (normalized commits, checks, checks_incomplete) for a raw PR.

    Only the last commit is normalized. An empty commit list or missing
    rollup returns incomplete checks with a synthetic PENDING check.
    Malformed commit or context node lists, non-dict commits, truthy non-dict
    commit authors, and non-null non-dict rollups raise OSError.
    """
    commits = _nodes(raw.get("commits"), "commits")
    if not commits:
        return [], [dict(_TRUNCATED_CHECK)], True
    commit = commits[-1].get("commit")
    if not isinstance(commit, dict):
        raise OSError("malformed commit")
    normalized_commits = _normalized_commit(commit)
    rollup = commit.get("statusCheckRollup")
    if rollup is None:
        return normalized_commits, [dict(_TRUNCATED_CHECK)], True
    if not isinstance(rollup, dict):
        raise OSError("malformed statusCheckRollup")
    checks, checks_incomplete = _rollup_checks(rollup)
    return normalized_commits, checks, checks_incomplete


def _rollup_checks(rollup: dict[str, Any]) -> tuple[list[dict[str, str]], bool]:
    """Return (normalized checks, checks_incomplete) from a statusCheckRollup."""
    connection = rollup.get("contexts")
    checks_incomplete = _checks_truncated(connection)
    checks: list[dict[str, str]] = []
    if isinstance(connection, dict):
        for context in _nodes(connection, "status check contexts"):
            normalized = _check_state(context)
            if normalized is not None:
                checks.append({"name": normalized[0], "state": normalized[1]})
    if checks_incomplete:
        checks.append(dict(_TRUNCATED_CHECK))
    return checks, checks_incomplete


def check_state(context: dict[str, Any]) -> tuple[str, str] | None:
    """Return a check name/state pair.

    Return None for unsupported context types or non-string names.
    """
    return _check_state(context)
