"""Tests for open Octopus review-thread findings routing to escalation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pr_lifecycle_inventory_norm import _normalize_pr

from tests.pr_lifecycle_helpers import (
    make_inventory_pr,
    make_unblock_pr,
    route_unblock_pr,
)


def _thread(
    login: str,
    typename: str = "Bot",
    *,
    resolved: bool = False,
    outdated: bool = False,
) -> dict:
    """Build one review-thread node authored by the given login."""
    return {
        "isResolved": resolved,
        "isOutdated": outdated,
        "comments": {"nodes": [{"author": {"login": login, "__typename": typename}}]},
    }


def _with_threads(raw: dict, threads: list, *, has_next: bool = False) -> dict:
    """Attach a reviewThreads connection to a raw inventory PR fixture."""
    raw["reviewThreads"] = {
        "pageInfo": {"hasNextPage": has_next},
        "nodes": threads,
    }
    return raw


class OctopusFindingsTests(unittest.TestCase):
    def test_only_open_octopus_threads_count(self) -> None:
        """Count only unresolved, current threads authored by the Octopus bot."""
        raw = _with_threads(
            make_inventory_pr(),
            [
                _thread("octopus-review"),
                _thread("octopus-review", resolved=True),
                _thread("octopus-review", outdated=True),
                _thread("kilo-code-bot"),
                _thread("coderabbitai"),
                _thread("reviewer", "User"),
            ],
        )
        self.assertEqual(_normalize_pr(raw, "owner/repo")["openOctopusFindings"], 1)

    def test_truncated_thread_page_reports_findings_unknown(self) -> None:
        """Treat incomplete review-thread pagination as an unknown finding count."""
        raw = _with_threads(make_inventory_pr(), [], has_next=True)
        self.assertIsNone(_normalize_pr(raw, "owner/repo")["openOctopusFindings"])

    def test_absent_or_malformed_threads_fail_closed(self) -> None:
        """Reject inventory whose review threads are missing or malformed."""
        absent = make_inventory_pr()
        absent.pop("reviewThreads")
        for raw in (
            absent,
            _with_threads(make_inventory_pr(), [{"isResolved": None}]),
        ):
            with self.subTest(raw=raw), self.assertRaises(OSError):
                _normalize_pr(raw, "owner/repo")

    def test_empty_threads_normalize_to_zero(self) -> None:
        """Normalize a complete, empty review-thread connection to zero findings."""
        self.assertEqual(
            _normalize_pr(make_inventory_pr(), "owner/repo")["openOctopusFindings"],
            0,
        )

    def test_open_findings_escalate_to_the_decision_issue(self) -> None:
        """Escalate open findings to a human with evidence and a safe default."""
        actions = route_unblock_pr(make_unblock_pr(openOctopusFindings=3))
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["action"], "ESCALATE")
        self.assertEqual(action["blocker"], "open_octopus_findings")
        self.assertEqual(action["owner"], "human")
        self.assertEqual(action["evidence"], {"open_octopus_findings": 3})
        self.assertIn(
            "no merge or close without a human decision", action["safe_default"]
        )

    def test_unknown_findings_escalate_fail_closed(self) -> None:
        """Escalate an unknown finding count with explicit unknown evidence."""
        actions = route_unblock_pr(make_unblock_pr(openOctopusFindings=None))
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["blocker"], "open_octopus_findings")
        self.assertEqual(actions[0]["evidence"], {"open_octopus_findings": "unknown"})

    def test_zero_findings_emit_no_action(self) -> None:
        """Leave an otherwise unblocked PR with zero findings without actions."""
        self.assertEqual(route_unblock_pr(make_unblock_pr()), [])

    def test_findings_escalate_alongside_other_blockers(self) -> None:
        """Preserve the branch-update action when findings also need escalation."""
        actions = route_unblock_pr(
            make_unblock_pr(openOctopusFindings=2, mergeStateStatus="BEHIND")
        )
        blockers = {a.get("blocker") for a in actions}
        self.assertGreaterEqual(len(actions), 2)
        self.assertIn("open_octopus_findings", blockers)
        self.assertTrue(
            any(a.get("action") == "UPDATE_BRANCH" for a in actions),
            "expected the BEHIND update-branch action to fire alongside",
        )

    def test_findings_suppress_automatic_close(self) -> None:
        """A stale-lineage PR with findings escalates instead of auto-closing."""
        actions = route_unblock_pr(
            make_unblock_pr(
                headRefName="pr-lifecycle-docs-20261001-run",
                openOctopusFindings=1,
            )
        )
        self.assertFalse(
            any(str(a.get("action") or "").startswith("CLOSE") for a in actions),
            "open findings must suppress automatic close actions",
        )
        self.assertTrue(
            any(a.get("blocker") == "open_octopus_findings" for a in actions)
        )

    def test_findings_kept_with_conflict_routing(self) -> None:
        actions = route_unblock_pr(
            make_unblock_pr(openOctopusFindings=2, mergeable="CONFLICTING")
        )
        self.assertGreaterEqual(len(actions), 2)
        self.assertTrue(
            any(a.get("blocker") == "open_octopus_findings" for a in actions)
        )
        self.assertTrue(
            any(a.get("blocker") in (None, "merge_conflict") for a in actions),
            "expected the conflict route to fire alongside the escalation",
        )

    def test_unverifiable_thread_author_fails_closed(self) -> None:
        raw = _with_threads(
            make_inventory_pr(),
            [
                {
                    "isResolved": False,
                    "isOutdated": False,
                    "comments": {"nodes": [{"author": None}]},
                }
            ],
        )
        with self.assertRaises(OSError):
            _normalize_pr(raw, "owner/repo")


if __name__ == "__main__":
    unittest.main()
