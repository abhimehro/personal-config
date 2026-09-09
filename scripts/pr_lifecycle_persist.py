"""Keep in-memory ledger projection fields off persisted YAML.

`apply_transition()` records `latest_transition` and `latest_transition_kind` on
the in-memory projection so receipt validation can see the latest handoff. Those
keys are not in `$defs.item` (`additionalProperties: false`). Dumping the
projection onto `items` is what made Devin's 2026-09-06 CAS pass its own rewrite
and fail Cursor's schema validator.

This module strips only that known pair. Unknown extra fields still fail closed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pr_lifecycle_yaml import load_yaml

IN_MEMORY_ITEM_FIELDS = frozenset({"latest_transition", "latest_transition_kind"})
DERIVED_ITEM_LINE = re.compile(
    r"^[ ]{2,4}latest_transition(?:_kind)?:[^\n]*\n",
    re.MULTILINE,
)
LEDGER_REVISION_LINE = re.compile(
    r"^(ledger_revision:)[ ]+(\d+)\s*$",
    re.MULTILINE,
)


def persistable_item(item: dict[str, Any]) -> dict[str, Any]:
    """Return a schema-legal item copy without in-memory projection keys."""
    return {key: value for key, value in item.items() if key not in IN_MEMORY_ITEM_FIELDS}


def _remove_known_item_fields(item: Any) -> int:
    """Drop the known projection pair from one item. Return fields removed."""
    if not isinstance(item, dict):
        return 0
    removed = 0
    for field in IN_MEMORY_ITEM_FIELDS:
        if field not in item:
            continue
        del item[field]
        removed += 1
    return removed


def strip_in_memory_item_fields(ledger: dict[str, Any]) -> int:
    """Remove known derived keys from `items` in place. Return fields removed."""
    items = ledger.get("items")
    if not isinstance(items, list):
        return 0
    return sum(_remove_known_item_fields(item) for item in items)


def count_in_memory_item_fields(ledger: dict[str, Any]) -> int:
    """Count known derived keys on items without mutating the ledger."""
    items = ledger.get("items")
    if not isinstance(items, list):
        return 0
    return sum(
        1
        for item in items
        if isinstance(item, dict)
        for field in IN_MEMORY_ITEM_FIELDS
        if field in item
    )


def strip_derived_item_lines(text: str) -> tuple[str, int]:
    """Drop derived item lines from dumped YAML without rewriting the document."""
    removed = len(DERIVED_ITEM_LINE.findall(text))
    if removed == 0:
        return text, 0
    return DERIVED_ITEM_LINE.sub("", text), removed


def increment_ledger_revision_line(text: str) -> tuple[str, int]:
    """Bump the root `ledger_revision` scalar by one. Return new revision."""
    match = LEDGER_REVISION_LINE.search(text)
    if match is None:
        raise ValueError("ledger YAML: missing ledger_revision line")
    new_revision = int(match.group(2)) + 1
    updated, count = LEDGER_REVISION_LINE.subn(
        f"{match.group(1)} {new_revision}",
        text,
        count=1,
    )
    if count != 1:
        raise ValueError("ledger YAML: could not bump ledger_revision")
    return updated, new_revision


def dump_ledger(ledger: dict[str, Any]) -> str:
    """Serialize a ledger after stripping known in-memory item fields."""
    strip_in_memory_item_fields(ledger)
    return yaml.safe_dump(ledger, sort_keys=False, allow_unicode=True)


def sanitize_ledger_file(path: Path, *, bump_revision: bool) -> dict[str, int]:
    """Strip derived item lines from a fetched runtime ledger file in place."""
    original = path.read_text(encoding="utf-8")
    sanitized, removed = strip_derived_item_lines(original)
    new_revision = 0
    if bump_revision:
        sanitized, new_revision = increment_ledger_revision_line(sanitized)
    if sanitized != original:
        path.write_text(sanitized, encoding="utf-8")
    return {"removed_fields": removed, "ledger_revision": new_revision}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_ledger", type=Path)
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="rewrite the file, stripping known derived item lines",
    )
    parser.add_argument(
        "--bump-revision",
        action="store_true",
        help="increment ledger_revision when rewriting in place",
    )
    args = parser.parse_args()
    ledger = load_yaml(args.runtime_ledger)
    pending = count_in_memory_item_fields(ledger)
    if args.in_place:
        result = sanitize_ledger_file(args.runtime_ledger, bump_revision=args.bump_revision)
        print(
            "PR_LIFECYCLE_SANITIZED: "
            f"removed_fields={result['removed_fields']} "
            f"ledger_revision={result['ledger_revision'] or 'unchanged'}"
        )
        return 0
    print(f"PR_LIFECYCLE_DERIVED_FIELDS: {pending}")
    return 0 if pending == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
