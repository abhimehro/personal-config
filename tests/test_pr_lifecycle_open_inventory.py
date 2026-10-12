"""Tests for normalized, paginated open-PR inventory."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_open_inventory as inventory

from tests.pr_lifecycle_helpers import (
    make_inventory_payload,
    make_inventory_pr,
)


class OpenInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = types.SimpleNamespace(
            inv=inventory,
            make_pr=make_inventory_pr,
            payload=make_inventory_payload,
        )

    def test_bot_logins_gain_rest_style_suffix(self):
        raw = self.fx.make_pr()
        raw["author"] = {"login": "coderabbitai", "__typename": "Bot"}
        raw["latestReviews"]["nodes"] = [
            {
                "author": {"login": "coderabbitai", "__typename": "Bot"},
                "state": "CHANGES_REQUESTED",
            }
        ]
        raw["comments"]["nodes"] = [
            {
                "author": {"login": "dependabot", "__typename": "Bot"},
                "body": "comment",
                "createdAt": "2026-10-02T00:00:00Z",
            }
        ]
        live = self.fx.inv._normalize_pr(raw, "owner/repo")
        self.assertEqual(live["author"]["login"], "coderabbitai[bot]")
        self.assertEqual(
            live["latestReviews"][0]["author"]["login"], "coderabbitai[bot]"
        )
        self.assertEqual(live["comments"][0]["author"]["login"], "dependabot[bot]")

    def test_normalizes_pr_identity_reviews_comments_commits_and_checks(self):
        """Normalize GraphQL connections and truncate the PR body for classification."""
        live = self.fx.inv._normalize_pr(self.fx.make_pr(), "owner/repo")
        self.assertEqual(live["author"], {"login": "dependabot[bot]", "type": "Bot"})
        self.assertEqual(
            live["commits"], [{"commit": {"author": {"email": "bot@example.com"}}}]
        )
        self.assertEqual(live["latestReviews"][0]["author"]["login"], "reviewer")
        self.assertEqual(live["comments"][0]["body"], "comment")
        self.assertEqual(live["commentsTotalCount"], 1)
        self.assertFalse(live["checksIncomplete"])
        self.assertEqual(len(live["body"]), 2000)
        self.assertEqual(
            live["checks"],
            [
                {"name": "Build", "state": "SUCCESS"},
                {"name": "Lint", "state": "PENDING"},
                {"name": "Legacy", "state": "FAILURE"},
                {"name": "Optional", "state": "PENDING"},
            ],
        )
        self.assertEqual(live["repository"], "owner/repo")
        self.assertTrue(live["isDraft"])

    def test_check_conclusion_and_status_normalization(self):
        """Map check runs and legacy statuses to the expected lifecycle states."""
        cases = (
            (
                {
                    "__typename": "CheckRun",
                    "name": "failed",
                    "conclusion": "TIMED_OUT",
                    "status": "COMPLETED",
                },
                ("failed", "FAILURE"),
            ),
            (
                {
                    "__typename": "CheckRun",
                    "name": "skip",
                    "conclusion": "SKIPPED",
                    "status": "COMPLETED",
                },
                ("skip", "SKIPPED"),
            ),
            (
                {
                    "__typename": "CheckRun",
                    "name": "neutral",
                    "conclusion": "NEUTRAL",
                    "status": "COMPLETED",
                },
                ("neutral", "NEUTRAL"),
            ),
            (
                {"__typename": "StatusContext", "context": "error", "state": "ERROR"},
                ("error", "FAILURE"),
            ),
            (
                {
                    "__typename": "StatusContext",
                    "context": "waiting",
                    "state": "PENDING",
                },
                ("waiting", "PENDING"),
            ),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(self.fx.inv.check_state(raw), expected)

    def test_paginates_open_prs_with_50_per_page_query(self):
        """Follow the next-page cursor while requesting the required PR metadata."""
        commands = []
        responses = [
            subprocess.CompletedProcess(
                ["gh"],
                0,
                json.dumps(self.fx.payload([self.fx.make_pr()], next_page=True)),
                "",
            ),
            subprocess.CompletedProcess(
                ["gh"], 0, json.dumps(self.fx.payload([self.fx.make_pr(13)])), ""
            ),
        ]

        def run(argv, **_kwargs):
            """Record the query arguments and return the next fake inventory page."""
            commands.append(argv)
            return responses.pop(0)

        prs = self.fx.inv.list_open_prs("owner/repo", run=run)
        self.assertEqual([pr["number"] for pr in prs], [12, 13])
        self.assertEqual(len(commands), 2)
        self.assertIn("pullRequests(first: 50, states: OPEN", commands[0][4])
        self.assertIn("comments(last: 50) { totalCount nodes", commands[0][4])
        self.assertIn("pageInfo { hasNextPage }", commands[0][4])
        self.assertIn("cursor=cursor-1", commands[1])

    def test_truncated_or_unknown_check_page_info_marks_checks_incomplete(self) -> None:
        """Mark rollups pending when pagination is truncated or cannot be verified."""
        for page_info in (
            {"hasNextPage": True},
            None,
            {"hasNextPage": "false"},
        ):
            raw = self.fx.make_pr()
            contexts = raw["commits"]["nodes"][0]["commit"]["statusCheckRollup"][
                "contexts"
            ]
            if page_info is None:
                contexts.pop("pageInfo")
            else:
                contexts["pageInfo"] = page_info
            with self.subTest(page_info=page_info):
                live = self.fx.inv._normalize_pr(raw, "owner/repo")
                self.assertTrue(live["checksIncomplete"])
                self.assertEqual(
                    live["checks"][-1],
                    {"name": "statusCheckRollup truncated", "state": "PENDING"},
                )

    def test_missing_or_noninteger_comment_total_is_unknown(self) -> None:
        """Preserve an unknown comment count when the API value is absent or invalid."""
        for count in (None, "120", True, -1):
            raw = self.fx.make_pr()
            if count is None:
                raw["comments"].pop("totalCount")
            else:
                raw["comments"]["totalCount"] = count
            with self.subTest(count=count):
                live = self.fx.inv._normalize_pr(raw, "owner/repo")
                self.assertIsNone(live["commentsTotalCount"])

    def test_nonzero_exit_and_malformed_json_raise_oserror(self):
        """Expose failed commands and invalid JSON as inventory errors."""
        for result in (
            subprocess.CompletedProcess(["gh"], 1, "", "failure"),
            subprocess.CompletedProcess(["gh"], 0, "{bad", ""),
        ):
            with (
                self.subTest(returncode=result.returncode, stdout=result.stdout),
                self.assertRaises(OSError),
            ):
                self.fx.inv.list_open_prs(
                    "owner/repo",
                    run=lambda *_a, _result=result, **_k: _result,
                    sleep=lambda _seconds: None,
                )

    def test_invalid_repository_is_rejected_before_invoking_github(self):
        for repo in (None, "", "owner", "/repo", "owner/", "owner/repo/extra"):
            with self.subTest(repo=repo):
                run = mock.Mock()
                with self.assertRaisesRegex(OSError, "invalid repository"):
                    self.fx.inv.list_open_prs(repo, run=run)
                run.assert_not_called()

    def test_pagination_requires_a_new_nonempty_cursor(self):
        for cursor in (None, "", 42, "cursor-1"):
            with self.subTest(cursor=cursor):
                pages = [
                    self.fx.payload([self.fx.make_pr()], next_page=True),
                    self.fx.payload(
                        [self.fx.make_pr(13)], next_page=True, cursor=cursor
                    ),
                ]
                run = mock.Mock(
                    side_effect=[
                        subprocess.CompletedProcess(["gh"], 0, json.dumps(page), "")
                        for page in pages
                    ]
                )
                sleep = mock.Mock()
                with self.assertRaisesRegex(OSError, "malformed payload"):
                    self.fx.inv.list_open_prs("owner/repo", run=run, sleep=sleep)
                self.assertEqual(run.call_count, 2)
                sleep.assert_not_called()

    def test_later_page_failure_raises_instead_of_returning_partial_inventory(self):
        run = mock.Mock(
            side_effect=[
                subprocess.CompletedProcess(
                    ["gh"],
                    0,
                    json.dumps(self.fx.payload([self.fx.make_pr()], next_page=True)),
                    "",
                ),
                *[subprocess.CompletedProcess(["gh"], 1, "", "unavailable")] * 3,
            ]
        )
        sleep = mock.Mock()
        with self.assertRaisesRegex(OSError, "unavailable"):
            self.fx.inv.list_open_prs("owner/repo", run=run, sleep=sleep)
        self.assertEqual(run.call_count, 4)
        self.assertEqual(sleep.call_args_list, [mock.call(2), mock.call(4)])
        for call in run.call_args_list[1:]:
            self.assertIn("cursor=cursor-1", call.args[0])

    def test_missing_commit_or_rollup_keeps_checks_incomplete(self):
        for commits in ({"nodes": []}, {"nodes": [{"commit": {"author": None}}]}):
            with self.subTest(commits=commits):
                raw = self.fx.make_pr()
                raw["commits"] = commits
                live = self.fx.inv._normalize_pr(raw, "owner/repo")
                self.assertTrue(live["checksIncomplete"])
                self.assertEqual(
                    live["checks"],
                    [{"name": "statusCheckRollup truncated", "state": "PENDING"}],
                )

    def test_invalid_identity_and_connections_are_rejected(self):
        for field, value in (
            ("number", True),
            ("number", 0),
            ("number", "12"),
            ("url", "http://github.com/owner/repo/pull/12"),
            ("isDraft", "false"),
            ("author", {"login": 42}),
            ("body", ["text"]),
            ("latestReviews", {"nodes": [None]}),
            ("comments", {"nodes": {}}),
            ("commits", {"nodes": [None]}),
        ):
            with self.subTest(field=field, value=value):
                raw = self.fx.make_pr()
                raw[field] = value
                with self.assertRaises(OSError):
                    self.fx.inv._normalize_pr(raw, "owner/repo")

    def test_check_failures_take_precedence_over_incomplete_run_status(self):
        """A failed conclusion must not become pending during a status race."""
        for conclusion in (
            "failure",
            "timed_out",
            "cancelled",
            "action_required",
            "startup_failure",
        ):
            for status in ("COMPLETED", "IN_PROGRESS", None):
                with self.subTest(conclusion=conclusion, status=status):
                    self.assertEqual(
                        self.fx.inv.check_state(
                            {
                                "__typename": "CheckRun",
                                "name": "Build",
                                "conclusion": conclusion,
                                "status": status,
                            }
                        ),
                        ("Build", "FAILURE"),
                    )

    def test_nonfailure_checks_require_completion_before_reporting_success(self):
        for conclusion, status, expected in (
            ("success", "completed", "SUCCESS"),
            ("SUCCESS", "QUEUED", "PENDING"),
            ("SKIPPED", "IN_PROGRESS", "PENDING"),
            (None, "COMPLETED", "NEUTRAL"),
            ("UNKNOWN", "COMPLETED", "NEUTRAL"),
        ):
            with self.subTest(conclusion=conclusion, status=status):
                self.assertEqual(
                    self.fx.inv.check_state(
                        {
                            "__typename": "CheckRun",
                            "name": "Build",
                            "conclusion": conclusion,
                            "status": status,
                        }
                    ),
                    ("Build", expected),
                )

    def test_unsupported_or_nameless_checks_are_ignored(self):
        for context in (
            {"__typename": "Unknown", "name": "Build", "state": "FAILURE"},
            {"__typename": "CheckRun", "name": None, "conclusion": "FAILURE"},
            {"__typename": "StatusContext", "context": 42, "state": "ERROR"},
        ):
            with self.subTest(context=context):
                self.assertIsNone(self.fx.inv.check_state(context))

    def test_only_latest_commit_checks_and_author_are_used(self):
        raw = self.fx.make_pr()
        latest = copy.deepcopy(raw["commits"]["nodes"][0])
        latest["commit"]["author"]["email"] = "latest@example.com"
        latest["commit"]["statusCheckRollup"]["contexts"]["nodes"] = []
        raw["commits"]["nodes"].append(latest)
        before = copy.deepcopy(raw)
        live = self.fx.inv._normalize_pr(raw, "owner/repo")
        self.assertEqual(live["checks"], [])
        self.assertFalse(live["checksIncomplete"])
        self.assertEqual(
            live["commits"],
            [{"commit": {"author": {"email": "latest@example.com"}}}],
        )
        self.assertEqual(raw, before)

    def test_deleted_author_remains_unknown_without_losing_other_metadata(self):
        raw = self.fx.make_pr()
        raw["author"] = None
        raw["body"] = None
        live = self.fx.inv._normalize_pr(raw, "owner/repo")
        self.assertEqual(live["author"], {"login": ""})
        self.assertEqual(live["body"], "")
        self.assertEqual(live["number"], 12)
        self.assertEqual(live["headRefOid"], "a" * 40)

    def test_malformed_commit_data_fails_closed(self):
        for commit in (
            None,
            {"author": "not an author"},
            {"author": {}, "statusCheckRollup": []},
            {"author": {}, "statusCheckRollup": {"contexts": {"nodes": [None]}}},
        ):
            with self.subTest(commit=commit):
                raw = self.fx.make_pr()
                raw["commits"] = {"nodes": [{"commit": commit}]}
                with self.assertRaisesRegex(OSError, "malformed"):
                    self.fx.inv._normalize_pr(raw, "owner/repo")

    def test_empty_inventory_is_a_successful_single_request(self):
        run = mock.Mock(
            return_value=subprocess.CompletedProcess(
                ["gh"], 0, json.dumps(self.fx.payload([])), ""
            )
        )
        self.assertEqual(self.fx.inv.list_open_prs("owner/repo", run=run), [])
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
