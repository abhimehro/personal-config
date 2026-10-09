"""Trigger marker authorship and bot-family fork guards for unblock routing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from tests.pr_lifecycle_helpers import (
    make_unblock_pr as _pr,
)
from tests.pr_lifecycle_helpers import (
    route_unblock_pr as _route,
)


class TriggerMarkerGuardsTests(unittest.TestCase):
    def test_cross_repo_coderabbit_branch_is_escalated_not_triggered(self):
        """A fork PR cannot claim the coderabbit family via a branch prefix."""
        action = _route(
            _pr(
                headRefName="coderabbit-fixes",
                mergeable="CONFLICTING",
                isCrossRepository=True,
                author={"login": "random-bot[bot]", "type": "Bot"},
            ),
        )[0]
        self.assertEqual(action["action"], "ESCALATE")

    def test_same_repo_coderabbit_branch_still_routes_fixer(self):
        """Same-repo coderabbit-prefixed branches keep the fixer family."""
        action = _route(
            _pr(
                headRefName="coderabbit-fixes",
                mergeable="CONFLICTING",
                author={"login": "random-bot[bot]", "type": "Bot"},
            ),
        )[0]
        self.assertEqual(action["action"], "TRIGGER")
        self.assertEqual(action["kind"], "coderabbit_conflict")

    def test_marker_from_untrusted_author_does_not_suppress_trigger(self):
        """Only owner-authored trigger markers dedupe; anyone else is ignored."""
        marker = f"<!-- pr-lifecycle-trigger kind=dependabot_rebase head={'a' * 40} -->"
        for comment in (
            {
                "author": {"login": "rando"},
                "body": marker,
                "createdAt": "2026-10-09T00:00:00Z",
            },
            {"body": marker, "createdAt": "2026-10-09T00:00:00Z"},
        ):
            with self.subTest(author=comment.get("author")):
                actions = _route(
                    _pr(
                        author={"login": "dependabot[bot]", "type": "Bot"},
                        mergeStateStatus="BEHIND",
                        comments=[comment],
                    )
                )
                self.assertEqual(actions[0]["action"], "TRIGGER")


    def test_codescene_not_triggered_on_fork_pr(self):
        """A fork PR never receives the push-capable /cs-agent trigger."""
        pr = _pr(
            isCrossRepository=True,
            checks=[{"name": "CodeScene quality gate", "state": "FAILURE"}],
        )
        actions = _route(pr, author_type="HUMAN")
        self.assertNotIn("TRIGGER", [a["action"] for a in actions])

    def test_not_run_ledger_item_blocks_triggers_until_guardrails_run(self):
        """Freshly ingested NOT_RUN items escalate instead of triggering."""
        item = {
            "key": f"abhimehro/personal-config#23@{'a' * 40}",
            "lifecycle_state": "STAGE1_INTAKE",
            "guardrail_outcome": "NOT_RUN",
        }
        pr = _pr(
            author={"login": "dependabot[bot]", "type": "Bot"},
            mergeStateStatus="BEHIND",
        )
        actions = _route(pr, items=[item])
        self.assertNotIn("TRIGGER", [a["action"] for a in actions])
        self.assertEqual(actions[0]["action"], "ESCALATE")


if __name__ == "__main__":
    unittest.main()
