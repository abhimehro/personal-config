"""Contracts for the expanded lifecycle stage prompts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_validation as validator  # noqa: E402
from sync_cursor_export_prompts import expand_prompt_source  # noqa: E402


class TestStagePromptContracts(unittest.TestCase):
    """Stage prompts bind runtime authority, routing, and action limits."""

    def _prompt(self, name: str) -> str:
        """Read an automation prompt for contract assertions."""
        text = expand_prompt_source(ROOT / "docs/cursor-automations/prompts" / name)
        return " ".join(text.split())

    def test_review_prompt_routes_stage2_and_overflow(self) -> None:
        """Mechanical work is owned even when a bounded review run fills up."""
        review = self._prompt("daily-pr-review.md")
        self.assertIn("create exactly one complete Stage 2 work item", review)
        self.assertIn(
            "inventory cap filled as overflow, not as unowned",
            review,
        )
        self.assertIn("run record", review)

    def test_salvage_prompt_validates_work_and_preserves_drafts(self) -> None:
        """Salvage requires bounded work, validation, and a draft handoff."""
        salvage = self._prompt("daily-pr-salvage.md")
        self.assertIn("complete unexpired work items", salvage)
        self.assertIn("allowed and prohibited paths", salvage)
        self.assertIn(
            "Never approve, request review, mark ready, merge, close",
            salvage,
        )
        self.assertIn("Run the named test", salvage)
        self.assertIn("re-read `isDraft`", salvage)
        self.assertIn(
            "do not expand scope when a path was split or removed",
            salvage,
        )

    def test_review_prompt_requires_validated_cas(self) -> None:
        """Unreadable or unwritable runtime state prevents lifecycle actions."""
        review = self._prompt("daily-pr-review.md")
        self.assertIn(
            "read, validated, or written through its selected CAS path",
            review,
        )
        self.assertIn("take no lifecycle action or calibration step", review)
        self.assertIn("revision-checked events", review)

    def test_completion_prompt_re_reads_predicates(self) -> None:
        """Completion independently verifies evidence before acting."""
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn(
            "immutable anchors immediately before every action",
            completion,
        )
        self.assertIn(
            "Re-read every predicate independently of Stage 2's recovery notes",
            completion,
        )
        self.assertIn(
            "Recheck every predicate after approval and before queue submission",
            completion,
        )

    def test_completion_prompt_holds_without_required_evidence(self) -> None:
        """Completion cannot treat missing check evidence as merge authority."""
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn(
            "Never act on human, unknown, security-sensitive",
            completion,
        )
        self.assertIn(
            "required-check configuration cannot be read, hold rather than act",
            completion,
        )
        self.assertIn("TRUNK_QUEUE", completion)

    def test_completion_prompt_requires_approved_calibration(self) -> None:
        """Bounded completion is conditional on approval for the current policy."""
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn("bounded-completion variant", completion)
        self.assertIn(
            "calibration status `APPROVED` for the current scope and policy revision",
            completion,
        )
        self.assertIn("five state-changing actions", completion)
        self.assertIn("Stop before exceeding the cap", completion)

    def test_pr_desk_flags_starvation(self) -> None:
        """The PR Desk profile must expose starvation indicators."""
        profile = (ROOT / "docs/grok-bot/pr-desk.profile.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("salvage-eligible", profile)
        self.assertIn("Write Nothing", profile)
        self.assertIn("66a8e7a8-9c42-11f1-ba66-0e7d0216e441", profile)
        self.assertIn("d9d2c058-9c42-11f1-ba66-0e7d0216e441", profile)

    def test_stage_prompts_shared_ownership(self) -> None:
        """Stage prompts bind the lifecycle contract; ownership prose lives there."""
        for name, stage in (
            ("daily-pr-review.md", "Stage-1-owned"),
            ("daily-pr-salvage.md", "Stage-2-owned"),
            ("daily-pr-completion.md", "Stage-3-owned"),
        ):
            with self.subTest(name):
                text = " ".join(self._prompt(name).split())
                self.assertIn("docs/automated-pr-lifecycle.md", text)
                self.assertIn(stage, text)
                self.assertIn("run record", text)
                self.assertIn("revision-checked events", text)
                self.assertIn(
                    "A changed anchor invalidates prior evidence",
                    text,
                )
                self.assertIn("selected CAS path", text)
        contract = (ROOT / "docs" / "automated-pr-lifecycle.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Shared ownership", contract)
        self.assertIn("development partners", contract)
        self.assertIn("security-first development partners", contract)
        self.assertIn("`REVIEW.md`", contract)
        self.assertIn("Citing those files is not enough", contract)

    def test_calibration_prompt_reset_is_not_success(self) -> None:
        """Calibration resets stale policy without counting a successful run."""
        calibration = self._prompt("daily-pr-completion.calibration.md")
        self.assertIn("rewrite `calibration` to `REPORT_ONLY`", calibration)
        self.assertIn("`successful_run_count` 0", calibration)
        self.assertIn(
            "That reset is not a successful calibration run",
            calibration,
        )
        self.assertIn(
            "report-only for approve/merge/close/comment/branch mutations",
            calibration,
        )
        self.assertIn(
            "Never approve, merge, submit to a queue, close, comment",
            calibration,
        )

    def test_stage_caps_are_80_40_10_and_15(self) -> None:
        """Verify the documented intake, mutation, salvage, and completion caps."""
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        caps = config["lifecycle"]["stage_caps"]
        self.assertEqual(caps["stage1_inventory"], 80)
        self.assertEqual(caps["stage1_actions"], 40)
        self.assertEqual(caps["stage2_salvage_candidates"], 10)
        self.assertEqual(caps["stage3_completion_actions"], 15)
        self.assertEqual(config["lifecycle"]["policy_revision"], "pr-lifecycle-v1.4")
