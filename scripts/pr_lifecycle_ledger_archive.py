#!/usr/bin/env python3
"""Archive TERMINAL ledger items older than 30 days.

Dry-run by default. ``--apply`` rewrites the active ledger (CAS) and writes
``archive/YYYY-MM.yaml`` siblings on the data branch layout. Validator accepts
archives; active ledger target size < 1MB.

Does not close or merge PRs.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position
import pr_lifecycle_ledger_cas as cas
from pr_lifecycle_config import validate_config
from pr_lifecycle_persist import dump_ledger, strip_in_memory_item_fields
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

ACTIVE_LEDGER_MAX_BYTES = 1_000_000
DEFAULT_ARCHIVE_AFTER_DAYS = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError:
        return None


def select_archive_items(
    ledger: dict[str, Any],
    *,
    after_days: int = DEFAULT_ARCHIVE_AFTER_DAYS,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    clock = now or _utc_now()
    cutoff = clock - timedelta(days=after_days)
    selected: list[dict[str, Any]] = []
    for item in ledger.get("items") or []:
        if not isinstance(item, dict):
            continue
        if item.get("lifecycle_state") != "TERMINAL":
            continue
        stamp = _parse_utc(item.get("updated_at_utc"))
        if stamp is None:
            continue
        if stamp <= cutoff:
            selected.append(item)
    return selected


def partition_by_month(
    items: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        stamp = _parse_utc(item.get("updated_at_utc"))
        if stamp is None:
            continue
        key = stamp.strftime("%Y-%m")
        buckets.setdefault(key, []).append(item)
    return buckets


def build_archive_document(
    month: str, items: list[dict[str, Any]], *, source_revision: Any
) -> dict[str, Any]:
    return {
        "archive_format_version": 1,
        "month": month,
        "archived_at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_ledger_revision": source_revision,
        "item_count": len(items),
        "items": items,
    }


def plan_archive(
    ledger: dict[str, Any],
    *,
    after_days: int = DEFAULT_ARCHIVE_AFTER_DAYS,
    now: datetime | None = None,
) -> dict[str, Any]:
    selected = select_archive_items(ledger, after_days=after_days, now=now)
    buckets = partition_by_month(selected)
    remaining = [
        item
        for item in ledger.get("items") or []
        if not isinstance(item, dict)
        or item.get("key") not in {i.get("key") for i in selected}
    ]
    preview = dict(ledger)
    preview["items"] = remaining
    strip_in_memory_item_fields(preview)
    preview_text = dump_ledger(preview)
    return {
        "dry_run": True,
        "archive_after_days": after_days,
        "selected_count": len(selected),
        "remaining_count": len(remaining),
        "active_ledger_bytes_preview": len(preview_text.encode("utf-8")),
        "active_ledger_max_bytes": ACTIVE_LEDGER_MAX_BYTES,
        "months": {
            month: {
                "count": len(items),
                "path": f"archive/{month}.yaml",
            }
            for month, items in sorted(buckets.items())
        },
        "selected_keys": [str(i.get("key")) for i in selected],
    }


def apply_archive(
    ledger: dict[str, Any],
    *,
    after_days: int,
    out_dir: Path,
) -> dict[str, Any]:
    selected = select_archive_items(ledger, after_days=after_days)
    buckets = partition_by_month(selected)
    selected_keys = {item.get("key") for item in selected}
    ledger["items"] = [
        item
        for item in ledger.get("items") or []
        if not isinstance(item, dict) or item.get("key") not in selected_keys
    ]
    # Drop events that only reference archived items (keep shared/calibration).
    archived_keys = selected_keys
    events = []
    for event in ledger.get("events") or []:
        if not isinstance(event, dict):
            continue
        item_key = event.get("item_key")
        if item_key in archived_keys:
            continue
        events.append(event)
    ledger["events"] = events
    ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
    strip_in_memory_item_fields(ledger)

    written: dict[str, str] = {}
    for month, items in sorted(buckets.items()):
        doc = build_archive_document(
            month, items, source_revision=ledger.get("ledger_revision")
        )
        path = out_dir / "archive" / f"{month}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Reuse dump_ledger shape for YAML stability.
        path.write_text(dump_ledger(doc), encoding="utf-8")
        written[month] = str(path)

    active_text = dump_ledger(ledger)
    active_path = out_dir / "pr-lifecycle-ledger.yaml"
    active_path.write_text(active_text, encoding="utf-8")
    return {
        "active_path": str(active_path),
        "active_bytes": len(active_text.encode("utf-8")),
        "archives": written,
        "selected_count": len(selected),
        "remaining_count": len(ledger.get("items") or []),
    }


def run_archive(*, apply: bool, after_days: int, json_out: bool) -> int:
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    with tempfile.TemporaryDirectory(prefix="pr-lifecycle-archive-") as tmp:
        out = Path(tmp) / "ledger.yaml"
        fetch = cas.run_preflight(out)
        ledger = load_yaml(Path(fetch["ledger_path"]))
        plan = plan_archive(ledger, after_days=after_days)
        plan["dry_run"] = not apply
        if not apply:
            if json_out:
                print(json.dumps(plan, indent=2, sort_keys=True))
            else:
                print(f"dry_run=true selected_count={plan['selected_count']}")
                print(
                    f"active_ledger_bytes_preview={plan['active_ledger_bytes_preview']}"
                )
                for month, meta in plan["months"].items():
                    print(
                        f"archive month={month} count={meta['count']} path={meta['path']}"
                    )
            return 0
        result = apply_archive(ledger, after_days=after_days, out_dir=Path(tmp))
        # CAS the active ledger only via existing helper (single-file CAS today).
        cas_result = cas.run_commit(
            Path(result["active_path"]),
            "archive: move TERMINAL items older than "
            f"{after_days}d into archive/YYYY-MM.yaml",
            bump_revision=False,
        )
        payload = {**plan, "apply_result": result, "cas": cas_result}
        if result["active_bytes"] > ACTIVE_LEDGER_MAX_BYTES:
            payload["warning"] = "active ledger still exceeds 1MB after archive"
        if json_out:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"dry_run=false selected_count={result['selected_count']}")
            print(f"active_bytes={result['active_bytes']}")
            for path in result["archives"].values():
                print(f"wrote {path}")
            print(
                "NOTE: archive/*.yaml files are written locally in this run; "
                "multi-file data-branch CAS for archives may need a follow-up "
                "if cas.run_commit only replaces the primary ledger path."
            )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--after-days", type=int, default=DEFAULT_ARCHIVE_AFTER_DAYS)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_archive(
            apply=args.apply, after_days=args.after_days, json_out=args.json
        )
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PR_LIFECYCLE_ARCHIVE_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
