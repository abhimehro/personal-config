"""Regression tests for PR Recap prefix filtering and missing Linear issues."""

from __future__ import annotations

import dataclasses
import sys
import unittest
from pathlib import Path
from unittest.mock import call, create_autospec, patch

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pr_recap  # noqa: E402


def make_issue(identifier: str = "ABHI-12") -> pr_recap.LinearIssue:
    return pr_recap.LinearIssue(
        id=f"id-{identifier}",
        identifier=identifier,
        title="Synthetic issue",
        state=pr_recap.LinearState(
            id=pr_recap.CANONICAL_STATES["todo"], name="Todo", type="unstarted"
        ),
        comments=(),
        attachments=(),
    )


class TestIssuePrefixFiltering(unittest.TestCase):
    def test_team_prefix_length_boundaries(self) -> None:
        for team_id, expected in (
            ("a", ()),
            ("aB", ("AB",)),
            ("aBcDeFgHiJ", ("ABCDEFGHIJ",)),
            ("ABCDEFGHIJK", ()),
        ):
            with self.subTest(team_id=team_id):
                config = pr_recap.Config.from_dict({"teamId": team_id})
                self.assertEqual(config.issue_key_prefixes, expected)

    def test_non_ascii_or_non_letter_team_ids_disable_filtering(self) -> None:
        for team_id in (
            "AB2",
            "AB_HI",
            "AB-HI",
            "AB HI",
            "ÄB",
            "ＡＢ",
            "AB\nHI",
            "550e8400-e29b-41d4-a716-446655440000",
        ):
            with self.subTest(team_id=team_id):
                config = pr_recap.Config.from_dict({"teamId": team_id})
                self.assertEqual(config.issue_key_prefixes, ())

    def test_config_trims_team_id_before_deriving_prefix(self) -> None:
        config = pr_recap.Config.from_dict({"teamId": " \tabHi\n"})
        self.assertEqual(config.issue_key_prefixes, ("ABHI",))

    def test_multiple_prefixes_preserve_relationships_without_mutating_input(
        self,
    ) -> None:
        issue_map = {
            "ABHI-1": "closes",
            "OPS-2": "contributes",
            "OPS-3": "links",
            "CWE-88": "links",
            "ABHIX-4": "closes",
            "AB-5": "links",
        }
        original = issue_map.copy()
        self.assertEqual(
            pr_recap.filter_issue_keys(issue_map, ("ABHI", "OPS")),
            {"ABHI-1": "closes", "OPS-2": "contributes", "OPS-3": "links"},
        )
        self.assertEqual(issue_map, original)

    def test_explicit_keep_applies_only_to_exact_existing_keys(self) -> None:
        self.assertEqual(
            pr_recap.filter_issue_keys(
                {"OPS-1": "closes", "OPS-10": "links", "CWE-88": "links"},
                ("ABHI",),
                keep=frozenset({"OPS-1", "MISSING-2"}),
            ),
            {"OPS-1": "closes"},
        )

    def test_empty_and_completely_rejected_maps(self) -> None:
        for issue_map in ({}, {"CWE-88": "links", "CVE-2024": "links"}):
            with self.subTest(issue_map=issue_map):
                self.assertEqual(pr_recap.filter_issue_keys(issue_map, ("ABHI",)), {})

    def test_only_rejected_keys_are_logged(self) -> None:
        with self.assertLogs("pr_recap", level="INFO") as logs:
            pr_recap.filter_issue_keys(
                {"ABHI-1": "links", "OPS-2": "closes", "CWE-88": "links"},
                ("ABHI",),
                keep=frozenset({"OPS-2"}),
            )
        self.assertEqual(len(logs.records), 1)
        self.assertIn("CWE-88", logs.records[0].getMessage())
        self.assertEqual(logs.records[0].levelname, "INFO")

    def test_explicit_keys_ignore_blanks_and_deduplicate_relationship_variants(
        self,
    ) -> None:
        self.assertEqual(
            pr_recap._explicit_issue_keys(
                ("", " \t\n", " ops-1 : closes ", "OPS-1:contributes", " abhi-2 ")
            ),
            frozenset({"OPS-1", "ABHI-2"}),
        )
        self.assertEqual(pr_recap._explicit_issue_keys(()), frozenset())


