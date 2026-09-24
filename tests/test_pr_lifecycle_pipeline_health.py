"""Pipeline health: Stage 2 starvation and salvage-eligible classification.

Install pinned `requirements.txt` (`jsonschema==4.26.0`) before running this
module; Ubuntu system jsonschema is not sufficient.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_pipeline_health as health  # noqa: E402
from tests.pr_lifecycle_helpers import (  # noqa: E402
    NOW,
    make_item,
    make_ledger,
    make_work_item,
)

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



class TestSalvageEligibleClassifier(unittest.TestCase):
    def test_classifier_table(self) -> None:
        for label, overrides, expected in CLASSIFIER_CASES:
            with self.subTest(label):
                actual = health.is_salvage_eligible(make_item(**overrides))
                self.assertEqual(actual, expected)


class TestPipelineHealthSummarize(unittest.TestCase):
    def test_starvation_when_eligible_and_empty_stage2(self) -> None:
        report = health.summarize(make_ledger([make_item()], [], revision=30))
        self.assertTrue(report.starvation)
        self.assertEqual(report.salvage_eligible_count, 1)

    def test_no_starvation_when_nothing_is_eligible(self) -> None:
        blocked = make_item(
            guardrail_outcome="REVIEW_SECURITY",
            next_action="Human packet",
        )
        report = health.summarize(make_ledger([blocked], []))
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
                    make_ledger([make_item()], [make_work_item(expiry_utc=expiry)]),
                    now=NOW,
                )
                self.assertEqual(report.starvation, starved)
                self.assertEqual(report.stage2_work_item_count, wi_count)

    def test_owned_item_starvation_matrix(self) -> None:
        owned = make_item(
            current_owner="stage2",
            lifecycle_state="STAGE2_QUEUED",
        )
        remainder = make_item(key="abhimehro/demo#2@def")
        cases = (
            ("owned no WI plus remainder", [owned, remainder], [], True, 0, 1, 1),
            ("owned no WI no remainder", [owned], [], False, 0, 1, 0),
            (
                "owned plus usable WI plus remainder",
                [owned, remainder],
                [make_work_item()],
                False,
                1,
                1,
                1,
            ),
        )
        for label, items, wis, starved, wi_count, owned_count, eligible in cases:
            with self.subTest(label):
                report = health.summarize(make_ledger(items, wis), now=NOW)
                self.assertEqual(report.starvation, starved)
                self.assertEqual(report.stage2_work_item_count, wi_count)
                self.assertEqual(report.stage2_owned_item_count, owned_count)
                self.assertEqual(report.salvage_eligible_count, eligible)

    def test_attempt_count_zero_and_empty_optional_lists_are_usable(self) -> None:
        report = health.summarize(
            make_ledger(
                [make_item()],
                [make_work_item(attempt_count=0, prohibited_paths=[], history=[])],
            ),
            now=NOW,
        )
        self.assertFalse(report.starvation)
        self.assertEqual(report.stage2_work_item_count, 1)

    def test_incomplete_work_item_does_not_suppress_starvation(self) -> None:
        incomplete = make_work_item()
        del incomplete["repository"]
        report = health.summarize(make_ledger([make_item()], [incomplete]), now=NOW)
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
                    make_ledger([make_item()], [make_work_item(**overrides)]),
                    now=NOW,
                )
                self.assertTrue(report.starvation)
                self.assertEqual(report.stage2_work_item_count, 0)

    def test_required_work_item_fields_match_schema(self) -> None:
        schema_path = ROOT / "schemas/pr-lifecycle-ledger.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        expected = tuple(schema["$defs"]["stage2WorkItem"]["required"])
        self.assertEqual(health.REQUIRED_WORK_ITEM_FIELDS, expected)

