"""Pure blocker-routing decisions for the PR lifecycle unblock stage.

No GitHub or subprocess calls live here: route_pr and its helpers consume a
normalized open-PR inventory entry plus ledger state and return ordered
proposals. All mutating execution is in pr_lifecycle_unblock_apply.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pr_lifecycle_unblock_route_support import (
    _JULES_PREFIXES,  # noqa: F401
    _LINEAGE_RE,  # noqa: F401
    _S2_HANDOFF_PREFIX,  # noqa: F401
    _advisory,
    _advisory_patterns,
    _escalation,
    _family,
    _iso,  # noqa: F401
    _lineage_date,
    _parse_datetime,  # noqa: F401
    _Route,
    _safe_check_names,
    _salvage_replacement,
    _sticky_security,
    _terminal_but_open,
    _trigger_action,
    _trigger_gate,  # noqa: F401
    _unanswered_trigger,  # noqa: F401
    _utc,
)


def _lineage_closable(ctx: _Route) -> bool:
    """True for a bot-authored lineage PR without a security hold."""
    return ctx.family == "lineage" and ctx.author_type == "BOT" and not ctx.security


def _route_stale_lineage(ctx: _Route) -> list[dict[str, Any]] | None:
    """Close a bot lineage docs PR older than the configured stale window."""
    if not _lineage_closable(ctx):
        return None
    lineage_date = _lineage_date(ctx.pr)
    if lineage_date is None:
        return None
    stale_days = ctx.settings.get("lineage_stale_days", 3)
    age_days = (_utc(ctx.now).date() - lineage_date).days
    if age_days <= stale_days:
        return None
    return [
        {
            "action": "CLOSE_STALE_LINEAGE",
            "repository": ctx.repo,
            "pr": ctx.number,
            "url": ctx.pr.get("url"),
            "head_sha": ctx.head,
            "author_type": ctx.author_type,
            "comment": (
                "Closing stale pipeline run-record PR (older than "
                f"{stale_days} days); a newer lineage PR / the runtime "
                "ledger supersedes it. Branch retained — reopen to recover."
            ),
            "age_days": age_days,
        }
    ]


def _route_superseded(
    ctx: _Route,
    ledger_items_for_pr: list[dict[str, Any]],
    ledger: dict[str, Any],
) -> list[dict[str, Any]] | None:
    """Close or escalate a PR superseded by a merged salvage replacement."""
    replacement = _salvage_replacement(ctx.pr, ledger_items_for_pr, ledger)
    if replacement is None:
        return None
    replacement_url = str(replacement.get("url") or "")
    if ctx.author_type == "BOT" and not ctx.security:
        return [
            {
                "action": "CLOSE_SUPERSEDED",
                "repository": ctx.repo,
                "pr": ctx.number,
                "url": ctx.pr.get("url"),
                "head_sha": ctx.head,
                "author_type": ctx.author_type,
                "replacement_url": replacement_url,
                "comment": (
                    f"Superseded by {replacement_url} (merged salvage replacement)."
                ),
            }
        ]
    return [
        _escalation(
            ctx,
            "salvage_replacement_merged",
            evidence={"replacement_url": replacement_url},
            recommended_action=(f"close original as superseded by {replacement_url}"),
        )
    ]


@dataclass(frozen=True)
class _ConflictSpec:
    """The kind, comment body, and action text of a conflict trigger."""

    kind: str
    body: str
    action_text: str


def _conflict_trigger(
    ctx: _Route, spec: _ConflictSpec, evidence: Any
) -> list[dict[str, Any]]:
    """Propose the family-specific merge-conflict fix trigger."""
    return _trigger_action(
        ctx,
        spec.kind,
        spec.body,
        blocker="merge_conflict",
        evidence=evidence,
        recommended_action=spec.action_text,
    )


def _route_conflict(ctx: _Route) -> list[dict[str, Any]] | None:
    """Route a merge conflict to a family fixer or a bounded-salvage decision."""
    mergeable = str(ctx.pr.get("mergeable") or "").upper()
    merge_state = str(ctx.pr.get("mergeStateStatus") or "").upper()
    if mergeable != "CONFLICTING" and merge_state != "DIRTY":
        return None
    evidence = {"mergeable": mergeable, "mergeStateStatus": merge_state}
    handler = _CONFLICT_TRIGGERS.get(ctx.family)
    if handler is not None:
        return handler(ctx, evidence)
    return [
        _escalation(
            ctx,
            "merge_conflict",
            evidence=evidence,
            recommended_action="bounded Stage 2 salvage / conflict repair",
            owner="stage2" if ctx.author_type == "BOT" else "human",
        )
    ]


def _update_branch_action(ctx: _Route) -> list[dict[str, Any]] | None:
    """Return UPDATE_BRANCH for a non-secured bot PR, else None."""
    if ctx.author_type != "BOT" or ctx.security:
        return None
    return [
        {
            "action": "UPDATE_BRANCH",
            "repository": ctx.repo,
            "pr": ctx.number,
            "url": ctx.pr.get("url"),
            "head_sha": ctx.head,
            "author_type": ctx.author_type,
            "expected_head_sha": ctx.head,
        }
    ]


def _route_behind(ctx: _Route) -> list[dict[str, Any]]:
    """Route a behind-base PR to rebase, update-branch, or escalation."""
    merge_state = str(ctx.pr.get("mergeStateStatus") or "").upper()
    if merge_state != "BEHIND":
        return []
    evidence = {"mergeStateStatus": merge_state}
    if ctx.family == "dependabot":
        return _trigger_action(
            ctx,
            "dependabot_rebase",
            "@dependabot rebase",
            blocker="behind_base",
            evidence=evidence,
            recommended_action="request a bounded rebase",
        )
    update = _update_branch_action(ctx)
    if update is not None:
        return update
    return [
        _escalation(
            ctx,
            "behind_base",
            evidence=evidence,
            recommended_action="update the branch from its base or close",
        )
    ]


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
        blocker="codescene_failure",
        evidence={"checks": names},
        recommended_action="run the CodeScene code-health remediation",
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
            "required_check_failure",
            evidence=evidence,
            recommended_action="fix failing checks or close",
            owner="human",
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
        blocker="required_check_failure",
        evidence=evidence,
        recommended_action="request Jules to fix failing required checks",
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
        blocker="required_check_failure",
        evidence=evidence,
        recommended_action="request CodeRabbit to fix failing CI",
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


def _coderabbit_requested(pr: dict[str, Any]) -> bool:
    """True when CodeRabbit's latest review requests changes."""
    return any(
        isinstance(review, dict)
        and str(review.get("state") or "").upper() == "CHANGES_REQUESTED"
        and str((review.get("author") or {}).get("login") or "").lower()
        == "coderabbitai[bot]"
        for review in pr.get("latestReviews") or []
    )


