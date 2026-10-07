"""Pure blocker-routing decisions for the PR lifecycle unblock stage.

No GitHub or subprocess calls live here: route_pr and its helpers consume a
normalized open-PR inventory entry plus ledger state and return ordered
proposals. All mutating execution is in pr_lifecycle_unblock_apply.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

_JULES_PREFIXES = (
    "sentinel/",
    "sentinel-",
    "bolt/",
    "bolt-",
    "palette/",
    "palette-",
    "jules-",
)
_LINEAGE_RE = re.compile(r"^pr-lifecycle-docs-(\d{8})")
# Stage 2 ledger handoff event ids mark a salvage replacement's origin.
_S2_HANDOFF_PREFIX = "evt-s2-"


def _utc(value: datetime) -> datetime:
    """Convert a datetime to UTC, treating naive values as already in UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    """Format a datetime as a UTC timestamp with second precision."""
    return _utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_datetime(value: object) -> datetime | None:
    """Parse an ISO timestamp as UTC, returning None for invalid input."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _utc(parsed)


def _safe_check_names(names: list[str]) -> list[str]:
    """Sanitize up to ten check names and cap each result at 80 characters."""
    safe: list[str] = []
    for name in names[:10]:
        if not isinstance(name, str):
            continue
        cleaned = re.sub(r"[^\w .:/()\-]", "", name)[:80]
        if cleaned:
            safe.append(cleaned)
    return safe


@dataclass(frozen=True)
class _Route:
    """Per-PR routing context: identity, family, security, and safe fields."""

    pr: dict[str, Any]
    author_type: str
    family: str
    security: bool
    settings: dict[str, Any]
    now: datetime
    repo: str
    number: Any
    head: str
    base: str


def _family(pr: dict[str, Any]) -> str:
    """Choose a routing family from author and branch hints, not identity policy."""
    author = pr.get("author")
    login = str(author.get("login") or "").lower() if isinstance(author, dict) else ""
    branch = str(pr.get("headRefName") or "").lower()
    if "dependabot" in login:
        return "dependabot"
    if login == "coderabbitai[bot]" or branch.startswith("coderabbit"):
        return "coderabbit"
    if branch.startswith(_JULES_PREFIXES):
        return "jules"
    if _LINEAGE_RE.match(str(pr.get("headRefName") or "")):
        return "lineage"
    return "other"


def _sticky_security(items: list[dict[str, Any]]) -> bool:
    """Report whether any nonterminal ledger item retains a security hold."""
    return any(
        item.get("lifecycle_state") != "TERMINAL"
        and item.get("guardrail_outcome") == "REVIEW_SECURITY"
        for item in items
    )


def _escalation(
    ctx: _Route,
    blocker: str,
    *,
    evidence: Any,
    recommended_action: str,
    owner: str = "human",
    security: bool | None = None,
) -> dict[str, Any]:
    """Build an escalation proposal with evidence, owner, and a leave-open default.

    ``security`` defaults to the route's sticky hold; pass an explicit value
    when the flag comes from a single ledger item rather than the whole set.
    """
    hold = ctx.security if security is None else security
    human_or_security = ctx.author_type != "BOT" or hold or owner == "human"
    return {
        "action": "ESCALATE",
        "repository": ctx.pr.get("repository"),
        "pr": ctx.pr.get("number"),
        "url": ctx.pr.get("url"),
        "head_sha": ctx.pr.get("headRefOid"),
        "author_type": ctx.author_type,
        "blocker": blocker,
        "evidence": evidence,
        "recommended_action": recommended_action,
        "security": hold,
        "safe_default": (
            "Leave open; no merge or close without a human decision."
            if human_or_security
            else "Leave open until the next owner acts."
        ),
        "owner": owner,
    }


def _trigger_gate(
    ctx: _Route,
    kind: str,
    blocker: str,
    evidence: Any,
    recommended_action: str,
) -> list[dict[str, Any]] | None:
    """Return a non-trigger proposal when policy or history blocks triggering."""
    if ctx.security or (
        kind != "codescene" and ctx.author_type != "BOT" and ctx.family != "jules"
    ):
        return [
            _escalation(
                ctx,
                blocker,
                evidence=evidence,
                recommended_action=recommended_action,
            )
        ]
    if ctx.pr.get("comments_incomplete"):
        return [
            {
                "action": "TRIGGER_SKIPPED",
                "repository": ctx.pr.get("repository"),
                "pr": ctx.pr.get("number"),
                "url": ctx.pr.get("url"),
                "head_sha": ctx.pr.get("headRefOid"),
                "author_type": ctx.author_type,
                "kind": kind,
                "reason": "comment history unavailable; marker dedupe unverified",
            }
        ]
    return None


def _unanswered_trigger(
    ctx: _Route, kind: str, comment: dict[str, Any]
) -> list[dict[str, Any]]:
    """Suppress a fresh duplicate marker; escalate an expired or undated one."""
    created = _parse_datetime(comment.get("createdAt"))
    expiry = ctx.settings.get("trigger_expiry_days", 3)
    if not isinstance(expiry, int) or isinstance(expiry, bool) or expiry < 1:
        expiry = 3
    if created is not None and _utc(ctx.now) - created <= timedelta(days=expiry):
        return []
    sent = comment.get("createdAt") or "unknown date"
    return [
        _escalation(
            ctx,
            "trigger_unanswered",
            evidence={"kind": kind, "sent": sent},
            recommended_action=(
                f"trigger {kind} sent {sent} without a new push; decide fix/close"
            ),
        )
    ]


def _trigger_action(
    ctx: _Route,
    kind: str,
    body: str,
    *,
    blocker: str,
    evidence: Any,
    recommended_action: str,
) -> list[dict[str, Any]]:
    """Propose a trigger only after ownership, security, and history checks.

    Deduplicate by trigger kind and head SHA. Return no action for a recent
    matching marker, or escalate an expired or undated matching trigger.
    """
    gated = _trigger_gate(ctx, kind, blocker, evidence, recommended_action)
    if gated is not None:
        return gated
    marker = f"<!-- pr-lifecycle-trigger kind={kind} head={ctx.head} -->"
    matching = [
        comment
        for comment in ctx.pr.get("comments") or []
        if isinstance(comment, dict) and marker in str(comment.get("body") or "")
    ]
    if matching:
        return _unanswered_trigger(ctx, kind, matching[-1])
    return [
        {
            "action": "TRIGGER",
            "repository": ctx.pr.get("repository"),
            "pr": ctx.pr.get("number"),
            "url": ctx.pr.get("url"),
            "head_sha": ctx.head,
            "author_type": ctx.author_type,
            "kind": kind,
            "body": f"{body.rstrip()}\n\n{marker}",
            "marker": marker,
        }
    ]


def _advisory(name: str, patterns: list[str]) -> bool:
    """Match a check name against exact names or trailing-asterisk prefixes."""
    return any(
        name.startswith(pattern[:-1]) if pattern.endswith("*") else name == pattern
        for pattern in patterns
    )


def _advisory_patterns(settings: dict[str, Any]) -> list[Any]:
    """Return the configured advisory patterns list, defaulting to empty."""
    patterns = settings.get("advisory_checks", [])
    return patterns if isinstance(patterns, list) else []


def _lineage_date(pr: dict[str, Any]) -> date | None:
    """Extract a docs lineage branch date, returning None if absent or invalid."""
    match = _LINEAGE_RE.match(str(pr.get("headRefName") or ""))
    if match is None:
        return None
    try:
        return (
            datetime.strptime(match.group(1), "%Y%m%d")
            .replace(tzinfo=timezone.utc)
            .date()
        )
    except ValueError:
        return None


def _salvage_replacement(
    pr: dict[str, Any],
    ledger_items_for_pr: list[dict[str, Any]],
    ledger: dict[str, Any],
) -> dict[str, Any] | None:
    """Find a merged Stage 2 replacement whose evidence links to this PR."""
    items = [
        item
        for item in (ledger.get("items") or [])
        if isinstance(item, dict) and item.get("lifecycle_state") == "TERMINAL"
    ]
    items.extend(
        item
        for item in ledger_items_for_pr
        if item.get("lifecycle_state") == "TERMINAL" and item not in items
    )
    for replacement in items:
        if not str(replacement.get("terminal_disposition") or "").startswith("MERGED_"):
            continue
        handoffs = replacement.get("handoffs") or []
        evidence_urls = replacement.get("evidence_urls") or []
        if (
            handoffs
            and str(handoffs[0]).startswith(_S2_HANDOFF_PREFIX)
            and replacement.get("url") != pr.get("url")
            and pr.get("url") in evidence_urls
        ):
            return replacement
    return None


def _terminal_but_open(
    ctx: _Route, ledger_items_for_pr: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Escalate an open head marked terminal when no active ledger item exists."""
    if any(item.get("lifecycle_state") != "TERMINAL" for item in ledger_items_for_pr):
        return None
    for item in ledger_items_for_pr:
        key = f"{ctx.pr.get('repository')}#{ctx.pr.get('number')}@{ctx.head}"
        if item.get("lifecycle_state") == "TERMINAL" and item.get("key") == key:
            return _escalation(
                ctx,
                "ledger_terminal_but_open",
                evidence={"terminal_disposition": item.get("terminal_disposition")},
                recommended_action=(
                    "PR is open but ledger says "
                    f"{item.get('terminal_disposition')}: close it or confirm it "
                    "should be re-reviewed"
                ),
                security=item.get("guardrail_outcome") == "REVIEW_SECURITY",
            )
    return None


