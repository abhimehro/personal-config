"""Pipeline health: Stage 2 starvation and salvage-eligible classification."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_pipeline_health as health  # noqa: E402
import yaml  # noqa: E402


def _item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "key": "abhimehro/demo#1@abc",
        "author_type": "BOT",
        "lifecycle_state": "STAGE3_RECONCILIATION",
        "current_owner": "stage3",
        "guardrail_outcome": "HOLD_CONTRACT",
        "sensitive_paths": ["generated_output"],
        "next_action": (
            "Recover unique source only on a new focused draft that "
            "excludes .jules/journals/"
        ),
    }
    base.update(overrides)
    return base


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def _work_item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "work_item_id": "s2-20260830-demo",
        "source_item_key": "abhimehro/demo#1@abc",
        "allowed_paths": ["src/demo.py"],
        "required_test_command": "python3 -m unittest",
        "expiry_utc": "2026-08-31T12:00:00Z",
        "current_owner": "stage2",
    }
    base.update(overrides)
    return base


class TestSalvageEligibleClassifier(unittest.TestCase):
    def test_recover_unique_hold_contract_is_eligible(self) -> None:
        self.assertTrue(health.is_salvage_eligible(_item()))

    def test_review_security_is_not_eligible(self) -> None:
        self.assertFalse(
            health.is_salvage_eligible(_item(guardrail_outcome="REVIEW_SECURITY"))
        )

    def test_lockfile_hold_contract_is_not_eligible(self) -> None:
        self.assertFalse(
            health.is_salvage_eligible(
                _item(
                    sensitive_paths=["lockfiles_and_major_dependencies"],
                    next_action="Stage 3: HOLD_CONTRACT uv.lock. Do not merge.",
                )
            )
        )

    def test_hold_canonical_is_stage1_not_stage2(self) -> None:
        self.assertFalse(
            health.is_salvage_eligible(
                _item(
                    guardrail_outcome="HOLD_CANONICAL",
                    next_action="Stage 1 canonical-pick cluster",
                )
            )
        )

    def test_human_is_not_eligible(self) -> None:
        self.assertFalse(health.is_salvage_eligible(_item(author_type="HUMAN")))

    def test_hold_platform_swift_is_not_eligible(self) -> None:
        self.assertFalse(
            health.is_salvage_eligible(
                _item(
                    guardrail_outcome="HOLD_PLATFORM",
                    next_action="Linux cannot run make guardrails",
                )
            )
        )

    def test_unrecognized_sticky_label_is_not_eligible(self) -> None:
        self.assertFalse(
            health.is_salvage_eligible(
                _item(sensitive_paths=["network_browser_origins"])
            )
        )

    def test_lint_repair_is_eligible(self) -> None:
        self.assertTrue(
            health.is_salvage_eligible(_item(next_action="Fix ruff lint on src/foo.py"))
        )

    def test_import_repair_is_eligible(self) -> None:
        self.assertTrue(
            health.is_salvage_eligible(
                _item(next_action="Add TYPE_CHECKING import for Foo")
            )
        )

    def test_wrap_repair_is_eligible(self) -> None:
        self.assertTrue(
            health.is_salvage_eligible(_item(next_action="wrap export to 88 columns"))
        )

    def test_non_major_pin_is_eligible(self) -> None:
        self.assertTrue(
            health.is_salvage_eligible(
                _item(next_action="non-major pin patch for requests")
            )
        )

    def test_missing_test_is_eligible(self) -> None:
        self.assertTrue(
            health.is_salvage_eligible(
                _item(next_action="Add the missing test named in the work item")
            )
        )

    def test_conflict_marker_is_eligible(self) -> None:
        self.assertTrue(
            health.is_salvage_eligible(
                _item(next_action="Remove conflict markers in src/foo.py")
            )
        )

    def test_dirty_unique_remaining_is_eligible(self) -> None:
        self.assertTrue(
            health.is_salvage_eligible(
                _item(next_action="DIRTY unique remaining source after 0cs journal")
            )
        )

    def test_do_not_import_is_not_eligible(self) -> None:
        self.assertFalse(
            health.is_salvage_eligible(
                _item(next_action="HOLD_CONTRACT: do not import optional ML deps")
            )
        )


class TestPipelineHealthSummarize(unittest.TestCase):
    def test_starvation_when_eligible_and_empty_stage2(self) -> None:
        report = health.summarize(
            {
                "ledger_revision": 30,
                "items": [_item()],
                "stage2_work_items": [],
            }
        )
        self.assertTrue(report.starvation)
        self.assertEqual(report.salvage_eligible_count, 1)

    def test_no_starvation_when_truly_empty(self) -> None:
        report = health.summarize(
            {
                "ledger_revision": 1,
                "items": [
                    _item(
                        guardrail_outcome="REVIEW_SECURITY",
                        next_action="Human packet",
                    )
                ],
                "stage2_work_items": [],
            }
        )
        self.assertFalse(report.starvation)
        self.assertEqual(report.salvage_eligible_count, 0)

    def test_no_starvation_when_work_item_queued(self) -> None:
        report = health.summarize(
            {
                "ledger_revision": 2,
                "items": [_item()],
                "stage2_work_items": [_work_item()],
            },
            now=NOW,
        )
        self.assertFalse(report.starvation)
        self.assertEqual(report.stage2_work_item_count, 1)

    def test_expired_work_item_does_not_hide_starvation(self) -> None:
        report = health.summarize(
            {
                "ledger_revision": 3,
                "items": [_item()],
                "stage2_work_items": [_work_item(expiry_utc="2026-08-29T12:00:00Z")],
            },
            now=NOW,
        )
        self.assertTrue(report.starvation)
        self.assertEqual(report.stage2_work_item_count, 0)

    def test_malformed_expiry_does_not_hide_starvation(self) -> None:
        report = health.summarize(
            {
                "ledger_revision": 4,
                "items": [_item()],
                "stage2_work_items": [_work_item(expiry_utc="not-a-timestamp")],
            },
            now=NOW,
        )
        self.assertTrue(report.starvation)

    def test_future_work_item_clears_starvation(self) -> None:
        report = health.summarize(
            {
                "ledger_revision": 5,
                "items": [_item()],
                "stage2_work_items": [_work_item(expiry_utc="2026-09-01T00:00:00Z")],
            },
            now=NOW,
        )
        self.assertFalse(report.starvation)


class TestPipelineHealthCli(unittest.TestCase):
    def _write(self, ledger: dict[str, object]) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "runtime-ledger.yaml"
        path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
        return path

    def test_cli_exit_2_on_starvation(self) -> None:
        path = self._write(
            {
                "ledger_revision": 30,
                "items": [_item()],
                "stage2_work_items": [],
            }
        )
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "pr_lifecycle_pipeline_health.py"), str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("starvation=true", proc.stdout)

    def test_cli_json_and_exit_0_when_clear(self) -> None:
        path = self._write(
            {
                "ledger_revision": 1,
                "items": [
                    _item(
                        guardrail_outcome="REVIEW_SECURITY",
                        next_action="Human packet",
                    )
                ],
                "stage2_work_items": [],
            }
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "pr_lifecycle_pipeline_health.py"),
                "--json",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["starvation"])

    def test_cli_refuses_main_branch_pointer(self) -> None:
        pointer = ROOT / "tasks" / "pr-lifecycle-ledger.yaml"
        self.assertTrue(pointer.is_file())
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "pr_lifecycle_pipeline_health.py"),
                str(pointer),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refusing main-branch pointer", proc.stderr)


class TestStage1BurndownAndSalvagePrompts(unittest.TestCase):
    def _prompt(self, name: str) -> str:
        return (ROOT / "docs/cursor-automations/prompts" / name).read_text(
            encoding="utf-8"
        )

    def test_review_prompt_raised_caps_and_salvage_queue(self) -> None:
        review = self._prompt("daily-pr-review.md")
        self.assertIn("at most 80 inventory items and at most 40", review)
        self.assertIn("salvage-eligible", review)
        self.assertIn("bookkeeping", review)
        self.assertIn("empty-intake", review)

    def test_salvage_prompt_starvation_label_without_inventing(self) -> None:
        salvage = self._prompt("daily-pr-salvage.md")
        self.assertIn("EMPTY_INTAKE_STARVATION", salvage)
        self.assertIn("Do not invent recoveries", salvage)

    def test_completion_prompt_overflow_complete_and_stage2_wi(self) -> None:
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn("Do **not** bounce MERGEABLE", completion)
        self.assertIn("complete Stage 2 work item", completion)

    def test_pr_desk_flags_starvation(self) -> None:
        profile = (ROOT / "docs/grok-bot/pr-desk.profile.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("salvage-eligible", profile)
        self.assertIn("Write Nothing", profile)

    def test_stage_caps_are_80_and_40(self) -> None:
        import pr_lifecycle_validation as validator

        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        self.assertEqual(config["lifecycle"]["stage_caps"]["stage1_inventory"], 80)
        self.assertEqual(config["lifecycle"]["stage_caps"]["stage1_actions"], 40)
        self.assertEqual(
            config["lifecycle"]["policy_revision"], "pr-lifecycle-v1.4"
        )


if __name__ == "__main__":
    unittest.main()
