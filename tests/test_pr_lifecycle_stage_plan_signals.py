"""Planner regressions for live anchors, immutable inputs, and stage ownership."""

from __future__ import annotations

import copy
import unittest
from typing import Any
from unittest import mock

import pr_lifecycle_pipeline_health as health

from tests.pr_lifecycle_helpers import (
    NOW,
    import_lifecycle_run,
    make_ledger,
    make_queryable_item,
    make_work_item,
)

run = import_lifecycle_run()


class StagePlanSignalTests(unittest.TestCase):
    def setUp(self) -> None:
        # Exercise the real selector while preserving the runner fixture's
        # module isolation and avoiding any reconciliation network calls.
        # BOT fixtures never reach the author allowlist, so no gate patch.
        self.enterContext(
            mock.patch.object(
                run.health, "list_reselect_candidates", health.list_reselect_candidates
            )
        )

    @staticmethod
    def candidate(stage: int, pr: int = 1) -> dict[str, Any]:
        return make_queryable_item(
            key=f"abhimehro/demo#{pr}@{'c' * 40}",
            repository="abhimehro/demo",
            pr=pr,
            current_owner=f"stage{stage}",
            lifecycle_state="STAGE3_RECONCILIATION" if stage == 3 else "STAGE1_REVIEW",
            next_action="CONFLICTING unique remaining",
        )

    @staticmethod
    def actions(
        stage: int, ledger: dict[str, Any], signals: health.ReselectSignals
    ) -> list[dict[str, Any]]:
        if stage == 1:
            return run.plan_stage2_enqueues(ledger, signals=signals)["enqueue_actions"]
        return run.plan_stage3_mechanical_handoffs(ledger, signals=signals)

    def test_base_anchor_precedence_and_fallback_for_both_stages(self) -> None:
        for stage in (1, 3):
            item = self.candidate(stage)
            prefix = "abhimehro/demo#1"
            for mapping, expected in (
                (None, "b" * 40),
                ({prefix: "d" * 40}, "d" * 40),
                ({prefix: "d" * 40, item["key"]: "e" * 40}, "e" * 40),
                ({prefix: "d" * 40, item["key"]: ""}, "b" * 40),
            ):
                with self.subTest(stage=stage, mapping=mapping):
                    actions = self.actions(
                        stage,
                        make_ledger([item], []),
                        health.ReselectSignals(live_base_sha_by_key=mapping),
                    )
                    self.assertEqual(len(actions), 1)
                    self.assertEqual(actions[0]["base_sha"], expected)
                    self.assertEqual(actions[0]["head_sha"], "c" * 40)
                    self.assertEqual(actions[0]["source_key"], item["key"])

    def test_live_base_does_not_rescue_missing_ledger_anchor(self) -> None:
        for stage in (1, 3):
            for field in ("head_sha", "base_sha"):
                with self.subTest(stage=stage, field=field):
                    item = self.candidate(stage)
                    item[field] = ""
                    # A sibling with intact anchors stays selected, so an
                    # empty result here is not a vacuous pass.
                    control = self.candidate(stage, pr=9)
                    signals = health.ReselectSignals(
                        live_base_sha_by_key={item["key"]: "d" * 40},
                        live_head_sha_by_key={item["key"]: "c" * 40},
                    )
                    actions = self.actions(
                        stage, make_ledger([item, control], []), signals
                    )
                    self.assertEqual(
                        [a["source_key"] for a in actions], [control["key"]]
                    )

    def test_planning_and_editing_action_paths_do_not_mutate_inputs(self) -> None:
        for stage in (1, 3):
            for live_paths in (False, True):
                with self.subTest(stage=stage, live_paths=live_paths):
                    item = self.candidate(stage)
                    item["changed_paths"] = [".jules/bolt.md", "src/ledger.py"]
                    ledger = make_ledger([item], [])
                    signals = health.ReselectSignals(
                        unique_paths_by_key=(
                            {item["key"]: [".jules/bolt.md", "src/live.py"]}
                            if live_paths
                            else None
                        )
                    )
                    before_ledger, before_signals = copy.deepcopy((ledger, signals))
                    actions = self.actions(stage, ledger, signals)
                    self.assertEqual(len(actions), 1)
                    self.assertEqual(
                        actions[0]["allowed_paths"],
                        ["src/live.py" if live_paths else "src/ledger.py"],
                    )
                    actions[0]["allowed_paths"].append("src/later-edit.py")
                    self.assertEqual(ledger, before_ledger)
                    self.assertEqual(signals, before_signals)

    def test_live_signals_preserve_exclusive_stage_ownership(self) -> None:
        items = [self.candidate(1, 1), self.candidate(3, 2)]
        ledger = make_ledger(items, [])
        # The stage-1 item's ledger action does not qualify on its own, so
        # its selection depends on the live DIRTY mergeable signal.
        items[0]["next_action"] = "needs verification"
        signals = health.ReselectSignals(
            live_mergeable_by_key={item["key"]: "DIRTY" for item in items},
            live_base_sha_by_key={item["key"]: "d" * 40 for item in items},
        )
        enqueues = self.actions(1, ledger, signals)
        handoffs = self.actions(3, ledger, signals)
        self.assertEqual(
            [action["source_key"] for action in enqueues], [items[0]["key"]]
        )
        self.assertEqual(
            [action["source_key"] for action in handoffs], [items[1]["key"]]
        )
        self.assertEqual(enqueues[0]["action"], "ENQUEUE_STAGE2_WI")
        self.assertEqual(handoffs[0]["action"], "HANDOFF_MECHANICAL_TO_STAGE2")

    def test_live_exclusions_leave_capacity_for_later_candidates(self) -> None:
        for stage in (1, 3):
            with self.subTest(stage=stage):
                items = [self.candidate(stage, pr) for pr in range(1, 6)]
                signals = health.ReselectSignals(
                    closed_keys=frozenset({items[0]["key"]}),
                    live_head_sha_by_key={items[1]["key"]: "d" * 40},
                    live_mergeable_by_key={items[2]["key"]: "CLEAN"},
                    unique_paths_by_key={items[3]["key"]: ["src/live.py"]},
                    live_base_sha_by_key={items[3]["key"]: "e" * 40},
                )
                ledger = make_ledger(items, [])
                if stage == 1:
                    planned = run.plan_stage2_enqueues(ledger, signals=signals, limit=1)
                    self.assertEqual(planned["candidate_count"], 2)
                    self.assertEqual(planned["enqueued_count"], 1)
                    self.assertEqual(planned["skipped_incomplete"], [])
                    actions = planned["enqueue_actions"]
                else:
                    actions = run.plan_stage3_mechanical_handoffs(
                        ledger, signals=signals, limit=1
                    )
                self.assertEqual(len(actions), 1)
                self.assertEqual(actions[0]["source_key"], items[3]["key"])
                self.assertEqual(actions[0]["base_sha"], "e" * 40)
                self.assertEqual(actions[0]["head_sha"], "c" * 40)
                self.assertEqual(actions[0]["allowed_paths"], ["src/live.py"])

    def test_exact_empty_paths_override_prefix_and_ledger_paths(self) -> None:
        for stage in (1, 3):
            item = self.candidate(stage)
            for paths in ([], [".jules/bolt.md"]):
                with self.subTest(stage=stage, paths=paths):
                    signals = health.ReselectSignals(
                        unique_paths_by_key={
                            "abhimehro/demo#1": ["src/prefix.py"],
                            item["key"]: paths,
                        },
                        live_mergeable_by_key={item["key"]: "CONFLICTING"},
                    )
                    self.assertEqual(
                        self.actions(stage, make_ledger([item], []), signals), []
                    )

    @mock.patch("pr_lifecycle_health_runtime._clock", return_value=NOW)
    def test_live_signals_do_not_duplicate_queued_work_for_another_head(
        self, _clock: mock.Mock
    ) -> None:
        for stage in (1, 3):
            with self.subTest(stage=stage):
                item = self.candidate(stage)
                queued = make_work_item(
                    source_item_key="abhimehro/demo#1@" + "a" * 40,
                    head_sha="a" * 40,
                )
                signals = health.ReselectSignals(
                    live_mergeable_by_key={item["key"]: "CONFLICTING"},
                    live_head_sha_by_key={item["key"]: item["head_sha"]},
                    unique_paths_by_key={item["key"]: ["src/live.py"]},
                )
                # A usable WI suppresses the entire PR prefix even if the
                # new ledger head and live signals would otherwise qualify.
                self.assertEqual(
                    self.actions(stage, make_ledger([item], [queued]), signals), []
                )
                self.assertEqual(
                    len(self.actions(stage, make_ledger([item], []), signals)), 1
                )


if __name__ == "__main__":
    unittest.main()
