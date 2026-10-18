"""Unit tests for title-vs-path/diff security tagging in pr_lifecycle_reconcile."""

from __future__ import annotations

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

import pr_lifecycle_reconcile_guards as guards  # noqa: E402
from pr_identity import identity_policy_from_config  # noqa: E402

from tests.pr_lifecycle_helpers import (  # noqa: E402
    load_reconcile_with_stubs,
    reconcile_item,
)

reconcile = load_reconcile_with_stubs()

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
CONFIG = yaml.safe_load((ROOT / "tasks/pr-review-agent.config.yaml").read_text())
POLICY = identity_policy_from_config(CONFIG)
REPO = CONFIG["repos"][0]
_OPEN_LIVE = {"state": "OPEN", "headRefOid": "a" * 40, "baseRefOid": "b" * 40}


def _live_pr(**overrides):
    pr = {
        "number": 587,
        "repository": REPO,
        "url": f"https://github.com/{REPO}/pull/587",
        "title": "🛡️ Sentinel: Refactor logging in export_comparison_sheets",
        "body": "Created automatically by Jules",
        "isDraft": False,
        "headRefName": "sentinel/logging-cleanup",
        "headRefOid": "a" * 40,
        "baseRefName": "main",
        "baseRefOid": "b" * 40,
        "author": {"login": "google-labs-jules[bot]", "type": "Bot"},
        "comments": [],
        "latestReviews": [],
        "commits": [],
        "checks": [],
    }
    pr.update(overrides)
    return pr


