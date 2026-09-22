"""Unit tests for pr_lifecycle_reconcile classification (no network)."""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# Stub heavy repo modules so classify_item can load without PyYAML / CAS.
for name in (
    "pr_lifecycle_ledger",
    "pr_lifecycle_ledger_cas",
    "pr_lifecycle_config",
    "pr_lifecycle_persist",
    "pr_lifecycle_support",
    "pr_lifecycle_yaml",
):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)

sys.modules["pr_lifecycle_ledger"].STATE_OWNERS = {
    "STAGE1_INTAKE": "stage1",
    "STAGE2_QUEUED": "stage2",
    "STAGE2_ACTIVE": "stage2",
    "STAGE3_RECONCILIATION": "stage3",
    "WAITING_HUMAN": "human",
    "TERMINAL": "none",
}
sys.modules["pr_lifecycle_ledger"].apply_transition = lambda *a, **k: None
sys.modules["pr_lifecycle_support"].ROOT = ROOT
sys.modules["pr_lifecycle_config"].validate_config = lambda *_a, **_k: None
sys.modules["pr_lifecycle_yaml"].load_yaml = lambda *_a, **_k: {}
sys.modules["pr_lifecycle_persist"].dump_ledger = lambda *_a, **_k: ""
sys.modules["pr_lifecycle_persist"].strip_in_memory_item_fields = lambda *_a, **_k: 0

import pr_lifecycle_reconcile as reconcile  # noqa: E402

NOW = datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc)


def _item(**overrides):
    base = {
        "key": "abhimehro/personal-config#99@" + "a" * 40,
        "repository": "abhimehro/personal-config",
        "pr": 99,
        "head_sha": "a" * 40,
        "base_sha": "b" * 40,
        "author_type": "BOT",
        "guardrail_outcome": "HOLD_EVIDENCE",
        "lifecycle_state": "WAITING_HUMAN",
        "current_owner": "human",
        "next_owner": "human",
        "terminal_disposition": None,
        "revision": 1,
        "handoffs": [],
        "updated_at_utc": (NOW - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "next_action": "Await human",
    }
    base.update(overrides)
    return base


class ClassifyItemTests(unittest.TestCase):
    def test_merged_goes_terminal(self):
        action = reconcile.classify_item(
            _item(lifecycle_state="STAGE1_INTAKE"),
            {"state": "MERGED", "headRefOid": "a" * 40},
            expiry_days=7,
            now=NOW,
        )
        self.assertEqual(action["action"], "TERMINAL_MERGED")
        self.assertEqual(action["disposition"], "MERGED_ROUTINE")

    def test_closed_goes_terminal(self):
        action = reconcile.classify_item(
            _item(lifecycle_state="STAGE2_QUEUED"),
            {"state": "CLOSED", "headRefOid": "a" * 40},
            expiry_days=7,
            now=NOW,
        )
        self.assertEqual(action["action"], "TERMINAL_CLOSED")
        self.assertEqual(action["disposition"], "CLOSED_NOOP")

    def test_sha_drift_reintake(self):
        action = reconcile.classify_item(
            _item(lifecycle_state="STAGE2_QUEUED"),
            {"state": "OPEN", "headRefOid": "c" * 40},
            expiry_days=7,
            now=NOW,
        )
        self.assertEqual(action["action"], "SHA_DRIFT_REINTAKE")
        self.assertEqual(action["to_state"], "STAGE1_INTAKE")

    def test_stale_waiting_human_bot(self):
        action = reconcile.classify_item(
            _item(),
            {"state": "OPEN", "headRefOid": "a" * 40},
            expiry_days=7,
            now=NOW,
        )
        self.assertEqual(action["action"], "CLOSE_STALE")
        self.assertEqual(action["disposition"], "CLOSED_STALE")

    def test_review_security_not_stale_closed(self):
        action = reconcile.classify_item(
            _item(guardrail_outcome="REVIEW_SECURITY"),
            {"state": "OPEN", "headRefOid": "a" * 40},
            expiry_days=7,
            now=NOW,
        )
        self.assertIsNone(action)

    def test_fresh_waiting_human_not_stale(self):
        action = reconcile.classify_item(
            _item(
                updated_at_utc=(NOW - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
            ),
            {"state": "OPEN", "headRefOid": "a" * 40},
            expiry_days=7,
            now=NOW,
        )
        self.assertIsNone(action)


if __name__ == "__main__":
    unittest.main()
