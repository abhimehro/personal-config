#!/usr/bin/env python3
"""Detect Stage 2 starvation and summarize salvage-eligible ledger stock.

Read a fetched runtime ledger (never the main-branch pointer). Exit 2 when
Stage 2 would empty-intake while salvage-eligible BOT items remain. This is
observability for PR Desk and CI; it does not CAS-write, launch stages, or
merge PRs.

CLI validates JSON Schema and runtime-record invariants on the fetched ledger.
It does not validate Cursor exports or prompts. `summarize()` still accepts
minimal mappings so unit tests can classify without a full schema document.

Salvage-eligible matches the lifecycle contract: BOT, nonterminal,
`current_owner` in {stage1, stage3}, not REVIEW_SECURITY, sticky paths empty
or only generated_output, not HOLD_PLATFORM / HOLD_CANONICAL / PASS_ROUTINE /
CLOSE_NONSECURITY_NOOP, and a mechanical next_action (unique-source draft,
wrap, lint, import, non-major pin, missing tests, conflict markers, DIRTY
unique remaining). Lockfile, workflow, auth, secrets, WAITING_HUMAN, Stage 2
owned stock, and any other remaining sticky label stay out. Expired mechanical
`next_action` still counts; SHA_MATCH skip applies only to unexpired
non-executable work.

`PipelineHealth.stage2_work_item_count` is complete unexpired work items, not
`len(stage2_work_items)`. Expired, malformed, or empty-required-string records
do not suppress starvation. `stage2_owned_item_count` is observational for
the health flag: a Stage 2-owned ledger item without a usable work item
does not hide EMPTY_INTAKE. Cascade CLAIM still passes that count as
`stage2_owned_materializable` so Stage 2 proceeds to materialize.

Option 3 (2026-09-24): `is_reselect_salvage_candidate` is a separate Stage 1
enqueue predicate for live CONFLICTING/DIRTY ledger-BOT stock with unique
remaining. It does not widen `is_salvage_eligible` (monitor starvation stays
unchanged). Soft sticky `shell_execution` is allowed only for Palette wrap
with a tight path allowlist. Never-touch (Seatek#692, ctrld#1206 CSPRNG,
Hydro Sentinel / REVIEW_SECURITY / HUMAN sticky, real HOLD_PLATFORM) stays out.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position
from pr_identity import identities_match
from pr_lifecycle_health_runtime import (  # noqa: F401 -- re-exported
    REQUIRED_WORK_ITEM_FIELDS,
    STAGE2_OWNED_STATES,
    _clock,
    _ledger_items,
    _ledger_revision,
    _load_runtime_ledger,
    _print_report,
    _stage2_owned,
    _usable_work_items,
    existing_wi_prefixes,
    parse_expiry_utc,
    source_pr_prefix,
    work_item_is_usable,
)
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

LOGGER = logging.getLogger(__name__)

__all__ = [
    "AUTHORITATIVE_MERGEABLE_STATES",
    "MECHANICAL_RESELECT_NA",
    "NON_SALVAGE_OUTCOMES",
    "REQUIRED_WORK_ITEM_FIELDS",
    "SALVAGE_OUTCOMES",
    "STAGE2_OWNED_STATES",
    "LivePrSignals",
    "PipelineHealth",
    "ReselectAuthorGate",
    "ReselectSignals",
    "existing_wi_prefixes",
    "is_never_touch_key",
    "is_reselect_plausible",
    "is_reselect_salvage_candidate",
    "is_salvage_eligible",
    "list_reselect_candidates",
    "non_journal_paths",
    "parse_expiry_utc",
    "signal_value",
    "source_pr_prefix",
    "summarize",
    "work_item_is_usable",
]

NON_SALVAGE_OUTCOMES = frozenset(
    {
        "REVIEW_SECURITY",
        "HOLD_PLATFORM",
        "HOLD_CANONICAL",
        "PASS_ROUTINE",
        "CLOSE_NONSECURITY_NOOP",
        "ANALYSIS_ERROR",
    }
)
SALVAGE_OUTCOMES = frozenset({"HOLD_CONTRACT", "HOLD_EVIDENCE", "NOT_RUN"})
# Allowlist: unknown owners fail closed. Stage 2 already owns its queue.
AUTOMATED_SALVAGE_OWNERS = frozenset({"stage1", "stage3"})
PROHIBITED_NEXT_ACTION = re.compile(
    r"\bdo not (import|lint|wrap|pin|test)\b|" r"\bdon't (import|lint|wrap|pin|test)\b",
    re.IGNORECASE,
)
MECHANICAL_PATTERNS = (
    re.compile(r"recover unique source", re.IGNORECASE),
    re.compile(r"focused draft", re.IGNORECASE),
    re.compile(r"conflict.?marker", re.IGNORECASE),
    re.compile(r"\bwrap\b", re.IGNORECASE),
    re.compile(r"\blint\b", re.IGNORECASE),
    re.compile(r"\bimport\b", re.IGNORECASE),
    re.compile(r"TYPE_CHECKING", re.IGNORECASE),
    re.compile(r"unique remaining", re.IGNORECASE),
    re.compile(r"\bDIRTY\b"),
    re.compile(r"non-?major pin", re.IGNORECASE),
    re.compile(r"missing tests?", re.IGNORECASE),
)
MAJOR_DEP_BLOCK = re.compile(
    r"major-?dep|lockfile|pandas 3|opencv|workflow pin|uv\.lock",
    re.IGNORECASE,
)
CONFIG_PATH = ROOT / "tasks/pr-review-agent.config.yaml"

# Option 3 reselect: never invent whole-PR rebase; never-touch stays human/Desk.
NEVER_TOUCH_PR_PREFIXES = frozenset(
    {
        "abhimehro/Seatek_Analysis#692",
        "abhimehro/ctrld-sync#1206",
    }
)
RESELECT_LIVE_STATES = frozenset({"CONFLICTING", "DIRTY"})
RESELECT_SOFT_STICKY = frozenset({"shell_execution"})
RESELECT_TITLE_PREFIXES = (
    "⚡ Bolt",
    "🎨 Palette",
    "salvage(",
    "chore(qa)",
    "chore(repo-health)",
)
AUTHORITATIVE_MERGEABLE_STATES = frozenset(
    {
        "CONFLICTING",
        "DIRTY",
        "MERGEABLE",
        "CLEAN",
        "BLOCKED",
        "BEHIND",
        "UNSTABLE",
        "HAS_HOOKS",
    }
)
NORMALIZED_RESELECT_TITLE_PREFIXES = (
    "⚡bolt",
    "🎨palette",
    "salvage(",
    "chore(qa)",
    "chore(repo-health)",
)
_TITLE_VARIATION_SELECTORS = ("\ufe0f", "\ufe0e")
# Soft shell_execution only when every non-journal path matches Palette wrap.
PALETTE_WRAP_PATH_ALLOW = (
    re.compile(r"(^|/)analytics_dashboard\.sh$"),
    re.compile(r"(^|/)maintenance/bin/.*\.sh$"),
    re.compile(r"docs/cursor-automations/"),
)
JOURNAL_PATH_RE = re.compile(r"(^|/)\.jules/")
LIVE_STATE_IN_TEXT = re.compile(r"\b(CONFLICTING|DIRTY)\b")
MECHANICAL_RESELECT_NA = (
    "Recover unique source only on a new focused draft that excludes "
    "journals and sticky paths outside the work-item allowlist."
)


@dataclass(frozen=True)
class PipelineHealth:
    """Starvation report. stage2_work_item_count is complete unexpired WIs."""

    ledger_revision: int
    stage2_work_item_count: int
    stage2_owned_item_count: int
    salvage_eligible_count: int
    salvage_eligible_keys: tuple[str, ...]
    reselect_candidate_count: int
    starvation: bool
    reason: str


def _has_blocking_sticky(item: dict[str, Any]) -> bool:
    sticky = set(item.get("sensitive_paths") or []) - {"generated_output"}
    return bool(sticky)


def _identity_blocks_salvage(item: dict[str, Any]) -> bool:
    return (
        item.get("author_type") != "BOT"
        or item.get("lifecycle_state") == "TERMINAL"
        or item.get("current_owner") not in AUTOMATED_SALVAGE_OWNERS
    )


def _outcome_blocks_salvage(item: dict[str, Any]) -> bool:
    outcome = item.get("guardrail_outcome") or ""
    return outcome in NON_SALVAGE_OUTCOMES or outcome not in SALVAGE_OUTCOMES


def _next_action_is_mechanical(next_action: str) -> bool:
    if not next_action or PROHIBITED_NEXT_ACTION.search(next_action):
        return False
    unique_source = "Recover unique source" in next_action
    if MAJOR_DEP_BLOCK.search(next_action) and not unique_source:
        return False
    return any(pattern.search(next_action) for pattern in MECHANICAL_PATTERNS)


def is_salvage_eligible(item: dict[str, Any]) -> bool:
    """Return True when a ledger item should feed a complete Stage 2 work item."""
    if _identity_blocks_salvage(item) or _outcome_blocks_salvage(item):
        return False
    if _has_blocking_sticky(item):
        return False
    return _next_action_is_mechanical(item.get("next_action") or "")


def is_never_touch_key(key: object) -> bool:
    """Identify the two hard never-touch source PRs, ignoring any @SHA suffix."""
    # Seatek_Analysis#692 (journals) and ctrld-sync#1206 (CSPRNG).
    return source_pr_prefix(key) in NEVER_TOUCH_PR_PREFIXES


_BUILTIN_RESELECT_AUTHORS = (
    "dependabot[bot]",
    "renovate[bot]",
    "google-labs-jules[bot]",
    "cursor[bot]",
    "devin[bot]",
    "copilot[bot]",
    "app/copilot-swe-agent",
    "abhimehro",
)


def _reselect_authors_from_config(config: dict[str, Any]) -> tuple[str, ...]:
    """Return bot_authors + maintainer_token_logins from a caller config."""
    bots = list(config.get("bot_authors") or [])
    identity = config.get("identity_classification") or {}
    maintainers = list(identity.get("maintainer_token_logins") or [])
    return tuple(bots) + tuple(maintainers)


def _reselect_authors_from_disk() -> tuple[str, ...]:
    """Return configured author lists from CONFIG_PATH, or () when unreadable.

    A missing file or non-mapping document yields (); malformed
    identity_classification is tolerated as empty on disk.
    """
    if not CONFIG_PATH.is_file():
        return ()
    loaded = load_yaml(CONFIG_PATH)
    if not isinstance(loaded, dict):
        return ()
    bots = list(loaded.get("bot_authors") or [])
    identity = loaded.get("identity_classification")
    if not isinstance(identity, dict):
        identity = {}
    maintainers = list(identity.get("maintainer_token_logins") or [])
    return tuple(bots) + tuple(maintainers)


def _load_reselect_allowed_authors(
    config: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    """Load bot and maintainer logins from config, disk, then built-in defaults.

    Use the first source with a nonempty list; do not merge sources or cache
    disk reads. Disk OSError/ValueError failures, including invalid YAML, fall
    back to built-ins. Other errors propagate, as do errors reading the
    caller-supplied config.
    """
    if config:
        authors = _reselect_authors_from_config(config)
        if authors:
            return authors
    try:
        authors = _reselect_authors_from_disk()
    # ArtifactValidationError subclasses ValueError; other errors propagate.
    except (OSError, ValueError) as exc:
        LOGGER.warning(
            "reselect allowlist: config unreadable (%s); using built-in list",
            type(exc).__name__,
        )
        authors = ()
    return authors or _BUILTIN_RESELECT_AUTHORS


def _normalize_title_for_prefix(title: str) -> str:
    """Normalize NFC and lowercase, removing whitespace and invisible markers."""
    text = unicodedata.normalize("NFC", title)
    # Strip variation selectors and invisible format characters (ZWSP, ZWNJ, ZWJ, etc.)
    chars = [
        ch
        for ch in text
        if ch not in _TITLE_VARIATION_SELECTORS and unicodedata.category(ch) != "Cf"
    ]
    text = "".join("".join(chars).split())
    return text.lower()


def _title_is_reselect_bot(title: str | None) -> bool:
    """Return whether a normalized title starts with an allowed reselect prefix.

    Ignore case, whitespace, variation selectors, and Unicode format characters.
    Missing or empty titles do not match.
    """
    if not title:
        return False
    norm = _normalize_title_for_prefix(title)
    return any(norm.startswith(prefix) for prefix in NORMALIZED_RESELECT_TITLE_PREFIXES)


def _extract_item_author_login(item: dict[str, Any]) -> str | None:
    """Extract candidate author login from ledger item author or author_login fields."""
    author = item.get("author")
    if isinstance(author, dict):
        login = author.get("login")
        if isinstance(login, str) and login.strip():
            return login.strip()
    elif isinstance(author, str) and author.strip():
        return author.strip()
    author_login = item.get("author_login")
    if isinstance(author_login, str) and author_login.strip():
        return author_login.strip()
    return None


def _lifecycle_blocks_reselect(item: dict[str, Any]) -> bool:
    """Exclude terminal and Stage 2-owned/queued items from reselect.

    Already Stage 2 owned/queued: reselecting it would emit a duplicate
    ENQUEUE_STAGE2_WI for work Stage 2 already holds.
    """
    return (
        item.get("lifecycle_state") == "TERMINAL"
        or item.get("current_owner") == "stage2"
        or item.get("lifecycle_state") in STAGE2_OWNED_STATES
    )


def _title_gated_identity_ok(
    item: dict[str, Any], live: LivePrSignals, gate: ReselectAuthorGate
) -> bool:
    """Non-BOT items need an allowed title prefix and, when gated, a login.

    A nonblank live author login wins over the ledger record; inside the
    record, author precedes author_login. Missing identity fails the author
    gate when enabled.
    """
    if not _title_is_reselect_bot(live.title):
        return False
    login = (live.author_login or "").strip() or _extract_item_author_login(item)
    return gate.allows(login)


def _identity_allows_reselect(
    item: dict[str, Any],
    live: LivePrSignals,
    *,
    author_gate: ReselectAuthorGate | None = None,
) -> bool:
    """Check reselect authorship, excluding terminal and Stage 2-owned items.

    Ledger BOT authors bypass title and login checks. Other items need an
    allowed title prefix; a disabled gate bypasses only the login check.
    """
    if _lifecycle_blocks_reselect(item):
        return False
    if item.get("author_type") == "BOT":
        return True
    gate = author_gate or ReselectAuthorGate()
    return _title_gated_identity_ok(item, live, gate)


def _infer_live_mergeable(item: dict[str, Any], live_mergeable: str | None) -> str:
    """Return the authoritative supplied state, else the first CONFLICTING/DIRTY in next_action."""
    if live_mergeable:
        cand = str(live_mergeable).strip().upper()
        if cand in AUTHORITATIVE_MERGEABLE_STATES:
            return cand
    next_action = item.get("next_action") or ""
    match = LIVE_STATE_IN_TEXT.search(next_action)
    return match.group(1).upper() if match else ""


def non_journal_paths(paths: list[str]) -> list[str]:
    """Return paths outside any .jules directory."""
    return [path for path in paths if not JOURNAL_PATH_RE.search(path)]


def _paths_allow_soft_shell(paths: list[str]) -> bool:
    """Return True when every non-journal path is on the Palette wrap allowlist."""
    remaining = non_journal_paths(paths)
    if not remaining:
        return False
    for path in remaining:
        if not any(pattern.search(path) for pattern in PALETTE_WRAP_PATH_ALLOW):
            return False
    return True


def _sticky_allows_reselect(item: dict[str, Any], paths: list[str]) -> bool:
    """Accept generated_output, or Palette shell_execution on allowed paths."""
    sticky = set(item.get("sensitive_paths") or []) - {"generated_output"}
    if not sticky:
        return True
    if sticky <= RESELECT_SOFT_STICKY:
        next_action = (item.get("next_action") or "").lower()
        if PROHIBITED_NEXT_ACTION.search(next_action):
            return False
        palette_wrap = "palette" in next_action and "wrap" in next_action
        return palette_wrap and _paths_allow_soft_shell(paths)
    return False


def _unique_remaining_ok(
    unique_remaining_paths: list[str] | None, fallback_paths: list[str]
) -> tuple[bool, list[str]]:
    """Drop journal paths; an explicit empty unique list means no reselect source."""
    if unique_remaining_paths is not None:
        cleaned = non_journal_paths([str(p) for p in unique_remaining_paths])
        return (bool(cleaned), cleaned)
    cleaned = non_journal_paths([str(p) for p in fallback_paths])
    # Planner may use changed_paths as a proxy; APPLY must live-verify unique.
    return (bool(cleaned), cleaned)


def _reselect_identity_ok(
    item: dict[str, Any],
    live: LivePrSignals,
    *,
    author_gate: ReselectAuthorGate | None = None,
) -> bool:
    """Check never-touch, identity, and guardrail-outcome exclusions."""
    if is_never_touch_key(item.get("key")):
        return False
    if not _identity_allows_reselect(item, live, author_gate=author_gate):
        return False
    outcome = item.get("guardrail_outcome") or ""
    # Empty outcome allowed during intake; NON_SALVAGE blocks REVIEW_SECURITY /
    # HOLD_PLATFORM / HOLD_CANONICAL / PASS_ROUTINE / CLOSE_NONSECURITY_NOOP.
    return outcome not in NON_SALVAGE_OUTCOMES


LOCKFILE_SUFFIXES = (
    ".lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "poetry.lock",
)


def _reselect_paths_ok(
    item: dict[str, Any], unique_remaining_paths: list[str] | None
) -> bool:
    """Check unique remaining, sticky, and lockfile exclusions on paths."""
    fallback = list(item.get("changed_paths") or item.get("paths") or [])
    unique_ok, paths = _unique_remaining_ok(unique_remaining_paths, fallback)
    if not unique_ok:
        return False
    if not _sticky_allows_reselect(item, paths):
        return False
    sticky = set(item.get("sensitive_paths") or [])
    if "lockfiles_and_major_dependencies" not in sticky:
        return True
    return not any(path.endswith(LOCKFILE_SUFFIXES) for path in paths)


def _anchors_match(item: dict[str, Any], live: LivePrSignals) -> bool:
    """Require a supplied live head SHA to match the nonempty ledger anchor.

    A live head that disagrees with the ledger anchor means commits were
    pushed since intake; the item needs Stage 1 re-intake, not salvage with
    an obsolete anchor. An absent live head falls back to the ledger anchor.
    The live base SHA is deliberately not gated: baseRefOid tracks the moving
    tip of the base branch, so a routine merge advances it without
    invalidating the item. Plan actions stamp the fetched live base instead
    of shipping the stale ledger anchor; pr_lifecycle_reconcile.py owns
    base-drift re-anchoring.
    """
    if live.head_sha is None:
        return True
    ledger_head = str(item.get("head_sha") or "").strip().lower()
    return bool(ledger_head) and str(live.head_sha).strip().lower() == ledger_head


def is_reselect_salvage_candidate(
    item: dict[str, Any],
    *,
    live: LivePrSignals | None = None,
    author_gate: ReselectAuthorGate | None = None,
) -> bool:
    """Return whether Stage 1 may plan a unique-source reselect for this item.

    Exclude terminal, Stage 2-owned, never-touch, and blocked-outcome items.
    Ledger BOT authors bypass title and author checks. Other items need an
    allowed title prefix and, with the author gate enabled, an allowed login.
    A nonblank live author login wins over the ledger record; inside the
    record, author precedes author_login. Missing identity fails the author
    gate; disabling it still requires the title.

    Known live mergeability overrides next_action; unknown or absent values
    fall back to its first CONFLICTING/DIRTY marker. Only those two states
    qualify. A supplied live head SHA must match the nonempty ledger anchor
    after trimming and ignoring case; drift means the item needs re-intake.
    Live base movement is routine base-branch advance and never excludes.
    Explicit empty unique_paths rejects the item; None uses changed_paths,
    then paths, as a proxy. At least one non-journal path must survive
    sticky-path exclusions.

    When a title-based author check needs an allowlist and the gate has no
    concrete allowed_authors, load it via _load_reselect_allowed_authors; its
    uncaught errors propagate. Callers evaluating many items can resolve it
    once via ReselectAuthorGate.resolved(), as list_reselect_candidates does.
    """
    # Accept a nonterminal BOT item or one with an allowed title prefix and
    # author when its supplied mergeability, or a state inferred from
    # next_action, is CONFLICTING or DIRTY. An explicit unique_paths
    # list must contain a non-journal path; when omitted, changed_paths (then
    # paths) is a proxy. A supplied live head must match the ledger anchor.
    # Never-touch sources and NON_SALVAGE outcomes are excluded first.
    # generated_output is the only unrestricted sensitive label; shell_execution
    # additionally requires a Palette action and wrap-allowlist paths. Separate
    # from ``is_salvage_eligible``.
    live = live or LivePrSignals()
    if not _reselect_identity_ok(item, live, author_gate=author_gate):
        return False
    if not _anchors_match(item, live):
        return False
    state = _infer_live_mergeable(item, live.mergeable)
    if state not in RESELECT_LIVE_STATES:
        return False
    return _reselect_paths_ok(item, live.unique_paths)


def _reselect_structural_ok(item: dict[str, Any]) -> bool:
    """Require anchors and pass lifecycle, never-touch, and outcome gates."""
    return (
        _has_anchors(item)
        and not _lifecycle_blocks_reselect(item)
        and not is_never_touch_key(item.get("key"))
        and (item.get("guardrail_outcome") or "") not in NON_SALVAGE_OUTCOMES
    )


def is_reselect_plausible(
    item: dict[str, Any],
    *,
    author_gate: ReselectAuthorGate | None = None,
) -> bool:
    """Return whether a ledger item can pass every non-live reselect gate.

    Used by the live-signals prefilter so that records which can never yield
    a salvage action do not consume the live query cap. Requires nonempty
    base/head anchors (a complete work item cannot be assembled without them),
    passes never-touch, lifecycle, outcome, and path gates, and for non-BOT
    authors requires an allowlisted ledger author login. Ledger records carry
    no title field, so title-gated items stay plausible when their ledger
    author is allowed; the selector evaluates the live title later. The gate
    is resolved once per call, as with the resolved gates call sites pass in.
    """
    if not _reselect_structural_ok(item):
        return False
    if item.get("author_type") != "BOT":
        login = _extract_item_author_login(item)
        if not login:
            return False
        gate = (author_gate or ReselectAuthorGate()).resolved()
        if not gate.allows(login):
            return False
    return _reselect_paths_ok(item, None)


def _has_anchors(item: dict[str, Any]) -> bool:
    """Require nonempty base and head SHA anchors for a complete work item."""
    return bool(
        str(item.get("base_sha") or "").strip()
        and str(item.get("head_sha") or "").strip()
    )


@dataclass(frozen=True)
class ReselectAuthorGate:
    """Author gate for reselect identity checks.

    enabled=False bypasses only the login check (titles still gate). A None
    allowed_authors resolves lazily via _load_reselect_allowed_authors on the
    first check; resolved() materializes the allowlist once up front.
    """

    enabled: bool = True
    allowed_authors: Sequence[str] | None = None

    def resolved(self) -> "ReselectAuthorGate":
        """Return a gate whose allowlist is concrete (loads config once)."""
        if not self.enabled or self.allowed_authors is not None:
            return self
        return ReselectAuthorGate(allowed_authors=_load_reselect_allowed_authors())

    def allows(self, login: str | None) -> bool:
        """Return whether the login passes the gate."""
        if not self.enabled:
            return True
        if not login:
            return False
        allowed = (
            self.allowed_authors
            if self.allowed_authors is not None
            else _load_reselect_allowed_authors()
        )
        return identities_match(login, allowed)


@dataclass(frozen=True)
class LivePrSignals:
    """Live signal values resolved for one ledger key; None means no signal."""

    mergeable: str | None = None
    title: str | None = None
    unique_paths: list[str] | None = None
    head_sha: str | None = None
    base_sha: str | None = None
    author_login: str | None = None


@dataclass(frozen=True)
class ReselectSignals:
    """Optional live signals narrowing reselect candidate evaluation."""

    live_mergeable_by_key: dict[str, str] | None = None
    titles_by_key: dict[str, str] | None = None
    unique_paths_by_key: dict[str, list[str]] | None = None
    live_head_sha_by_key: dict[str, str] | None = None
    live_base_sha_by_key: dict[str, str] | None = None
    author_login_by_key: dict[str, str] | None = None
    # Keys whose live PR state is authoritatively CLOSED/MERGED.
    closed_keys: frozenset[str] | None = None


def signal_contains(keys: frozenset[str] | None, key: str) -> bool:
    """Check key-set membership by full key or @sha-stripped prefix."""
    if not keys:
        return False
    return key in keys or source_pr_prefix(key) in keys


def signal_value(mapping: dict[str, Any] | None, key: str) -> Any:
    """Look up a signal by full key, falling back to the @sha-stripped prefix."""
    if not mapping:
        return None
    if key in mapping:
        return mapping[key]
    return mapping.get(source_pr_prefix(key))


def list_reselect_candidates(
    ledger: dict[str, Any],
    *,
    signals: ReselectSignals | None = None,
    limit: int | None = None,
    author_gate: ReselectAuthorGate | None = None,
) -> list[dict[str, Any]]:
    """Return eligible keyed ledger items in their original order.

    Exclude sources with usable queued work and keys signaled closed/merged.
    Resolve signals by full key before repository#PR prefix, honoring explicit
    empty values. Return the original item dictionaries. A None limit is
    unbounded; a nonpositive limit still returns the first eligible item.

    Pass author_gate through to is_reselect_salvage_candidate. With the gate
    enabled and no explicit allowlist, resolve it once per call; uncaught
    allowlist-loading errors propagate.
    """
    # Signal maps are looked up by full key then repository#PR prefix; a key
    # present with an empty value is honored (e.g. [] means "no unique paths").
    # None limit is unbounded; the limit is
    # checked after appending, so a nonpositive limit still returns one item.
    signals = signals or ReselectSignals()
    # Resolve the allowlist once per call; deliberately not cached across
    # calls so config edits stay visible.
    gate = (author_gate or ReselectAuthorGate()).resolved()
    queued_prefixes = existing_wi_prefixes(ledger)
    selected: list[dict[str, Any]] = []
    for item in _ledger_items(ledger):
        if not _reselect_item_key(item, queued_prefixes, signals, author_gate=gate):
            continue
        selected.append(item)
        if limit is not None and len(selected) >= limit:
            break
    return selected


def _reselect_item_key(
    item: dict[str, Any],
    queued_prefixes: set[str],
    signals: ReselectSignals,
    *,
    author_gate: ReselectAuthorGate | None = None,
) -> str:
    """Return the key if unqueued, not signaled closed, and eligible; else ""."""
    key = str(item.get("key") or "")
    if not key or source_pr_prefix(key) in queued_prefixes:
        return ""
    if signal_contains(signals.closed_keys, key):
        return ""
    if not _reselect_item_ok(item, key, signals, author_gate=author_gate):
        return ""
    return key


def _live_signals_for(signals: ReselectSignals, key: str) -> LivePrSignals:
    """Resolve all per-key live signals into a per-item value bundle."""
    return LivePrSignals(
        mergeable=signal_value(signals.live_mergeable_by_key, key),
        title=signal_value(signals.titles_by_key, key),
        unique_paths=signal_value(signals.unique_paths_by_key, key),
        head_sha=signal_value(signals.live_head_sha_by_key, key),
        base_sha=signal_value(signals.live_base_sha_by_key, key),
        author_login=signal_value(signals.author_login_by_key, key),
    )


def _reselect_item_ok(
    item: dict[str, Any],
    key: str,
    signals: ReselectSignals,
    *,
    author_gate: ReselectAuthorGate | None = None,
) -> bool:
    """Apply the signal-resolved reselect predicate to one ledger item."""
    # Head/base SHA drift is enforced inside is_reselect_salvage_candidate.
    return is_reselect_salvage_candidate(
        item,
        live=_live_signals_for(signals, key),
        author_gate=author_gate,
    )


def _eligible_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible: list[dict[str, Any]] = []
    for item in items:
        if is_salvage_eligible(item):
            eligible.append(item)
    return eligible


def _eligible_keys(eligible: list[dict[str, Any]]) -> tuple[str, ...]:
    keys: list[str] = []
    for item in eligible:
        keys.append(str(item.get("key") or ""))
    return tuple(keys)


def _is_starved(usable_count: int, eligible_count: int) -> bool:
    return usable_count == 0 and eligible_count > 0


def _starvation_reason(starvation: bool, usable_count: int, eligible: int) -> str:
    if starvation:
        return f"Stage 2 EMPTY_INTAKE while salvage-eligible > 0 ({eligible} items)"
    if usable_count == 0:
        return "Stage 2 empty intake with zero salvage-eligible remainder"
    return "Stage 2 has queued work"


def summarize(
    ledger: dict[str, Any],
    now: datetime | None = None,
    *,
    signals: ReselectSignals | None = None,
) -> PipelineHealth:
    """Build a starvation report from a runtime ledger dict.

    Use now (an aware datetime, defaulting to current UTC) for work-item
    expiry in the starvation counts. Signals affect only the reselect count;
    its queued-work exclusions use the current clock independently of now.
    Schema validation is left to callers. Starvation requires no usable work
    items and at least one salvage-eligible item; owned-item and reselect
    counts do not affect that flag.
    """
    clock = _clock(now)
    items = _ledger_items(ledger)
    usable = _usable_work_items(ledger, clock)
    owned = _stage2_owned(items)
    eligible = _eligible_items(items)
    usable_count = len(usable)
    eligible_count = len(eligible)
    starvation = _is_starved(usable_count, eligible_count)
    return PipelineHealth(
        ledger_revision=_ledger_revision(ledger),
        stage2_work_item_count=usable_count,
        stage2_owned_item_count=len(owned),
        salvage_eligible_count=eligible_count,
        salvage_eligible_keys=_eligible_keys(eligible),
        reselect_candidate_count=len(list_reselect_candidates(ledger, signals=signals)),
        starvation=starvation,
        reason=_starvation_reason(starvation, usable_count, eligible_count),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "runtime_ledger",
        type=Path,
        help="fetched runtime ledger from automation/pr-lifecycle-ledger",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the health report as JSON",
    )
    args = parser.parse_args()
    ledger, status = _load_runtime_ledger(args.runtime_ledger)
    if ledger is None:
        return status
    report = summarize(ledger)
    _print_report(report, args.json)
    if report.starvation:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
