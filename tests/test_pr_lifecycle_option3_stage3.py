"""Option 3 Stage 3 handoff tests for pr_lifecycle_run."""

from __future__ import annotations

import unittest
from unittest import mock

from tests.pr_lifecycle_helpers import (
    import_lifecycle_run,
    make_health_report,
)

run = import_lifecycle_run()

_report = make_health_report


class Option3Stage3HandoffTests(unittest.TestCase):
    def test_stage3_handoff_requires_owner_state_and_salvage_outcome(self) -> None:
        """Verify handoffs require Stage 3 ownership, state, and salvage outcome."""
        base = {
            "key": "abhimehro/demo#1@head",
            "repository": "abhimehro/demo",
            "pr": 1,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["maintenance/bin/refresh.sh"],
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

    def test_stage3_handoff_cap_applies_after_owner_and_outcome_filter(self) -> None:
        """Verify the handoff cap applies after eligibility filtering."""
        base = {
            "repository": "abhimehro/demo",
            "pr": 3,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["maintenance/bin/refresh.sh"],
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

    def test_stage3_handoff_needs_anchors_and_live_paths(self) -> None:
        """Do not request a handoff that cannot form a complete Stage 2 item."""
        base = {
            "repository": "abhimehro/demo",
            "pr": 1,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["src/stale.py"],
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
        }
        candidates = [
            {**base, "key": "abhimehro/demo#1@head", "head_sha": ""},
            {**base, "key": "abhimehro/demo#2@head"},
            {**base, "key": "abhimehro/demo#3@head"},
        ]
        signals = run.health.ReselectSignals(
            unique_paths_by_key={
                candidates[1]["key"]: [".jules/journal.md"],
                candidates[2]["key"]: [".jules/journal.md", "src/live.py"],
            }
        )
        with (
            mock.patch.object(
                run.health, "list_reselect_candidates", return_value=candidates
            ),
            mock.patch.object(
                run.health,
                "non_journal_paths",
                side_effect=lambda paths: [
                    path for path in paths if not path.startswith(".jules/")
                ],
            ),
        ):
            actions = run.plan_stage3_mechanical_handoffs(
                {"items": candidates}, signals=signals
            )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["source_key"], candidates[2]["key"])
        self.assertEqual(actions[0]["allowed_paths"], ["src/live.py"])
        self.assertEqual(actions[0]["base_sha"], base["base_sha"])
        self.assertEqual(actions[0]["head_sha"], base["head_sha"])

    def test_stage3_handoff_and_closed_noop_deferred(self) -> None:
        """Verify Stage 3 hands off mechanical work and defers closed no-ops."""
        candidate = {
            "key": "abhimehro/personal-config#2092@abc",
            "repository": "abhimehro/personal-config",
            "pr": 2092,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["maintenance/bin/refresh.sh"],
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
