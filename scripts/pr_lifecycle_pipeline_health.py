#!/usr/bin/env python3
"""Detect Stage 2 starvation and summarize salvage-eligible ledger stock.

Read a fetched runtime ledger (never the main-branch pointer). Exit 2 when
Stage 2 would empty-intake while salvage-eligible BOT items remain. This is
observability for PR Desk and CI; it does not CAS-write, launch stages, or
merge PRs.

Salvage-eligible matches the lifecycle contract: BOT, nonterminal, not
REVIEW_SECURITY, sticky paths empty or only generated_output, not
HOLD_PLATFORM / HOLD_CANONICAL / PASS_ROUTINE / CLOSE_NONSECURITY_NOOP, and a
mechanical next_action (unique-source draft, wrap, lint, import, non-major
pin, missing tests, conflict markers, DIRTY unique remaining). Lockfile,
workflow, auth, secrets, and any other remaining sticky label stay out.
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

from pr_lifecycle_yaml import load_yaml  # noqa: E402

NON_SALVAGE_OUTCOMES = frozenset(
    {
        "REVIEW_SECURITY",
        "HOLD_PLATFORM",
        "HOLD_CANONICAL",
        "PASS_ROUTINE",
        "CLOSE_NONSECURITY_NOOP",
        "ANALYSIS_ERROR",
        "NOT_RUN",
    }
)
SALVAGE_OUTCOMES = frozenset({"HOLD_CONTRACT", "HOLD_EVIDENCE"})
STAGE2_OWNED_STATES = frozenset({"STAGE2_QUEUED", "STAGE2_ACTIVE"})
REQUIRED_WORK_ITEM_FIELDS = (
    "work_item_id",
    "source_item_key",
    "allowed_paths",
    "required_test_command",
    "expiry_utc",
    "current_owner",
)
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


@dataclass(frozen=True)
class PipelineHealth:
    ledger_revision: int
    stage2_work_item_count: int
    stage2_owned_item_count: int
    salvage_eligible_count: int
    salvage_eligible_keys: tuple[str, ...]
    starvation: bool
    reason: str


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
        or item.get("current_owner") == "stage2"
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


def parse_expiry_utc(value: object) -> datetime | None:
    """Parse a ledger expiry timestamp. Missing or malformed values are None."""
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc)


def work_item_is_usable(item: dict[str, Any], now: datetime | None = None) -> bool:
    """Return True for a complete work item whose expiry_utc is still in the future."""
    clock = _clock(now)
    if item.get("current_owner") != "stage2":
        return False
    if not all(item.get(field) for field in REQUIRED_WORK_ITEM_FIELDS):
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


def _is_starved(queued: int, eligible_count: int) -> bool:
    return queued == 0 and eligible_count > 0


def _starvation_reason(starvation: bool, queued: int, eligible: int) -> str:
    if starvation:
        return "Stage 2 EMPTY_INTAKE while salvage-eligible > 0 " f"({eligible} items)"
    if queued == 0:
        return "Stage 2 empty intake with zero salvage-eligible remainder"
    return "Stage 2 has queued work"


def _health_report(
    ledger: dict[str, Any],
    usable: list[dict[str, Any]],
    owned: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
) -> PipelineHealth:
    queued = len(usable) + len(owned)
    eligible_count = len(eligible)
    starvation = _is_starved(queued, eligible_count)
    return PipelineHealth(
        ledger_revision=_ledger_revision(ledger),
        stage2_work_item_count=len(usable),
        stage2_owned_item_count=len(owned),
        salvage_eligible_count=eligible_count,
        salvage_eligible_keys=_eligible_keys(eligible),
        starvation=starvation,
        reason=_starvation_reason(starvation, queued, eligible_count),
    )


def summarize(ledger: dict[str, Any], now: datetime | None = None) -> PipelineHealth:
    """Build a starvation report from a validated-shape runtime ledger dict."""
    clock = _clock(now)
    items = _ledger_items(ledger)
    usable = _usable_work_items(ledger, clock)
    owned = _stage2_owned(items)
    eligible = _eligible_items(items)
    return _health_report(ledger, usable, owned, eligible)


def _print_report(report: PipelineHealth, as_json: bool) -> None:
    payload = asdict(report)
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(f"ledger_revision={report.ledger_revision}")
    print(f"stage2_work_items={report.stage2_work_item_count}")
    print(f"stage2_owned_items={report.stage2_owned_item_count}")
    print(f"salvage_eligible={report.salvage_eligible_count}")
    print(f"starvation={str(report.starvation).lower()}")
    print(f"reason={report.reason}")
    for key in report.salvage_eligible_keys:
        print(f"eligible_key={key}")


def _refuse_if_bootstrap_pointer(pointer: Path) -> int | None:
    if pointer.name == "pr-lifecycle-ledger.yaml" and "tasks" in pointer.parts:
        print(
            "PR_LIFECYCLE_HEALTH: refusing main-branch pointer "
            "(fetch automation/pr-lifecycle-ledger)",
            file=sys.stderr,
        )
        return 1
    return None


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
    refused = _refuse_if_bootstrap_pointer(args.runtime_ledger.resolve())
    if refused is not None:
        return refused
    try:
        ledger = load_yaml(args.runtime_ledger)
    except (OSError, ValueError, KeyError) as exc:
        print(f"PR_LIFECYCLE_HEALTH_ERROR: {exc}", file=sys.stderr)
        return 1
    report = summarize(ledger)
    _print_report(report, args.json)
    if report.starvation:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
