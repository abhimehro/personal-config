"""Tests for normalized, paginated open-PR inventory."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_open_inventory as inventory


def _pr(number: int = 12) -> dict:
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
            "nodes": [
                {
                    "author": {"login": "reviewer"},
                    "body": "comment",
                    "createdAt": "2026-10-02T00:00:00Z",
                }
            ]
        },
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "author": {"email": "bot@example.com"},
                        "statusCheckRollup": {
                            "contexts": {
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
                                ]
                            }
                        },
                    }
                }
            ]
        },
    }


def _payload(nodes: list[dict], *, next_page: bool = False, cursor: str = "cursor-1"):
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
    def test_normalizes_pr_identity_reviews_comments_commits_and_checks(self):
        live = inventory._normalize_pr(_pr(), "owner/repo")
        self.assertEqual(live["author"], {"login": "dependabot[bot]", "type": "Bot"})
        self.assertEqual(
            live["commits"], [{"commit": {"author": {"email": "bot@example.com"}}}]
        )
        self.assertEqual(live["latestReviews"][0]["author"]["login"], "reviewer")
        self.assertEqual(live["comments"][0]["body"], "comment")
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
        commands = []
        responses = [
            subprocess.CompletedProcess(
                ["gh"], 0, json.dumps(_payload([_pr()], next_page=True)), ""
            ),
            subprocess.CompletedProcess(["gh"], 0, json.dumps(_payload([_pr(13)])), ""),
        ]

        def run(argv, **_kwargs):
            commands.append(argv)
            return responses.pop(0)

        prs = inventory.list_open_prs("owner/repo", run=run)
        self.assertEqual([pr["number"] for pr in prs], [12, 13])
        self.assertEqual(len(commands), 2)
        self.assertIn("pullRequests(first: 50, states: OPEN", commands[0][4])
        self.assertIn("cursor=cursor-1", commands[1])

    def test_nonzero_exit_and_malformed_json_raise_oserror(self):
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
                )

    def test_api_and_shape_errors_raise_oserror(self):
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


if __name__ == "__main__":
    unittest.main()
