"""Option 3 Stage 2 rebalance plan tests for pr_lifecycle_run."""

from __future__ import annotations

import copy
import unittest
from unittest import mock

from tests.pr_lifecycle_helpers import import_lifecycle_run, make_health_report

run = import_lifecycle_run()

_report = make_health_report


class Option3RebalancePlanTests(unittest.TestCase):
    def test_stage1_enqueue_cap_and_unique_path_override(self):
        candidates = [
            {
                "key": f"abhimehro/demo#{pr}@head",
                "repository": "abhimehro/demo",
                "pr": pr,
                "base_sha": "a" * 40,
                "head_sha": "b" * 40,
                "changed_paths": ["src/old.py"],
            }
            for pr in range(1, 7)
        ]
        with mock.patch.object(
            run.health, "list_reselect_candidates", return_value=candidates
        ) as select:
            planned = run.plan_stage2_enqueues(
                {"items": candidates},
                signals=run.health.ReselectSignals(
                    unique_paths_by_key={"abhimehro/demo#1": ["src/unique.py"]}
                ),
            )
        self.assertNotIn("limit", select.call_args.kwargs)
        self.assertEqual(planned["candidate_count"], 6)
        self.assertEqual(planned["enqueued_count"], 5)
        self.assertEqual(
            [action["source_key"] for action in planned["enqueue_actions"]],
            [candidate["key"] for candidate in candidates[:5]],
        )
        first = planned["enqueue_actions"][0]
        self.assertEqual(first["allowed_paths"], ["src/unique.py"])
        self.assertEqual(first["base_sha"], "a" * 40)
        self.assertEqual(first["head_sha"], "b" * 40)
        self.assertEqual(
            first["next_action"], run.health.MECHANICAL_RESELECT_NA
        )
        self.assertTrue(
            all(
                action["action"] == "ENQUEUE_STAGE2_WI"
                for action in planned["enqueue_actions"]
            )
        )

    def test_stage1_partial_enqueue_reports_incomplete_candidate(self):
        complete = {
            "key": "abhimehro/demo#1@head",
            "repository": "abhimehro/demo",
            "pr": 1,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["src/demo.py"],
        }
        incomplete = {**complete, "key": "abhimehro/demo#2@head", "head_sha": ""}
        ledger = {"ledger_revision": 1, "items": [complete, incomplete]}
        original = copy.deepcopy(ledger)
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.reconcile_mod, "collect_actions", return_value=[]),
            mock.patch.object(
                run.health, "list_reselect_candidates", return_value=ledger["items"]
            ),
        ):
            plan = run.build_stage_plan(1, ledger, {})
        self.assertEqual(ledger, original)
        self.assertEqual(
            [action["action"] for action in plan["actions"]],
            ["ENQUEUE_STAGE2_WI", "FEED_CHECK"],
        )
        self.assertEqual(plan["actions"][0]["source_key"], complete["key"])
        self.assertEqual(plan["actions"][0]["allowed_paths"], ["src/demo.py"])
        self.assertEqual(plan["actions"][1]["reselect_candidates"], 2)
        self.assertEqual(plan["actions"][1]["enqueued"], 1)
        self.assertEqual(
            plan["actions"][1]["skipped_incomplete"],
            [{"source_key": incomplete["key"], "reason": "INCOMPLETE_WI_FIELDS"}],
        )
        self.assertEqual(plan["actions"][1]["grade"], "PASS")
        self.assertIsNone(plan["stop_class"])

    def test_stage1_all_incomplete_candidates_fail_feed_check(self):
        incomplete = {
            "key": "abhimehro/demo#1@head",
            "repository": "abhimehro/demo",
            "pr": 1,
            "base_sha": "a" * 40,
            "head_sha": "",
            "changed_paths": ["src/demo.py"],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.reconcile_mod, "collect_actions", return_value=[]),
            mock.patch.object(
                run.health, "list_reselect_candidates", return_value=[incomplete]
            ),
        ):
            plan = run.build_stage_plan(1, {"items": [incomplete]}, {})
        self.assertEqual(
            [action["action"] for action in plan["actions"]], ["FEED_CHECK"]
        )
        self.assertEqual(plan["actions"][0]["grade"], "FAIL")
        self.assertEqual(plan["actions"][0]["enqueued"], 0)
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "FEED_CHECK_FAIL")

    def test_stage2_mixed_feed_salvages_only_usable_sources(self):
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
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
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
        self.assertIs(plan["actions"][1]["wi"], usable)

    def test_stage3_handoff_requires_owner_state_and_salvage_outcome(self):
        base = {
            "key": "abhimehro/demo#1@head",
            "repository": "abhimehro/demo",
            "pr": 1,
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
        }
        candidates = [
            base,
            {**base, "key": "abhimehro/demo#2@head", "current_owner": "stage1"},
            {
                **base,
                "key": "abhimehro/demo#3@head",
                "lifecycle_state": "WAITING_HUMAN",
            },
            {
                **base,
                "key": "abhimehro/demo#4@head",
                "guardrail_outcome": "REVIEW_SECURITY",
            },
            {
                **base,
                "key": "abhimehro/demo#5@head",
                "guardrail_outcome": "HOLD_EVIDENCE",
            },
        ]
        with mock.patch.object(
            run.health, "list_reselect_candidates", return_value=candidates
        ):
            actions = run.plan_stage3_mechanical_handoffs({"items": candidates})
        self.assertEqual(
            [action["source_key"] for action in actions],
            [candidates[0]["key"], candidates[4]["key"]],
        )
        self.assertTrue(
            all(
                action["action"] == "HANDOFF_MECHANICAL_TO_STAGE2"
                for action in actions
            )
        )
        self.assertEqual(
            [action["reason"] for action in actions],
            ["CONFLICTING_UNIQUE_RESELECT", "CONFLICTING_UNIQUE_RESELECT"],
        )

    def test_stage3_handoff_cap_applies_after_owner_and_outcome_filter(self):
        base = {
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
        }
        candidates = [
            {**base, "key": "demo#1@head", "current_owner": "stage1"},
            {**base, "key": "demo#2@head", "guardrail_outcome": "REVIEW_SECURITY"},
            {**base, "key": "demo#3@head"},
            {**base, "key": "demo#4@head"},
            {**base, "key": "demo#5@head"},
        ]
        with mock.patch.object(
            run.health, "list_reselect_candidates", return_value=candidates
        ) as select:
            actions = run.plan_stage3_mechanical_handoffs(
                {"items": candidates}, limit=2
            )
        self.assertNotIn("limit", select.call_args.kwargs)
        self.assertEqual(
            [action["source_key"] for action in actions],
            ["demo#3@head", "demo#4@head"],
        )

    def test_stage2_stop_with_stock_takes_precedence_over_never_touch_filter(self):
        feed_payload = {
            "empty_with_stock": True,
            "reason": "EMPTY_FEED_WITH_ELIGIBLE_STOCK",
            "work_item_count": 1,
            "eligible_stock_count": 1,
            "work_items": [{"source_item_key": "abhimehro/ctrld-sync#1206@head"}],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
            mock.patch.object(run.health, "is_never_touch_key", return_value=True),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 1}, {})
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "EMPTY_FEED_WITH_ELIGIBLE_STOCK")
        self.assertFalse(plan["skip_cursor"])
        self.assertEqual(plan["mechanical_candidate_count"], 0)
        self.assertEqual(
            [action["action"] for action in plan["actions"]], ["FEED_SUMMARY"]
        )

    def test_stage1_emits_enqueue_when_reselect_candidates_exist(self):
        candidate = {
            "key": "abhimehro/personal-config#2069@abc",
            "repository": "abhimehro/personal-config",
            "pr": 2069,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["maintenance/bin/analytics_dashboard.sh"],
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.reconcile_mod, "collect_actions", return_value=[]),
            mock.patch.object(
                run.health, "list_reselect_candidates", return_value=[candidate]
            ),
        ):
            plan = run.build_stage_plan(1, {"ledger_revision": 1}, {})
        enqueue = [a for a in plan["actions"] if a["action"] == "ENQUEUE_STAGE2_WI"]
        self.assertEqual(len(enqueue), 1)
        self.assertEqual(enqueue[0]["reason"], "CONFLICTING_UNIQUE_RESELECT")
        feed = plan["actions"][-1]
        self.assertEqual(feed["action"], "FEED_CHECK")
        self.assertEqual(feed["grade"], "PASS")
        self.assertEqual(feed["enqueued"], 1)
        self.assertIsNone(plan["stop_class"])

    def test_stage1_feed_check_fails_when_candidates_not_enqueued(self):
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.reconcile_mod, "collect_actions", return_value=[]),
            mock.patch.object(
                run,
                "plan_stage2_enqueues",
                return_value={
                    "candidate_count": 2,
                    "enqueued_count": 0,
                    "skipped_incomplete": [
                        {
                            "source_key": "owner/repo#1@a",
                            "reason": "INCOMPLETE_WI_FIELDS",
                        }
                    ],
                    "enqueue_actions": [],
                },
            ),
        ):
            plan = run.build_stage_plan(1, {"ledger_revision": 1}, {})
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "FEED_CHECK_FAIL")
        feed = plan["actions"][-1]
        self.assertEqual(feed["grade"], "FAIL")

    def test_stage2_skip_if_empty_exits_success_without_docs_pr(self):
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

    def test_stage2_filters_never_touch_then_may_skip(self):
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

    def test_stage3_handoff_and_closed_noop_deferred(self):
        candidate = {
            "key": "abhimehro/personal-config#2092@abc",
            "repository": "abhimehro/personal-config",
            "pr": 2092,
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(
                run.health, "list_reselect_candidates", return_value=[candidate]
            ),
        ):
            plan = run.build_stage_plan(3, {"ledger_revision": 3}, {})
        kinds = [a["action"] for a in plan["actions"]]
        self.assertIn("CLOSED_NOOP_DEFERRED", kinds)
        self.assertIn("HANDOFF_MECHANICAL_TO_STAGE2", kinds)
        self.assertIn("ADVISORY_BOT_THREADS", kinds)



if __name__ == "__main__":
    unittest.main()
