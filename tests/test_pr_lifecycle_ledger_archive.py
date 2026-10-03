"""Unit tests for pr_lifecycle_ledger_archive selection."""

from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# Restoring sys.modules keeps unittest discovery from leaking the stubs into
# the rest of the suite.
_STUB_NAMES = (
    "pr_lifecycle_ledger_cas",
    "pr_lifecycle_config",
    "pr_lifecycle_persist",
    "pr_lifecycle_support",
    "pr_lifecycle_yaml",
)
_saved_modules = {name: sys.modules.get(name) for name in _STUB_NAMES}
for name in _STUB_NAMES:
    sys.modules[name] = types.ModuleType(name)

sys.modules["pr_lifecycle_support"].ROOT = ROOT
sys.modules["pr_lifecycle_config"].validate_config = lambda *_a, **_k: None
sys.modules["pr_lifecycle_yaml"].load_yaml = lambda *_a, **_k: {}
sys.modules["pr_lifecycle_persist"].dump_ledger = lambda *_a, **_k: ""
sys.modules["pr_lifecycle_persist"].strip_in_memory_item_fields = lambda *_a, **_k: 0

import pr_lifecycle_ledger_archive as archive  # noqa: E402

for _name in _STUB_NAMES:
    _saved = _saved_modules[_name]
    if _saved is None:
        sys.modules.pop(_name, None)
    else:
        sys.modules[_name] = _saved

NOW = datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc)


def _item(key: str, *, age_days: int, state: str = "TERMINAL"):
    return {
        "key": key,
        "lifecycle_state": state,
        "updated_at_utc": (NOW - timedelta(days=age_days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }


class ArchiveTests(unittest.TestCase):
    def test_selects_old_terminal_only(self):
        ledger = {
            "items": [
                {
                    "key": "r#1@" + "a" * 40,
                    "lifecycle_state": "TERMINAL",
                    "updated_at_utc": (NOW - timedelta(days=40)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                },
                {
                    "key": "r#2@" + "b" * 40,
                    "lifecycle_state": "TERMINAL",
                    "updated_at_utc": (NOW - timedelta(days=5)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                },
                {
                    "key": "r#3@" + "c" * 40,
                    "lifecycle_state": "WAITING_HUMAN",
                    "updated_at_utc": (NOW - timedelta(days=40)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                },
            ]
        }
        selected = archive.select_archive_items(ledger, after_days=30, now=NOW)
        self.assertEqual([i["key"] for i in selected], ["r#1@" + "a" * 40])

    def test_partition_by_month(self):
        items = [
            {"key": "1", "updated_at_utc": "2026-07-01T00:00:00Z"},
            {"key": "2", "updated_at_utc": "2026-07-15T00:00:00Z"},
            {"key": "3", "updated_at_utc": "2026-08-01T00:00:00Z"},
        ]
        buckets = archive.partition_by_month(items)
        self.assertEqual(len(buckets["2026-07"]), 2)
        self.assertEqual(len(buckets["2026-08"]), 1)

    def test_selection_includes_exact_cutoff_and_skips_malformed_records(self):
        ledger = {
            "items": [
                _item("cutoff", age_days=30),
                _item("newer", age_days=29),
                _item("active", age_days=90, state="WAITING_HUMAN"),
                {"key": "missing-timestamp", "lifecycle_state": "TERMINAL"},
                {
                    "key": "bad-timestamp",
                    "lifecycle_state": "TERMINAL",
                    "updated_at_utc": "not-a-date",
                },
                "not-a-mapping",
            ]
        }
        selected = archive.select_archive_items(ledger, after_days=30, now=NOW)
        self.assertEqual([item["key"] for item in selected], ["cutoff"])

    def test_partition_by_month_ignores_invalid_timestamps(self):
        buckets = archive.partition_by_month(
            [
                {"key": "valid", "updated_at_utc": "2026-07-31T23:59:59Z"},
                {"key": "offset", "updated_at_utc": "2026-07-01T00:00:00+00:00"},
                {"key": "invalid", "updated_at_utc": "invalid"},
            ]
        )
        self.assertEqual(list(buckets), ["2026-07"])
        self.assertEqual([item["key"] for item in buckets["2026-07"]], ["valid"])

    def test_plan_archive_reports_months_remaining_items_and_size(self):
        ledger = {
            "ledger_revision": 7,
            "items": [
                _item("old-july", age_days=60),
                _item("old-august", age_days=31),
                _item("recent", age_days=3),
                "preserved-invalid-record",
            ],
            "events": [],
        }
        with mock.patch.object(archive, "dump_ledger", return_value="abc"):
            with mock.patch.object(archive, "strip_in_memory_item_fields") as strip:
                plan = archive.plan_archive(ledger, after_days=30, now=NOW)
        self.assertEqual(plan["selected_count"], 2)
        self.assertEqual(plan["remaining_count"], 2)
        self.assertEqual(plan["active_ledger_bytes_preview"], 3)
        self.assertEqual(
            plan["months"],
            {
                "2026-07": {"count": 1, "path": "archive/2026-07.yaml"},
                "2026-08": {"count": 1, "path": "archive/2026-08.yaml"},
            },
        )
        preview = strip.call_args.args[0]
        self.assertEqual(
            preview["items"],
            [_item("recent", age_days=3), "preserved-invalid-record"],
        )
        self.assertEqual(
            len(ledger["items"]), 4, "dry-run planning must not mutate input"
        )

    def test_apply_archive_prunes_item_events_and_writes_month_documents(self):
        old = _item("old", age_days=40)
        recent = _item("recent", age_days=5)
        ledger = {
            "ledger_revision": 3,
            "items": [old, recent],
            "events": [
                {"event_id": "old-event", "item_key": "old"},
                {"event_id": "recent-event", "item_key": "recent"},
                {"event_id": "shared-event", "item_key": None},
                "preserved-event",
            ],
        }

        def dump(document):
            return json.dumps(document, sort_keys=True)

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(archive, "_utc_now", return_value=NOW):
                with mock.patch.object(archive, "dump_ledger", side_effect=dump):
                    with mock.patch.object(archive, "strip_in_memory_item_fields"):
                        result = archive.apply_archive(
                            ledger, after_days=30, out_dir=Path(tmp)
                        )
            active = json.loads(Path(result["active_path"]).read_text(encoding="utf-8"))
            archived = json.loads(
                Path(result["archives"]["2026-08"]).read_text(encoding="utf-8")
            )

        self.assertEqual(result["selected_count"], 1)
        self.assertEqual(active["ledger_revision"], 4)
        self.assertEqual([item["key"] for item in active["items"]], ["recent"])
        self.assertEqual(
            [
                event["event_id"] if isinstance(event, dict) else event
                for event in active["events"]
            ],
            ["recent-event", "shared-event", "preserved-event"],
        )
        self.assertEqual(archived["month"], "2026-08")
        self.assertEqual(archived["source_ledger_revision"], 4)
        self.assertEqual(archived["items"], [old])

    def test_build_archive_document_uses_source_revision_and_fixed_clock(self):
        with mock.patch.object(archive, "_utc_now", return_value=NOW):
            document = archive.build_archive_document(
                "2026-08", [_item("old", age_days=40)], source_revision=9
            )
        self.assertEqual(document["archive_format_version"], 1)
        self.assertEqual(document["source_ledger_revision"], 9)
        self.assertEqual(document["archived_at_utc"], "2026-09-21T18:00:00Z")


if __name__ == "__main__":
    unittest.main()
