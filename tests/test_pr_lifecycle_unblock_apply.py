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
    route_unblock_pr as _route,
)
from tests.pr_lifecycle_helpers import (
    run_unblock_plan as _run_unblock_plan,
)


class UnblockApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.st = types.SimpleNamespace(**vars(unblock), run_plan=_run_unblock_plan)

    def test_unknown_action_is_rejected_before_any_github_command(self):
        run = mock.Mock()
        action = {
            "action": "CLOSE_UNKNOWN",
            "repository": REPO,
            "pr": 23,
            "comment": "Must not be posted.",
        }
        with self.assertRaisesRegex(ValueError, "unsupported action: CLOSE_UNKNOWN"):
            self.st._apply_action(action, run=run)
        run.assert_not_called()

    def test_inventory_failure_skips_backlog_refresh_in_apply_mode(self):
        """Preserve the existing backlog issue when repository inventory fails."""
        plan, update_issue = self.st.run_plan(
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
        plan, _ = self.st.run_plan(live, run=runner)
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
        plan, _ = self.st.run_plan(live, run=runner)
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
        plan, _ = self.st.run_plan(complete, run=runner)
        runner.assert_not_called()
        self.assertEqual(plan["comment_history_fetch_pr_count"], 0)
        self.assertEqual(plan["actions"][0]["action"], "TRIGGER")

        unknown = _pr(
            author={"login": "dependabot[bot]", "type": "Bot"},
            mergeable="CONFLICTING",
        )
        unknown.pop("commentsTotalCount")
        runner.reset_mock()
        plan, _ = self.st.run_plan(unknown, run=runner)
        runner.assert_not_called()
        self.assertEqual(plan["comment_history_fetch_pr_count"], 0)
        self.assertEqual(plan["actions"][0]["action"], "TRIGGER_SKIPPED")

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
                self.st._load_full_comments(pr, run=run)
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
                self.st._load_full_comments(pr, run=run)
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

    def test_invalid_repository_filter_fails_before_ledger_or_inventory_reads(self):
        with (
            mock.patch.object(unblock, "load_yaml", return_value=CONFIG),
            mock.patch.object(unblock.cas, "run_preflight") as fetch,
            mock.patch.object(unblock, "list_open_prs") as inventory,
            mock.patch.object(unblock, "_apply_action") as apply,
            self.assertRaisesRegex(ValueError, "unknown repository filter"),
        ):
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
                    decision_issues=True,
                )
            )
        self.assertEqual(inventory.call_args_list, [mock.call(REPO), mock.call(other)])
        update.assert_called_once_with(other, [], now=mock.ANY, notify_overdue=False)
        apply.assert_not_called()
        self.assertEqual(
            output["escalation_issues"][REPO]["action"], "ISSUE_UPDATE_SKIPPED"
        )
        self.assertEqual(output["escalation_issues"][other]["action"], "NOOP_EMPTY")
        self.assertEqual(output["inventory_failed"][0]["repository"], REPO)
        self.assertEqual(
            output["mutation_cap"], CONFIG["lifecycle"]["stage_caps"]["stage1_actions"]
        )

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
                self.st.cas,
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
            result = self.st.run_unblock(
                self.st._UnblockArgs(
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
