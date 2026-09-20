"""Keep in-memory ledger projection fields off persisted YAML."""

# apply_transition() records latest_transition* on the in-memory projection.
# Those keys are not in $defs.item (additionalProperties: false). Strip only
# that known pair; unknown extra fields still fail closed.
# pylint: disable=wrong-import-position

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

# pylint: disable=wrong-import-position
from pr_lifecycle_yaml import UniqueKeyLoader, load_yaml

IN_MEMORY_ITEM_FIELDS = frozenset({"latest_transition", "latest_transition_kind"})
DERIVED_ITEM_LINE = re.compile(
    r"^[ ]{2,4}latest_transition(?:_kind)?:[^\n]*\n",
    re.MULTILINE,
)
LEDGER_REVISION_LINE = re.compile(
    r"^(ledger_revision:)[ ]+(\d+)\s*$",
    re.MULTILINE,
)
__all__ = [
    "DERIVED_ITEM_LINE",
    "IN_MEMORY_ITEM_FIELDS",
    "LEDGER_REVISION_LINE",
    "count_in_memory_item_fields",
    "dump_ledger",
    "persistable_item",
    "sanitize_ledger_file",
    "strip_derived_item_lines",
    "strip_in_memory_item_fields",
]


def persistable_item(item: dict[str, Any]) -> dict[str, Any]:
    """Return a schema-legal item copy without in-memory projection keys."""
    return {
        key: value for key, value in item.items() if key not in IN_MEMORY_ITEM_FIELDS
    }


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
    if not removed:
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
    items = ledger.get("items")
    if isinstance(items, list):
        ledger["items"] = [
            persistable_item(item) if isinstance(item, dict) else item for item in items
        ]
    return yaml.safe_dump(ledger, sort_keys=False, allow_unicode=True)


def _parse_ledger_mapping(text: str, path: Path) -> dict[str, Any]:
    """Parse stripped YAML with duplicate-key rejection. Fail closed on junk."""
    try:
        loader = UniqueKeyLoader(text)
        try:
            parsed = loader.get_single_data()
        finally:
            loader.dispose()
    except (yaml.YAMLError, ValueError) as exc:
        raise ValueError(f"{path}: invalid YAML after strip: {exc}") from exc
    if not isinstance(parsed, dict):
        raise TypeError(f"{path}: root must be a mapping")
    return parsed


def _sanitize_text(
    original: str, path: Path, bump_revision: bool
) -> tuple[str, int, int]:
    """Line-strip, fail closed on leftover projection keys, optionally bump."""
    sanitized, removed = strip_derived_item_lines(original)
    parsed = _parse_ledger_mapping(sanitized, path)
    leftover = count_in_memory_item_fields(parsed)
    if leftover:
        # CAUTION: regex miss (flow-style `{latest_transition: evt-x, ...}`).
        removed += leftover
        sanitized = dump_ledger(parsed)
    new_revision = 0
    if bump_revision:
        sanitized, new_revision = increment_ledger_revision_line(sanitized)
    return sanitized, removed, new_revision


def sanitize_ledger_file(path: Path, *, bump_revision: bool) -> dict[str, int]:
    """Strip derived item fields from a fetched runtime ledger file in place."""
    original = path.read_text(encoding="utf-8")
    sanitized, removed, new_revision = _sanitize_text(original, path, bump_revision)
    if sanitized != original:
        path.write_text(sanitized, encoding="utf-8")
    return {"removed_fields": removed, "ledger_revision": new_revision}


def build_parser() -> argparse.ArgumentParser:
    """CLI for counting or rewriting known in-memory item fields."""
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
    return parser


def main() -> int:
    """Count or strip known in-memory item fields from a ledger file."""
    args = build_parser().parse_args()
    pending = count_in_memory_item_fields(load_yaml(args.runtime_ledger))
    if not args.in_place:
        print(f"PR_LIFECYCLE_DERIVED_FIELDS: {pending}")
        return 0 if not pending else 2
    result = sanitize_ledger_file(args.runtime_ledger, bump_revision=args.bump_revision)
    print(
        "PR_LIFECYCLE_SANITIZED: "
        f"removed_fields={result['removed_fields']} "
        f"ledger_revision={result['ledger_revision'] or 'unchanged'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
