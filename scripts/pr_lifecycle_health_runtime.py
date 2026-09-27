#!/usr/bin/env python3
"""Runtime-ledger intake helpers for pipeline health.

Split from pr_lifecycle_pipeline_health.py: raw ledger/work-item accessors,
expiry and completeness evaluation, queued-work prefix resolution, runtime
ledger file acceptance (bootstrap-pointer refusal, shape checks, schema and
runtime-record validation), and PipelineHealth report emission. Kept free of
any import from pr_lifecycle_pipeline_health at runtime so the parent module
can re-export these helpers without a cycle.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pr_lifecycle_config import validate_config
from pr_lifecycle_ledger import validate_runtime_records
from pr_lifecycle_persist import strip_in_memory_item_fields
from pr_lifecycle_schema import validate_schema
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

if TYPE_CHECKING:
    from pr_lifecycle_pipeline_health import PipelineHealth

CONFIG_PATH = ROOT / "tasks/pr-review-agent.config.yaml"
SCHEMA_PATH = ROOT / "schemas/pr-lifecycle-ledger.schema.json"
STAGE2_OWNED_STATES = frozenset({"STAGE2_QUEUED", "STAGE2_ACTIVE"})
NONEMPTY_WORK_ITEM_LISTS = ("allowed_paths", "acceptance_criteria", "provenance_urls")


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


def source_pr_prefix(key: object) -> str:
    """Return repository#pr from a ledger key (strip @sha)."""
    text_key = str(key or "")
    if "@" in text_key:
        text_key = text_key.split("@", 1)[0]
    return text_key


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


def _ledger_revision(ledger: dict[str, Any]) -> int:
    return int(ledger.get("ledger_revision") or 0)


def existing_wi_prefixes(
    ledger: dict[str, Any], now: datetime | None = None
) -> set[str]:
    """Return repo#PR prefixes of sources with a usable Stage 2 WI."""
    prefixes: set[str] = set()
    for work_item in _raw_work_items(ledger):
        if not work_item_is_usable(work_item, now):
            continue
        source = work_item.get("source_item_key") or work_item.get("source_key")
        if source:
            prefixes.add(source_pr_prefix(source))
    return prefixes


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
