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
