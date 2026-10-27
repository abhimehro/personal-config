"""Tests for open Octopus finding issues linked to pull requests."""

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

import pr_lifecycle_unblock as unblock
from pr_lifecycle_octopus_issues import (
    OCTOPUS_ISSUE_AUTHOR,
    fetch_open_octopus_issues,
    linked_prs,
)

from tests.pr_lifecycle_helpers import (
    UNBLOCK_CONFIG,
    UNBLOCK_REPO,
    UNBLOCK_SETTINGS,
    make_unblock_pr,
    route_unblock_pr,
)


class LinkedPrTests(unittest.TestCase):
    def test_url_form_matches_same_repository_case_insensitively(self) -> None:
        body = "See HTTPS://GITHUB.COM/OWNER/REPO/PULL/392?diff=split"
        self.assertEqual(linked_prs("owner/repo", body), {392})

    def test_pull_request_line_form(self) -> None:
        self.assertEqual(
            linked_prs("owner/repo", "Pull Request: fix a thing (#392)"),
            {392},
        )

    def test_other_repository_url_is_ignored(self) -> None:
        self.assertEqual(
            linked_prs("owner/repo", "https://github.com/other/repo/pull/392"),
            set(),
        )

    def test_non_string_body_has_no_links(self) -> None:
        self.assertEqual(linked_prs("owner/repo", None), set())

    def test_structured_forms_deduplicate_the_same_pr(self) -> None:
        body = (
            "Pull Request: fix a thing (#392)\n"
            "URL: https://github.com/owner/repo/pull/392"
        )
        self.assertEqual(linked_prs("owner/repo", body), {392})


class FetchOpenOctopusIssuesTests(unittest.TestCase):
    def test_fetches_slurped_pages_and_sorts_issues_by_linked_pr(self) -> None:
        issue_457 = {
            "number": 457,
            "user": {"login": OCTOPUS_ISSUE_AUTHOR},
            "body": "URL: https://github.com/owner/repo/pull/392",
        }
        issue_455 = {
            "number": 455,
            "user": {"login": OCTOPUS_ISSUE_AUTHOR},
            "body": "Pull Request: fix a thing (#392)",
        }
        pages = [
            [
                issue_457,
                {
                    "number": 458,
                    "user": {"login": OCTOPUS_ISSUE_AUTHOR},
                    "body": "https://github.com/owner/repo/pull/392",
                    "pull_request": {},
                },
                {
                    "number": 459,
                    "user": {"login": "someone-else"},
                    "body": "https://github.com/owner/repo/pull/392",
                },
            ],
            [issue_455],
        ]
        run = mock.Mock(
            return_value=subprocess.CompletedProcess(["gh"], 0, json.dumps(pages), "")
        )

        self.assertEqual(
            fetch_open_octopus_issues("owner/repo", run=run),
            {392: [455, 457]},
        )
        command = run.call_args.args[0]
        self.assertIn("--paginate", command)
        self.assertIn("--slurp", command)
        self.assertIn(
            "repos/owner/repo/issues?state=open&creator="
            "octopus-review%5Bbot%5D&per_page=100",
            command,
        )
        self.assertEqual(
            run.call_args.kwargs,
            {
                "check": False,
                "capture_output": True,
                "text": True,
                "timeout": 60,
            },
        )

    def test_accepts_a_flat_issue_list(self) -> None:
        issue = {
            "number": 457,
            "user": {"login": OCTOPUS_ISSUE_AUTHOR},
            "body": "https://github.com/owner/repo/pull/392",
        }
        run = mock.Mock(
            return_value=subprocess.CompletedProcess(["gh"], 0, json.dumps([issue]), "")
        )
        self.assertEqual(fetch_open_octopus_issues("owner/repo", run=run), {392: [457]})

    def test_nonzero_exit_and_malformed_payloads_raise_oserror(self) -> None:
        responses = (
            subprocess.CompletedProcess(["gh"], 1, "", "failed"),
            subprocess.CompletedProcess(["gh"], 0, "not json", ""),
            subprocess.CompletedProcess(["gh"], 0, json.dumps({"issues": []}), ""),
            subprocess.CompletedProcess(["gh"], 0, json.dumps([[None]]), ""),
        )
        for response in responses:
            with self.subTest(response=response), self.assertRaises(OSError):
                fetch_open_octopus_issues(
                    "owner/repo", run=mock.Mock(return_value=response)
                )


