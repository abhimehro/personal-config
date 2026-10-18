"""Evidence evaluation logic for guardrail evaluation."""

from typing import Any, Set


def calculate_signals(
    evidence: Any, diff_security_signals: Any
) -> Set[str]:
    """Return security signals from diff text."""
    if evidence is not None and evidence.diff_text:
        return diff_security_signals(evidence.diff_text)
    return set()


def should_fail_closed(
    item: dict[str, Any], evidence: Any, effective: Set[str], _CLEARABLE_HOLDS: Set[str]
) -> bool:
    """Return whether to fail closed due to missing evidence."""
    return (
        evidence is not None
        and evidence.diff_fetch_failed
        and not effective
        and (
            item.get("guardrail_outcome") in _CLEARABLE_HOLDS
            or item.get("classification") == "SECURITY"
        )
    )