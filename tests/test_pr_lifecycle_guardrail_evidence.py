"""Unit tests for check rollups, evidence fetching, and fail-closed decisions."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_guardrails as guardrails  # noqa: E402

from tests.pr_lifecycle_helpers import guardrail_item as _item  # noqa: E402


class RequiredChecksTests(unittest.TestCase):
    def test_accepts_graphql_contexts_and_case_insensitive_states(self) -> None:
        rollup = {
            "contexts": {
                "nodes": [
                    None,
                    {"context": "legacy/build", "state": "success"},
                    {"name": "test", "status": "completed", "conclusion": "success"},
                    {"name": "CodeScene delta", "conclusion": "FAILURE"},
                ]
            }
        }
        self.assertTrue(guardrails.required_checks_green(rollup, ["CodeScene*"]))

    def test_all_supported_success_conclusions(self) -> None:
        for conclusion in ("SUCCESS", "SKIPPED", "NEUTRAL", "PASSED"):
            with self.subTest(conclusion=conclusion):
                self.assertTrue(
                    guardrails.required_checks_green(
                        [{"name": "build", "conclusion": conclusion}], []
                    )
                )

    def test_required_failures_pending_and_unknown_are_not_green(self) -> None:
        for conclusion in (
            "FAILURE",
            "TIMED_OUT",
            "CANCELLED",
            "ACTION_REQUIRED",
            "STARTUP_FAILURE",
            "ERROR",
            "PENDING",
            "EXPECTED",
            "",
            "UNRECOGNIZED",
        ):
            with self.subTest(conclusion=conclusion):
                self.assertFalse(
                    guardrails.required_checks_green(
                        [{"context": "build", "state": conclusion}], []
                    )
                )
        for status in ("QUEUED", "IN_PROGRESS", "WAITING"):
            with self.subTest(status=status):
                self.assertFalse(
                    guardrails.required_checks_green(
                        [{"name": "build", "status": status, "conclusion": "SUCCESS"}],
                        [],
                    )
                )

    def test_missing_or_malformed_rollups_are_unknown(self) -> None:
        for rollup in (
            None,
            [],
            {},
            "SUCCESS",
            [None, "bad"],
            {"contexts": {}},
            {"contexts": {"nodes": None}},
        ):
            with self.subTest(rollup=rollup):
                self.assertIsNone(guardrails.required_checks_green(rollup, []))

    def test_advisory_names_match_exactly_or_by_trailing_star(self) -> None:
        for name, expected in (
            ("review", True),
            ("CodeScene delta", True),
            ("review-build", False),
            ("Review", False),
            ("prefix CodeScene delta", False),
        ):
            with self.subTest(name=name):
                self.assertEqual(
                    expected,
                    guardrails.required_checks_green(
                        [{"name": name, "status": "IN_PROGRESS"}],
                        ["", "review", "CodeScene*"],
                    ),
                )


class FetchEvidenceTests(unittest.TestCase):
    def test_success_reads_only_view_and_diff_and_normalizes_evidence(self) -> None:
        payload = {
            "title": "Bump lib from 1.2.3 to 1.2.4",
            "headRefName": "dependabot/lib",
            "mergeable": "MERGEABLE",
            "statusCheckRollup": [
                {"name": "build", "conclusion": "SUCCESS"},
                {"name": "review", "conclusion": "FAILURE"},
            ],
        }
        view = subprocess.CompletedProcess([], 0, stdout=json.dumps(payload))
        diff = subprocess.CompletedProcess([], 0, stdout="a synthetic diff")
        with mock.patch.object(
            guardrails.subprocess, "run", side_effect=[view, diff]
        ) as run:
            evidence = guardrails.fetch_guardrail_evidence(_item(), ["review"])
        self.assertEqual(
            guardrails.GuardrailEvidence(
                diff_text=diff.stdout,
                required_checks_green=True,
                mergeable=True,
                title=payload["title"],
                head_ref=payload["headRefName"],
            ),
            evidence,
        )
        self.assertEqual(
            [
                mock.call(
                    [
                        "gh",
                        "pr",
                        "view",
                        "1",
                        "--repo",
                        "owner/repo",
                        "--json",
                        "title,mergeable,statusCheckRollup,headRefName",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=60,
                ),
                mock.call(
                    ["gh", "pr", "diff", "1", "--repo", "owner/repo"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=60,
                ),
            ],
            run.call_args_list,
        )

    def test_metadata_only_fetch_avoids_diff_and_requires_explicit_mergeability(
        self,
    ) -> None:
        for mergeable in ("CONFLICTING", "UNKNOWN", None):
            with self.subTest(mergeable=mergeable):
                view = subprocess.CompletedProcess(
                    [], 0, stdout=json.dumps({"mergeable": mergeable})
                )
                with mock.patch.object(
                    guardrails.subprocess, "run", return_value=view
                ) as run:
                    evidence = guardrails.fetch_guardrail_evidence(
                        _item(), [], include_diff=False
                    )
                self.assertEqual(1, run.call_count)
                self.assertFalse(evidence.diff_fetch_failed)
                self.assertFalse(evidence.mergeable)
                self.assertIsNone(evidence.required_checks_green)
                self.assertEqual("", evidence.diff_text)
                self.assertEqual("", evidence.title)
                self.assertEqual("", evidence.head_ref)

    def test_invalid_item_identity_never_calls_github(self) -> None:
        for overrides in (
            {"repository": ""},
            {"repository": None},
            {"pr": "1"},
            {"pr": None},
        ):
            with self.subTest(overrides=overrides):
                with mock.patch.object(guardrails.subprocess, "run") as run:
                    evidence = guardrails.fetch_guardrail_evidence(
                        _item(**overrides), []
                    )
                self.assertEqual(
                    guardrails.GuardrailEvidence(diff_fetch_failed=True), evidence
                )
                run.assert_not_called()

    def test_failed_view_or_diff_fails_closed(self) -> None:
        success = subprocess.CompletedProcess([], 0, stdout="{}")
        for failure in (
            subprocess.CompletedProcess([], 1, stdout=""),
            OSError("gh unavailable"),
            subprocess.TimeoutExpired(["gh"], 60),
        ):
            for stage in ("view", "diff"):
                with self.subTest(failure=type(failure).__name__, stage=stage):
                    responses = [failure] if stage == "view" else [success, failure]
                    with mock.patch.object(
                        guardrails.subprocess, "run", side_effect=responses
                    ) as run:
                        evidence = guardrails.fetch_guardrail_evidence(_item(), [])
                    self.assertEqual(
                        guardrails.GuardrailEvidence(diff_fetch_failed=True), evidence
                    )
                    self.assertEqual(1 if stage == "view" else 2, run.call_count)

    def test_invalid_view_json_fails_closed(self) -> None:
        for text in ("not json", "[]", "null", '"not a mapping"'):
            with self.subTest(text=text):
                view = subprocess.CompletedProcess([], 0, stdout=text)
                with mock.patch.object(guardrails.subprocess, "run", return_value=view):
                    evidence = guardrails.fetch_guardrail_evidence(
                        _item(), [], include_diff=False
                    )
                self.assertTrue(evidence.diff_fetch_failed)


class EvidenceDecisionTests(unittest.TestCase):
    def test_live_evidence_is_only_needed_for_clearable_or_dependabot_lanes(
        self,
    ) -> None:
        cases = (
            ({}, False),
            ({"classification": "SECURITY"}, True),
            ({"guardrail_outcome": "REVIEW_SECURITY"}, True),
            ({"guardrail_outcome": "HOLD_CONTRACT"}, True),
            ({"guardrail_outcome": "HOLD_EVIDENCE"}, True),
            ({"classification": "SECURITY", "changed_paths": ["src/task.sh"]}, False),
            ({"classification": "SECURITY", "changed_paths": []}, False),
            ({"changed_paths": ".github/workflows/ci.yml"}, False),
            (
                {"author": {"login": "dependabot[bot]"}, "changed_paths": ["uv.lock"]},
                True,
            ),
            (
                {
                    "author": {"login": "dependabot[bot]"},
                    "changed_paths": [".github/workflows/ci.yaml"],
                },
                True,
            ),
        )
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                self.assertEqual(
                    expected, guardrails.needs_live_evidence(_item(**overrides))
                )

    def test_failed_fetch_preserves_prior_sorted_evidence_without_mutating_item(
        self,
    ) -> None:
        item = _item(
            guardrail_outcome="REVIEW_SECURITY",
            changed_paths=["src/main.py"],
            sensitive_paths=["shell_execution", "secrets", "shell_execution"],
        )
        before = copy.deepcopy(item)
        patch = guardrails.evaluate_item(
            item, evidence=guardrails.GuardrailEvidence(diff_fetch_failed=True)
        )
        self.assertEqual(
            {
                "guardrail_outcome": "REVIEW_SECURITY",
                "guardrail_source": "path_eval",
                "risk_class": "SENSITIVE",
                "sensitive_paths": ["secrets", "shell_execution"],
            },
            patch,
        )
        self.assertEqual(before, item)

    def test_contract_and_evidence_holds_clear_only_with_clean_evidence(self) -> None:
        for outcome in ("HOLD_CONTRACT", "HOLD_EVIDENCE"):
            item = _item(guardrail_outcome=outcome, changed_paths=["src/main.py"])
            for evidence in (
                guardrails.GuardrailEvidence(diff_fetch_failed=True),
                guardrails.GuardrailEvidence(
                    diff_text="+++ b/src/main.py\n+eval(value)\n"
                ),
            ):
                with self.subTest(outcome=outcome, evidence=evidence):
                    self.assertIsNone(guardrails.evaluate_item(item, evidence=evidence))
            with self.subTest(outcome=outcome, clean=True):
                patch = guardrails.evaluate_item(
                    item, evidence=guardrails.GuardrailEvidence(diff_text="")
                )
                self.assertIsNotNone(patch)
                self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])


if __name__ == "__main__":
    unittest.main()
