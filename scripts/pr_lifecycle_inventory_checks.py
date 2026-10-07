"""Check-state normalization for open-PR inventory.

CheckRun and StatusContext contexts become name/state pairs; a statusCheckRollup
connection becomes a check list plus a truncation flag. Pure functions only —
no GitHub or subprocess calls live here.
"""

from __future__ import annotations

from typing import Any

_FAILURE_CONCLUSIONS = {
    "FAILURE",
    "TIMED_OUT",
    "CANCELLED",
    "ACTION_REQUIRED",
    "STARTUP_FAILURE",
}

_TRUNCATED_CHECK = {"name": "statusCheckRollup truncated", "state": "PENDING"}


# Structured types take precedence; message markers cover untyped errors only.
# The "temporar" marker requires a word boundary and no leading "not " so an
# explicit "not temporary" error does not count as transient.
def _concluded_state(conclusion: str) -> str:
    """Map a COMPLETED CheckRun conclusion to a normalized state."""
    if conclusion == "SUCCESS":
        return "SUCCESS"
    return conclusion if conclusion in {"SKIPPED", "NEUTRAL"} else "NEUTRAL"


def _check_run_state(context: dict[str, Any]) -> tuple[str, str] | None:
    """Normalize a CheckRun context to a name/state pair, or None if nameless."""
    name = context.get("name")
    if not isinstance(name, str):
        return None
    conclusion = str(context.get("conclusion") or "").upper()
    if conclusion in _FAILURE_CONCLUSIONS:
        return name, "FAILURE"
    status = str(context.get("status") or "").upper()
    if status != "COMPLETED":
        return name, "PENDING"
    return name, _concluded_state(conclusion)


def _status_context_state(context: dict[str, Any]) -> tuple[str, str] | None:
    """Normalize a legacy StatusContext to a name/state pair, or None if nameless."""
    name = context.get("context")
    if not isinstance(name, str):
        return None
    status = str(context.get("state") or "").upper()
    if status in {"FAILURE", "ERROR"}:
        return name, "FAILURE"
    if status in {"PENDING", "EXPECTED"}:
        return name, "PENDING"
    if status == "SUCCESS":
        return name, "SUCCESS"
    return name, "NEUTRAL"


def _check_state(context: dict[str, Any]) -> tuple[str, str] | None:
    """Normalize a check run or legacy status to a name/state pair.

    Return None for unsupported context types or missing string names.
    """
    typename = context.get("__typename")
    if typename == "CheckRun":
        return _check_run_state(context)
    if typename == "StatusContext":
        return _status_context_state(context)
    return None


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

    Only the last commit is normalized. An absent commit, non-dict commit or
    commit author, or a non-dict statusCheckRollup fails closed: missing
    rollups mark checks incomplete and a synthetic PENDING check is appended.
    """
    commits = _nodes(raw.get("commits"), "commits")
    if not commits:
        return [], [dict(_TRUNCATED_CHECK)], True
    commit = commits[-1].get("commit")
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
