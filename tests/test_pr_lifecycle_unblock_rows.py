"""Unit tests for repository-scoped unblock backlog rows and deadlines."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_unblock_rows as rows

REPO = "owner/repo"


def human_item(**overrides):
    """Build a minimal nonterminal ledger item awaiting a human decision."""
    return {
        "repository": REPO,
        "pr": 23,
        "url": f"https://github.com/{REPO}/pull/23",
        "lifecycle_state": "WAITING_HUMAN",
        "current_owner": "human",
        "updated_at_utc": "2026-10-01T12:00:00Z",
        "next_action": "Review the changes.",
        **overrides,
    }


class UnblockRowsTests(unittest.TestCase):
    def test_rows_select_human_and_security_items_only_in_requested_repo(self):
        ledger = {
            "items": [
                human_item(),
                human_item(
                    pr=24, current_owner="stage3", guardrail_outcome="REVIEW_SECURITY"
                ),
                human_item(
                    pr=25,
                    lifecycle_state="TERMINAL",
                    guardrail_outcome="REVIEW_SECURITY",
                ),
                human_item(pr=26, current_owner="stage2"),
                human_item(pr=27, repository="owner/other"),
                None,
            ]
        }
        actions = [
            {"action": "ESCALATE", "repository": REPO, "pr": 28, "owner": "stage2"},
            {"action": "ESCALATE", "repository": "owner/other", "pr": 29},
            {"action": "TRIGGER", "repository": REPO, "pr": 30},
        ]
        before = copy.deepcopy((ledger, actions))
        result = rows._rows_for_repo(REPO, actions, ledger, 3)
        self.assertEqual([row["pr"] for row in result], [23, 24, 28])
        self.assertEqual([row["owner"] for row in result], ["human", "human", "stage2"])
        self.assertTrue(all(row["packet_expiry_close_days"] == 3 for row in result))
        self.assertEqual((ledger, actions), before)

    def test_explicit_deadline_overrides_age_even_beyond_displayed_evidence(self):
        item = human_item(next_action="x" * 220 + " Expires 2026-10-20T12:00:00Z")
        row = rows._human_ledger_rows(REPO, {"items": [item]}, 3)[0]
        self.assertEqual(row["expires"], "2026-10-20T12:00:00Z")
        self.assertEqual(row["evidence"], "x" * 200)
        self.assertEqual(row["recommended_action"], "x" * 200)
        self.assertEqual(row["blocker"], "human_decision")
        self.assertEqual(
            row["safe_default"],
            "Leave open; no merge or close without a human decision.",
        )

    def test_derived_deadline_normalizes_timezone_and_handles_missing_age(self):
        for updated, expected in (
            ("2026-10-01T14:00:00+02:00", "2026-10-04T12:00:00Z"),
            ("2026-10-01T12:00:00", "2026-10-04T12:00:00Z"),
            (None, None),
            ("not a date", None),
        ):
            with self.subTest(updated=updated):
                item = human_item(updated_at_utc=updated, safe_default="Keep open.")
                row = rows._human_ledger_rows(REPO, {"items": [item]}, 3)[0]
                self.assertEqual(row["expires"], expected)
                self.assertEqual(row["safe_default"], "Keep open.")

    def test_counts_keep_empty_repositories_and_ignore_foreign_actions(self):
        result = rows._repo_counts(
            [
                {"repository": REPO, "action": "ESCALATE", "blocker": "conflict"},
                {"repository": REPO, "action": "ESCALATE", "blocker": "conflict"},
                {"repository": REPO, "blocker": ""},
                {
                    "repository": "owner/foreign",
                    "action": "TRIGGER",
                    "blocker": "checks",
                },
            ],
            [REPO, "owner/empty"],
        )
        self.assertEqual(
            result,
            {
                REPO: {
                    "by_action": {"ESCALATE": 2, "UNKNOWN": 1},
                    "by_blocker": {"conflict": 2},
                },
                "owner/empty": {"by_action": {}, "by_blocker": {}},
            },
        )


if __name__ == "__main__":
    unittest.main()
