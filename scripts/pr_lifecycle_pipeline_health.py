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
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position
from pr_lifecycle_config import validate_config
from pr_lifecycle_ledger import validate_runtime_records
from pr_lifecycle_persist import strip_in_memory_item_fields
from pr_lifecycle_schema import validate_schema
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

__all__ = [
    "MECHANICAL_RESELECT_NA",
    "NON_SALVAGE_OUTCOMES",
    "REQUIRED_WORK_ITEM_FIELDS",
    "SALVAGE_OUTCOMES",
    "PipelineHealth",
    "ReselectSignals",
    "is_never_touch_key",
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
STAGE2_OWNED_STATES = frozenset({"STAGE2_QUEUED", "STAGE2_ACTIVE"})
NONEMPTY_WORK_ITEM_LISTS = ("allowed_paths", "acceptance_criteria", "provenance_urls")
SCHEMA_PATH = ROOT / "schemas/pr-lifecycle-ledger.schema.json"
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


def _load_required_work_item_fields() -> tuple[str, ...]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    required = schema["$defs"]["stage2WorkItem"]["required"]
    return tuple(required)


REQUIRED_WORK_ITEM_FIELDS = _load_required_work_item_fields()


def _clock(now: datetime | None) -> datetime:
    if now is not None:
        return now
    return datetime.now(timezone.utc)


def _as_item_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for entry in raw:
        if isinstance(entry, dict):
            items.append(entry)
    return items


def _ledger_items(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    return _as_item_list(ledger.get("items"))


def _raw_work_items(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    return _as_item_list(ledger.get("stage2_work_items"))


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


def source_pr_prefix(key: object) -> str:
    """Return repository#pr from a ledger key (strip @sha)."""
    text_key = str(key or "")
    if "@" in text_key:
        text_key = text_key.split("@", 1)[0]
    return text_key


def is_never_touch_key(key: object) -> bool:
    """Identify the two hard never-touch source PRs, ignoring any @SHA suffix."""
    # Seatek_Analysis#692 (journals) and ctrld-sync#1206 (CSPRNG).
    return source_pr_prefix(key) in NEVER_TOUCH_PR_PREFIXES


def _title_is_reselect_bot(title: str | None) -> bool:
    """Return whether a stripped title starts with an allowed reselect prefix."""
    if not title:
        return False
    stripped = title.strip()
    return any(stripped.startswith(prefix) for prefix in RESELECT_TITLE_PREFIXES)


def _identity_allows_reselect(item: dict[str, Any], title: str | None) -> bool:
    """Accept nonterminal items with BOT authorship or an allowed title."""
    if item.get("lifecycle_state") == "TERMINAL":
        return False
    # Already Stage 2 owned/queued: reselecting it would emit a duplicate
    # ENQUEUE_STAGE2_WI for work Stage 2 already holds.
    if (
        item.get("current_owner") == "stage2"
        or item.get("lifecycle_state") in STAGE2_OWNED_STATES
    ):
        return False
    if item.get("author_type") == "BOT":
        return True
    return _title_is_reselect_bot(title)


def _infer_live_mergeable(item: dict[str, Any], live_mergeable: str | None) -> str:
    """Return the supplied state, else the first CONFLICTING/DIRTY in next_action."""
    if live_mergeable:
        return str(live_mergeable).upper()
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


def _reselect_identity_ok(item: dict[str, Any], title: str | None) -> bool:
    """Check never-touch, identity, and guardrail-outcome exclusions."""
    if is_never_touch_key(item.get("key")):
        return False
    if not _identity_allows_reselect(item, title):
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


def is_reselect_salvage_candidate(
    item: dict[str, Any],
    *,
    live_mergeable: str | None = None,
    title: str | None = None,
    unique_remaining_paths: list[str] | None = None,
) -> bool:
    """Return whether Stage 1 may plan a unique-source reselect for this item."""
    # Accept a nonterminal BOT item or one with an allowed title prefix when its
    # supplied mergeability, or a state inferred from next_action, is
    # CONFLICTING or DIRTY. An explicit unique_remaining_paths list must contain
    # a non-journal path; when omitted, changed_paths (then paths) is a proxy.
    # Never-touch sources and NON_SALVAGE outcomes are excluded first.
    # generated_output is the only unrestricted sensitive label; shell_execution
    # additionally requires a Palette action and wrap-allowlist paths. Separate
    # from ``is_salvage_eligible``.
    if not _reselect_identity_ok(item, title):
        return False
    state = _infer_live_mergeable(item, live_mergeable)
    if state not in RESELECT_LIVE_STATES:
        return False
    return _reselect_paths_ok(item, unique_remaining_paths)


@dataclass(frozen=True)
class ReselectSignals:
    """Optional live signals narrowing reselect candidate evaluation."""

    live_mergeable_by_key: dict[str, str] | None = None
    titles_by_key: dict[str, str] | None = None
    unique_paths_by_key: dict[str, list[str]] | None = None


def signal_value(mapping: dict[str, Any] | None, key: str) -> Any:
    """Look up a signal by full key, falling back to the @sha-stripped prefix."""
    if not mapping:
        return None
    if key in mapping:
        return mapping[key]
    return mapping.get(source_pr_prefix(key))


def _existing_wi_prefixes(ledger: dict[str, Any]) -> set[str]:
    """Return repo#PR prefixes of sources with a usable Stage 2 WI."""
    prefixes: set[str] = set()
    for work_item in _raw_work_items(ledger):
        if not work_item_is_usable(work_item):
            continue
        source = work_item.get("source_item_key") or work_item.get("source_key")
        if source:
            prefixes.add(source_pr_prefix(source))
    return prefixes


def list_reselect_candidates(
    ledger: dict[str, Any],
    *,
    signals: ReselectSignals | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return eligible keyed ledger items in their original order."""
    # Signal maps are looked up by full key then repository#PR prefix; a key
    # present with an empty value is honored (e.g. [] means "no unique paths").
    # None limit is unbounded; the limit is
    # checked after appending, so a nonpositive limit still returns one item.
    signals = signals or ReselectSignals()
    queued_prefixes = _existing_wi_prefixes(ledger)
    selected: list[dict[str, Any]] = []
    for item in _ledger_items(ledger):
        if not _reselect_item_key(item, queued_prefixes, signals):
            continue
        selected.append(item)
        if limit is not None and len(selected) >= limit:
            break
    return selected


def _reselect_item_key(
    item: dict[str, Any], queued_prefixes: set[str], signals: ReselectSignals
) -> str:
    """Return the item's key when it survives dedupe and the predicate."""
    key = str(item.get("key") or "")
    if not key or source_pr_prefix(key) in queued_prefixes:
        return ""
    if not _reselect_item_ok(item, key, signals):
        return ""
    return key


def _reselect_item_ok(
    item: dict[str, Any], key: str, signals: ReselectSignals
) -> bool:
    """Apply the signal-resolved reselect predicate to one ledger item."""
    return is_reselect_salvage_candidate(
        item,
        live_mergeable=signal_value(signals.live_mergeable_by_key, key),
        title=signal_value(signals.titles_by_key, key),
        unique_remaining_paths=signal_value(signals.unique_paths_by_key, key),
    )


def parse_expiry_utc(value: object) -> datetime | None:
    """Parse a ledger expiry timestamp. Missing or malformed values are None."""
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc)


def _has_required_work_item_fields(item: dict[str, Any]) -> bool:
    # SECURITY: empty required strings are not usable intake. Do not use
    # truthiness on non-strings: attempt_count 0 and empty optional lists
    # remain complete.
    return all(
        field in item
        and item[field] is not None
        and not (isinstance(item[field], str) and item[field] == "")
        for field in REQUIRED_WORK_ITEM_FIELDS
    )


def _has_required_work_item_lists(item: dict[str, Any]) -> bool:
    for field in NONEMPTY_WORK_ITEM_LISTS:
        value = item.get(field)
        if not isinstance(value, list) or len(value) < 1:
            return False
    return True


def work_item_is_usable(item: dict[str, Any], now: datetime | None = None) -> bool:
    """Return True for a complete work item whose expiry_utc is still in the future."""
    clock = _clock(now)
    if item.get("current_owner") != "stage2":
        return False
    if not _has_required_work_item_fields(item):
        return False
    if not _has_required_work_item_lists(item):
        return False
    expiry = parse_expiry_utc(item.get("expiry_utc"))
    if expiry is None:
        return False
    return expiry > clock


def _stage2_owned(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    owned: list[dict[str, Any]] = []
    for item in items:
        owner = item.get("current_owner") == "stage2"
        queued = item.get("lifecycle_state") in STAGE2_OWNED_STATES
        if owner or queued:
            owned.append(item)
    return owned


def _usable_work_items(ledger: dict[str, Any], clock: datetime) -> list[dict[str, Any]]:
    usable: list[dict[str, Any]] = []
    for item in _raw_work_items(ledger):
        if work_item_is_usable(item, clock):
            usable.append(item)
    return usable


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


def _ledger_revision(ledger: dict[str, Any]) -> int:
    return int(ledger.get("ledger_revision") or 0)


def _is_starved(usable_count: int, eligible_count: int) -> bool:
    return usable_count == 0 and eligible_count > 0


def _starvation_reason(starvation: bool, usable_count: int, eligible: int) -> str:
    if starvation:
        return f"Stage 2 EMPTY_INTAKE while salvage-eligible > 0 ({eligible} items)"
    if usable_count == 0:
        return "Stage 2 empty intake with zero salvage-eligible remainder"
    return "Stage 2 has queued work"


def _health_report(
    ledger: dict[str, Any],
    usable: list[dict[str, Any]],
    owned: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
) -> PipelineHealth:
    usable_count = len(usable)
    owned_count = len(owned)
    eligible_count = len(eligible)
    starvation = _is_starved(usable_count, eligible_count)
    return PipelineHealth(
        ledger_revision=_ledger_revision(ledger),
        stage2_work_item_count=usable_count,
        stage2_owned_item_count=owned_count,
        salvage_eligible_count=eligible_count,
        salvage_eligible_keys=_eligible_keys(eligible),
        reselect_candidate_count=len(list_reselect_candidates(ledger)),
        starvation=starvation,
        reason=_starvation_reason(starvation, usable_count, eligible_count),
    )


def summarize(ledger: dict[str, Any], now: datetime | None = None) -> PipelineHealth:
    """Build a starvation report from a runtime ledger dict."""
    clock = _clock(now)
    items = _ledger_items(ledger)
    usable = _usable_work_items(ledger, clock)
    owned = _stage2_owned(items)
    eligible = _eligible_items(items)
    return _health_report(ledger, usable, owned, eligible)


def _print_report(report: PipelineHealth, as_json: bool) -> None:
    """Print the health report as JSON or readable fields."""
    payload = asdict(report)
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(f"ledger_revision={report.ledger_revision}")
    print(f"stage2_work_items={report.stage2_work_item_count}")
    print(f"stage2_owned_items={report.stage2_owned_item_count}")
    print(f"salvage_eligible={report.salvage_eligible_count}")
    print(f"reselect_candidates={report.reselect_candidate_count}")
    print(f"starvation={str(report.starvation).lower()}")
    print(f"reason={report.reason}")
    for key in report.salvage_eligible_keys:
        print(f"eligible_key={key}")


def _print_pointer_refusal() -> int:
    print(
        "PR_LIFECYCLE_HEALTH: refusing main-branch pointer "
        "(fetch automation/pr-lifecycle-ledger)",
        file=sys.stderr,
    )
    return 1


def _print_health_error(exc: BaseException) -> int:
    print(f"PR_LIFECYCLE_HEALTH_ERROR: {exc}", file=sys.stderr)
    return 1


def _path_is_bootstrap_pointer(pointer: Path) -> bool:
    return pointer.name == "pr-lifecycle-ledger.yaml" and "tasks" in pointer.parts


def _is_bootstrap_pointer_document(data: dict[str, Any]) -> bool:
    if data.get("pointer_kind") == "runtime_lifecycle_ledger":
        return True
    runtime = data.get("runtime_ledger")
    return isinstance(runtime, dict) and "items" not in data


def _is_list_or_missing(value: Any) -> bool:
    return value is None or isinstance(value, list)


def _has_runtime_ledger_shape(data: dict[str, Any]) -> bool:
    if "items" not in data:
        return False
    items_ok = _is_list_or_missing(data.get("items"))
    work_ok = _is_list_or_missing(data.get("stage2_work_items"))
    return items_ok and work_ok


def _require_valid_runtime_ledger(ledger: dict[str, Any]) -> None:
    strip_in_memory_item_fields(ledger)
    validate_schema(ledger)
    config = load_yaml(CONFIG_PATH)
    validate_config(config)
    validate_runtime_records(ledger, config)


def _parse_ledger_file(path: Path) -> tuple[dict[str, Any] | None, int]:
    try:
        return load_yaml(path), 0
    except (OSError, ValueError, KeyError) as exc:
        return None, _print_health_error(exc)


def _accept_runtime_ledger(ledger: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    if _is_bootstrap_pointer_document(ledger):
        return None, _print_pointer_refusal()
    if not _has_runtime_ledger_shape(ledger):
        print(
            "PR_LIFECYCLE_HEALTH: not a runtime ledger mapping "
            "(expected items list)",
            file=sys.stderr,
        )
        return None, 1
    try:
        _require_valid_runtime_ledger(ledger)
    except (OSError, ValueError, KeyError) as exc:
        return None, _print_health_error(exc)
    return ledger, 0


def _load_runtime_ledger(path: Path) -> tuple[dict[str, Any] | None, int]:
    if _path_is_bootstrap_pointer(path.resolve()):
        return None, _print_pointer_refusal()
    ledger, status = _parse_ledger_file(path)
    if ledger is None:
        return None, status
    return _accept_runtime_ledger(ledger)


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
