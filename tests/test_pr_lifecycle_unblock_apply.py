"""Tests for bounded GitHub mutations in the lifecycle unblock stage."""

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
    route_unblock_pr as _route,
)
from tests.pr_lifecycle_helpers import (
    run_unblock_plan as _run_unblock_plan,
)


class UnblockApplyTests(unittest.TestCase):
    def test_unknown_action_is_rejected_before_any_github_command(self):
        run = mock.Mock()
        action = {
            "action": "CLOSE_UNKNOWN",
            "repository": REPO,
            "pr": 23,
            "comment": "Must not be posted.",
        }
        with self.assertRaisesRegex(ValueError, "unsupported action: CLOSE_UNKNOWN"):
            unblock._apply_action(action, run=run)
        run.assert_not_called()

    def test_inventory_failure_skips_backlog_refresh_in_apply_mode(self):
        """Preserve the existing backlog issue when repository inventory fails."""
        plan, update_issue = _run_unblock_plan(
            apply=True,
            inventory_error=OSError("network unavailable"),
        )
        self.assertEqual(
            plan["escalation_issues"][REPO],
            {
                "action": "ISSUE_UPDATE_SKIPPED",
                "repository": REPO,
                "reason": "INVENTORY_FAILED",
            },
        )
        update_issue.assert_not_called()

    def test_paginated_comment_history_dedupes_and_expires_old_marker(self):
        """Fetch all comments and escalate an expired trigger outside the recent page."""
        marker = (
            f"<!-- pr-lifecycle-trigger kind=dependabot_rebase " f"head={'a' * 40} -->"
        )
        live = _pr(
            author={"login": "dependabot[bot]", "type": "Bot"},
            mergeable="CONFLICTING",
            comments=[
                {"body": f"recent-{index}", "createdAt": "2026-10-09T00:00:00Z"}
                for index in range(50)
            ],
            commentsTotalCount=120,
        )
        full_comments = [
            {
                "user": {"login": "reviewer"},
                "body": f"comment-{index}",
                "created_at": "2026-10-09T00:00:00Z",
            }
            for index in range(120)
        ]
        full_comments[101].update(
            user={"login": "abhimehro"},
            body=marker,
            created_at="2026-10-01T00:00:00Z",
        )
        runner = mock.Mock(
            return_value=subprocess.CompletedProcess(
                ["gh"],
                0,
                json.dumps([full_comments[:100], full_comments[100:]]),
                "",
            )
        )
        plan, _ = _run_unblock_plan(live, run=runner)
        self.assertEqual(
            runner.call_args.args[0],
            [
                "gh",
                "api",
                "--paginate",
                "--slurp",
                f"repos/{REPO}/issues/23/comments",
            ],
        )
        self.assertEqual(runner.call_args.kwargs["timeout"], 60)
        self.assertEqual(plan["comment_history_fetch_pr_count"], 1)
        self.assertNotIn("TRIGGER", [action["action"] for action in plan["actions"]])
        self.assertEqual(plan["actions"][0]["blocker"], "trigger_unanswered")
        self.assertEqual(plan["actions"][0]["evidence"]["sent"], "2026-10-01T00:00:00Z")

    def test_failed_comment_fetch_skips_trigger(self):
        """Suppress triggers when the full comment history cannot be retrieved."""
        live = _pr(
            author={"login": "dependabot[bot]", "type": "Bot"},
            mergeable="CONFLICTING",
            commentsTotalCount=120,
        )
        runner = mock.Mock(
            return_value=subprocess.CompletedProcess(["gh"], 1, "", "unavailable")
        )
        plan, _ = _run_unblock_plan(live, run=runner)
        self.assertEqual(plan["comment_history_fetch_pr_count"], 1)
        self.assertEqual(plan["actions"][0]["action"], "TRIGGER_SKIPPED")
        self.assertEqual(
            plan["actions"][0]["reason"],
            "comment history unavailable; marker dedupe unverified",
        )
        self.assertNotIn("TRIGGER", [action["action"] for action in plan["actions"]])

    def test_complete_or_unknown_comment_counts_avoid_fetch_and_unknown_skips(self):
        """Avoid redundant fetches and suppress triggers when comment counts are unknown."""
        complete = _pr(
            author={"login": "dependabot[bot]", "type": "Bot"},
            mergeable="CONFLICTING",
            comments=[{"body": "existing", "createdAt": "2026-10-09T00:00:00Z"}],
            commentsTotalCount=1,
        )
        runner = mock.Mock()
        plan, _ = _run_unblock_plan(complete, run=runner)
        runner.assert_not_called()
        self.assertEqual(plan["comment_history_fetch_pr_count"], 0)
        self.assertEqual(plan["actions"][0]["action"], "TRIGGER")

        unknown = _pr(
            author={"login": "dependabot[bot]", "type": "Bot"},
            mergeable="CONFLICTING",
        )
        unknown.pop("commentsTotalCount")
        runner.reset_mock()
        plan, _ = _run_unblock_plan(unknown, run=runner)
        runner.assert_not_called()
        self.assertEqual(plan["comment_history_fetch_pr_count"], 0)
        self.assertEqual(plan["actions"][0]["action"], "TRIGGER_SKIPPED")

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
        unblock._apply_action(action, run=run)
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
        unblock._apply_action(action, run=run)
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

        unblock._apply_action(
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
        unblock._apply_action(action, run=run)
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
                unblock.cas,
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
            unblock.run_unblock(
                unblock._UnblockArgs(
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
                unblock.cas,
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
            unblock.run_unblock(
                unblock._UnblockArgs(
                    apply=True, json_out=True, repos_filter=[REPO], limit=3
                )
            )
        self.assertEqual(apply.call_count, 3)
        self.assertEqual(output["mutations_selected"], 3)
        self.assertEqual(output["mutations_applied"], 2)
        self.assertEqual(output["mutations_unconfirmed"], 1)
        self.assertEqual(output["deferred_by_cap_count"], 1)

    def test_partial_or_malformed_comment_history_suppresses_trigger(self):
        valid = {"user": {"login": "reviewer"}, "body": "hello", "created_at": None}
        for payload in (
            [[valid]],  # Fewer comments than the advertised count.
            [[valid], [None]],
            [[valid], [{"user": None, "body": "hello"}]],
            [[valid], [dict(valid, body=42)]],
            [[valid], [dict(valid, created_at=42)]],
            {"message": "not a comment list"},
        ):
            with self.subTest(payload=payload):
                pr = _pr(
                    author={"login": "dependabot[bot]", "type": "Bot"},
                    mergeStateStatus="BEHIND",
                    commentsTotalCount=2,
                )
                run = mock.Mock(
                    return_value=subprocess.CompletedProcess(
                        ["gh"], 0, json.dumps(payload), ""
                    )
                )
                unblock._load_full_comments(pr, run=run)
                self.assertTrue(pr["comments_incomplete"])
                self.assertEqual(pr["comments"], [])
                self.assertEqual([a["action"] for a in _route(pr)], ["TRIGGER_SKIPPED"])
                run.assert_called_once()

    def test_complete_comment_history_clears_previous_failure(self):
        comment = {"user": {"login": "reviewer"}, "body": None, "created_at": None}
        for payload in ([comment], [[comment]]):
            with self.subTest(payload=payload):
                pr = _pr(commentsTotalCount=1, comments_incomplete=True)
                run = mock.Mock(
                    return_value=subprocess.CompletedProcess(
                        ["gh"], 0, json.dumps(payload), ""
                    )
                )
                unblock._load_full_comments(pr, run=run)
                self.assertNotIn("comments_incomplete", pr)
                self.assertEqual(
                    pr["comments"],
                    [
                        {
                            "author": {"login": "reviewer"},
                            "body": "",
                            "createdAt": None,
                        }
                    ],
                )

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
                unblock._apply_action(action, run=run)
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

    def test_invalid_repository_filter_fails_before_ledger_or_inventory_reads(self):
        with (
            mock.patch.object(unblock, "load_yaml", return_value=CONFIG),
            mock.patch.object(unblock.cas, "run_preflight") as fetch,
            mock.patch.object(unblock, "list_open_prs") as inventory,
            mock.patch.object(unblock, "_apply_action") as apply,
        ):
            with self.assertRaisesRegex(ValueError, "unknown repository filter"):
                unblock.run_unblock(
                    unblock._UnblockArgs(
                        apply=True,
                        json_out=True,
                        repos_filter=["unconfigured/repo"],
                        limit=None,
                    )
                )
        fetch.assert_not_called()
        inventory.assert_not_called()
        apply.assert_not_called()

    def test_inventory_failure_does_not_block_other_repository_refresh(self):
        """Only the failed repository keeps its previous decision issue."""
        other = CONFIG["repos"][1]
        output = {}
        with (
            mock.patch.object(
                unblock,
                "load_yaml",
                side_effect=[
                    dict(CONFIG, repos=[REPO, other]),
                    {"items": []},
                ],
            ),
            mock.patch.object(
                unblock.cas,
                "run_preflight",
                return_value={
                    "ledger_path": "ledger.yaml",
                },
            ),
            mock.patch.object(
                unblock,
                "list_open_prs",
                side_effect=[
                    OSError("unavailable"),
                    [],
                ],
            ) as inventory,
            mock.patch.object(unblock, "_apply_action") as apply,
            mock.patch.object(
                unblock,
                "update_backlog_issue",
                return_value={
                    "action": "NOOP_EMPTY",
                },
            ) as update,
            mock.patch.object(
                unblock, "_emit", side_effect=lambda plan, _: output.update(plan)
            ),
        ):
            unblock.run_unblock(
                unblock._UnblockArgs(
                    apply=True,
                    json_out=True,
                    repos_filter=None,
                    limit=None,
                )
            )
        self.assertEqual(inventory.call_args_list, [mock.call(REPO), mock.call(other)])
        update.assert_called_once_with(other, [], now=mock.ANY)
        apply.assert_not_called()
        self.assertEqual(
            output["escalation_issues"][REPO]["action"], "ISSUE_UPDATE_SKIPPED"
        )
        self.assertEqual(output["escalation_issues"][other]["action"], "NOOP_EMPTY")
        self.assertEqual(output["inventory_failed"][0]["repository"], REPO)
        self.assertEqual(
            output["mutation_cap"], CONFIG["lifecycle"]["stage_caps"]["stage1_actions"]
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
                    unblock._apply_action(action, run=run)
                    self.assertTrue(action["unconfirmed"])
                    self.assertEqual(len(action["github_steps"]), 1)
                    step = action["github_steps"][0]
                    if isinstance(failure, BaseException):
                        self.assertIsNone(step["exit_code"])
                        self.assertEqual(step["error"], type(failure).__name__)
                    else:
                        self.assertEqual(step["exit_code"], 1)
                    run.assert_called_once()

    def test_dry_run_plans_mutations_without_applying_or_updating_issues(self):
        live = _pr(
            author={"login": "dependabot[bot]", "type": "Bot"},
            mergeStateStatus="BEHIND",
        )
        config = dict(CONFIG, repos=[REPO])
        output = {}
        with (
            mock.patch.object(
                unblock, "load_yaml", side_effect=[config, {"items": []}]
            ),
            mock.patch.object(
                unblock.cas,
                "run_preflight",
                return_value={"ledger_path": "ledger.yaml"},
            ),
            mock.patch.object(unblock, "list_open_prs", return_value=[live]),
            mock.patch.object(unblock, "_apply_action") as apply_action,
            mock.patch.object(unblock, "update_backlog_issue") as update_issue,
            mock.patch.object(
                unblock, "_emit", side_effect=lambda plan, _json: output.update(plan)
            ),
        ):
            result = unblock.run_unblock(
                unblock._UnblockArgs(
                    apply=False,
                    json_out=True,
                    repos_filter=[REPO],
                    limit=1,
                )
            )
        self.assertEqual(result, 0)
        self.assertTrue(output["dry_run"])
        self.assertEqual(output["mutations_selected"], 1)
        self.assertEqual(output["mutations_applied"], 0)
        self.assertEqual(output["mutations_unconfirmed"], 0)
        self.assertEqual(output["actions"][0]["action"], "TRIGGER")
        apply_action.assert_not_called()
        update_issue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
