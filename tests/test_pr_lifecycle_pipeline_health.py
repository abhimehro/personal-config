"""Pipeline health: Stage 2 starvation and salvage-eligible classification.

Install pinned `requirements.txt` (`jsonschema==4.26.0`) before running this
module; Ubuntu system jsonschema is not sufficient.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_pipeline_health as health  # noqa: E402
import pr_lifecycle_validation as validator  # noqa: E402
import yaml  # noqa: E402

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
HEALTH_SCRIPT = SCRIPTS / "pr_lifecycle_pipeline_health.py"
EXAMPLE_LEDGER = ROOT / "tasks/pr-lifecycle-ledger.example.yaml"

# (label, item overrides, expected eligible)
CLASSIFIER_CASES: tuple[tuple[str, dict[str, Any], bool], ...] = (
    ("recover unique HOLD_CONTRACT", {}, True),
    (
        "REVIEW_SECURITY",
        {"guardrail_outcome": "REVIEW_SECURITY"},
        False,
    ),
    (
        "lockfile HOLD_CONTRACT",
        {
            "sensitive_paths": ["lockfiles_and_major_dependencies"],
            "next_action": "Stage 3: HOLD_CONTRACT uv.lock. Do not merge.",
        },
        False,
    ),
    (
        "HOLD_CANONICAL",
        {
            "guardrail_outcome": "HOLD_CANONICAL",
            "next_action": "Stage 1 canonical-pick cluster",
        },
        False,
    ),
    ("HUMAN", {"author_type": "HUMAN"}, False),
    (
        "HOLD_PLATFORM Swift",
        {
            "guardrail_outcome": "HOLD_PLATFORM",
            "next_action": "Linux cannot run make guardrails",
        },
        False,
    ),
    (
        "unrecognized sticky",
        {"sensitive_paths": ["network_browser_origins"]},
        False,
    ),
    ("lint repair", {"next_action": "Fix ruff lint on src/foo.py"}, True),
    (
        "import repair",
        {"next_action": "Add TYPE_CHECKING import for Foo"},
        True,
    ),
    ("wrap repair", {"next_action": "wrap export to 88 columns"}, True),
    (
        "non-major pin",
        {"next_action": "non-major pin patch for requests"},
        True,
    ),
    (
        "missing test",
        {"next_action": "Add the missing test named in the work item"},
        True,
    ),
    (
        "conflict marker",
        {"next_action": "Remove conflict markers in src/foo.py"},
        True,
    ),
    (
        "DIRTY unique remaining",
        {"next_action": "DIRTY unique remaining source after 0cs journal"},
        True,
    ),
    (
        "do not import",
        {"next_action": "HOLD_CONTRACT: do not import optional ML deps"},
        False,
    ),
    (
        "NOT_RUN mechanical overflow",
        {"guardrail_outcome": "NOT_RUN"},
        True,
    ),
    (
        "human owner WAITING_HUMAN",
        {
            "current_owner": "human",
            "lifecycle_state": "WAITING_HUMAN",
        },
        False,
    ),
    (
        "stage2 owner",
        {
            "current_owner": "stage2",
            "lifecycle_state": "STAGE2_QUEUED",
        },
        False,
    ),
    ("unknown owner", {"current_owner": "desk"}, False),
    ("none owner", {"current_owner": "none"}, False),
    (
        "stage1 owner",
        {
            "current_owner": "stage1",
            "lifecycle_state": "STAGE1_INTAKE",
        },
        True,
    ),
)


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


def _work_item(**overrides: object) -> dict[str, object]:
    sha = "0123456789abcdef0123456789abcdef01234567"
    base: dict[str, object] = {
        "work_item_id": "s2-20260830-demo",
        "source_item_key": f"abhimehro/demo#1@{sha}",
        "repository": "abhimehro/demo",
        "pr": 1,
        "base_sha": sha,
        "head_sha": sha,
        "allowed_paths": ["src/demo.py"],
        "prohibited_paths": [],
        "repair_description": "Repair the demo path.",
        "required_test_command": "python3 -m unittest",
        "expected_test_result": "ok",
        "acceptance_criteria": ["Allowed path changes only."],
        "provenance_urls": ["https://github.com/abhimehro/demo/pull/1"],
        "expiry_utc": "2026-08-31T12:00:00Z",
        "attempt_count": 0,
        "current_owner": "stage2",
        "creation_event_id": "evt-20260830-demo",
        "history": [],
    }
    base.update(overrides)
    return base


def _ledger(
    items: list[dict[str, object]],
    work_items: list[dict[str, object]],
    revision: int = 1,
) -> dict[str, object]:
    return {
        "ledger_revision": revision,
        "items": items,
        "stage2_work_items": work_items,
    }


def _schema_valid_starved_ledger() -> dict[str, Any]:
    ledger = copy.deepcopy(yaml.safe_load(EXAMPLE_LEDGER.read_text(encoding="utf-8")))
    keeper = ledger["items"][0]
    keeper["lifecycle_state"] = "STAGE3_RECONCILIATION"
    keeper["current_owner"] = "stage3"
    keeper["next_owner"] = "stage3"
    keeper["next_action"] = (
        "Recover unique source only on a new focused draft that "
        "excludes .jules/journals/"
    )
    ledger["stage2_work_items"] = []
    events = []
    for event in ledger["events"]:
        if event["event_id"] == "evt-2026-stage2-ack-001":
            continue
        if event["event_id"] == "evt-2026-stage1-stage2-001":
            event = dict(event)
            event["to_owner"] = "stage3"
            event["to_state"] = "STAGE3_RECONCILIATION"
            event["next_owner"] = "stage3"
            event["reason"] = "Stage 1 overflowed salvage-eligible remainder."
        events.append(event)
    ledger["events"] = events
    return ledger


def _run_cli(*cli_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HEALTH_SCRIPT), *cli_args],
        check=False,
        capture_output=True,
        text=True,
    )


class TestSalvageEligibleClassifier(unittest.TestCase):
    def test_classifier_table(self) -> None:
        for label, overrides, expected in CLASSIFIER_CASES:
            with self.subTest(label):
                actual = health.is_salvage_eligible(_item(**overrides))
                self.assertEqual(actual, expected)


class TestPipelineHealthSummarize(unittest.TestCase):
    def test_starvation_when_eligible_and_empty_stage2(self) -> None:
        report = health.summarize(_ledger([_item()], [], revision=30))
        self.assertTrue(report.starvation)
        self.assertEqual(report.salvage_eligible_count, 1)

    def test_no_starvation_when_nothing_is_eligible(self) -> None:
        blocked = _item(
            guardrail_outcome="REVIEW_SECURITY",
            next_action="Human packet",
        )
        report = health.summarize(_ledger([blocked], []))
        self.assertFalse(report.starvation)
        self.assertEqual(report.salvage_eligible_count, 0)

    def test_work_item_expiry_gates_starvation(self) -> None:
        cases = (
            ("queued future", "2026-08-31T12:00:00Z", False, 1),
            ("expired", "2026-08-29T12:00:00Z", True, 0),
            ("malformed", "not-a-timestamp", True, 0),
            ("far future", "2026-09-01T00:00:00Z", False, 1),
        )
        for label, expiry, starved, wi_count in cases:
            with self.subTest(label):
                report = health.summarize(
                    _ledger([_item()], [_work_item(expiry_utc=expiry)]),
                    now=NOW,
                )
                self.assertEqual(report.starvation, starved)
                self.assertEqual(report.stage2_work_item_count, wi_count)

    def test_owned_item_starvation_matrix(self) -> None:
        owned = _item(
            current_owner="stage2",
            lifecycle_state="STAGE2_QUEUED",
        )
        remainder = _item(key="abhimehro/demo#2@def")
        cases = (
            ("owned no WI plus remainder", [owned, remainder], [], True, 0, 1, 1),
            ("owned no WI no remainder", [owned], [], False, 0, 1, 0),
            (
                "owned plus usable WI plus remainder",
                [owned, remainder],
                [_work_item()],
                False,
                1,
                1,
                1,
            ),
        )
        for label, items, wis, starved, wi_count, owned_count, eligible in cases:
            with self.subTest(label):
                report = health.summarize(_ledger(items, wis), now=NOW)
                self.assertEqual(report.starvation, starved)
                self.assertEqual(report.stage2_work_item_count, wi_count)
                self.assertEqual(report.stage2_owned_item_count, owned_count)
                self.assertEqual(report.salvage_eligible_count, eligible)

    def test_attempt_count_zero_and_empty_optional_lists_are_usable(self) -> None:
        report = health.summarize(
            _ledger(
                [_item()],
                [_work_item(attempt_count=0, prohibited_paths=[], history=[])],
            ),
            now=NOW,
        )
        self.assertFalse(report.starvation)
        self.assertEqual(report.stage2_work_item_count, 1)

    def test_incomplete_work_item_does_not_suppress_starvation(self) -> None:
        incomplete = _work_item()
        del incomplete["repository"]
        report = health.summarize(_ledger([_item()], [incomplete]), now=NOW)
        self.assertTrue(report.starvation)
        self.assertEqual(report.stage2_work_item_count, 0)

    def test_empty_required_strings_do_not_suppress_starvation(self) -> None:
        cases = (
            ("empty repair_description", {"repair_description": ""}),
            ("empty work_item_id", {"work_item_id": ""}),
            ("empty required_test_command", {"required_test_command": ""}),
        )
        for label, overrides in cases:
            with self.subTest(label):
                report = health.summarize(
                    _ledger([_item()], [_work_item(**overrides)]),
                    now=NOW,
                )
                self.assertTrue(report.starvation)
                self.assertEqual(report.stage2_work_item_count, 0)

    def test_required_work_item_fields_match_schema(self) -> None:
        schema_path = ROOT / "schemas/pr-lifecycle-ledger.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        expected = tuple(schema["$defs"]["stage2WorkItem"]["required"])
        self.assertEqual(health.REQUIRED_WORK_ITEM_FIELDS, expected)


class TestPipelineHealthCli(unittest.TestCase):
    def _write(self, ledger: dict[str, object]) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "runtime-ledger.yaml"
        path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
        return path

    def test_cli_exit_2_on_starvation(self) -> None:
        path = self._write(_schema_valid_starved_ledger())
        proc = _run_cli(str(path))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("starvation=true", proc.stdout)

    def test_cli_json_and_exit_0_when_clear(self) -> None:
        proc = _run_cli("--json", str(EXAMPLE_LEDGER))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["starvation"])
        self.assertEqual(payload["stage2_work_item_count"], 0)
        self.assertGreaterEqual(payload["stage2_owned_item_count"], 1)

    def test_cli_exit_1_on_schema_invalid_items_mapping(self) -> None:
        path = self._write({"items": [], "stage2_work_items": []})
        proc = _run_cli(str(path))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("PR_LIFECYCLE_HEALTH_ERROR", proc.stderr)

    def test_cli_refuses_pointer_copies_and_non_ledger(self) -> None:
        path_pointer = ROOT / "tasks" / "pr-lifecycle-ledger.yaml"
        self.assertTrue(path_pointer.is_file())
        proc = _run_cli(str(path_pointer))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refusing main-branch pointer", proc.stderr)

        pointer = yaml.safe_load(path_pointer.read_text(encoding="utf-8"))
        cases = (
            ("copied pointer", pointer, "refusing main-branch pointer"),
            ("arbitrary mapping", {"foo": "bar"}, "not a runtime ledger mapping"),
        )
        for label, document, needle in cases:
            with self.subTest(label):
                copied = self._write(document)
                result = _run_cli(str(copied))
                self.assertEqual(result.returncode, 1)
                self.assertIn(needle, result.stderr)


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
        self.assertIn("not inventory-capped", review)
        self.assertIn("Hold five inventory slots", review)

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
        self.assertIn("66a8e7a8-9c42-11f1-ba66-0e7d0216e441", profile)
        self.assertIn("d9d2c058-9c42-11f1-ba66-0e7d0216e441", profile)

    def test_stage_caps_are_80_and_40(self) -> None:
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        self.assertEqual(config["lifecycle"]["stage_caps"]["stage1_inventory"], 80)
        self.assertEqual(config["lifecycle"]["stage_caps"]["stage1_actions"], 40)
        self.assertEqual(config["lifecycle"]["policy_revision"], "pr-lifecycle-v1.4")


if __name__ == "__main__":
    unittest.main()
