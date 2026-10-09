"""Check-failure routing for the PR lifecycle unblock stage.

Split out of pr_lifecycle_unblock_routing for cohesion: every function here
decides what to do about the PR's check rollup — CodeScene remediation,
required-check triggers, advisory notes, and reviewer-specific conflict
triggers. Pure decisions only; no GitHub or subprocess calls.
"""

from __future__ import annotations

from typing import Any

from pr_lifecycle_unblock_route_support import (
    _advisory,
    _advisory_patterns,
    _conflict_trigger,
    _ConflictSpec,
    _escalation,
    _EscalationSpec,
    _Route,
    _safe_check_names,
    _trigger_action,
)


def _route_codescene(
    ctx: _Route, failures: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Trigger the CodeScene remediation skill when a CodeScene check fails."""
    codescene = [
        check
        for check in failures
        if str(check.get("name") or "").startswith("CodeScene")
    ]
    if not codescene:
        return []
    names = sorted({str(check.get("name") or "") for check in codescene})
    return _trigger_action(
        ctx,
        "codescene",
        "/cs-agent skill:fix-code-health-degradations",
        _EscalationSpec(
            "codescene_failure",
            evidence={"checks": names},
            recommended_action="run the CodeScene code-health remediation",
        ),
    )


def _route_required_checks(
    ctx: _Route, failures: list[dict[str, Any]], advisory: list[Any]
) -> list[dict[str, Any]]:
    """Route non-advisory check failures to a fixer or a human decision."""
    required = [
        check
        for check in failures
        if not _advisory(str(check.get("name") or ""), advisory)
    ]
    if not required:
        return []
    names = _safe_check_names(
        sorted({str(check.get("name") or "") for check in required})
    )
    evidence = {"checks": names}
    handler = _CHECK_TRIGGERS.get(ctx.family)
    action = handler(ctx, names, evidence) if handler is not None else None
    if action is not None:
        return action
    return [
        _escalation(
            ctx,
            _EscalationSpec(
                "required_check_failure",
                evidence=evidence,
                recommended_action="fix failing checks or close",
                owner="human",
            ),
        )
    ]


def _jules_checks(
    ctx: _Route, names: list[str], evidence: dict[str, Any]
) -> list[dict[str, Any]]:
    """Trigger Jules to fix the named failing checks."""
    body = (
        "@google-labs-jules These checks are failing on this PR: "
        f"{', '.join(names)}. "
        "Please fix the failures and push to this branch."
    )
    return _trigger_action(
        ctx,
        "jules_checks",
        body,
        _EscalationSpec(
            "required_check_failure",
            evidence=evidence,
            recommended_action="request Jules to fix failing required checks",
        ),
    )


def _coderabbit_checks(
    ctx: _Route, names: list[str], evidence: dict[str, Any]
) -> list[dict[str, Any]] | None:
    """Trigger CodeRabbit fix-ci on bot-authored PRs, else None."""
    if ctx.author_type != "BOT":
        return None
    return _trigger_action(
        ctx,
        "coderabbit_fixci",
        "@coderabbitai fix-ci commit",
        _EscalationSpec(
            "required_check_failure",
            evidence=evidence,
            recommended_action="request CodeRabbit to fix failing CI",
        ),
    )


_CHECK_TRIGGERS = {
    "jules": _jules_checks,
    "coderabbit": _coderabbit_checks,
}


def _advisory_notes(
    ctx: _Route, failures: list[dict[str, Any]], advisory: list[Any]
) -> list[dict[str, Any]]:
    """Emit an ADVISORY_ONLY note listing advisory-pattern check failures."""
    names = sorted(
        {
            str(check.get("name") or "")
            for check in failures
            if _advisory(str(check.get("name") or ""), advisory)
        }
    )
    if not names:
        return []
    return [
        {
            "action": "ADVISORY_ONLY",
            "repository": ctx.repo,
            "pr": ctx.number,
            "url": ctx.pr.get("url"),
            "checks": names,
            "reason": (
                "Stage 1 routine predicates may treat advisory checks as green."
            ),
        }
    ]


def _dependabot_conflict(ctx: _Route, evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Trigger a bounded Dependabot rebase for a conflicted PR."""
    return _conflict_trigger(
        ctx,
        _ConflictSpec(
            "dependabot_rebase",
            "@dependabot rebase",
            "request a bounded conflict rebase",
        ),
        evidence,
    )


def _coderabbit_conflict(ctx: _Route, evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Trigger CodeRabbit conflict resolution for a conflicted PR."""
    return _conflict_trigger(
        ctx,
        _ConflictSpec(
            "coderabbit_conflict",
            "@coderabbitai resolve merge conflict",
            "request merge conflict resolution",
        ),
        evidence,
    )


def _jules_conflict(ctx: _Route, evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Trigger Jules to merge the base branch and resolve conflicts."""
    body = (
        f"@google-labs-jules This PR has merge conflicts with `{ctx.base}`. "
        f"Please merge the latest `{ctx.base}` into this branch, resolve "
        "the conflicts, and push."
    )
    return _conflict_trigger(
        ctx,
        _ConflictSpec(
            "jules_conflict",
            body,
            "request Jules to resolve merge conflicts",
        ),
        evidence,
    )


_CONFLICT_TRIGGERS = {
    "dependabot": _dependabot_conflict,
    "coderabbit": _coderabbit_conflict,
    "jules": _jules_conflict,
}


def _incomplete_check_action(ctx: _Route) -> list[dict[str, Any]]:
    """Return the fail-closed action for a truncated status check rollup."""
    return [
        {
            "action": "CHECKS_INCOMPLETE",
            "repository": ctx.repo,
            "pr": ctx.number,
            "url": ctx.pr.get("url"),
            "head_sha": ctx.head,
            "reason": (
                "status check rollup is truncated or pagination metadata "
                "is unavailable"
            ),
        }
    ]


def _check_failures(pr: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the FAILURE-state check dicts of a normalized PR."""
    return [
        check
        for check in pr.get("checks") or []
        if isinstance(check, dict) and check.get("state") == "FAILURE"
    ]


def _route_checks(ctx: _Route) -> list[dict[str, Any]]:
    """Route failing checks; fail closed when the rollup is truncated."""
    if ctx.pr.get("checksIncomplete"):
        return _incomplete_check_action(ctx)
    failures = _check_failures(ctx.pr)
    advisory = _advisory_patterns(ctx.settings)
    actions = _route_codescene(ctx, failures)
    actions.extend(_route_required_checks(ctx, failures, advisory))
    actions.extend(_advisory_notes(ctx, failures, advisory))
    return actions
