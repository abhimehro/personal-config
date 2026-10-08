"""Unit tests for non-human escalation handoffs on the backlog issue."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_issue_status as issue_status

from tests.pr_lifecycle_helpers import NOW


class Stage2HandoffTests(unittest.TestCase):
    """Non-human escalation rows render as handoffs, never as overdue work."""

    def test_stage2_rows_render_in_handoff_section_and_never_overdue(self):
        """Non-human escalations list under Stage 2 handoffs without a deadline."""
        rows = [
            {"pr": 42, "blocker": "conflict", "owner": "stage2"},
            {"pr": 43, "blocker": "security", "owner": "human"},
        ]
        prepared, state, overdue = issue_status._prepare_backlog_rows(
            "owner/repo", rows, {}, NOW
        )
        by_pr = {row["pr"]: row for row in prepared}
        self.assertFalse(by_pr[42]["overdue"])
        self.assertEqual(by_pr[42]["expires"], "—")
        self.assertEqual(overdue, [])
        self.assertEqual(state["overdue_notified"], [])
        body = issue_status.backlog_issue_body("owner/repo", rows, {}, NOW)
        self.assertIn("Stage 2 handoffs", body)
        self.assertIn("| stage2 |", body)

    def test_ownerless_rows_stay_on_the_human_table(self):
        """A row without an owner still gets a real expiry and can go overdue."""
        row = {"pr": 42, "blocker": "conflict", "expires": "2026-08-01T00:00:00Z"}
        prepared, _, overdue = issue_status._prepare_backlog_rows(
            "owner/repo", [row], {}, NOW
        )
        self.assertTrue(prepared[0]["overdue"])
        self.assertEqual(len(overdue), 1)


if __name__ == "__main__":
    unittest.main()
