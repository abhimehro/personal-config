"""Tests for normalized, paginated open-PR inventory."""

from __future__ import annotations

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

import pr_lifecycle_open_inventory as inventory


def _pr(number: int = 12) -> dict:
    """Build a GraphQL PR fixture with reviews, comments, commits, and check states."""
    return {
        "number": number,
        "url": f"https://github.com/owner/repo/pull/{number}",
        "title": "Example",
        "body": "x" * 2200,
        "isDraft": True,
        "headRefName": "bot/update",
        "headRefOid": "a" * 40,
        "baseRefName": "main",
        "baseRefOid": "b" * 40,
        "author": {"login": "dependabot[bot]", "__typename": "Bot"},
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "reviewDecision": "REVIEW_REQUIRED",
        "createdAt": "2026-10-01T00:00:00Z",
        "updatedAt": "2026-10-02T00:00:00Z",
        "latestReviews": {
            "nodes": [{"author": {"login": "reviewer"}, "state": "APPROVED"}]
        },
        "comments": {
            "totalCount": 1,
            "nodes": [
                {
                    "author": {"login": "reviewer"},
                    "body": "comment",
                    "createdAt": "2026-10-02T00:00:00Z",
                }
            ],
        },
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "author": {"email": "bot@example.com"},
                        "statusCheckRollup": {
                            "contexts": {
                                "pageInfo": {"hasNextPage": False},
                                "nodes": [
                                    {
                                        "__typename": "CheckRun",
                                        "name": "Build",
                                        "conclusion": "SUCCESS",
                                        "status": "COMPLETED",
                                    },
                                    {
                                        "__typename": "CheckRun",
                                        "name": "Lint",
                                        "conclusion": None,
                                        "status": "IN_PROGRESS",
                                    },
                                    {
                                        "__typename": "StatusContext",
                                        "context": "Legacy",
                                        "state": "ERROR",
                                    },
                                    {
                                        "__typename": "StatusContext",
                                        "context": "Optional",
                                        "state": "EXPECTED",
                                    },
                                ],
                            }
                        },
                    }
                }
            ]
        },
    }


def _payload(nodes: list[dict], *, next_page: bool = False, cursor: str = "cursor-1"):
    """Wrap PR nodes in a GraphQL page with configurable pagination metadata."""
    return {
        "data": {
            "repository": {
                "pullRequests": {
                    "pageInfo": {
                        "hasNextPage": next_page,
                        "endCursor": cursor if next_page else None,
                    },
                    "nodes": nodes,
                }
            }
        }
    }


