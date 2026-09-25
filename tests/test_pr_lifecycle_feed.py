"""Unit tests for pr_lifecycle_feed minimal WI emission."""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from io import StringIO
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
sys.modules["pr_lifecycle_pipeline_health"].is_never_touch_key = (
    lambda *_a, **_k: False
)


def _parse_utc_stub(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError:
        return None


sys.modules["pr_lifecycle_pipeline_health"].parse_expiry_utc = _parse_utc_stub

import pr_lifecycle_feed as feed  # noqa: E402

for _name in _STUB_NAMES:
    _saved = _saved_modules[_name]
    if _saved is None:
        sys.modules.pop(_name, None)
    else:
        sys.modules[_name] = _saved

NOW = datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc)


def _item(**overrides):
    base = {
        "key": "abhimehro/personal-config#1@" + "a" * 40,
        "repository": "abhimehro/personal-config",
        "pr": 1,
        "base_sha": "b" * 40,
        "head_sha": "a" * 40,
        "changed_paths": ["scripts/foo.py"],
        "author_type": "BOT",
        "guardrail_outcome": "HOLD_EVIDENCE",
        "lifecycle_state": "WAITING_HUMAN",
        "updated_at_utc": (NOW - timedelta(days=9)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "next_action": "salvage the focused change",
    }
    base.update(overrides)
    return base


class FeedTests(unittest.TestCase):
    def test_expired_packet_reason(self):
        item = _item()
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
            is_never_touch_key=lambda *_a, **_k: False,
            parse_expiry_utc=_parse_utc_stub,
        )
        with mock.patch.object(feed, "health", fake_health):
            payload = feed.build_feed(ledger, config, now=NOW)
        self.assertTrue(payload["empty_with_stock"])
        self.assertEqual(payload["reason"], "EMPTY_FEED_WITH_ELIGIBLE_STOCK")

    def test_expired_packet_rejects_boundary_and_ineligible_records(self):
        cases = (
            _item(
                updated_at_utc=(NOW - timedelta(days=7)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            ),
            _item(author_type="HUMAN"),
            _item(guardrail_outcome="REVIEW_SECURITY"),
            _item(lifecycle_state="STAGE2_QUEUED"),
            _item(updated_at_utc="invalid"),
            _item(updated_at_utc="2026-09-01T00:00:00+00:00"),
        )
        for item in cases:
            with self.subTest(item=item):
                self.assertFalse(
                    feed.is_expired_packet_salvage(item, expiry_days=7, now=NOW)
                )

    def test_minimal_work_item_uses_paths_fallback_and_copies_the_list(self):
        paths = ["src/one.py"]
        item = _item(changed_paths=None, paths=paths)
        work_item = feed.minimal_work_item(item, reason="SALVAGE_ELIGIBLE")
        paths.append("src/two.py")
        self.assertEqual(work_item["paths"], ["src/one.py"])

    def test_build_feed_deduplicates_keys_and_prioritizes_regular_salvage(self):
        first = _item()
        duplicate = _item(pr=2, changed_paths=["scripts/duplicate.py"])
        expired_only = _item(
            key="abhimehro/personal-config#3@" + "c" * 40,
            pr=3,
            changed_paths=["scripts/expired.py"],
        )
        ignored = _item(
            key="abhimehro/personal-config#4@" + "d" * 40,
            pr=4,
            author_type="HUMAN",
        )
        ledger = {
            "ledger_revision": 8,
            "items": [first, duplicate, expired_only, ignored],
        }
        report = types.SimpleNamespace(salvage_eligible_count=1)

        def eligible(item):
            return item is first or item is duplicate

        fake_health = types.SimpleNamespace(
            summarize=lambda *_a, **_k: report,
            is_salvage_eligible=eligible,
            is_never_touch_key=lambda *_a, **_k: False,
            parse_expiry_utc=_parse_utc_stub,
        )
        with mock.patch.object(feed, "health", fake_health):
            payload = feed.build_feed(
                ledger,
                {"lifecycle": {"packet_expiry_close_days": 7}},
                now=NOW,
            )

        self.assertEqual(payload["reason"], "FEED_OK")
        self.assertEqual(payload["work_item_count"], 2)
        self.assertEqual(payload["eligible_stock_count"], 2)
        self.assertEqual(
            [work_item["reason"] for work_item in payload["work_items"]],
            ["SALVAGE_ELIGIBLE", "EXPIRED_PACKET_OR_CLOSE_STALE"],
        )
        self.assertEqual(
            [work_item["pr"] for work_item in payload["work_items"]], [1, 3]
        )

    def test_build_feed_counts_stock_excluding_never_touch(self):
        never_touch = _item(key="abhimehro/Seatek_Analysis#692@" + "a" * 40)
        usable = _item(
            key="abhimehro/personal-config#2@" + "c" * 40, pr=2
        )
        ledger = {
            "ledger_revision": 8,
            "items": [never_touch, usable],
        }
        fake_health = types.SimpleNamespace(
            summarize=lambda *_a, **_k: types.SimpleNamespace(
                salvage_eligible_count=2
            ),
            is_salvage_eligible=lambda *_a, **_k: True,
            is_never_touch_key=lambda key, **_k: str(key or "").startswith(
                "abhimehro/Seatek_Analysis#692"
            ),
            parse_expiry_utc=_parse_utc_stub,
        )
        with mock.patch.object(feed, "health", fake_health):
            payload = feed.build_feed(
                ledger,
                {"lifecycle": {"packet_expiry_close_days": 7}},
                now=NOW,
            )
        self.assertEqual(payload["eligible_stock_count"], 2)
        self.assertEqual(payload["non_never_touch_stock_count"], 1)

    def test_non_never_touch_stock_includes_expired_packets_beyond_feed_limit(self):
        """Stock diagnostics count eligible records even after feed truncation."""
        regular = _item(
            key="abhimehro/demo#1@head", lifecycle_state="STAGE1_INTAKE"
        )
        expired = _item(key="abhimehro/demo#2@head")
        protected = _item(key="abhimehro/Seatek_Analysis#692@head")
        recent = _item(
            key="abhimehro/demo#3@head",
            updated_at_utc=(NOW - timedelta(days=7)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        )
        security = _item(
            key="abhimehro/demo#4@head", guardrail_outcome="REVIEW_SECURITY"
        )
        ledger = {
            "ledger_revision": 8,
            "items": [regular, expired, protected, recent, security],
        }
        fake_health = types.SimpleNamespace(
            summarize=lambda *_a, **_k: types.SimpleNamespace(
                salvage_eligible_count=1
            ),
            is_salvage_eligible=lambda item: item is regular,
            is_never_touch_key=lambda key: str(key or "").split("@", 1)[0]
            == "abhimehro/Seatek_Analysis#692",
            parse_expiry_utc=_parse_utc_stub,
        )
        with mock.patch.object(feed, "health", fake_health):
            payload = feed.build_feed(ledger, {}, now=NOW, limit=1)
        self.assertEqual(payload["work_item_count"], 1)
        self.assertEqual(payload["work_items"][0]["source_key"], regular["key"])
        self.assertEqual(payload["eligible_stock_count"], 3)
        self.assertEqual(payload["non_never_touch_stock_count"], 2)

    def test_build_feed_honors_limit_and_falls_back_for_invalid_expiry(self):
        ledger = {
            "ledger_revision": 8,
            "items": [
                _item(
                    updated_at_utc=(NOW - timedelta(days=8)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                ),
                _item(
                    key="abhimehro/personal-config#2@" + "c" * 40,
                    pr=2,
                    updated_at_utc=(NOW - timedelta(days=8)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                ),
            ],
        }
        fake_health = types.SimpleNamespace(
            summarize=lambda *_a, **_k: types.SimpleNamespace(
                salvage_eligible_count=0
            ),
            is_salvage_eligible=lambda *_a, **_k: False,
            is_never_touch_key=lambda *_a, **_k: False,
            parse_expiry_utc=_parse_utc_stub,
        )
        with mock.patch.object(feed, "health", fake_health):
            payload = feed.build_feed(
                ledger,
                {"lifecycle": {"packet_expiry_close_days": 0}},
                now=NOW,
                limit=1,
            )
        self.assertEqual(payload["work_item_count"], 1)
        self.assertEqual(payload["eligible_stock_count"], 2)

    def test_empty_feed_without_stock_is_a_successful_empty_feed(self):
        fake_health = types.SimpleNamespace(
            summarize=lambda *_a, **_k: types.SimpleNamespace(
                salvage_eligible_count=0
            ),
            is_salvage_eligible=lambda *_a, **_k: False,
            is_never_touch_key=lambda *_a, **_k: False,
            parse_expiry_utc=_parse_utc_stub,
        )
        with mock.patch.object(feed, "health", fake_health):
            payload = feed.build_feed(
                {"ledger_revision": 1, "items": []},
                {"lifecycle": {}},
                now=NOW,
            )
        self.assertEqual(payload["reason"], "EMPTY_FEED")
        self.assertFalse(payload["empty_with_stock"])

    def test_run_feed_returns_named_exit_two_for_empty_feed_with_stock(self):
        payload = {
            "reason": "EMPTY_FEED_WITH_ELIGIBLE_STOCK",
            "work_item_count": 0,
            "eligible_stock_count": 2,
            "work_items": [],
            "empty_with_stock": True,
        }
        with mock.patch.object(feed, "load_yaml", side_effect=[{"lifecycle": {}}, {}]):
            with mock.patch.object(feed, "validate_config"):
                with mock.patch.object(
                    feed.cas,
                    "run_preflight",
                    return_value={"ledger_path": "ledger.yaml"},
                    create=True,
                ):
                    with mock.patch.object(feed, "build_feed", return_value=payload):
                        with mock.patch("sys.stdout", new=StringIO()) as output:
                            result = feed.run_feed(limit=None, json_out=False)
        self.assertEqual(result, feed.EXIT_EMPTY_WITH_STOCK)
        self.assertIn("reason=EMPTY_FEED_WITH_ELIGIBLE_STOCK", output.getvalue())


if __name__ == "__main__":
    unittest.main()
