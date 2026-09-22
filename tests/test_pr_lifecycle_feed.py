"""Unit tests for pr_lifecycle_feed minimal WI emission."""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# Stub remote/health deps for this module only; restoring sys.modules keeps
# unittest discovery from leaking the stubs into the rest of the suite.
_STUB_NAMES = (
    "pr_lifecycle_ledger_cas",
    "pr_lifecycle_pipeline_health",
    "pr_lifecycle_config",
    "pr_lifecycle_support",
    "pr_lifecycle_yaml",
)
_saved_modules = {name: sys.modules.get(name) for name in _STUB_NAMES}
for name in _STUB_NAMES:
    sys.modules[name] = types.ModuleType(name)

sys.modules["pr_lifecycle_support"].ROOT = ROOT
sys.modules["pr_lifecycle_config"].validate_config = lambda *_a, **_k: None
sys.modules["pr_lifecycle_yaml"].load_yaml = lambda *_a, **_k: {}
sys.modules["pr_lifecycle_pipeline_health"].is_salvage_eligible = (
    lambda *_a, **_k: False
)
sys.modules["pr_lifecycle_pipeline_health"].summarize = (
    lambda *_a, **_k: types.SimpleNamespace(
        salvage_eligible_count=0,
        stage2_work_item_count=0,
        starvation=False,
        reason="ok",
    )
)

import pr_lifecycle_feed as feed  # noqa: E402

for _name in _STUB_NAMES:
    _saved = _saved_modules[_name]
    if _saved is None:
        sys.modules.pop(_name, None)
    else:
        sys.modules[_name] = _saved

NOW = datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc)


class FeedTests(unittest.TestCase):
    def test_expired_packet_reason(self):
        item = {
            "key": "abhimehro/personal-config#1@" + "a" * 40,
            "lifecycle_state": "WAITING_HUMAN",
            "author_type": "BOT",
            "guardrail_outcome": "HOLD_EVIDENCE",
            "updated_at_utc": (NOW - timedelta(days=9)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self.assertTrue(feed.is_expired_packet_salvage(item, expiry_days=7, now=NOW))

    def test_minimal_work_item_shape(self):
        item = {
            "key": "abhimehro/personal-config#1@" + "a" * 40,
            "repository": "abhimehro/personal-config",
            "pr": 1,
            "base_sha": "b" * 40,
            "head_sha": "a" * 40,
            "changed_paths": ["scripts/foo.py"],
            "author_type": "BOT",
            "guardrail_outcome": "HOLD_CONTRACT",
            "lifecycle_state": "STAGE1_INTAKE",
            "next_action": "wrap export",
        }
        wi = feed.minimal_work_item(item, reason="SALVAGE_ELIGIBLE")
        self.assertEqual(wi["source_key"], item["key"])
        self.assertEqual(wi["paths"], ["scripts/foo.py"])
        self.assertEqual(wi["reason"], "SALVAGE_ELIGIBLE")
        self.assertNotIn("acceptance_criteria", wi)

    def test_empty_feed_with_stock_flag(self):
        ledger = {"ledger_revision": 1, "items": []}
        config = {"lifecycle": {"packet_expiry_close_days": 7}}

        class FakeReport:
            salvage_eligible_count = 3
            stage2_work_item_count = 0
            starvation = True
            reason = "starved"

        fake_health = types.SimpleNamespace(
            summarize=lambda *a, **k: FakeReport(),
            is_salvage_eligible=lambda *a, **k: False,
        )
        with mock.patch.object(feed, "health", fake_health):
            payload = feed.build_feed(ledger, config, now=NOW)
        self.assertTrue(payload["empty_with_stock"])
        self.assertEqual(payload["reason"], "EMPTY_FEED_WITH_ELIGIBLE_STOCK")


if __name__ == "__main__":
    unittest.main()
