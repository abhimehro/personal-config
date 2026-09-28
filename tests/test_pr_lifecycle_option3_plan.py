"""Option 3 Stage 2 rebalance plan tests for pr_lifecycle_run."""

from __future__ import annotations

import copy
import unittest
from unittest import mock

from tests.pr_lifecycle_helpers import (
    import_lifecycle_run,
    make_health_report,
    make_item,
    make_ledger,
)

import pr_lifecycle_pipeline_health as real_health

run = import_lifecycle_run()

_report = make_health_report


class Option3RebalancePlanTests(unittest.TestCase):
    def test_stage1_planner_uses_live_selector_before_enqueuing(self) -> None:
        """Only current conflicting or dirty sources become enqueue actions."""
        base = {
            "repository": "abhimehro/demo",
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "current_owner": "stage1",
            "changed_paths": ["src/stale.py"],
        }
        stale = make_item(
            **base,
            key="abhimehro/demo#1@new",
            pr=1,
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        live = make_item(
            **base,
            key="abhimehro/demo#2@new",
            pr=2,
            next_action="Needs live verification",
        )
        ledger = make_ledger([stale, live], [])
        signals = real_health.ReselectSignals(
            live_mergeable_by_key={
                "abhimehro/demo#1": "MERGEABLE",
                "abhimehro/demo#2": "DIRTY",
            },
            unique_paths_by_key={
                "abhimehro/demo#2": [".jules/journal.md", "src/unique.py"]
            },
        )
        with (
            mock.patch.object(
                run.health,
                "list_reselect_candidates",
                side_effect=real_health.list_reselect_candidates,
            ),
            mock.patch.object(
                run.health,
                "non_journal_paths",
                side_effect=real_health.non_journal_paths,
            ),
            mock.patch.object(
                run.health, "signal_value", side_effect=real_health.signal_value
            ),
        ):
            planned = run.plan_stage2_enqueues(ledger, signals=signals)
        self.assertEqual(planned["candidate_count"], 1)
        self.assertEqual(planned["enqueued_count"], 1)
        self.assertEqual(planned["skipped_incomplete"], [])
        self.assertEqual(
            [action["source_key"] for action in planned["enqueue_actions"]],
            [live["key"]],
        )
        self.assertEqual(
            planned["enqueue_actions"][0]["allowed_paths"], ["src/unique.py"]
        )


    def test_stage1_enqueue_cap_and_unique_path_override(self) -> None:
        """Verify Stage 1 caps complete enqueues and uses unique source paths."""
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

    def test_stage1_partial_enqueue_reports_incomplete_candidate(self) -> None:
        """Verify Stage 1 reports incomplete candidates beside valid enqueues."""
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

    def test_stage1_cap_counts_complete_items_after_incomplete_candidates(self) -> None:
        """Incomplete early candidates must not consume the enqueue cap."""
        candidates = [
            {
                "key": f"abhimehro/demo#{pr}@head",
                "repository": "abhimehro/demo",
                "pr": pr,
                "base_sha": "a" * 40,
                "head_sha": "" if pr < 3 else "b" * 40,
                "changed_paths": ["src/demo.py"],
            }
            for pr in range(1, 6)
        ]
        with mock.patch.object(
            run.health, "list_reselect_candidates", return_value=candidates
        ):
            planned = run.plan_stage2_enqueues(
                {"items": candidates}, limit=2
            )
        self.assertEqual(planned["candidate_count"], 5)
        self.assertEqual(planned["enqueued_count"], 2)
        self.assertEqual(
            [action["source_key"] for action in planned["enqueue_actions"]],
            [candidates[2]["key"], candidates[3]["key"]],
        )
        self.assertEqual(
            [item["source_key"] for item in planned["skipped_incomplete"]],
            [candidates[0]["key"], candidates[1]["key"]],
        )

    def test_stage1_all_incomplete_candidates_fail_feed_check(self) -> None:
        """Verify Stage 1 fails the feed check when every candidate is incomplete."""
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




    def test_stage1_emits_enqueue_when_reselect_candidates_exist(self) -> None:
        """Verify Stage 1 enqueues eligible reselection candidates."""
        candidate = {
            "key": "abhimehro/personal-config#2069@abc",
            "repository": "abhimehro/personal-config",
            "pr": 2069,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["maintenance/bin/analytics_dashboard.sh"],
            "current_owner": "stage1",
            "lifecycle_state": "CONFLICTING",
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

    def test_stage1_excludes_stage3_owned_from_enqueues(self):
        """Verify Stage 1 leaves Stage 3 owned items to the handoff path."""
        stage3_item = {
            "key": "abhimehro/demo#1@abc",
            "repository": "abhimehro/demo",
            "pr": 1,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["src/demo.py"],
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
        }
        with mock.patch.object(
            run.health, "list_reselect_candidates", return_value=[stage3_item]
        ):
            planned = run.plan_stage2_enqueues(
                {"items": [stage3_item]},
            )
        self.assertEqual(planned["candidate_count"], 0)
        self.assertEqual(planned["enqueued_count"], 0)
        self.assertEqual(planned["enqueue_actions"], [])

    def test_stage1_enqueue_uses_paths_when_changed_paths_missing(self) -> None:
        """Verify enqueue path resolution falls back to the item paths field."""
        candidate = {
            "key": "abhimehro/demo#2@abc",
            "repository": "abhimehro/demo",
            "pr": 2,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "paths": ["src/demo.py"],
        }
        with mock.patch.object(
            run.health, "list_reselect_candidates", return_value=[candidate]
        ):
            planned = run.plan_stage2_enqueues({"items": [candidate]})
        self.assertEqual(planned["enqueued_count"], 1)
        self.assertEqual(
            planned["enqueue_actions"][0]["allowed_paths"], ["src/demo.py"]
        )
        self.assertEqual(planned["skipped_incomplete"], [])

    def test_stage1_feed_check_fails_when_candidates_not_enqueued(self) -> None:
        """Verify the feed check fails when no candidate can be enqueued."""
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






if __name__ == "__main__":
    unittest.main()