class OctopusIssueRoutingTests(unittest.TestCase):
    def test_issue_only_finding_escalates_to_human(self) -> None:
        actions = route_unblock_pr(
            make_unblock_pr(openOctopusFindings=0, openOctopusIssues=[457])
        )
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["action"], "ESCALATE")
        self.assertEqual(action["blocker"], "open_octopus_findings")
        self.assertEqual(action["owner"], "human")
        self.assertEqual(
            action["evidence"],
            {
                "open_octopus_findings": 0,
                "open_octopus_issues": ["#457"],
            },
        )
        self.assertIn("#457", action["recommended_action"])

    def test_absent_issue_list_and_zero_threads_emit_no_octopus_action(self) -> None:
        self.assertEqual(
            route_unblock_pr(make_unblock_pr(openOctopusFindings=0)),
            [],
        )

    def test_issue_and_thread_findings_share_one_escalation(self) -> None:
        actions = route_unblock_pr(
            make_unblock_pr(openOctopusFindings=1, openOctopusIssues=[457])
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            actions[0]["evidence"],
            {
                "open_octopus_findings": 1,
                "open_octopus_issues": ["#457"],
            },
        )
        self.assertIn("open Octopus review findings", actions[0]["recommended_action"])
        self.assertIn("#457", actions[0]["recommended_action"])

    def test_issue_only_finding_suppresses_automatic_close(self) -> None:
        actions = route_unblock_pr(
            make_unblock_pr(
                headRefName="pr-lifecycle-docs-20261001-run",
                openOctopusFindings=0,
                openOctopusIssues=[457],
            )
        )
        self.assertFalse(
            any(
                str(action.get("action") or "").startswith("CLOSE")
                for action in actions
            )
        )
        self.assertEqual(
            [action["blocker"] for action in actions],
            ["open_octopus_findings"],
        )


class OctopusIssueScanTests(unittest.TestCase):
    def _job(self) -> unblock._ScanJob:
        return unblock._ScanJob(
            repositories=[UNBLOCK_REPO],
            ledger={"items": []},
            policy=unblock.identity_policy_from_config(UNBLOCK_CONFIG),
            settings=UNBLOCK_SETTINGS,
        )

    def test_fetch_failure_marks_repo_inventory_failed(self) -> None:
        pr = make_unblock_pr(number=453)
        run = mock.Mock(
            return_value=subprocess.CompletedProcess(["gh"], 1, "", "unavailable")
        )
        with mock.patch.object(unblock, "list_open_prs", return_value=[pr]):
            actions, inventory_failed, _ = unblock._scan_repositories(self._job(), run)

        self.assertEqual(len(inventory_failed), 1)
        self.assertEqual(inventory_failed[0]["action"], "INVENTORY_FAILED")
        self.assertEqual(inventory_failed[0]["repository"], UNBLOCK_REPO)
        self.assertEqual(actions, inventory_failed)

    def test_fetch_timeout_fails_only_affected_repo(self) -> None:
        first_pr = make_unblock_pr(number=453)
        second_repo = "owner/other"
        second_pr = make_unblock_pr(
            repository=second_repo,
            url=f"https://github.com/{second_repo}/pull/454",
            number=454,
            openOctopusFindings=1,
        )
        job = unblock._ScanJob(
            repositories=[UNBLOCK_REPO, second_repo],
            ledger={"items": []},
            policy=unblock.identity_policy_from_config(UNBLOCK_CONFIG),
            settings=UNBLOCK_SETTINGS,
        )
        run = mock.Mock()
        timeout = subprocess.TimeoutExpired(cmd=["gh"], timeout=60)
        with (
            mock.patch.object(
                unblock, "list_open_prs", side_effect=[[first_pr], [second_pr]]
            ) as list_prs,
            mock.patch.object(
                unblock,
                "fetch_open_octopus_issues",
                side_effect=[timeout, {}],
            ) as fetch_issues,
        ):
            actions, inventory_failed, _ = unblock._scan_repositories(job, run)

        self.assertEqual(len(inventory_failed), 1)
        self.assertEqual(inventory_failed[0]["action"], "INVENTORY_FAILED")
        self.assertEqual(inventory_failed[0]["repository"], UNBLOCK_REPO)
        self.assertTrue(inventory_failed[0]["reason"].startswith("TimeoutExpired"))
        self.assertEqual(
            list_prs.call_args_list,
            [mock.call(UNBLOCK_REPO), mock.call(second_repo)],
        )
        self.assertEqual(
            fetch_issues.call_args_list,
            [mock.call(UNBLOCK_REPO, run=run), mock.call(second_repo, run=run)],
        )
        self.assertTrue(
            any(
                action.get("repository") == second_repo and action.get("pr") == 454
                for action in actions
            )
        )

    def test_success_attaches_issue_and_escalates_only_linked_pr(self) -> None:
        linked = make_unblock_pr(number=453)
        unlinked = make_unblock_pr(number=454)
        issue = {
            "number": 457,
            "user": {"login": OCTOPUS_ISSUE_AUTHOR},
            "body": f"https://github.com/{UNBLOCK_REPO}/pull/453",
        }
        run = mock.Mock(
            return_value=subprocess.CompletedProcess(
                ["gh"], 0, json.dumps([[issue]]), ""
            )
        )
        with mock.patch.object(
            unblock, "list_open_prs", return_value=[linked, unlinked]
        ):
            actions, inventory_failed, _ = unblock._scan_repositories(self._job(), run)

        self.assertEqual(inventory_failed, [])
        self.assertEqual(linked["openOctopusIssues"], [457])
        self.assertEqual(unlinked["openOctopusIssues"], [])
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "ESCALATE")
        self.assertEqual(actions[0]["pr"], 453)
        self.assertEqual(actions[0]["evidence"]["open_octopus_issues"], ["#457"])


if __name__ == "__main__":
    unittest.main()
