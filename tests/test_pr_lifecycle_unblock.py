"""Tests for PR blocker routing and bounded GitHub mutations."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_issue_status as issue_status
import pr_lifecycle_unblock as unblock

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
CONFIG = yaml.safe_load((ROOT / "tasks/pr-review-agent.config.yaml").read_text())
REPO = CONFIG["repos"][0]
BOT_LOGIN = CONFIG["bot_authors"][1]
SETTINGS = {
    "advisory_checks": ["CodeScene*", "review"],
    "trigger_expiry_days": 3,
    "lineage_stale_days": 3,
}


def _pr(**overrides):
    pr = {
        "number": 23,
        "repository": REPO,
        "url": f"https://github.com/{REPO}/pull/23",
        "author": {"login": BOT_LOGIN, "type": "Bot"},
        "headRefName": "bot/update",
        "headRefOid": "a" * 40,
        "baseRefName": "main",
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "reviewDecision": "REVIEW_REQUIRED",
        "isDraft": False,
        "checks": [],
        "comments": [],
        "latestReviews": [],
    }
    pr.update(overrides)
    return pr


def _route(pr, *, author_type="BOT", items=None, ledger=None, settings=None):
    return unblock.route_pr(
        pr,
        author_type=author_type,
        ledger_items_for_pr=items or [],
        ledger=ledger or {"items": []},
        settings=settings or SETTINGS,
        now=NOW,
    )


def _salvage_item(**overrides):
    item = {
        "key": f"{REPO}#90@{'b' * 40}",
        "repository": REPO,
        "pr": 90,
        "url": f"https://github.com/{REPO}/pull/90",
        "evidence_urls": [f"https://github.com/{REPO}/pull/23"],
        "handoffs": ["evt-s2-20261001-salvage"],
        "lifecycle_state": "TERMINAL",
        "terminal_disposition": "MERGED_ROUTINE",
    }
    item.update(overrides)
    return item


class RoutePrTests(unittest.TestCase):
    def test_stale_and_fresh_lineage(self):
        stale = _pr(headRefName="pr-lifecycle-docs-20261005-run")
        action = _route(stale)
        self.assertEqual(action[0]["action"], "CLOSE_STALE_LINEAGE")
        self.assertIn("older than 3 days", action[0]["comment"])
        fresh = _pr(headRefName="pr-lifecycle-docs-20261008-run")
        self.assertEqual(_route(fresh), [])

    def test_salvage_bot_closes_human_or_security_escalates(self):
        replacement = _salvage_item()
        bot = _route(_pr(), ledger={"items": [replacement]})
        self.assertEqual(bot[0]["action"], "CLOSE_SUPERSEDED")
        self.assertIn(replacement["url"], bot[0]["comment"])
        human = _route(_pr(), author_type="HUMAN", ledger={"items": [replacement]})
        self.assertEqual(human[0]["blocker"], "salvage_replacement_merged")
        security_item = {
            "lifecycle_state": "STAGE1_INTAKE",
            "guardrail_outcome": "REVIEW_SECURITY",
        }
        security = _route(
            _pr(),
            items=[security_item],
            ledger={"items": [replacement]},
        )
        self.assertEqual(security[0]["action"], "ESCALATE")
        self.assertEqual(security[0]["blocker"], "salvage_replacement_merged")

    def test_non_stage2_replacement_is_ignored(self):
        replacement = _salvage_item(handoffs=["evt-import-20261001"])
        self.assertEqual(_route(_pr(), ledger={"items": [replacement]}), [])

    def test_conflict_routing_by_family_and_author(self):
        cases = (
            (
                _pr(
                    author={"login": "dependabot[bot]", "type": "Bot"},
                    mergeable="CONFLICTING",
                ),
                "BOT",
                "dependabot_rebase",
            ),
            (
                _pr(
                    author={"login": "coderabbitai[bot]", "type": "Bot"},
                    mergeStateStatus="DIRTY",
                ),
                "BOT",
                "coderabbit_conflict",
            ),
            (
                _pr(headRefName="jules-fix", mergeable="CONFLICTING"),
                "HUMAN",
                "jules_conflict",
            ),
        )
        for pr, author_type, kind in cases:
            with self.subTest(kind=kind):
                action = _route(pr, author_type=author_type)[0]
                self.assertEqual(action["action"], "TRIGGER")
                self.assertEqual(action["kind"], kind)
                self.assertTrue(
                    action["body"].endswith(
                        f"<!-- pr-lifecycle-trigger kind={kind} head={'a' * 40} -->"
                    )
                )
        bot = _route(_pr(mergeable="CONFLICTING"))[0]
        self.assertEqual(bot["action"], "ESCALATE")
        self.assertEqual(bot["owner"], "stage2")
        human = _route(_pr(mergeable="CONFLICTING"), author_type="HUMAN")[0]
        self.assertEqual(human["owner"], "human")

    def test_conflict_gates_behind_checks_and_review(self):
        pr = _pr(
            mergeable="CONFLICTING",
            mergeStateStatus="BEHIND",
            checks=[{"name": "Build", "state": "FAILURE"}],
            reviewDecision="CHANGES_REQUESTED",
        )
        self.assertEqual(len(_route(pr)), 1)
        self.assertEqual(_route(pr)[0]["blocker"], "merge_conflict")

    def test_behind_bot_updates_branch_human_and_security_escalate(self):
        pr = _pr(mergeStateStatus="BEHIND")
        self.assertEqual(_route(pr)[0]["action"], "UPDATE_BRANCH")
        human = _route(pr, author_type="HUMAN")[0]
        self.assertEqual(human["blocker"], "behind_base")
        security = _route(
            pr,
            items=[
                {
                    "lifecycle_state": "STAGE1_INTAKE",
                    "guardrail_outcome": "REVIEW_SECURITY",
                }
            ],
        )[0]
        self.assertEqual(security["action"], "ESCALATE")

    def test_required_advisory_and_codescene_failures(self):
        advisory = _route(_pr(checks=[{"name": "review", "state": "FAILURE"}]))
        self.assertEqual(advisory[0]["action"], "ADVISORY_ONLY")
        mixed = _route(
            _pr(
                checks=[
                    {"name": "Build", "state": "FAILURE"},
                    {"name": "review", "state": "FAILURE"},
                ]
            )
        )
        self.assertEqual(
            [action["action"] for action in mixed],
            ["ESCALATE", "ADVISORY_ONLY"],
        )
        codescene = _route(
            _pr(checks=[{"name": "CodeScene quality gate", "state": "FAILURE"}])
        )
        self.assertEqual(
            [action["action"] for action in codescene],
            ["TRIGGER", "ADVISORY_ONLY"],
        )
        self.assertEqual(codescene[0]["kind"], "codescene")

    def test_jules_checks_and_coderabbit_review_triggers(self):
        jules = _route(
            _pr(
                headRefName="jules-task",
                checks=[{"name": "Build", "state": "FAILURE"}],
            ),
            author_type="HUMAN",
        )
        self.assertEqual(jules[0]["kind"], "jules_checks")
        coderabbit = _route(
            _pr(
                latestReviews=[
                    {
                        "author": {"login": "coderabbitai[bot]"},
                        "state": "CHANGES_REQUESTED",
                    }
                ],
                reviewDecision="CHANGES_REQUESTED",
            )
        )
        self.assertEqual(coderabbit[0]["kind"], "coderabbit_autofix")

    def test_trigger_markers_dedupe_same_head_but_allow_new_head(self):
        marker = f"<!-- pr-lifecycle-trigger kind=dependabot_rebase head={'a' * 40} -->"
        pr = _pr(
            author={"login": "dependabot[bot]", "type": "Bot"},
            mergeStateStatus="BEHIND",
            comments=[
                {
                    "body": f"@dependabot rebase\n{marker}",
                    "createdAt": "2026-10-09T00:00:00Z",
                }
            ],
        )
        self.assertEqual(_route(pr), [])
        newer = dict(pr, headRefOid="c" * 40)
        self.assertEqual(_route(newer)[0]["action"], "TRIGGER")

    def test_expired_marker_escalates_and_human_non_jules_never_gets_push_trigger(self):
        marker = f"<!-- pr-lifecycle-trigger kind=dependabot_rebase head={'a' * 40} -->"
        pr = _pr(
            author={"login": "dependabot[bot]", "type": "Bot"},
            mergeStateStatus="BEHIND",
            comments=[
                {
                    "body": marker,
                    "createdAt": "2026-10-01T00:00:00Z",
                }
            ],
        )
        action = _route(pr)[0]
        self.assertEqual(action["blocker"], "trigger_unanswered")
        human = _route(
            _pr(
                author={"login": "someone", "type": "User"},
                mergeable="CONFLICTING",
            ),
            author_type="HUMAN",
        )[0]
        self.assertEqual(human["action"], "ESCALATE")
        self.assertNotIn("kind", human)

    def test_terminal_but_open_is_escalated(self):
        item = {
            "key": f"{REPO}#23@{'a' * 40}",
            "lifecycle_state": "TERMINAL",
            "terminal_disposition": "CLOSED_NOOP",
            "author_type": "BOT",
        }
        action = _route(_pr(), items=[item])[0]
        self.assertEqual(action["blocker"], "ledger_terminal_but_open")

    def test_human_owned_ledger_rows_are_included_in_backlog(self):
        ledger_item = {
            "key": f"{REPO}#23@{'a' * 40}",
            "repository": REPO,
            "pr": 23,
            "url": f"https://github.com/{REPO}/pull/23",
            "current_owner": "human",
            "lifecycle_state": "WAITING_HUMAN",
            "guardrail_outcome": "REVIEW_SECURITY",
            "next_action": "Review security-sensitive changes.",
            "safe_default": "Leave open.",
            "updated_at_utc": "2026-10-01T00:00:00Z",
        }
        rows = unblock._rows_for_repo(
            REPO,
            [
                {
                    "action": "ESCALATE",
                    "repository": REPO,
                    "pr": 23,
                    "blocker": "REVIEW_SECURITY",
                    "url": ledger_item["url"],
                    "evidence": {},
                    "recommended_action": "Review security-sensitive changes.",
                    "safe_default": "Leave open.",
                    "owner": "human",
                }
            ],
            {"items": [ledger_item]},
            7,
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["blocker"], "REVIEW_SECURITY")
        self.assertEqual(rows[0]["owner"], "human")
        rendered = issue_status.backlog_issue_body(REPO, rows, {}, NOW)
        self.assertEqual(rendered.count(f"[23](https://github.com/{REPO}/pull/23)"), 1)

    def test_drafts_are_skipped_after_salvage_lineage_routes(self):
        self.assertEqual(_route(_pr(isDraft=True)), [])
        stale = _route(_pr(isDraft=True, headRefName="pr-lifecycle-docs-20261001"))
        self.assertEqual(stale[0]["action"], "CLOSE_STALE_LINEAGE")


class UnblockApplyTests(unittest.TestCase):
    def test_apply_close_uses_pinned_argv_and_confirms_without_deleting_branch(self):
        calls = []

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            stdout = (
                json.dumps({"state": "CLOSED"}) if argv[1:3] == ["pr", "view"] else ""
            )
            return subprocess.CompletedProcess(argv, 0, stdout, "")

        action = {
            "action": "CLOSE_SUPERSEDED",
            "repository": REPO,
            "pr": 23,
            "comment": "Superseded.",
        }
        unblock._apply_action(action, run=run)
        self.assertFalse(action["unconfirmed"])
        self.assertEqual(
            [call[0][2] for call in calls], ["comment", "edit", "close", "view"]
        )
        for argv, kwargs in calls:
            self.assertIn("--repo", argv)
            self.assertEqual(argv[argv.index("--repo") + 1], REPO)
            self.assertEqual(kwargs["timeout"], 60)
            self.assertFalse(kwargs["check"])
        close_argv = calls[2][0]
        self.assertNotIn("--delete-branch", close_argv)

    def test_update_branch_uses_expected_sha_and_pinned_repository(self):
        calls = []

        def run(argv, **kwargs):
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
                "--repo",
                REPO,
                "-X",
                "PUT",
                f"repos/{REPO}/pulls/23/update-branch",
                "-f",
                f"expected_head_sha={'a' * 40}",
            ],
        )
        self.assertFalse(kwargs["check"])

    def test_failed_close_step_is_unconfirmed_and_remaining_steps_run(self):
        calls = []

        def run(argv, **_kwargs):
            calls.append(argv)
            rc = 1 if len(calls) == 1 else 0
            stdout = (
                json.dumps({"state": "CLOSED"}) if argv[1:3] == ["pr", "view"] else ""
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
            unblock.run_unblock(apply=True, json_out=True, repos_filter=[REPO], limit=0)
        self.assertEqual(output["deferred_by_cap_count"], 1)
        self.assertEqual(output["deferred_by_cap"][0]["kind"], "dependabot_rebase")
        apply_action.assert_not_called()


if __name__ == "__main__":
    unittest.main()
