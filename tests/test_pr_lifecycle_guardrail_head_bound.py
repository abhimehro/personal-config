"""Head-bound evidence requirements for routine lifecycle guardrail decisions."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_guardrails as guardrails
from pr_lifecycle_schema import validate_schema
from pr_lifecycle_yaml import load_yaml

from tests.pr_lifecycle_helpers import (
    guardrail_item,
    load_reconcile_with_stubs,
)

HEAD_SHA = "a" * 40
BASE_SHA = "b" * 40
OTHER_SHA = "c" * 40
BENIGN_DIFF = (
    "diff --git a/src/worker.py b/src/worker.py\n"
    "--- a/src/worker.py\n"
    "+++ b/src/worker.py\n"
    "@@\n"
    "+print('ready')\n"
)


def _evidence(diff_text: str = BENIGN_DIFF, **overrides: object):
    values = {
        "diff_text": diff_text,
        "head_sha": HEAD_SHA,
        "diff_sha256": hashlib.sha256(diff_text.encode("utf-8")).hexdigest(),
    }
    values.update(overrides)
    return guardrails.GuardrailEvidence(**values)


class HeadBoundDecisionTests(unittest.TestCase):
    def test_git_config_path_without_diff_cannot_receive_routine_patch(self) -> None:
        item = guardrail_item(changed_paths=["configs/.gitconfig"])

        self.assertTrue(guardrails.needs_live_evidence(item))
        self.assertIsNone(guardrails.evaluate_item(item))

    def test_not_run_executable_requires_live_evidence(self) -> None:
        item = guardrail_item(changed_paths=["src/worker.py"])
        before = copy.deepcopy(item)
        self.assertTrue(guardrails.needs_live_evidence(item))
        self.assertIsNone(guardrails.evaluate_item(item))
        self.assertEqual(before, item)

    def test_terminal_executable_item_does_not_need_live_evidence(self) -> None:
        item = guardrail_item(
            lifecycle_state="TERMINAL",
            changed_paths=["src/worker.py"],
        )

        self.assertFalse(guardrails.needs_live_evidence(item))

    def test_currently_stamped_routine_item_does_not_need_live_evidence(self) -> None:
        item = guardrail_item(
            changed_paths=["src/worker.py"],
            guardrail_outcome="PASS_ROUTINE",
            guardrail_evidence={
                "head_sha": HEAD_SHA,
                "basis": "head_bound_diff",
                "diff_sha256": hashlib.sha256(BENIGN_DIFF.encode("utf-8")).hexdigest(),
            },
        )

        self.assertFalse(guardrails.needs_live_evidence(item))

    def test_human_owned_nonroutine_item_does_not_need_live_evidence(self) -> None:
        item = guardrail_item(
            changed_paths=["src/worker.py"],
            current_owner="human",
            guardrail_outcome="NOT_RUN",
        )

        self.assertFalse(guardrails.needs_live_evidence(item))

    def test_owner_held_stamp_candidate_needs_live_evidence(self) -> None:
        item = guardrail_item(
            changed_paths=["src/worker.py"],
            current_owner="stage3",
            guardrail_outcome="PASS_ROUTINE",
        )

        self.assertTrue(guardrails.needs_live_evidence(item))

    def test_benign_matching_head_diff_stamps_routine_decision(self) -> None:
        item = guardrail_item(changed_paths=["src/worker.py"])
        patch = guardrails.evaluate_item(item, evidence=_evidence())
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])
        self.assertEqual(
            {
                "head_sha": HEAD_SHA,
                "basis": "head_bound_diff",
                "diff_sha256": hashlib.sha256(BENIGN_DIFF.encode("utf-8")).hexdigest(),
            },
            patch["guardrail_evidence"],
        )

    def test_matching_head_security_diff_stays_held_without_stamp(self) -> None:
        diff_text = (
            "diff --git a/src/worker.py b/src/worker.py\n"
            "+++ b/src/worker.py\n"
            "@@\n"
            "+subprocess.run(user_input, shell=True)\n"
        )
        patch = guardrails.evaluate_item(
            guardrail_item(changed_paths=["src/worker.py"]),
            evidence=_evidence(diff_text),
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("REVIEW_SECURITY", patch["guardrail_outcome"])
        self.assertIsNone(patch["guardrail_evidence"])

    def test_mismatched_failed_and_blank_evidence_fail_closed(self) -> None:
        for evidence in (
            _evidence(head_sha=OTHER_SHA),
            guardrails.GuardrailEvidence(
                diff_text=BENIGN_DIFF,
                head_sha=HEAD_SHA,
                diff_fetch_failed=True,
            ),
            _evidence(""),
        ):
            with self.subTest(evidence=evidence):
                item = guardrail_item(changed_paths=["src/worker.py"])
                before = copy.deepcopy(item)
                self.assertIsNone(guardrails.evaluate_item(item, evidence=evidence))
                self.assertEqual(before, item)

    def test_non_executable_paths_receive_non_executable_stamp(self) -> None:
        patch = guardrails.evaluate_item(
            guardrail_item(changed_paths=["README.md", "docs/plan.txt"])
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])
        self.assertEqual(
            {
                "head_sha": HEAD_SHA,
                "basis": "non_executable_paths",
                "diff_sha256": None,
            },
            patch["guardrail_evidence"],
        )

    def test_mixed_non_executable_and_javascript_requires_evidence(self) -> None:
        item = guardrail_item(changed_paths=["README.md", "app.js"])
        self.assertTrue(guardrails.needs_live_evidence(item))
        self.assertIsNone(guardrails.evaluate_item(item))

    def test_shell_and_typescript_suffixes_are_executable(self) -> None:
        self.assertTrue(guardrails.is_executable_path("scripts/run.sh"))
        shell_patch = guardrails.evaluate_item(
            guardrail_item(changed_paths=["scripts/run.sh"])
        )
        self.assertIsNotNone(shell_patch)
        assert shell_patch is not None
        self.assertEqual("REVIEW_SECURITY", shell_patch["guardrail_outcome"])
        self.assertTrue(guardrails.is_executable_path("src/app.ts"))
        self.assertIsNone(
            guardrails.evaluate_item(guardrail_item(changed_paths=["src/app.ts"]))
        )

    def test_routine_stamp_is_rechecked_only_when_absent_or_stale(self) -> None:
        unstamped = guardrail_item(
            changed_paths=["src/worker.py"], guardrail_outcome="PASS_ROUTINE"
        )
        self.assertTrue(guardrails._evaluable(unstamped))
        patch = guardrails.evaluate_item(unstamped, evidence=_evidence())
        self.assertIsNotNone(patch)
        assert patch is not None
        unstamped.update(patch)
        self.assertFalse(guardrails._evaluable(unstamped))
        self.assertIsNone(guardrails.evaluate_item(unstamped, evidence=_evidence()))

        stale = guardrail_item(
            changed_paths=["src/worker.py"],
            guardrail_outcome="PASS_ROUTINE",
            guardrail_evidence={
                "head_sha": OTHER_SHA,
                "basis": "head_bound_diff",
                "diff_sha256": None,
            },
        )
        self.assertTrue(guardrails._evaluable(stale))
        self.assertIsNotNone(guardrails.evaluate_item(stale, evidence=_evidence()))

    def test_owner_held_routine_items_get_stamp_only_patches(self) -> None:
        cases = (
            {"current_owner": "stage3", "guardrail_source": "path_eval"},
            {"current_owner": "stage1", "guardrail_source": "manual"},
        )
        stamp = {
            "head_sha": HEAD_SHA,
            "basis": "head_bound_diff",
            "diff_sha256": hashlib.sha256(BENIGN_DIFF.encode("utf-8")).hexdigest(),
        }
        for overrides in cases:
            with self.subTest(overrides=overrides):
                item = guardrail_item(
                    changed_paths=["src/worker.py"],
                    guardrail_outcome="PASS_ROUTINE",
                    **overrides,
                )
                self.assertFalse(guardrails._evaluable(item))
                self.assertTrue(guardrails.needs_live_evidence(item))
                self.assertEqual(
                    {"guardrail_evidence": stamp},
                    guardrails.evaluate_item(item, evidence=_evidence()),
                )

    def test_owner_held_routine_stays_unstamped_for_security_diff(self) -> None:
        shell_diff = (
            "diff --git a/src/worker.py b/src/worker.py\n"
            "--- a/src/worker.py\n"
            "+++ b/src/worker.py\n"
            "@@\n"
            "+subprocess.run(user_input, shell=True)\n"
        )
        cases = (
            {"current_owner": "stage3", "guardrail_source": "path_eval"},
            {"current_owner": "stage1", "guardrail_source": "manual"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                item = guardrail_item(
                    changed_paths=["src/worker.py"],
                    guardrail_outcome="PASS_ROUTINE",
                    **overrides,
                )
                self.assertIsNone(
                    guardrails.evaluate_item(item, evidence=_evidence(shell_diff))
                )

    def test_human_review_routine_item_never_gets_stamp_only_patch(self) -> None:
        item = guardrail_item(
            changed_paths=["src/worker.py"],
            guardrail_outcome="PASS_ROUTINE",
            current_owner="stage3",
            risk_class="HUMAN_REVIEW",
        )
        self.assertIsNone(guardrails.evaluate_item(item, evidence=_evidence()))

    def test_unstamped_routine_summary_lists_unstamped_owner_item(self) -> None:
        key = "abhimehro/personal-config#123@" + HEAD_SHA
        item = guardrail_item(
            key=key,
            changed_paths=["src/worker.py"],
            guardrail_outcome="PASS_ROUTINE",
            current_owner="stage3",
        )
        ledger = {"items": [item], "events": [], "ledger_revision": 0}
        _, summary = guardrails.evaluate_ledger(
            ledger, None, evidence_for=lambda _item: None
        )
        self.assertEqual([key], summary["unstamped_routine"])

    def test_invalid_item_head_and_unstamped_routine_without_diff_stay_unchanged(
        self,
    ) -> None:
        for item in (
            guardrail_item(changed_paths=["src/worker.py"], head_sha="invalid"),
            guardrail_item(
                changed_paths=["src/worker.py"], guardrail_outcome="PASS_ROUTINE"
            ),
        ):
            before = copy.deepcopy(item)
            self.assertIsNone(guardrails.evaluate_item(item))
            self.assertEqual(before, item)

    def test_evaluate_ledger_counts_non_null_evidence_stamps(self) -> None:
        item = guardrail_item(changed_paths=["src/worker.py"])
        ledger = {"items": [item], "events": [], "ledger_revision": 0}
        _, summary = guardrails.evaluate_ledger(
            ledger, None, evidence_for=lambda _item: _evidence()
        )
        self.assertEqual(1, summary["evidence_stamped"])
        self.assertEqual([], summary["unstamped_routine"])
        self.assertEqual(HEAD_SHA, item["guardrail_evidence"]["head_sha"])

    def test_title_security_clear_invalidates_prior_stamp(self) -> None:
        reconcile = load_reconcile_with_stubs()
        item = {
            "classification": "SECURITY",
            "guardrail_outcome": "REVIEW_SECURITY",
            "guardrail_evidence": {
                "head_sha": HEAD_SHA,
                "basis": "head_bound_diff",
                "diff_sha256": "d" * 64,
            },
        }
        reconcile._reclassify_title_security_item(
            {"ledger_revision": 0},
            item,
            {
                "to_classification": "REFACTOR",
                "sensitive_paths": [],
                "clear_review_security": True,
            },
        )
        self.assertEqual("PASS_ROUTINE", item["guardrail_outcome"])
        self.assertIsNone(item["guardrail_evidence"])


class FetchHeadBoundEvidenceTests(unittest.TestCase):
    def test_head_mismatch_fails_without_compare_request(self) -> None:
        view = subprocess.CompletedProcess(
            [], 0, stdout=json.dumps({"headRefOid": OTHER_SHA})
        )
        with mock.patch.object(guardrails, "_gh_capture", return_value=view) as capture:
            evidence = guardrails.fetch_guardrail_evidence(guardrail_item(), [])
        self.assertTrue(evidence.diff_fetch_failed)
        capture.assert_called_once()
        self.assertIn("headRefOid", capture.call_args.args[0][-1])

    def test_invalid_item_shas_fail_without_github_calls(self) -> None:
        for overrides in (
            {"head_sha": "invalid"},
            {"base_sha": "invalid"},
        ):
            with self.subTest(overrides=overrides):
                with mock.patch.object(guardrails, "_gh_capture") as capture:
                    evidence = guardrails.fetch_guardrail_evidence(
                        guardrail_item(**overrides), []
                    )
                self.assertTrue(evidence.diff_fetch_failed)
                capture.assert_not_called()

    def test_compare_request_uses_item_shas_and_records_digest(self) -> None:
        view_payload = {
            "headRefOid": HEAD_SHA,
            "title": "Routine change",
            "headRefName": "feature",
            "mergeable": "MERGEABLE",
            "statusCheckRollup": [],
        }
        diff_text = "diff --git a/src/worker.py b/src/worker.py\n+print('ok')\n"
        responses = [
            subprocess.CompletedProcess([], 0, stdout=json.dumps(view_payload)),
            subprocess.CompletedProcess([], 0, stdout=diff_text),
        ]
        with mock.patch.object(
            guardrails, "_gh_capture", side_effect=responses
        ) as capture:
            evidence = guardrails.fetch_guardrail_evidence(guardrail_item(), [])
        self.assertFalse(evidence.diff_fetch_failed)
        self.assertEqual(HEAD_SHA, evidence.head_sha)
        self.assertEqual(
            hashlib.sha256(diff_text.encode("utf-8")).hexdigest(),
            evidence.diff_sha256,
        )
        self.assertEqual(
            [
                "gh",
                "api",
                "-H",
                "Accept: application/vnd.github.diff",
                f"repos/owner/repo/compare/{BASE_SHA}...{HEAD_SHA}",
            ],
            capture.call_args_list[1].args[0],
        )

    def test_blank_compare_response_fails_closed(self) -> None:
        view = subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps({"headRefOid": HEAD_SHA}),
        )
        blank = subprocess.CompletedProcess([], 0, stdout=" \n")
        with mock.patch.object(guardrails, "_gh_capture", side_effect=[view, blank]):
            evidence = guardrails.fetch_guardrail_evidence(guardrail_item(), [])
        self.assertTrue(evidence.diff_fetch_failed)


class GuardrailEvidenceSchemaTests(unittest.TestCase):
    def test_valid_stamp_is_allowed_and_bad_basis_is_rejected(self) -> None:
        ledger = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")
        item = ledger["items"][0]
        item["guardrail_evidence"] = {
            "head_sha": HEAD_SHA,
            "basis": "head_bound_diff",
            "diff_sha256": "d" * 64,
        }
        validate_schema(ledger)
        for updates, expected_error in (
            ({"basis": "path_only"}, "basis"),
            ({"head_sha": "bad"}, "head_sha"),
            ({"diff_sha256": "bad"}, "diff_sha256"),
            ({"extra": "not allowed"}, r"(?i)additional properties"),
        ):
            with self.subTest(updates=updates):
                item["guardrail_evidence"].update(updates)
                with self.assertRaisesRegex(ValueError, expected_error):
                    validate_schema(ledger)
                item["guardrail_evidence"] = {
                    "head_sha": HEAD_SHA,
                    "basis": "head_bound_diff",
                    "diff_sha256": "d" * 64,
                }


if __name__ == "__main__":
    unittest.main()
