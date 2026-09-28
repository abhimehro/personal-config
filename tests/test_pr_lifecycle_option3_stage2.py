"""Option 3 Stage 2 intake tests for pr_lifecycle_run."""

from __future__ import annotations

import copy
import unittest
from unittest import mock

from tests.pr_lifecycle_helpers import (
    import_lifecycle_run,
    make_health_report,
    make_ledger,
    make_work_item,
)

import pr_lifecycle_feed as real_feed
import pr_lifecycle_pipeline_health as real_health

run = import_lifecycle_run()

_report = make_health_report


class Option3Stage2IntakeTests(unittest.TestCase):
    def test_stage2_real_feed_filters_protected_queue_before_salvage(self) -> None:
        """Queued never-touch work cannot hide a later mechanical work item."""
        protected = make_work_item(
            work_item_id="s2-seatek-692",
            source_item_key="abhimehro/Seatek_Analysis#692@old",
            repository="abhimehro/Seatek_Analysis",
            pr=692,
            expiry_utc="2999-01-01T00:00:00Z",
        )
        mechanical = make_work_item(
            work_item_id="s2-demo-7",
            source_item_key="abhimehro/demo#7@new",
            pr=7,
            expiry_utc="2999-01-01T00:00:00Z",
        )
        ledger = make_ledger([], [protected, mechanical])
        original = copy.deepcopy(ledger)
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(
                run.health,
                "is_never_touch_key",
                side_effect=real_health.is_never_touch_key,
            ),
            mock.patch.object(
                run.feed_mod,
                "build_feed",
                return_value={
                    "empty_with_stock": False,
                    "reason": "FEED_OK",
                    "work_item_count": 2,
                    "eligible_stock_count": 2,
                    "non_never_touch_stock_count": 2,
                    "work_items": [protected, mechanical],
                },
            ),
        ):
            plan = run.build_stage_plan(
                2,
                ledger,
                {"lifecycle": {"stage_caps": {"stage2_salvage_candidates": 1}}},
            )
        self.assertEqual(plan["reason"], "OK")
        self.assertFalse(plan["skip_cursor"])
        self.assertEqual(plan["mechanical_candidate_count"], 1)
        self.assertEqual(
            plan["never_touch_skipped"],
            [{"source_key": protected["source_item_key"], "reason": "NEVER_TOUCH"}],
        )
        self.assertEqual(
            [
                action["wi"]["source_item_key"]
                for action in plan["actions"]
                if action["action"] == "SALVAGE_WI"
            ],
            [mechanical["source_item_key"]],
        )
        self.assertEqual(ledger, original)

    def test_stage2_full_feed_pipeline_filters_protected_queue(self) -> None:
        """Real build_feed + planner keep mechanical WI behind a never-touch one."""
        protected = make_work_item(
            work_item_id="s2-seatek-692",
            source_item_key="abhimehro/Seatek_Analysis#692@old",
            repository="abhimehro/Seatek_Analysis",
            pr=692,
            expiry_utc="2999-01-01T00:00:00Z",
        )
        mechanical = make_work_item(
            work_item_id="s2-demo-7",
            source_item_key="abhimehro/demo#7@new",
            pr=7,
            expiry_utc="2999-01-01T00:00:00Z",
        )
        ledger = make_ledger([], [protected, mechanical])
        # test_pr_lifecycle_feed binds feed.health to a stub at import; repoint it
        # to the real module for the duration of this regression check.
        with (
            mock.patch.object(
                run.health, "summarize", side_effect=real_health.summarize
            ),
            mock.patch.object(
                run.health,
                "is_never_touch_key",
                side_effect=real_health.is_never_touch_key,
            ),
            mock.patch.object(
                run.feed_mod, "build_feed", side_effect=real_feed.build_feed
            ),
            mock.patch.object(real_feed, "health", real_health),
        ):
            plan = run.build_stage_plan(
                2,
                ledger,
                {"lifecycle": {"stage_caps": {"stage2_salvage_candidates": 1}}},
            )
        self.assertEqual(plan["reason"], "OK")
        self.assertEqual(plan["mechanical_candidate_count"], 1)
        self.assertEqual(
            plan["never_touch_skipped"],
            [{"source_key": protected["source_item_key"], "reason": "NEVER_TOUCH"}],
        )
        self.assertEqual(
            [
                action["wi"]["source_item_key"]
                for action in plan["actions"]
                if action["action"] == "SALVAGE_WI"
            ],
            [mechanical["source_item_key"]],
        )

    def test_stage2_mixed_feed_salvages_only_usable_sources(self) -> None:
        """Verify Stage 2 filters never-touch entries from a mixed feed."""
        never_touch = {"source_item_key": "abhimehro/Seatek_Analysis#692@head"}
        usable = {"source_key": "abhimehro/demo#8@head"}
        feed_payload = {
            "empty_with_stock": False,
            "reason": "FEED_OK",
            "work_item_count": 2,
            "eligible_stock_count": 1,
            "work_items": [never_touch, usable],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(
                run.feed_mod, "build_feed", return_value=feed_payload
            ) as build_feed,
            mock.patch.object(
                run.health,
                "is_never_touch_key",
                side_effect=lambda key: key.startswith(
                    "abhimehro/Seatek_Analysis#692@"
                ),
            ),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 2}, {})
        self.assertEqual(plan["reason"], "OK")
        self.assertFalse(plan["skip_cursor"])
        self.assertEqual(plan["mechanical_candidate_count"], 1)
        self.assertEqual(
            plan["never_touch_skipped"],
            [{"source_key": never_touch["source_item_key"], "reason": "NEVER_TOUCH"}],
        )
        self.assertEqual(
            [action["action"] for action in plan["actions"]],
            ["FEED_SUMMARY", "SALVAGE_WI"],
        )
        build_feed.assert_called_once_with({"ledger_revision": 2}, {})
        self.assertIs(plan["actions"][1]["wi"], usable)

    def test_stage2_filters_protected_items_before_applying_candidate_cap(self) -> None:
        """Protected entries ahead of the cap cannot hide mechanical work."""
        protected = [
            {"source_key": f"abhimehro/Seatek_Analysis#692@{index}"}
            for index in range(11)
        ]
        mechanical = [
            {"source_item_key": f"abhimehro/demo#{pr}@head"}
            for pr in (7, 8)
        ]
        feed_payload = {
            "reason": "FEED_OK",
            "work_item_count": 13,
            "eligible_stock_count": 2,
            "non_never_touch_stock_count": 2,
            "work_items": protected + mechanical,
        }
        ledger = {"ledger_revision": 2}
        config = {"lifecycle": {"stage_caps": {"stage2_salvage_candidates": 1}}}
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(
                run.feed_mod, "build_feed", return_value=feed_payload
            ) as build_feed,
            mock.patch.object(
                run.health,
                "is_never_touch_key",
                side_effect=lambda key: key.split("@", 1)[0]
                == "abhimehro/Seatek_Analysis#692",
            ),
        ):
            plan = run.build_stage_plan(2, ledger, config)
        build_feed.assert_called_once_with(ledger, config)
        self.assertEqual(plan["reason"], "OK")
        self.assertEqual(plan["mechanical_candidate_count"], 1)
        self.assertEqual(len(plan["never_touch_skipped"]), 11)
        self.assertEqual(
            [
                action["wi"]
                for action in plan["actions"]
                if action["action"] == "SALVAGE_WI"
            ],
            mechanical[:1],
        )
        self.assertFalse(plan["skip_cursor"])

    @staticmethod
    def _never_touch_stock_feed(source_key: str, *, non_never_touch: int) -> dict:
        """Build a stock-only feed payload carrying one never-touch item."""
        return {
            "empty_with_stock": True,
            "reason": "EMPTY_FEED_WITH_ELIGIBLE_STOCK",
            "work_item_count": 1,
            "eligible_stock_count": 2,
            "non_never_touch_stock_count": non_never_touch,
            "work_items": [{"source_item_key": source_key}],
        }

    def _stage2_plan_with_feed(self, feed_payload: dict) -> dict:
        """Plan Stage 2 against a stubbed feed and all-never-touch sources."""
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
            mock.patch.object(run.health, "is_never_touch_key", return_value=True),
        ):
            return run.build_stage_plan(2, {"ledger_revision": 1}, {})

    def test_stage2_stop_with_stock_takes_precedence_over_never_touch_filter(self) -> None:
        """Verify eligible stock blocks an empty-intake skip despite filtering."""
        plan = self._stage2_plan_with_feed(
            self._never_touch_stock_feed(
                "abhimehro/ctrld-sync#1206@head", non_never_touch=1
            )
        )
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "EMPTY_FEED_WITH_ELIGIBLE_STOCK")
        self.assertFalse(plan["skip_cursor"])
        self.assertEqual(plan["mechanical_candidate_count"], 0)
        self.assertEqual(
            [action["action"] for action in plan["actions"]], ["FEED_SUMMARY"]
        )

    def test_stage2_skips_when_only_never_touch_stock_remains(self) -> None:
        """Verify never-touch-only stock still yields the successful skip."""
        plan = self._stage2_plan_with_feed(
            self._never_touch_stock_feed(
                "abhimehro/Seatek_Analysis#692@head", non_never_touch=0
            )
        )
        self.assertIsNone(plan["stop_class"])
        self.assertEqual(plan["reason"], "EMPTY_INTAKE_SKIP")
        self.assertTrue(plan["skip_cursor"])
        self.assertEqual(
            [action["action"] for action in plan["actions"]], ["SKIP_IF_EMPTY"]
        )

    def test_stage2_skip_if_empty_exits_success_without_docs_pr(self) -> None:
        """Verify empty Stage 2 intake succeeds without opening a docs PR."""
        feed_payload = {
            "empty_with_stock": False,
            "reason": "EMPTY_FEED",
            "work_item_count": 0,
            "eligible_stock_count": 0,
            "work_items": [],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 2}, {})
        self.assertEqual(plan["reason"], "EMPTY_INTAKE_SKIP")
        self.assertIsNone(plan["stop_class"])
        self.assertTrue(plan.get("skip_cursor"))
        self.assertTrue(plan.get("empty_intake_skip"))
        self.assertEqual(plan["actions"][0]["action"], "SKIP_IF_EMPTY")
        self.assertFalse(plan["stage2_may_merge"])

    def test_stage2_filters_never_touch_then_may_skip(self) -> None:
        """Verify Stage 2 skips when filtering leaves no usable work."""
        feed_payload = {
            "empty_with_stock": False,
            "reason": "FEED_OK",
            "work_item_count": 1,
            "eligible_stock_count": 0,
            "work_items": [
                {
                    "source_key": "abhimehro/ctrld-sync#1206@deadbeef",
                    "reason": "EXPIRED_PACKET_OR_CLOSE_STALE",
                }
            ],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
            mock.patch.object(run.health, "is_never_touch_key", return_value=True),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 2}, {})
        self.assertEqual(plan["reason"], "EMPTY_INTAKE_SKIP")
        self.assertTrue(plan.get("skip_cursor"))
        self.assertEqual(plan["actions"][0]["action"], "SKIP_IF_EMPTY")


if __name__ == "__main__":
    unittest.main()
