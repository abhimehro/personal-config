"""Tests for confirmed close/update/label mutations in the unblock stage."""

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

import types

import pr_lifecycle_unblock as unblock

from tests.pr_lifecycle_helpers import (
    UNBLOCK_CONFIG as CONFIG,
)
from tests.pr_lifecycle_helpers import (
    UNBLOCK_REPO as REPO,
)
from tests.pr_lifecycle_helpers import (
    make_unblock_pr as _pr,
)
from tests.pr_lifecycle_helpers import (
    run_unblock_plan as _run_unblock_plan,
)


class UnblockApplyMutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.st = types.SimpleNamespace(**vars(unblock), run_plan=_run_unblock_plan)

    def test_apply_close_uses_pinned_argv_and_confirms_without_deleting_branch(self):
        """Verify close commands target the repository and confirm the closed state."""
        calls = []

        def run(argv, **kwargs):
            """Record GitHub calls and simulate an existing label and confirmed closure."""
            calls.append((argv, kwargs))
            returncode = 1 if argv[1:3] == ["label", "create"] else 0
            stdout = (
                json.dumps({"state": "CLOSED"}) if argv[1:3] == ["pr", "view"] else ""
            )
            return subprocess.CompletedProcess(argv, returncode, stdout, "")

        action = {
            "action": "CLOSE_SUPERSEDED",
            "repository": REPO,
            "pr": 23,
            "comment": "Superseded.",
        }
        self.st._apply_action(action, run=run)
        self.assertFalse(action["unconfirmed"])
        self.assertEqual(
            [call[0][2] for call in calls],
            ["create", "edit", "close", "view", "comment"],
        )
        self.assertEqual(
            calls[0][0],
            [
                "gh",
                "label",
                "create",
                "superseded",
                "--repo",
                REPO,
                "--color",
                "cfd3d7",
                "--description",
                "Superseded by another PR (pr-lifecycle)",
            ],
        )
        for argv, kwargs in calls:
            self.assertIn("--repo", argv)
            self.assertEqual(argv[argv.index("--repo") + 1], REPO)
            self.assertEqual(kwargs["timeout"], 60)
            self.assertFalse(kwargs["check"])
        close_argv = calls[2][0]
        self.assertNotIn("--delete-branch", close_argv)

    def test_failed_close_skips_the_comment(self):
        """A close that does not confirm posts no comment step."""
        calls = []

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            stdout = (
                json.dumps({"state": "OPEN"}) if argv[1:3] == ["pr", "view"] else ""
            )
            return subprocess.CompletedProcess(argv, 0, stdout, "")

        action = {
            "action": "CLOSE_STALE_LINEAGE",
            "repository": REPO,
            "pr": 24,
            "comment": "Stale.",
        }
        self.st._apply_action(action, run=run)
        self.assertEqual(
            [call[0][2] for call in calls],
            ["create", "edit", "close", "view"],
        )
        self.assertTrue(action["unconfirmed"])

    def test_update_branch_uses_expected_sha_without_repo_flag(self):
        """Pin branch updates to the expected SHA in the repository API endpoint."""
        calls = []

        def run(argv, **kwargs):
            """Record the branch update request and return a successful process result."""
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, "", "")

        self.st._apply_action(
            {
                "action": "UPDATE_BRANCH",
                "repository": REPO,
                "pr": 23,
                "expected_head_sha": "a" * 40,
            },
            run=run,
        )
        argv, kwargs = calls[0]
        self.assertEqual(
            argv,
            [
                "gh",
                "api",
                "-X",
                "PUT",
                f"repos/{REPO}/pulls/23/update-branch",
                "-f",
                f"expected_head_sha={'a' * 40}",
            ],
        )
        self.assertNotIn("--repo", argv)
        self.assertFalse(kwargs["check"])

    def test_failed_close_step_is_unconfirmed_and_remaining_steps_run(self):
        """Record an unconfirmed close after a step fails while still running later steps."""
        calls = []

        def run(argv, **_kwargs):
            """Fail the first close-workflow step and simulate success for later commands."""
            calls.append(argv)
            rc = 1 if argv[1:3] == ["pr", "close"] else 0
            stdout = (
                json.dumps({"state": "OPEN"}) if argv[1:3] == ["pr", "view"] else ""
            )
            return subprocess.CompletedProcess(argv, rc, stdout, "")

        action = {
            "action": "CLOSE_STALE_LINEAGE",
            "repository": REPO,
            "pr": 23,
            "comment": "Stale.",
        }
        self.st._apply_action(action, run=run)
        self.assertTrue(action["unconfirmed"])
        self.assertEqual(len(calls), 4)

    def test_mutation_cap_defers_actions_without_silently_dropping_them(self):
        """Report mutations deferred by the cap without executing them."""
        config = dict(CONFIG)
        config["repos"] = [REPO]
        ledger = {"ledger_revision": 3, "items": []}
        live = _pr(
            author={"login": "dependabot[bot]", "type": "Bot"},
            mergeStateStatus="BEHIND",
        )
        output = {}
        with (
            mock.patch.object(unblock, "load_yaml", side_effect=[config, ledger]),
            mock.patch.object(
                self.st.cas,
                "run_preflight",
                return_value={"ledger_path": "ledger.yaml"},
            ),
            mock.patch.object(unblock, "list_open_prs", return_value=[live]),
            mock.patch.object(unblock, "_apply_action") as apply_action,
            mock.patch.object(
                unblock,
                "update_backlog_issue",
                return_value={"action": "NOOP_EMPTY"},
            ),
            mock.patch.object(
                unblock, "_emit", side_effect=lambda plan, _json: output.update(plan)
            ),
        ):
            self.st.run_unblock(
                self.st._UnblockArgs(
                    apply=True, json_out=True, repos_filter=[REPO], limit=0
                )
            )
        self.assertEqual(output["deferred_by_cap_count"], 1)
        self.assertEqual(output["deferred_by_cap"][0]["kind"], "dependabot_rebase")
        self.assertEqual(output["mutations_applied"], 0)
        self.assertEqual(output["mutations_unconfirmed"], 0)
        apply_action.assert_not_called()

    def test_summary_counts_selected_mutations_by_confirmation(self):
        """Separate unconfirmed results, excluding deferred and nonmutating rows."""
        actions = [
            {"action": "TRIGGER", "repository": REPO, "pr": number}
            for number in range(1, 5)
        ]
        actions.append({"action": "SKIP", "repository": REPO, "unconfirmed": True})
        actions[3]["unconfirmed"] = True
        output = {}

        def apply_action(action):
            if action["pr"] != 3:
                action["unconfirmed"] = action["pr"] == 2

        with (
            mock.patch.object(
                unblock,
                "load_yaml",
                side_effect=[dict(CONFIG, repos=[REPO]), {"items": []}],
            ),
            mock.patch.object(
                self.st.cas,
                "run_preflight",
                return_value={"ledger_path": "ledger.yaml"},
            ),
            mock.patch.object(unblock, "list_open_prs", return_value=[_pr()]),
            mock.patch.object(unblock, "route_pr", return_value=actions),
            mock.patch.object(
                unblock, "_apply_action", side_effect=apply_action
            ) as apply,
            mock.patch.object(unblock, "update_backlog_issue"),
            mock.patch.object(
                unblock, "_emit", side_effect=lambda plan, _json: output.update(plan)
            ),
        ):
            self.st.run_unblock(
                self.st._UnblockArgs(
                    apply=True, json_out=True, repos_filter=[REPO], limit=3
                )
            )
        self.assertEqual(apply.call_count, 3)
        self.assertEqual(output["mutations_selected"], 3)
        self.assertEqual(output["mutations_applied"], 2)
        self.assertEqual(output["mutations_unconfirmed"], 1)
        self.assertEqual(output["deferred_by_cap_count"], 1)

    def test_close_requires_successful_reread_of_closed_state(self):
        for confirmation in (
            subprocess.CompletedProcess(["gh"], 0, '{"state":"OPEN"}', ""),
            subprocess.CompletedProcess(["gh"], 0, "{invalid", ""),
            subprocess.CompletedProcess(["gh"], 0, "[]", ""),
            subprocess.CompletedProcess(["gh"], 1, '{"state":"CLOSED"}', "failure"),
            subprocess.TimeoutExpired(["gh"], 60),
        ):
            with self.subTest(confirmation=confirmation):
                run = mock.Mock(
                    side_effect=[
                        *[subprocess.CompletedProcess(["gh"], 0, "", "")] * 3,
                        confirmation,
                    ]
                )
                action = {
                    "action": "CLOSE_SUPERSEDED",
                    "repository": REPO,
                    "pr": 23,
                    "comment": "Superseded.",
                }
                self.st._apply_action(action, run=run)
                self.assertTrue(action["unconfirmed"])
                self.assertEqual(run.call_count, 4)
                self.assertEqual(action["github_steps"][-1]["step"], "confirm")
                step = action["github_steps"][-1]
                if isinstance(confirmation, BaseException):
                    self.assertEqual(step["error"], type(confirmation).__name__)
                    self.assertIsNone(step["exit_code"])
                else:
                    self.assertEqual(step["exit_code"], confirmation.returncode)
                self.assertNotIn(
                    "comment", [step["step"] for step in action["github_steps"]]
                )

    def test_confirmed_close_still_reports_failed_label_or_comment(self):
        """A closed PR alone does not prove that all required steps succeeded."""
        for failed_step in ("label", "close", "comment"):
            with self.subTest(failed_step=failed_step):
                steps = ("ensure_label", "label", "close", "confirm", "comment")
                run = mock.Mock(
                    side_effect=[
                        subprocess.CompletedProcess(
                            ["gh"],
                            1 if step == failed_step else 0,
                            '{"state":"CLOSED"}' if step == "confirm" else "",
                            "",
                        )
                        for step in steps
                    ]
                )
                action = {
                    "action": "CLOSE_SUPERSEDED",
                    "repository": REPO,
                    "pr": 23,
                    "comment": "Superseded.",
                }
                unblock._apply_action(action, run=run)
                self.assertTrue(action["unconfirmed"])
                self.assertEqual(run.call_count, 5)
                self.assertEqual(
                    [
                        step["step"]
                        for step in action["github_steps"]
                        if step["exit_code"]
                    ],
                    [failed_step],
                )

    def test_push_capable_action_failures_are_reported_without_retry(self):
        for kind in ("TRIGGER", "UPDATE_BRANCH"):
            for failure in (
                subprocess.CompletedProcess(["gh"], 1, "", "failure"),
                OSError("unavailable"),
                subprocess.TimeoutExpired(["gh"], 60),
            ):
                with self.subTest(kind=kind, failure=failure):
                    run = mock.Mock(side_effect=[failure])
                    action = {
                        "action": kind,
                        "repository": REPO,
                        "pr": 23,
                        "body": "@dependabot rebase",
                        "expected_head_sha": "a" * 40,
                    }
                    self.st._apply_action(action, run=run)
                    self.assertTrue(action["unconfirmed"])
                    self.assertEqual(len(action["github_steps"]), 1)
                    step = action["github_steps"][0]
                    if isinstance(failure, BaseException):
                        self.assertIsNone(step["exit_code"])
                        self.assertEqual(step["error"], type(failure).__name__)
                    else:
                        self.assertEqual(step["exit_code"], 1)
                    run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