def _coderabbit_review(
    ctx: _Route, evidence: dict[str, Any]
) -> list[dict[str, Any]] | None:
    """Trigger CodeRabbit autofix when its review requested changes on a bot PR."""
    if not _coderabbit_requested(ctx.pr) or ctx.author_type != "BOT":
        return None
    return _trigger_action(
        ctx,
        "coderabbit_autofix",
        "@coderabbitai autofix",
        blocker="changes_requested",
        evidence=evidence,
        recommended_action="request CodeRabbit autofix",
    )


def _jules_review(ctx: _Route, evidence: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Trigger Jules to address review changes on a Jules-family PR."""
    if ctx.family != "jules":
        return None
    return _trigger_action(
        ctx,
        "jules_review",
        "@google-labs-jules Please address the requested changes in the "
        "latest review on this PR and push.",
        blocker="changes_requested",
        evidence=evidence,
        recommended_action="request Jules to address review changes",
    )


_REVIEW_HANDLERS = (_coderabbit_review, _jules_review)


def _review_trigger(ctx: _Route, evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Pick the autofix or Jules trigger for a requested-changes review."""
    for handler in _REVIEW_HANDLERS:
        action = handler(ctx, evidence)
        if action is not None:
            return action
    return [
        _escalation(
            ctx,
            "changes_requested",
            evidence=evidence,
            recommended_action="address requested review changes or close",
        )
    ]


def _route_review(ctx: _Route) -> list[dict[str, Any]]:
    """Route a CHANGES_REQUESTED decision to autofix, Jules, or escalation."""
    if str(ctx.pr.get("reviewDecision") or "").upper() != "CHANGES_REQUESTED":
        return []
    return _review_trigger(ctx, {"reviewDecision": "CHANGES_REQUESTED"})


def _route_ctx(
    pr: dict[str, Any],
    author_type: str,
    ledger_items_for_pr: list[dict[str, Any]],
    settings: dict[str, Any],
    now: datetime,
) -> _Route:
    """Build the shared routing context for one normalized PR."""
    safe_base = _safe_check_names([str(pr.get("baseRefName") or "")])
    return _Route(
        pr=pr,
        author_type=author_type,
        family=_family(pr),
        security=_sticky_security(ledger_items_for_pr),
        settings=settings,
        now=now,
        repo=str(pr.get("repository") or ""),
        number=pr.get("number"),
        head=str(pr.get("headRefOid") or ""),
        base=safe_base[0] if safe_base else "base branch",
    )


def _route_prefix(
    ctx: _Route,
    pr: dict[str, Any],
    ledger_items_for_pr: list[dict[str, Any]],
    ledger: dict[str, Any],
) -> list[dict[str, Any]] | None:
    """Return lineage, salvage, terminal, or draft short-circuit actions."""
    stale = _route_stale_lineage(ctx)
    if stale is not None:
        return stale
    superseded = _route_superseded(ctx, ledger_items_for_pr, ledger)
    if superseded is not None:
        return superseded
    terminal_open = _terminal_but_open(ctx, ledger_items_for_pr)
    if terminal_open is not None:
        return [terminal_open]
    if pr.get("isDraft"):
        return []
    return None


def route_pr(
    pr: dict[str, Any],
    *,
    author_type: str,
    ledger_items_for_pr: list[dict[str, Any]],
    ledger: dict[str, Any],
    settings: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    """Return ordered fix, trigger, advisory, or escalation proposals.

    Consume normalized open-PR inventory and validated unblock settings
    without mutating GitHub or the inputs. Lineage, salvage, and terminal-head
    routes precede draft suppression; conflicts precede other blockers.
    Return an empty list when no proposal is needed, including recent duplicate
    triggers. Security holds prevent close and push-capable proposals.
    """
    ctx = _route_ctx(pr, author_type, ledger_items_for_pr, settings, now)
    prefix = _route_prefix(ctx, pr, ledger_items_for_pr, ledger)
    if prefix is not None:
        return prefix
    conflict = _route_conflict(ctx)
    if conflict is not None:
        return conflict
    actions = _route_behind(ctx)
    actions.extend(_route_checks(ctx))
    actions.extend(_route_review(ctx))
    return actions
