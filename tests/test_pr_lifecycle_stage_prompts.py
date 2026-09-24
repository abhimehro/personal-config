"""Stage prompt contracts: prompts stay thin bootstraps over pr_lifecycle_run."""

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
    """Stage prompts are thin bootstraps that defer to pr_lifecycle_run plans."""

    def _prompt(self, name: str) -> str:
        return expand_prompt_source(ROOT / "docs/cursor-automations/prompts" / name)

    def test_review_prompt_feeds_stage2_via_runner(self) -> None:
        review = self._prompt("daily-pr-review.md")
        self.assertIn("pr_lifecycle_run.py --stage 1", review)
        self.assertIn("emitted plan", review)
        self.assertIn("pr_lifecycle_feed.py", review)
        self.assertIn("run record", review)

    def test_salvage_prompt_heal_forward_without_merging(self) -> None:
        """The salvage prompt must heal starvation without invented merges."""
        salvage = self._prompt("daily-pr-salvage.md")
        self.assertIn("pr_lifecycle_run.py --stage 2", salvage)
        self.assertIn("never merges", salvage)
        self.assertIn("EMPTY_FEED_WITH_ELIGIBLE_STOCK", salvage)
        self.assertIn("LOGIC_STOP", salvage)
        self.assertIn("heal-forward", salvage)
        self.assertIn("Minimal WI intake", salvage)

    def test_review_prompt_schema_aware_cas_only(self) -> None:
        review = self._prompt("daily-pr-review.md")
        self.assertIn("Schema-aware CAS", review)
        self.assertIn("raw YAML", review)

    def test_completion_prompt_re_reads_predicates(self) -> None:
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn("pr_lifecycle_run.py --stage 3", completion)
        self.assertIn("Re-read predicates", completion)

    def test_completion_prompt_bot_thread_advisory(self) -> None:
        """The completion prompt binds the Abhi-approved bot-thread policy."""
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn("advisory", completion)
        self.assertIn("Codacy", completion)
        self.assertIn("REVIEW.md", completion)

    def test_completion_prompt_live_stage3_not_calibration(self) -> None:
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn("live Stage 3", completion)
        self.assertIn("Calibration stays", completion)

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
            ("daily-pr-review.md", "--stage 1"),
            ("daily-pr-salvage.md", "--stage 2"),
            ("daily-pr-completion.md", "--stage 3"),
        ):
            with self.subTest(name):
                text = " ".join(self._prompt(name).split())
                self.assertIn("docs/automated-pr-lifecycle.md", text)
                self.assertIn(f"scripts/pr_lifecycle_run.py {stage}", text)
                self.assertIn("run record", text)
                self.assertIn("Schema-aware CAS", text)
                self.assertIn("force-push", text)
                self.assertIn("Calibration stays", text)
        contract = (ROOT / "docs" / "automated-pr-lifecycle.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Shared ownership", contract)
        self.assertIn("development partners", contract)
        self.assertIn("security-first development partners", contract)
        self.assertIn("`REVIEW.md`", contract)
        self.assertIn("Citing those files is not enough", contract)

    def test_calibration_prompt_keeps_legacy_contract(self) -> None:
        """The calibration prompt is unchanged by the bootstrap rebalance."""
        calibration = self._prompt("daily-pr-completion.calibration.md")
        self.assertIn('--message "automated lifecycle ledger update"', calibration)
        self.assertIn("docs/automated-pr-lifecycle.md", calibration)
        self.assertIn("Memory is enabled", calibration)
        self.assertNotIn("{{include:", calibration)

    def test_stage_caps_are_80_40_10_and_15(self) -> None:
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        caps = config["lifecycle"]["stage_caps"]
        self.assertEqual(caps["stage1_inventory"], 80)
        self.assertEqual(caps["stage1_actions"], 40)
        self.assertEqual(caps["stage2_salvage_candidates"], 10)
        self.assertEqual(caps["stage3_completion_actions"], 15)
        self.assertEqual(config["lifecycle"]["policy_revision"], "pr-lifecycle-v1.4")