def _route_stale_lineage(ctx: _Route) -> list[dict[str, Any]] | None:
    """Close a bot lineage docs PR older than the configured stale window."""
    if ctx.family != "lineage" or ctx.author_type != "BOT" or ctx.security:
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


def _conflict_trigger(
    ctx: _Route, kind: str, body: str, evidence: Any, action_text: str
) -> list[dict[str, Any]]:
    """Propose the family-specific merge-conflict fix trigger."""
    return _trigger_action(
        ctx,
        kind,
        body,
        blocker="merge_conflict",
        evidence=evidence,
        recommended_action=action_text,
    )


def _route_conflict(ctx: _Route) -> list[dict[str, Any]] | None:
    """Route a merge conflict to a family fixer or a bounded-salvage decision."""
    mergeable = str(ctx.pr.get("mergeable") or "").upper()
    merge_state = str(ctx.pr.get("mergeStateStatus") or "").upper()
    if mergeable != "CONFLICTING" and merge_state != "DIRTY":
        return None
    evidence = {"mergeable": mergeable, "mergeStateStatus": merge_state}
    if ctx.family == "dependabot":
        return _conflict_trigger(
            ctx,
            "dependabot_rebase",
            "@dependabot rebase",
            evidence,
            "request a bounded conflict rebase",
        )
    if ctx.family == "coderabbit":
        return _conflict_trigger(
            ctx,
            "coderabbit_conflict",
            "@coderabbitai resolve merge conflict",
            evidence,
            "request merge conflict resolution",
        )
    if ctx.family == "jules":
        body = (
            f"@google-labs-jules This PR has merge conflicts with `{ctx.base}`. "
            f"Please merge the latest `{ctx.base}` into this branch, resolve "
            "the conflicts, and push."
        )
        return _conflict_trigger(
            ctx,
            "jules_conflict",
            body,
            evidence,
            "request Jules to resolve merge conflicts",
        )
    return [
        _escalation(
            ctx,
            "merge_conflict",
            evidence=evidence,
            recommended_action="bounded Stage 2 salvage / conflict repair",
            owner="stage2" if ctx.author_type == "BOT" else "human",
        )
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
    if ctx.author_type == "BOT" and not ctx.security:
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
    if ctx.family == "jules":
        body = (
            f"@google-labs-jules These checks are failing on this PR: "
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
    if ctx.family == "coderabbit" and ctx.author_type == "BOT":
        return _trigger_action(
            ctx,
            "coderabbit_fixci",
            "@coderabbitai fix-ci commit",
            blocker="required_check_failure",
            evidence=evidence,
            recommended_action="request CodeRabbit to fix failing CI",
        )
    return [
        _escalation(
            ctx,
            "required_check_failure",
            evidence=evidence,
            recommended_action="fix failing checks or close",
            owner="human",
        )
    ]


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


def _route_checks(ctx: _Route) -> list[dict[str, Any]]:
    """Route failing checks; fail closed when the rollup is truncated."""
    if ctx.pr.get("checksIncomplete"):
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
    failures = [
        check
        for check in ctx.pr.get("checks") or []
        if isinstance(check, dict) and check.get("state") == "FAILURE"
    ]
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


def _route_review(ctx: _Route) -> list[dict[str, Any]]:
    """Route a CHANGES_REQUESTED decision to autofix, Jules, or escalation."""
    if str(ctx.pr.get("reviewDecision") or "").upper() != "CHANGES_REQUESTED":
        return []
    evidence = {"reviewDecision": "CHANGES_REQUESTED"}
    if _coderabbit_requested(ctx.pr) and ctx.author_type == "BOT":
        return _trigger_action(
            ctx,
            "coderabbit_autofix",
            "@coderabbitai autofix",
            blocker="changes_requested",
            evidence=evidence,
            recommended_action="request CodeRabbit autofix",
        )
    if ctx.family == "jules":
        return _trigger_action(
            ctx,
            "jules_review",
            "@google-labs-jules Please address the requested changes in the "
            "latest review on this PR and push.",
            blocker="changes_requested",
            evidence=evidence,
            recommended_action="request Jules to address review changes",
        )
    return [
        _escalation(
            ctx,
            "changes_requested",
            evidence=evidence,
            recommended_action="address requested review changes or close",
        )
    ]


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
    safe_base = _safe_check_names([str(pr.get("baseRefName") or "")])
    ctx = _Route(
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
    conflict = _route_conflict(ctx)
    if conflict is not None:
        return conflict
    actions = _route_behind(ctx)
    actions.extend(_route_checks(ctx))
    actions.extend(_route_review(ctx))
    return actions
