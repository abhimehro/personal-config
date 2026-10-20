"""Sentinel persona and sentinel/ branches stay a fixed REVIEW_SECURITY hold."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_reconcile_guards as guards  # noqa: E402
from tests.pr_lifecycle_helpers import (  # noqa: E402
    load_reconcile_with_stubs,
    reconcile_item,
)

reconcile = load_reconcile_with_stubs()
_OPEN_LIVE = {"state": "OPEN", "headRefOid": "a" * 40, "baseRefOid": "b" * 40}


def _security_item(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "lifecycle_state": "STAGE1_INTAKE",
        "current_owner": "stage1",
        "next_owner": "stage1",
        "classification": "SECURITY",
        "risk_class": "SENSITIVE",
        "guardrail_outcome": "REVIEW_SECURITY",
        "guardrail_source": "path_eval",
        "changed_paths": ["src/report.py"],
        "next_action": "Review Sentinel title",
    }
    fields.update(overrides)
    return reconcile_item(**fields)


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

    def test_closed_live_pr_and_frozen_outcome_are_not_held(self) -> None:
        item = _security_item()
        closed = self._open(
            state="MERGED",
            title="🛡️ Sentinel: [security improvement]",
            headRefName="sentinel/fix-loaders",
        )
        self.assertIsNone(reconcile._sentinel_hold_action(item, closed))
        frozen = _security_item(guardrail_outcome="HOLD_CONTRACT")
        live = self._open(
            title="🛡️ Sentinel: [security improvement]",
            headRefName="jules-1",
        )
        self.assertIsNone(reconcile._sentinel_hold_action(frozen, live))

    def test_hold_keeps_prior_next_action_and_skips_a_terminal_item(self) -> None:
        item = _security_item(next_action="HUMAN_HOLD: stay with the owner")
        live = self._open(
            title="🛡️ Sentinel: [security improvement]",
            headRefName="jules-1",
        )
        hold = reconcile._sentinel_hold_action(item, live)
        ledger = {"ledger_revision": 1, "items": [item], "events": []}
        reconcile.apply_action_to_ledger(ledger, item, hold)
        self.assertIn(guards.SENTINEL_HOLD_MARKER, item["next_action"])
        self.assertIn("HUMAN_HOLD: stay with the owner", item["next_action"])
        item["lifecycle_state"] = "TERMINAL"
        with self.assertRaises(reconcile.ReconcileSkip):
            reconcile._hold_sentinel_security_item(ledger, item, hold)

    def test_sentinel_hold_suppresses_stale_close(self) -> None:
        item = _security_item(
            lifecycle_state="WAITING_HUMAN",
            guardrail_outcome="PASS_ROUTINE",
            risk_class="ROUTINE",
        )
        live = self._open(
            title="🛡️ Sentinel: [security improvement]",
            headRefName="jules-1",
        )
        with mock.patch.object(reconcile, "_gh_pr_view", return_value=live):
            actions = reconcile._action_for_item(
                item, 7, datetime(2026, 10, 20, tzinfo=timezone.utc)
            )
        names = [action["action"] for action in actions]
        self.assertIn("HOLD_SENTINEL_SECURITY", names)
        self.assertNotIn("CLOSE_STALE", names)

    def test_hold_does_not_downgrade_human_review(self) -> None:
        item = _security_item(
            guardrail_outcome="NOT_RUN",
            risk_class="HUMAN_REVIEW",
        )
        live = self._open(
            title="🛡️ Sentinel: [security improvement]",
            headRefName="jules-1",
        )
        hold = reconcile._sentinel_hold_action(item, live)
        ledger = {"ledger_revision": 1, "items": [item], "events": []}
        reconcile.apply_action_to_ledger(ledger, item, hold)
        self.assertEqual(item["guardrail_outcome"], "REVIEW_SECURITY")
        self.assertEqual(item["risk_class"], "HUMAN_REVIEW")

    def test_package_name_sentinel_is_not_the_persona(self) -> None:
        item = _security_item(guardrail_source="path_eval", next_action="Review")
        live = self._open(
            title="Bump redis-sentinel from 4.0 to 5.0",
            headRefName="dependabot/pip/redis-sentinel-5.0",
        )
        self.assertFalse(
            guards.is_sentinel_security_pr(guards.sentinel_record(item, live))
        )
        self.assertIsNone(reconcile._sentinel_hold_action(item, live))


if __name__ == "__main__":
    unittest.main()