class ReconcileSecurityTaggingTests(unittest.TestCase):
    def test_sentinel_title_alone_does_not_classify_as_security(self):
        """'Sentinel' is a Jules persona name, not a standalone security signal."""
        # Pathless intake: stays UNKNOWN, never SECURITY
        intake = reconcile.build_intake_item(_live_pr(), POLICY, NOW)
        self.assertEqual(intake["classification"], "UNKNOWN")
        self.assertEqual(intake["guardrail_outcome"], "NOT_RUN")

        # Non-sensitive paths + Sentinel title + .jules/sentinel.md journal: REFACTOR
        with_paths = _live_pr(
            changed_paths=[
                ".jules/sentinel.md",
                "scripts/export_comparison_sheets.py",
                "scripts/tests/test_export_comparison_sheets_security.py",
            ],
            diff_text=(
                "+++ b/scripts/export_comparison_sheets.py\n"
                "+logger.warning('Skipping invalid sheet %s', sheet_name)\n"
            ),
        )
        intake_with_paths = reconcile.build_intake_item(with_paths, POLICY, NOW)
        self.assertEqual(intake_with_paths["classification"], "REFACTOR")
        self.assertEqual(intake_with_paths["sensitive_paths"], [])
        self.assertEqual(intake_with_paths["guardrail_outcome"], "NOT_RUN")

    def test_sentinel_title_backed_by_security_path_or_diff_classifies_security(self):
        """A Sentinel/security title backed by sensitive paths or diff is SECURITY."""
        # Backed by production security module path
        by_path = _live_pr(
            changed_paths=[
                ".jules/sentinel.md",
                "src/hydrograph_seatek_analysis/utils/security.py",
            ]
        )
        self.assertEqual(reconcile.infer_pr_classification(by_path), "SECURITY")

        # Backed by path-traversal diff in an ordinary module path
        by_diff = _live_pr(
            changed_paths=[
                ".jules/sentinel.md",
                "scripts/batch_correction.py",
                "scripts/tests/test_batch_correction_security.py",
            ],
            diff_text=(
                "+++ b/scripts/batch_correction.py\n"
                "+resolved = os.path.realpath(target)\n"
                "+if os.path.commonpath([base_dir, resolved]) != base_dir:\n"
                "+    raise ValueError('Path traversal detected')\n"
            ),
        )
        self.assertEqual(reconcile.infer_pr_classification(by_diff), "SECURITY")

    def test_test_only_diff_patterns_do_not_back_security_classification(self):
        """Security keywords inside test files alone do not make a PR SECURITY."""
        test_only = _live_pr(
            changed_paths=[
                "Tests/RepoPromptTests/Security/MCPTerminalRecordSanitizationTests.swift"
            ],
            diff_text=(
                "+++ b/Tests/RepoPromptTests/Security/MCPTerminalRecordSanitizationTests.swift\n"
                '+func testRedaction() { let token = "ghp_123456" }\n'
            ),
        )
        self.assertEqual(reconcile.infer_pr_classification(test_only), "REFACTOR")

    def test_reconcile_emits_and_applies_reclassify_for_unbacked_sentinel_item(self):
        """Reconcile clears title-only SECURITY/REVIEW_SECURITY on unbacked BOT items."""
        item = reconcile_item(
            now=NOW,
            lifecycle_state="STAGE1_INTAKE",
            current_owner="stage1",
            next_owner="stage1",
            author_type="BOT",
            classification="SECURITY",
            risk_class="SENSITIVE",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="manual",
            sensitive_paths=["generated_output"],
            changed_paths=[
                ".jules/sentinel.md",
                "scripts/export_comparison_sheets.py",
                "scripts/tests/test_export_comparison_sheets_security.py",
            ],
            next_action=(
                "Stage 1 2026-10-17 AM: REVIEW_SECURITY "
                "(security-themed Sentinel title; Desk standing order)"
            ),
        )
        benign_diff = (
            "+++ b/scripts/export_comparison_sheets.py\n"
            "+logger.info('Exported %d rows', count)\n"
        )
        ledger = {"ledger_revision": 10, "items": [item], "events": []}
        with (
            mock.patch.object(reconcile, "_gh_pr_view", return_value=_OPEN_LIVE),
            mock.patch.object(reconcile, "_gh_pr_diff", return_value=benign_diff),
        ):
            actions = reconcile.collect_actions(ledger, {"lifecycle": {}}, now=NOW)
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["action"], "RECLASSIFY_TITLE_SECURITY")
        self.assertEqual(action["to_classification"], "REFACTOR")
        self.assertTrue(action["clear_review_security"])

        result = reconcile.apply_action_to_ledger(ledger, item, action)
        self.assertIsNone(result["event_id"])
        self.assertEqual(item["classification"], "REFACTOR")
        self.assertEqual(item["guardrail_outcome"], "PASS_ROUTINE")
        self.assertEqual(item["risk_class"], "ROUTINE")
        self.assertEqual(item["guardrail_source"], "path_eval")
        self.assertEqual(item["sensitive_paths"], [])
        self.assertEqual(item["revision"], 1)
        self.assertEqual(ledger["ledger_revision"], 11)

        with self.assertRaises(reconcile.ReconcileSkip):
            reconcile.apply_action_to_ledger(ledger, item, action)

    def test_reconcile_keeps_security_when_backed_or_fail_closed(self):
        """Items backed by paths/diff, missing paths, or human-held are never cleared."""
        backed_by_diff = reconcile_item(
            now=NOW,
            lifecycle_state="STAGE1_INTAKE",
            current_owner="stage1",
            next_owner="stage1",
            author_type="BOT",
            classification="SECURITY",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="manual",
            changed_paths=["scripts/batch_correction.py"],
            next_action="Stage 1 2026-10-17 AM: REVIEW_SECURITY (security-themed Sentinel title)",
        )
        traversal_diff = (
            "+++ b/scripts/batch_correction.py\n"
            "+if os.path.commonpath([base, os.path.realpath(p)]) != base:\n"
            "+    raise ValueError('Path traversal')\n"
        )
        with mock.patch.object(reconcile, "_gh_pr_diff", return_value=traversal_diff):
            self.assertIsNone(
                reconcile._security_tag_reconcile_action(backed_by_diff, _OPEN_LIVE)
            )

        # Missing diff lookup fails closed
        with mock.patch.object(reconcile, "_gh_pr_diff", return_value=None):
            self.assertIsNone(
                reconcile._security_tag_reconcile_action(backed_by_diff, _OPEN_LIVE)
            )

        # Empty changed_paths fails closed without calling _gh_pr_diff
        empty_paths = dict(backed_by_diff, changed_paths=[])
        with mock.patch.object(reconcile, "_gh_pr_diff") as diff_mock:
            self.assertIsNone(
                reconcile._security_tag_reconcile_action(empty_paths, _OPEN_LIVE)
            )
            diff_mock.assert_not_called()

        # Forced human hold is never touched
        forced = dict(
            backed_by_diff,
            next_action="HUMAN_HOLD (PR Desk list): explicit human decision required",
        )
        with mock.patch.object(reconcile, "_gh_pr_diff") as diff_mock:
            self.assertIsNone(
                reconcile._security_tag_reconcile_action(forced, _OPEN_LIVE)
            )
            diff_mock.assert_not_called()

    def test_reconcile_security_tagging_summary_counts_before_and_after(self):
        """Verify before/after summary counts on a mixed ledger fixture."""
        unbacked = reconcile_item(
            now=NOW,
            key=f"{REPO}#1@{'a' * 40}",
            pr=1,
            lifecycle_state="STAGE1_INTAKE",
            current_owner="stage1",
            author_type="BOT",
            classification="SECURITY",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="manual",
            changed_paths=[".jules/sentinel.md", "scripts/export_comparison_sheets.py"],
            diff_text="+++ b/scripts/export_comparison_sheets.py\n+log.info('ok')\n",
            next_action="Stage 1 2026-10-17 AM: REVIEW_SECURITY (security-themed Sentinel title)",
        )
        backed = reconcile_item(
            now=NOW,
            key=f"{REPO}#2@{'b' * 40}",
            pr=2,
            lifecycle_state="STAGE1_INTAKE",
            current_owner="stage1",
            author_type="BOT",
            classification="SECURITY",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="manual",
            changed_paths=[".jules/sentinel.md", "lib/safe_http.py"],
            next_action="Stage 1 2026-10-17 AM: REVIEW_SECURITY (security-themed Sentinel title)",
        )
        summary = guards.reconcile_security_tagging_summary(
            {"items": [unbacked, backed]}
        )
        self.assertEqual(summary["before_security_count"], 2)
        self.assertEqual(summary["after_security_count"], 1)
        self.assertEqual(summary["before_review_security_count"], 2)
        self.assertEqual(summary["after_review_security_count"], 1)
        self.assertEqual(summary["reclassified_count"], 1)
        self.assertEqual(summary["reclassified_items"][0]["pr"], 1)


if __name__ == "__main__":
    unittest.main()