class TestFetchIssueOrNone(unittest.TestCase):
    def test_success_returns_original_issue_in_both_modes(self) -> None:
        issue = make_issue()
        for dry_run in (False, True):
            with self.subTest(dry_run=dry_run):
                client = create_autospec(pr_recap.LinearClient, instance=True)
                client.get_issue.return_value = issue
                self.assertIs(
                    pr_recap._fetch_issue_or_none(client, "ABHI-12", dry_run), issue
                )
                self.assertEqual(client.method_calls, [call.get_issue("ABHI-12")])

    def test_missing_issue_error_is_case_insensitive_in_both_modes(self) -> None:
        for dry_run in (False, True):
            for message in (
                "ENTITY NOT FOUND: Issue",
                "GraphQL: eNtItY nOt FoUnD: Issue",
            ):
                with self.subTest(dry_run=dry_run, message=message):
                    client = create_autospec(pr_recap.LinearClient, instance=True)
                    client.get_issue.side_effect = pr_recap.LinearApiError(message)
                    self.assertIsNone(
                        pr_recap._fetch_issue_or_none(client, "ABHI-12", dry_run)
                    )
                    self.assertEqual(client.method_calls, [call.get_issue("ABHI-12")])

    def test_other_api_errors_propagate_unchanged_in_both_modes(self) -> None:
        for dry_run in (False, True):
            for message in (
                "HTTP 401: Unauthorized",
                "HTTP 429: Rate limited",
                "HTTP 500",
                "Issue not found",
            ):
                with self.subTest(dry_run=dry_run, message=message):
                    client = create_autospec(pr_recap.LinearClient, instance=True)
                    error = pr_recap.LinearApiError(message)
                    client.get_issue.side_effect = error
                    with self.assertRaises(pr_recap.LinearApiError) as raised:
                        pr_recap._fetch_issue_or_none(client, "ABHI-12", dry_run)
                    self.assertIs(raised.exception, error)

    def test_non_api_error_is_not_swallowed_even_with_matching_message(self) -> None:
        client = create_autospec(pr_recap.LinearClient, instance=True)
        error = RuntimeError("Entity not found")
        client.get_issue.side_effect = error
        for dry_run in (False, True):
            with self.subTest(dry_run=dry_run):
                with self.assertRaises(RuntimeError) as raised:
                    pr_recap._fetch_issue_or_none(client, "ABHI-12", dry_run)
                self.assertIs(raised.exception, error)


