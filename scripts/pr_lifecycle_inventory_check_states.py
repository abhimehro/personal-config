"""Leaf classifiers: map a checkRun/statusCheckRollup node to (state, name)."""

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
