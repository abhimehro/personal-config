"""Unit tests for pr_lifecycle_ledger_archive selection."""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