class TestIssueFilteringSync(unittest.TestCase):
    """Exercise orchestration with all external dependencies replaced by mocks."""

    def setUp(self) -> None:
        self.config = pr_recap.Config.from_dict({"teamId": "ABHI"})
        self.context = pr_recap.PRContext(
            event_name="pull_request",
            action="closed",
            pr_number=123,
            pr_title="",
            pr_body="",
            pr_url="https://github.com/org/repo/pull/123",
            branch_name="main",
            head_sha="abcdef123456",
            is_draft=False,
            is_merged=True,
            is_closed=True,
            commit_messages=(),
        )
        self.client = create_autospec(pr_recap.LinearClient, instance=True)
        self.client.get_issue.return_value = None
        self.client.find_issue_by_attachment_url.return_value = None
        self.client.upsert_recap_comment.return_value = ("comment-id", True)
        self.client.update_issue_state.return_value = True
        self.client.ensure_diff_link.return_value = True
        self.args = pr_recap.build_parser().parse_args(["sync"])

    def run_sync(self) -> int:
        with (
            patch("pr_recap.load_config", return_value=self.config),
            patch("pr_recap.resolve_pr_context", return_value=self.context),
            patch("pr_recap.resolve_linear_api_key", return_value=("test-key", "test")),
            patch("pr_recap.LinearClient", return_value=self.client),
            patch("pr_recap.GitNexusAnalyzer", autospec=True) as analyzer,
        ):
            analyzer.return_value.analyze.return_value = pr_recap.GitNexusAnalysis(
                available=False, degraded_reason="Synthetic unavailable analyzer"
            )
            return pr_recap.run_sync(self.args)

    def test_filter_applies_to_branch_title_body_and_commit_keys(self) -> None:
        self.context = dataclasses.replace(
            self.context,
            branch_name="fix/OPS-1-security",
            pr_title="Fixes CWE-88",
            pr_body="Relates to CVE-2024",
            commit_messages=("Closes abhi-12",),
        )
        self.assertEqual(self.run_sync(), 0)
        self.assertEqual(self.client.method_calls, [call.get_issue("ABHI-12")])

    def test_non_prefix_config_preserves_unrestricted_sync(self) -> None:
        self.config = pr_recap.Config.from_dict({"teamId": "personal-config"})
        self.context = dataclasses.replace(
            self.context, commit_messages=("CWE-88 and ABHI-12",)
        )
        self.assertEqual(self.run_sync(), 0)
        self.assertCountEqual(
            self.client.method_calls,
            [call.get_issue("CWE-88"), call.get_issue("ABHI-12")],
        )

    def test_explicit_override_preserves_closes_relationship_and_is_deduplicated(
        self,
    ) -> None:
        issue = make_issue("OPS-1")
        self.client.get_issue.return_value = issue
        self.args.issue = [" ops-1 : closes ", "OPS-1:links", " \t"]
        self.context = dataclasses.replace(
            self.context, commit_messages=("OPS-1 and OPS-2 and CWE-88",)
        )
        self.assertEqual(self.run_sync(), 0)
        self.client.get_issue.assert_called_once_with("OPS-1")
        self.client.update_issue_state.assert_called_once_with(
            issue.id, self.config.state_map["done"]
        )
        self.client.find_issue_by_attachment_url.assert_not_called()

    def test_filtered_keys_allow_mirrored_pr_resolution(self) -> None:
        issue = make_issue()
        self.context = dataclasses.replace(self.context, pr_title="Fix CWE-88")
        self.client.find_issue_by_attachment_url.return_value = issue
        self.client.get_issue.return_value = issue
        self.assertEqual(self.run_sync(), 0)
        self.client.find_issue_by_attachment_url.assert_called_once_with("pull/123")
        self.client.get_issue.assert_called_once_with(issue.identifier)
        self.client.upsert_recap_comment.assert_called_once()
        self.client.update_issue_state.assert_not_called()

    def test_filtered_keys_allow_mirrored_github_issue_relationship(self) -> None:
        issue = make_issue()
        self.context = dataclasses.replace(
            self.context, commit_messages=("Fix CWE-88; closes #42",)
        )
        self.client.find_issue_by_attachment_url.side_effect = [None, issue]
        self.client.get_issue.return_value = issue
        self.assertEqual(self.run_sync(), 0)
        self.assertEqual(
            self.client.find_issue_by_attachment_url.call_args_list,
            [call("pull/123"), call("issues/42")],
        )
        self.client.get_issue.assert_called_once_with(issue.identifier)
        self.client.update_issue_state.assert_called_once_with(
            issue.id, self.config.state_map["done"]
        )

    def test_missing_issue_warns_and_processing_continues_with_valid_issue(
        self,
    ) -> None:
        issue = make_issue("ABHI-13")
        self.context = dataclasses.replace(
            self.context, commit_messages=("Closes ABHI-12 and closes ABHI-13",)
        )
        for missing in (None, pr_recap.LinearApiError("Entity not found: Issue")):
            with self.subTest(missing=missing):
                self.client.reset_mock()
                self.client.get_issue.side_effect = [missing, issue]
                with self.assertLogs("pr_recap", level="WARNING") as logs:
                    self.assertEqual(self.run_sync(), 0)
                self.assertEqual(
                    [record.levelname for record in logs.records], ["WARNING"]
                )
                self.assertIn("ABHI-12", logs.records[0].getMessage())
                self.assertEqual(
                    self.client.get_issue.call_args_list,
                    [call("ABHI-12"), call("ABHI-13")],
                )
                self.client.update_issue_state.assert_called_once_with(
                    issue.id, self.config.state_map["done"]
                )
                self.client.upsert_recap_comment.assert_called_once()
                self.assertEqual(
                    self.client.upsert_recap_comment.call_args.kwargs["issue"], issue
                )
                self.client.ensure_diff_link.assert_called_once_with(
                    issue=issue, diff_url=self.context.diff_url, title="PR #123 Diff"
                )

    def test_dry_run_missing_issue_plans_without_mutations_or_warnings(self) -> None:
        self.args.dry_run = True
        self.args.issue = ["ABHI-12"]
        for missing in (None, pr_recap.LinearApiError("Entity not found: Issue")):
            with self.subTest(missing=missing):
                self.client.reset_mock()
                self.client.get_issue.side_effect = [missing]
                with self.assertLogs("pr_recap", level="INFO") as logs:
                    self.assertEqual(self.run_sync(), 0)
                self.assertTrue(
                    any(
                        "Would plan reconciliation for issue ABHI-12"
                        in record.getMessage()
                        for record in logs.records
                    )
                )
                self.assertTrue(
                    all(record.levelname == "INFO" for record in logs.records)
                )
                self.assertEqual(self.client.method_calls, [call.get_issue("ABHI-12")])

    def test_api_error_still_fails_sync_in_both_modes(self) -> None:
        self.args.issue = ["ABHI-12", "ABHI-13"]
        for dry_run in (False, True):
            with self.subTest(dry_run=dry_run):
                self.args.dry_run = dry_run
                self.client.reset_mock()
                self.client.get_issue.side_effect = [
                    pr_recap.LinearApiError("HTTP 401: Unauthorized"),
                    None,
                ]
                with self.assertLogs("pr_recap", level="ERROR") as logs:
                    self.assertEqual(self.run_sync(), 1)
                self.assertIn("HTTP 401", logs.records[0].getMessage())
                self.assertEqual(
                    self.client.method_calls,
                    [call.get_issue("ABHI-12"), call.get_issue("ABHI-13")],
                )


if __name__ == "__main__":
    unittest.main()
