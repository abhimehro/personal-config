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
        raw = _with_threads(make_inventory_pr(), [], has_next=True)
        self.assertIsNone(_normalize_pr(raw, "owner/repo")["openOctopusFindings"])

    def test_absent_or_malformed_threads_fail_closed(self) -> None:
        absent = make_inventory_pr()
        absent.pop("reviewThreads")
        for raw in (
            absent,
            _with_threads(make_inventory_pr(), [{"isResolved": None}]),
        ):
            with self.subTest(raw=raw), self.assertRaises(OSError):
                _normalize_pr(raw, "owner/repo")

    def test_empty_threads_normalize_to_zero(self) -> None:
        self.assertEqual(
            _normalize_pr(make_inventory_pr(), "owner/repo")["openOctopusFindings"],
            0,
        )

    def test_open_findings_escalate_to_the_decision_issue(self) -> None:
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
        actions = route_unblock_pr(make_unblock_pr(openOctopusFindings=None))
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["blocker"], "open_octopus_findings")
        self.assertEqual(actions[0]["evidence"], {"open_octopus_findings": "unknown"})

    def test_zero_findings_emit_no_action(self) -> None:
        self.assertEqual(route_unblock_pr(make_unblock_pr()), [])

    def test_findings_escalate_alongside_other_blockers(self) -> None:
        actions = route_unblock_pr(
            make_unblock_pr(
                openOctopusFindings=2,
                mergeStateStatus="BEHIND",
                author_type="BOT",
            )
        )
        blockers = {a.get("blocker") for a in actions}
        self.assertIn("open_octopus_findings", blockers)


if __name__ == "__main__":
    unittest.main()
