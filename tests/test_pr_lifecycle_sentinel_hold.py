"""Sentinel persona and sentinel/ branches stay a fixed REVIEW_SECURITY hold."""

from __future__ import annotations

import unittest
from unittest import mock

from tests.test_pr_lifecycle_reconcile_security_tagging import (
    _OPEN_LIVE,
    _security_item,
    guards,
    reconcile,
)


class SentinelFixedHoldTests(unittest.TestCase):
    """Sentinel persona and sentinel/ branches stay REVIEW_SECURITY."""

    def _open(self, **overrides):
        live = dict(_OPEN_LIVE)
        live.update(overrides)
        return live

    def test_persona_and_sentinel_branch_are_not_title_cleared(self):
        item = _security_item(
            changed_paths=["src/report.py"],
            guardrail_source="path_eval",
            next_action="Review",
        )
        benign = "+++ b/src/report.py\n+log.info(1)\n"
        cases = (
            {"title": "🛡️ Sentinel: [security improvement]", "headRefName": "jules-1"},
            {"title": "chore: format", "headRefName": "sentinel/fix-loaders"},
            {"title": "🛡️ Sentinel: tests", "headRefName": "sentinel-redact"},
        )
        for live_fields in cases:
            with self.subTest(live=live_fields):
                live = self._open(**live_fields)
                with mock.patch.object(reconcile, "_gh_pr_diff", return_value=benign):
                    self.assertIsNone(
                        reconcile._security_tag_reconcile_action(item, live)
                    )
                self.assertIsNone(
                    guards.evaluate_security_tag_reconcile(
                        guards.sentinel_record(item, live), diff_text=benign
                    )
                )

    def test_non_sentinel_security_title_can_still_clear(self):
        item = _security_item(guardrail_source="path_eval", next_action="Review")
        live = self._open(title="chore: security patch notes", headRefName="feat/notes")
        benign = "+++ b/src/report.py\n+log.info(1)\n"
        with mock.patch.object(reconcile, "_gh_pr_diff", return_value=benign):
            action = reconcile._security_tag_reconcile_action(item, live)
        self.assertEqual(action["action"], "RECLASSIFY_TITLE_SECURITY")
        self.assertTrue(action["clear_review_security"])

    def test_named_sentinel_prs_stay_or_return_to_review_security(self):
        """series#468/#489/#605 and rpce#368/#471 cannot be cleared."""
        named = (
            (
                "abhimehro/series_correction_project_updated",
                468,
                "sentinel/fix-loaders-file-not-found",
                "🛡️ Sentinel: [security improvement]",
            ),
            (
                "abhimehro/series_correction_project_updated",
                489,
                "sentinel/fix-exception-handling",
                "🛡️ Sentinel: [security improvement]",
            ),
            (
                "abhimehro/series_correction_project_updated",
                605,
                "sentinel/fix-cwe-209-logging",
                "🛡️ Sentinel: [security improvement]",
            ),
            (
                "abhimehro/repoprompt-ce",
                368,
                "jules-5632834899674527241-a9225959",
                "🛡️ Sentinel: Unit tests for staged release extraction",
            ),
            (
                "abhimehro/repoprompt-ce",
                471,
                "mcp-terminal-record-sanitization-tests",
                "🛡️ Sentinel: [security improvement] Add test coverage",
            ),
        )
        benign = "+++ b/src/report.py\n+log.info(1)\n"
        for repo, number, branch, title in named:
            with self.subTest(pr=f"{repo}#{number}"):
                item = _security_item(
                    repository=repo,
                    pr=number,
                    key=f"{repo}#{number}@{'a' * 40}",
                    guardrail_source="path_eval",
                    guardrail_outcome="PASS_ROUTINE",
                    risk_class="ROUTINE",
                    classification="REFACTOR",
                    next_action="title-only tag cleared",
                )
                live = self._open(title=title, headRefName=branch)
                self.assertTrue(
                    guards.is_sentinel_security_pr(guards.sentinel_record(item, live))
                )
                with mock.patch.object(reconcile, "_gh_pr_diff", return_value=benign):
                    self.assertIsNone(
                        reconcile._security_tag_reconcile_action(item, live)
                    )
                    hold = reconcile._sentinel_hold_action(item, live)
                self.assertEqual(hold["action"], "HOLD_SENTINEL_SECURITY")
                ledger = {"ledger_revision": 3, "items": [item], "events": []}
                reconcile.apply_action_to_ledger(ledger, item, hold)
                self.assertEqual(item["guardrail_outcome"], "REVIEW_SECURITY")
                self.assertEqual(item["risk_class"], "SENSITIVE")
                self.assertEqual(item["classification"], "REFACTOR")
                self.assertIn(guards.SENTINEL_HOLD_MARKER, item["next_action"])
                with mock.patch.object(reconcile, "_gh_pr_diff", return_value=benign):
                    self.assertIsNone(
                        reconcile._security_tag_reconcile_action(item, live)
                    )


if __name__ == "__main__":
    unittest.main()