class OpenInventoryTests(unittest.TestCase):
    def test_bot_logins_gain_rest_style_suffix(self):
        raw = _pr()
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
        live = inventory._normalize_pr(raw, "owner/repo")
        self.assertEqual(live["author"]["login"], "coderabbitai[bot]")
        self.assertEqual(
            live["latestReviews"][0]["author"]["login"], "coderabbitai[bot]"
        )
        self.assertEqual(live["comments"][0]["author"]["login"], "dependabot[bot]")

    def test_normalizes_pr_identity_reviews_comments_commits_and_checks(self):
        """Normalize GraphQL connections and truncate the PR body for classification."""
        live = inventory._normalize_pr(_pr(), "owner/repo")
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
                self.assertEqual(inventory.check_state(raw), expected)

    def test_paginates_open_prs_with_50_per_page_query(self):
        """Follow the next-page cursor while requesting the required PR metadata."""
        commands = []
        responses = [
            subprocess.CompletedProcess(
                ["gh"], 0, json.dumps(_payload([_pr()], next_page=True)), ""
            ),
            subprocess.CompletedProcess(["gh"], 0, json.dumps(_payload([_pr(13)])), ""),
        ]

        def run(argv, **_kwargs):
            """Record the query arguments and return the next fake inventory page."""
            commands.append(argv)
            return responses.pop(0)

        prs = inventory.list_open_prs("owner/repo", run=run)
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
            raw = _pr()
            contexts = raw["commits"]["nodes"][0]["commit"]["statusCheckRollup"][
                "contexts"
            ]
            if page_info is None:
                contexts.pop("pageInfo")
            else:
                contexts["pageInfo"] = page_info
            with self.subTest(page_info=page_info):
                live = inventory._normalize_pr(raw, "owner/repo")
                self.assertTrue(live["checksIncomplete"])
                self.assertEqual(
                    live["checks"][-1],
                    {"name": "statusCheckRollup truncated", "state": "PENDING"},
                )

    def test_missing_or_noninteger_comment_total_is_unknown(self) -> None:
        """Preserve an unknown comment count when the API value is absent or invalid."""
        for count in (None, "120", True, -1):
            raw = _pr()
            if count is None:
                raw["comments"].pop("totalCount")
            else:
                raw["comments"]["totalCount"] = count
            with self.subTest(count=count):
                live = inventory._normalize_pr(raw, "owner/repo")
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
                inventory.list_open_prs(
                    "owner/repo",
                    run=lambda *_a, _result=result, **_k: _result,
                    sleep=lambda _seconds: None,
                )

    def test_retries_transient_failures_then_succeeds(self):
        """Retry transient process or JSON failures with the configured timeout."""
        valid = subprocess.CompletedProcess(
            ["gh"], 0, json.dumps(_payload([_pr()])), ""
        )
        failures = (
            subprocess.CompletedProcess(["gh"], 1, "", "temporary failure"),
            subprocess.TimeoutExpired(["gh"], 120),
            OSError("temporary process failure"),
            subprocess.CompletedProcess(["gh"], 0, "{bad", ""),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                responses = [failure, valid]
                sleeps = []
                timeouts = []

                def run(
                    _argv,
                    *,
                    _responses=responses,
                    _timeouts=timeouts,
                    **kwargs,
                ):
                    """Record the timeout and replay the next transient failure or response."""
                    _timeouts.append(kwargs["timeout"])
                    response = _responses.pop(0)
                    if isinstance(response, BaseException):
                        raise response
                    return response

                prs = inventory.list_open_prs(
                    "owner/repo", run=run, sleep=sleeps.append
                )
                self.assertEqual([pr["number"] for pr in prs], [12])
                self.assertEqual(sleeps, [2])
                self.assertEqual(timeouts, [120, 120])

    def test_three_transient_failures_raise_oserror(self):
        """Stop after three failed attempts with two backoff delays."""
        failures = [
            subprocess.CompletedProcess(["gh"], 1, "", "temporary failure")
            for _ in range(3)
        ]
        sleeps = []
        with self.assertRaisesRegex(OSError, "rc=1"):
            inventory.list_open_prs(
                "owner/repo",
                run=lambda *_a, **_k: failures.pop(0),
                sleep=sleeps.append,
            )
        self.assertEqual(sleeps, [2, 4])

    def test_graphql_errors_are_not_retried(self):
        """Raise GraphQL API errors immediately without another request or sleep."""
        result = subprocess.CompletedProcess(
            ["gh"],
            0,
            json.dumps({"errors": [{"message": "API error"}]}),
            "",
        )
        calls = []
        sleeps = []
        with self.assertRaisesRegex(OSError, "API error"):
            inventory.list_open_prs(
                "owner/repo",
                run=lambda *_a, **_k: calls.append(1) or result,
                sleep=sleeps.append,
            )
        self.assertEqual(calls, [1])
        self.assertEqual(sleeps, [])

    def test_transient_graphql_errors_retry_then_succeed(self):
        rate_limited = subprocess.CompletedProcess(
            ["gh"],
            0,
            json.dumps({"errors": [{"message": "API rate limit exceeded"}]}),
            "",
        )
        valid = subprocess.CompletedProcess(
            ["gh"], 0, json.dumps(_payload([_pr()])), ""
        )
        responses = [rate_limited, valid]
        sleeps = []
        prs = inventory.list_open_prs(
            "owner/repo",
            run=lambda *_a, **_k: responses.pop(0),
            sleep=sleeps.append,
        )
        self.assertEqual([pr["number"] for pr in prs], [12])
        self.assertEqual(sleeps, [2])

    def test_persistent_transient_graphql_errors_raise_oserror(self):
        result = subprocess.CompletedProcess(
            ["gh"],
            0,
            json.dumps({"errors": [{"message": "API rate limit exceeded"}]}),
            "",
        )
        sleeps = []
        with self.assertRaisesRegex(OSError, "rate limit"):
            inventory.list_open_prs(
                "owner/repo",
                run=lambda *_a, **_k: result,
                sleep=sleeps.append,
            )
        self.assertEqual(sleeps, [2, 4])

    def test_api_and_shape_errors_raise_oserror(self):
        """Reject GraphQL errors and malformed inventory response shapes."""
        for payload in (
            {"errors": [{"message": "partial API failure"}]},
            {"data": {"repository": {"pullRequests": {"nodes": []}}}},
        ):
            result = subprocess.CompletedProcess(["gh"], 0, json.dumps(payload), "")
            with self.subTest(payload=payload), self.assertRaises(OSError):
                inventory.list_open_prs(
                    "owner/repo",
                    run=lambda *_a, _result=result, **_k: _result,
                )

    def test_invalid_repository_is_rejected_before_invoking_github(self):
        for repo in (None, "", "owner", "/repo", "owner/", "owner/repo/extra"):
            with self.subTest(repo=repo):
                run = mock.Mock()
                with self.assertRaisesRegex(OSError, "invalid repository"):
                    inventory.list_open_prs(repo, run=run)
                run.assert_not_called()

    def test_pagination_requires_a_new_nonempty_cursor(self):
        for cursor in (None, "", 42, "cursor-1"):
            with self.subTest(cursor=cursor):
                pages = [
                    _payload([_pr()], next_page=True),
                    _payload([_pr(13)], next_page=True, cursor=cursor),
                ]
                run = mock.Mock(
                    side_effect=[
                        subprocess.CompletedProcess(["gh"], 0, json.dumps(page), "")
                        for page in pages
                    ]
                )
                sleep = mock.Mock()
                with self.assertRaisesRegex(OSError, "malformed payload"):
                    inventory.list_open_prs("owner/repo", run=run, sleep=sleep)
                self.assertEqual(run.call_count, 2)
                sleep.assert_not_called()

    def test_later_page_failure_raises_instead_of_returning_partial_inventory(self):
        run = mock.Mock(
            side_effect=[
                subprocess.CompletedProcess(
                    ["gh"], 0, json.dumps(_payload([_pr()], next_page=True)), ""
                ),
                *[subprocess.CompletedProcess(["gh"], 1, "", "unavailable")] * 3,
            ]
        )
        sleep = mock.Mock()
        with self.assertRaisesRegex(OSError, "unavailable"):
            inventory.list_open_prs("owner/repo", run=run, sleep=sleep)
        self.assertEqual(run.call_count, 4)
        self.assertEqual(sleep.call_args_list, [mock.call(2), mock.call(5)])
        for call in run.call_args_list[1:]:
            self.assertIn("cursor=cursor-1", call.args[0])

    def test_retry_budget_resets_for_each_page(self):
        failure = subprocess.CompletedProcess(["gh"], 1, "", "retry")
        run = mock.Mock(
            side_effect=[
                failure,
                failure,
                subprocess.CompletedProcess(
                    ["gh"], 0, json.dumps(_payload([_pr()], next_page=True)), ""
                ),
                failure,
                failure,
                subprocess.CompletedProcess(
                    ["gh"], 0, json.dumps(_payload([_pr(13)])), ""
                ),
            ]
        )
        sleep = mock.Mock()
        prs = inventory.list_open_prs("owner/repo", run=run, sleep=sleep)
        self.assertEqual([pr["number"] for pr in prs], [12, 13])
        self.assertEqual(sleep.call_args_list, [mock.call(2), mock.call(5)] * 2)
        self.assertEqual(run.call_count, 6)

    def test_missing_commit_or_rollup_keeps_checks_incomplete(self):
        for commits in ({"nodes": []}, {"nodes": [{"commit": {"author": None}}]}):
            with self.subTest(commits=commits):
                raw = _pr()
                raw["commits"] = commits
                live = inventory._normalize_pr(raw, "owner/repo")
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
                raw = _pr()
                raw[field] = value
                with self.assertRaises(OSError):
                    inventory._normalize_pr(raw, "owner/repo")

    def test_empty_inventory_is_a_successful_single_request(self):
        run = mock.Mock(
            return_value=subprocess.CompletedProcess(
                ["gh"], 0, json.dumps(_payload([])), ""
            )
        )
        self.assertEqual(inventory.list_open_prs("owner/repo", run=run), [])
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
