"""Unit tests for pr_lifecycle_run plan shape."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# Stub only remote/study deps — never clobber pack modules under test.
for name in (
    "pr_lifecycle_ledger_cas",
    "pr_lifecycle_pipeline_health",
    "pr_lifecycle_config",
    "pr_lifecycle_support",
    "pr_lifecycle_yaml",
):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)

sys.modules["pr_lifecycle_support"].ROOT = ROOT
sys.modules["pr_lifecycle_config"].validate_config = lambda *_a, **_k: None
sys.modules["pr_lifecycle_yaml"].load_yaml = lambda *_a, **_k: {}
sys.modules["pr_lifecycle_pipeline_health"].summarize = (
    lambda *_a, **_k: types.SimpleNamespace(
        salvage_eligible_count=0,
        stage2_work_item_count=0,
        starvation=False,
        reason="ok",
    )
)

# Ensure feed/reconcile stubs exist only if not already loaded as real modules.
if "pr_lifecycle_reconcile" not in sys.modules:
    sys.modules["pr_lifecycle_reconcile"] = types.ModuleType("pr_lifecycle_reconcile")
    sys.modules["pr_lifecycle_reconcile"].collect_actions = lambda *_a, **_k: []
if "pr_lifecycle_feed" not in sys.modules:
    sys.modules["pr_lifecycle_feed"] = types.ModuleType("pr_lifecycle_feed")
    sys.modules["pr_lifecycle_feed"].build_feed = lambda *_a, **_k: {
        "empty_with_stock": False,
        "reason": "FEED_OK",
        "work_item_count": 0,
        "eligible_stock_count": 0,
        "work_items": [],
    }

import pr_lifecycle_run as run  # noqa: E402


class RunPlanTests(unittest.TestCase):
    def test_stage2_never_merges_in_plan(self):
        ledger = {"ledger_revision": 9, "items": []}
        config = {"lifecycle": {}}

        class FakeReport:
            salvage_eligible_count = 0
            stage2_work_item_count = 0
            starvation = False
            reason = "ok"

        with mock.patch.object(run.health, "summarize", return_value=FakeReport()):
            with mock.patch.object(
                run.feed_mod,
                "build_feed",
                return_value={
                    "empty_with_stock": False,
                    "reason": "FEED_OK",
                    "work_item_count": 0,
                    "eligible_stock_count": 0,
                    "work_items": [],
                },
            ):
                plan = run.build_stage_plan(2, ledger, config)
        self.assertFalse(plan.get("stage2_may_merge"))
        self.assertFalse(plan.get("calibration_enabled"))
        self.assertEqual(plan["stage"], 2)

    def test_stage3_mentions_advisory_bot_threads(self):
        ledger = {"ledger_revision": 9, "items": []}
        config = {"lifecycle": {}}

        class FakeReport:
            salvage_eligible_count = 0
            stage2_work_item_count = 0
            starvation = False
            reason = "ok"

        with mock.patch.object(run.health, "summarize", return_value=FakeReport()):
            plan = run.build_stage_plan(3, ledger, config)
        blob = str(plan).lower()
        self.assertIn("advisory", blob)
        self.assertFalse(plan.get("calibration_enabled"))


if __name__ == "__main__":
    unittest.main()
