"""Shared helpers for the unblock-stage blocker routing.

No GitHub or subprocess calls live here: these are pure predicates, datetime
utils, and proposal builders consumed by pr_lifecycle_unblock_routing.
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
    "jules/",
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


def _safe_ref_name(value: Any, fallback: str) -> str:
    """Display-sanitize one git ref name, or return fallback when nothing survives."""
    names = _safe_check_names([str(value or "")])
    return names[0] if names else fallback


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


def _trusted_marker_author(comment: dict[str, Any], repo: str) -> bool:
    """Trigger markers only count when authored by the repository owner.

    The executor posts marker comments through the owner's GH_TOKEN identity;
    any other author could pre-post the marker to suppress a real trigger.
    """
    author = comment.get("author")
    login = author.get("login") if isinstance(author, dict) else None
    return isinstance(login, str) and login == repo.split("/", 1)[0]


def _is_dependabot(login: str, branch: str, pr: dict[str, Any]) -> bool:
    """Return whether the login contains 'dependabot'."""
    return "dependabot" in login


def _is_coderabbit(login: str, branch: str, pr: dict[str, Any]) -> bool:
    """Match the CodeRabbit login, or a coderabbit-prefixed same-repo branch.

    The branch prefix alone is attacker-controllable on fork PRs, so it only
    counts when isCrossRepository is false — same rule as the jules family.
    """
    if login == "coderabbitai[bot]":
        return True
    return branch.startswith("coderabbit") and not pr.get("isCrossRepository")


def _is_jules(login: str, branch: str, pr: dict[str, Any]) -> bool:
    """Match a Jules-prefixed branch on a same-repository head.

    The prefix alone is attacker-controllable on fork PRs, so the family
    requires isCrossRepository to be false; fork PRs fall to 'other' and
    are escalated instead of triggering owner-token agent comments.
    """
    return branch.startswith(_JULES_PREFIXES) and not pr.get("isCrossRepository")


def _is_lineage(login: str, branch: str, pr: dict[str, Any]) -> bool:
    """Match a dated docs-lineage branch name."""
    return bool(_LINEAGE_RE.match(str(pr.get("headRefName") or "")))


_FAMILY_RULES = (
    ("dependabot", _is_dependabot),
    ("coderabbit", _is_coderabbit),
    ("jules", _is_jules),
    ("lineage", _is_lineage),
)


def _family(pr: dict[str, Any]) -> str:
    """Choose a routing family from author and branch hints, not identity policy."""
    author = pr.get("author")
    login = str(author.get("login") or "").lower() if isinstance(author, dict) else ""
    branch = str(pr.get("headRefName") or "").lower()
    return next(
        (name for name, matches in _FAMILY_RULES if matches(login, branch, pr)),
        "other",
    )


def _sticky_security(items: list[dict[str, Any]]) -> bool:
    """Report whether any nonterminal ledger item holds or has not yet cleared
    security review — ingested NOT_RUN items block push/close actions too."""
    return any(
        item.get("lifecycle_state") != "TERMINAL"
        and item.get("guardrail_outcome") in {"REVIEW_SECURITY", "NOT_RUN"}
        for item in items
    )


_BLOCKED_OWNERS = ("human", "stage2", "stage3")

_COMMENT_BOT_HINTS = (
    "[bot]",
    "app/",
    "dependabot",
    "snyk",
    "coderabbit",
    "octopus-review",
    "github-actions",
    "sonarcloud",
    "codacy",
    "kilo",
    "jules",
    "cursor",
    "trunk",
    "greptile",
    "devin",
    "renovate",
    "linear",
)


def _comment_is_human(comment: Any) -> bool:
    """True when a PR comment's author is a recognizable human.

    Bot-authored comments (``*-bot`` / ``app/*`` logins and the known reviewer
    and automation bots) never count as human participation. An author that
    cannot be read at all counts as human — the safe direction for an
    automatic close.
    """
    if not isinstance(comment, dict):
        return True
    author = comment.get("author")
    login = str(author.get("login") or "").lower() if isinstance(author, dict) else ""
    if not login:
        return True
    return not any(hint in login for hint in _COMMENT_BOT_HINTS)


def _has_human_comment(pr: dict[str, Any]) -> bool:
    """True when the PR has a human comment, or the history is incomplete."""
    if pr.get("comments_incomplete"):
        return True
    comments = pr.get("comments")
    if not isinstance(comments, list):
        return True
    return any(_comment_is_human(comment) for comment in comments)


def _ledger_owner_hold(items: list[dict[str, Any]]) -> str | None:
    """Return the non-stage1 owner holding a nonterminal item, else None.

    A ledger item owned by ``human``, ``stage2``, or ``stage3`` means another
    stage or a person already owns the next step, so a plain ``--apply`` must
    not mutate the PR (no close, trigger, or push). The hold lives in the
    ledger, not only in the Stage 1 wrapper prompt.
    """
    owners = [
        str(item.get("current_owner") or "")
        for item in items
        if item.get("lifecycle_state") != "TERMINAL"
    ]
    return next((owner for owner in _BLOCKED_OWNERS if owner in owners), None)


@dataclass(frozen=True)
class _EscalationSpec:
    """The escalation details: blocker name, evidence, action, ownership."""

    blocker: str
    evidence: Any
    recommended_action: str
    owner: str = "human"
    security: bool | None = None


def _escalation(ctx: _Route, spec: _EscalationSpec) -> dict[str, Any]:
    """Build an escalation proposal with evidence, owner, and a leave-open default.

    ``security`` defaults to the route's sticky hold; pass an explicit value
    when the flag comes from a single ledger item rather than the whole set.
    """
    hold = ctx.security if spec.security is None else spec.security
    human_or_security = ctx.author_type != "BOT" or hold or spec.owner == "human"
    return {
        "action": "ESCALATE",
        "repository": ctx.pr.get("repository"),
        "pr": ctx.pr.get("number"),
        "url": ctx.pr.get("url"),
        "head_sha": ctx.pr.get("headRefOid"),
        "author_type": ctx.author_type,
        "blocker": spec.blocker,
        "evidence": spec.evidence,
        "recommended_action": spec.recommended_action,
        "security": hold,
        "safe_default": (
            "Leave open; no merge or close without a human decision."
            if human_or_security
            else "Leave open until the next owner acts."
        ),
        "owner": spec.owner,
    }


def _trigger_blocked(ctx: _Route, kind: str) -> bool:
    """Return whether security, repository, or ownership rules block a trigger.

    Security holds, fork heads, and a missing isCrossRepository flag block
    every kind. On same-repository heads, CodeScene and Jules-family triggers
    do not require BOT ownership.
    """
    if ctx.security or ctx.pr.get("isCrossRepository", True):
        return True
    return kind != "codescene" and ctx.author_type != "BOT" and ctx.family != "jules"


def _trigger_skipped(ctx: _Route, kind: str) -> list[dict[str, Any]]:
    """Return the TRIGGER_SKIPPED entry for unverified comment history."""
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


def _trigger_gate(
    ctx: _Route, kind: str, spec: _EscalationSpec
) -> list[dict[str, Any]] | None:
    """Return a non-trigger proposal when policy or history blocks triggering."""
    if _trigger_blocked(ctx, kind):
        return [_escalation(ctx, spec)]
    if ctx.pr.get("comments_incomplete"):
        return _trigger_skipped(ctx, kind)
    return None


def _unanswered_trigger(
    ctx: _Route, kind: str, comment: dict[str, Any]
) -> list[dict[str, Any]]:
    """Suppress a fresh duplicate marker; escalate an expired or undated one."""
    created = _parse_datetime(comment.get("createdAt"))
    expiry = _trigger_expiry_days(ctx.settings)
    if created is not None and _utc(ctx.now) - created <= timedelta(days=expiry):
        return []
    sent = comment.get("createdAt") or "unknown date"
    return [
        _escalation(
            ctx,
            _EscalationSpec(
                "trigger_unanswered",
                evidence={"kind": kind, "sent": sent},
                recommended_action=(
                    f"trigger {kind} sent {sent} without a new push; "
                    "decide fix/close"
                ),
            ),
        )
    ]


def _trigger_action(
    ctx: _Route, kind: str, body: str, spec: _EscalationSpec
) -> list[dict[str, Any]]:
    """Propose a trigger only after ownership, security, and history checks.

    Deduplicate by trigger kind and head SHA. Return no action for a recent
    matching marker, or escalate an expired or undated matching trigger.
    """
    gated = _trigger_gate(ctx, kind, spec)
    if gated is not None:
        return gated
    marker = f"<!-- pr-lifecycle-trigger kind={kind} head={ctx.head} -->"
    matching = [
        comment
        for comment in ctx.pr.get("comments") or []
        if isinstance(comment, dict)
        and marker in str(comment.get("body") or "")
        and _trusted_marker_author(comment, ctx.repo)
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


def _valid_days(value: Any) -> bool:
    """Require a positive int day count (bool excluded)."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _trigger_expiry_days(settings: dict[str, Any]) -> int:
    """Return the configured unanswered-trigger expiry, defaulting to 3."""
    expiry = settings.get("trigger_expiry_days", 3)
    return expiry if _valid_days(expiry) else 3


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


def _terminal_items(
    ledger_items_for_pr: list[dict[str, Any]], ledger: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return terminal items from the ledger plus this PR's terminal items."""
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
    return items


def _is_salvage_replacement(replacement: dict[str, Any], pr: dict[str, Any]) -> bool:
    """True for a merged Stage 2 replacement whose evidence cites this PR."""
    if not str(replacement.get("terminal_disposition") or "").startswith("MERGED_"):
        return False
    handoffs = replacement.get("handoffs") or []
    if not handoffs or not str(handoffs[0]).startswith(_S2_HANDOFF_PREFIX):
        return False
    if replacement.get("url") == pr.get("url"):
        return False
    return pr.get("url") in (replacement.get("evidence_urls") or [])


def _salvage_replacement(
    pr: dict[str, Any],
    ledger_items_for_pr: list[dict[str, Any]],
    ledger: dict[str, Any],
) -> dict[str, Any] | None:
    """Find a merged Stage 2 replacement whose evidence links to this PR."""
    return next(
        (
            item
            for item in _terminal_items(ledger_items_for_pr, ledger)
            if _is_salvage_replacement(item, pr)
        ),
        None,
    )


def _terminal_but_open(
    ctx: _Route, ledger_items_for_pr: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Escalate an open head marked terminal when no active ledger item exists."""
    if any(item.get("lifecycle_state") != "TERMINAL" for item in ledger_items_for_pr):
        return None
    key = f"{ctx.pr.get('repository')}#{ctx.pr.get('number')}@{ctx.head}"
    item = next(
        (
            i
            for i in ledger_items_for_pr
            if i.get("lifecycle_state") == "TERMINAL" and i.get("key") == key
        ),
        None,
    )
    if item is None:
        return None
    return _escalation(
        ctx,
        _EscalationSpec(
            "ledger_terminal_but_open",
            evidence={"terminal_disposition": item.get("terminal_disposition")},
            recommended_action=(
                "PR is open but ledger says "
                f"{item.get('terminal_disposition')}: close it or confirm it "
                "should be re-reviewed"
            ),
            security=item.get("guardrail_outcome") == "REVIEW_SECURITY",
        ),
    )
