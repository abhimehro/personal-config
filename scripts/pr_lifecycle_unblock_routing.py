"""Pure blocker-routing decisions for the PR lifecycle unblock stage.

No GitHub or subprocess calls live here: route_pr and its helpers consume a
normalized open-PR inventory entry plus ledger state and return ordered
proposals. All mutating execution is in pr_lifecycle_unblock_apply.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pr_lifecycle_unblock_route_checks import _CONFLICT_TRIGGERS, _route_checks
from pr_lifecycle_unblock_route_support import (
    _JULES_PREFIXES,  # noqa: F401
    _LINEAGE_RE,  # noqa: F401
    _S2_HANDOFF_PREFIX,  # noqa: F401
    _advisory,  # noqa: F401
    _enforce_ledger_owner,
    _escalation,
    _EscalationSpec,
    _family,
    _has_human_comment,
    _iso,  # noqa: F401
    _lineage_date,
    _parse_datetime,  # noqa: F401
    _Route,
    _safe_check_names,  # noqa: F401
    _safe_ref_name,
    _salvage_replacement,
    _sticky_security,
    _terminal_but_open,
    _trigger_action,
    _trigger_gate,  # noqa: F401
    _unanswered_trigger,  # noqa: F401
    _utc,
)


def _lineage_closable(ctx: _Route) -> bool:
    """True for a bot lineage PR with no security hold or human comment.

    Bot-authored comments (Snyk, reviewer bots, app/* logins) never count as
    human participation, so they cannot hold a stale-lineage close; an
    unreadable author or incomplete history holds it.
    """
    return (
        ctx.family == "lineage"
        and ctx.author_type == "BOT"
        and not ctx.security
        and not _has_human_comment(ctx.pr)
    )


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
            _EscalationSpec(
                "salvage_replacement_merged",
                evidence={"replacement_url": replacement_url},
                recommended_action=(
                    f"close original as superseded by {replacement_url}"
                ),
            ),
        )
    ]


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
            _EscalationSpec(
                "merge_conflict",
                evidence=evidence,
                recommended_action="bounded Stage 2 salvage / conflict repair",
                owner="stage2" if ctx.author_type == "BOT" else "human",
            ),
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
            _EscalationSpec(
                "behind_base",
                evidence=evidence,
                recommended_action="request a bounded rebase",
            ),
        )
    update = _update_branch_action(ctx)
    if update is not None:
        return update
    return [
        _escalation(
            ctx,
            _EscalationSpec(
                "behind_base",
                evidence=evidence,
                recommended_action="update the branch from its base or close",
            ),
        )
    ]


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
        _EscalationSpec(
            "changes_requested",
            evidence=evidence,
            recommended_action="request CodeRabbit autofix",
        ),
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
        _EscalationSpec(
            "changes_requested",
            evidence=evidence,
            recommended_action="request Jules to address review changes",
        ),
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
            _EscalationSpec(
                "changes_requested",
                evidence=evidence,
                recommended_action="address requested review changes or close",
            ),
        )
    ]


def _route_review(ctx: _Route) -> list[dict[str, Any]]:
    """Route a CHANGES_REQUESTED decision to autofix, Jules, or escalation."""
    if str(ctx.pr.get("reviewDecision") or "").upper() != "CHANGES_REQUESTED":
        return []
    return _review_trigger(ctx, {"reviewDecision": "CHANGES_REQUESTED"})


def _route_octopus_findings(ctx: _Route) -> list[dict[str, Any]]:
    """Escalate open Octopus review findings; they block routine merge."""
    findings = ctx.pr.get("openOctopusFindings")
    if findings == 0:
        return []
    unknown = findings is None
    action = "verify the Octopus review threads on the PR (thread list truncated or unreadable), then resolve or close"
    if not unknown:
        action = "resolve the open Octopus review findings on the PR or close it"
    return [
        _escalation(
            ctx,
            _EscalationSpec(
                "open_octopus_findings",
                evidence={"open_octopus_findings": "unknown" if unknown else findings},
                recommended_action=action,
            ),
        )
    ]


@dataclass(frozen=True)
class _RouteArgs:
    """The non-PR routing inputs carried through to _route_ctx."""

    author_type: str
    ledger_items_for_pr: list[dict[str, Any]]
    ledger: dict[str, Any]
    settings: dict[str, Any]
    now: datetime


def _route_ctx(pr: dict[str, Any], args: _RouteArgs) -> _Route:
    """Build the shared routing context for one normalized PR."""
    safe_base = _safe_ref_name(pr.get("baseRefName"), "base branch")
    return _Route(
        pr=pr,
        author_type=args.author_type,
        family=_family(pr),
        security=_sticky_security(args.ledger_items_for_pr),
        settings=args.settings,
        now=args.now,
        repo=str(pr.get("repository") or ""),
        number=pr.get("number"),
        head=str(pr.get("headRefOid") or ""),
        base=safe_base,
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


def route_pr(pr: dict[str, Any], args: _RouteArgs) -> list[dict[str, Any]]:
    """Return ordered fix, trigger, advisory, or escalation proposals.

    Consume normalized open-PR inventory and validated unblock settings
    without mutating GitHub or the inputs. Lineage, salvage, and terminal-head
    routes precede draft suppression; conflicts precede other blockers.
    Return an empty list when no proposal is needed, including recent duplicate
    triggers. Security holds prevent close and push-capable proposals.
    Open or unknown Octopus findings always escalate: automatic close actions
    are suppressed and the escalation is kept alongside any other blockers.
    """
    ctx = _route_ctx(pr, args)
    octopus = _route_octopus_findings(ctx)
    actions = _route_candidates(ctx, pr, args, octopus)
    return _enforce_ledger_owner(ctx, actions, args.ledger_items_for_pr)


def _route_candidates(
    ctx: _Route,
    pr: dict[str, Any],
    args: _RouteArgs,
    octopus: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return every proposal routing would make, before the owner hold."""
    prefix = _route_prefix(ctx, pr, args.ledger_items_for_pr, args.ledger)
    if prefix is not None:
        if not octopus:
            return prefix
        actions = [
            action
            for action in prefix
            if not str(action.get("action") or "").startswith("CLOSE")
        ]
        actions.extend(octopus)
        return actions
    conflict = _route_conflict(ctx)
    if conflict is not None:
        return conflict + octopus
    actions = _route_behind(ctx)
    actions.extend(_route_checks(ctx))
    actions.extend(_route_review(ctx))
    actions.extend(octopus)
    return actions
