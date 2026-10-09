"""Tests for code-enforced holds in the lifecycle unblock stage."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_unblock as unblock

from tests.pr_lifecycle_helpers import (
    UNBLOCK_REPO as REPO,
)
from tests.pr_lifecycle_helpers import (
    make_unblock_pr as _pr,
)
from tests.pr_lifecycle_helpers import (
    route_unblock_pr as _route,
)


class LedgerOwnerHoldTests(unittest.TestCase):
    """A non-stage1 ledger owner suppresses every automatic mutation."""

    def _stage_owned_item(self, owner: str, state: str) -> dict[str, object]:
        return {
            "key": f"{REPO}#1@{'a' * 40}",
            "repository": REPO,
            "pr": 1,
            "lifecycle_state": state,
            "current_owner": owner,
            "guardrail_outcome": "PASS_ROUTINE",
        }

    def test_stage3_owned_stale_lineage_keeps_only_escalations(self):
        """pc#2237/#2244 shape: stale docs lineage owned by stage3, not closed."""
        actions = _route(
            _pr(headRefName="pr-lifecycle-docs-20260919"),
            items=[self._stage_owned_item("stage3", "STAGE3_RECONCILIATION")],
        )
        self.assertTrue(actions)
        for action in actions:
            self.assertEqual("ESCALATE", action.get("action"))
        self.assertEqual("ledger_owned_by_stage3", actions[0]["blocker"])
        self.assertEqual("stage3", actions[0]["owner"])

    def test_stage2_owned_item_not_closed(self):
        """pc#2254 shape: stage2-queued item is immune to plain apply."""
        actions = _route(
            _pr(headRefName="pr-lifecycle-docs-20260921"),
            items=[self._stage_owned_item("stage2", "STAGE2_QUEUED")],
        )
        self.assertEqual("ledger_owned_by_stage2", actions[0]["blocker"])

    def test_human_owned_item_keeps_escalations(self):
        actions = _route(
            _pr(headRefName="pr-lifecycle-docs-20260920"),
            items=[self._stage_owned_item("human", "WAITING_HUMAN")],
        )
        self.assertEqual("ledger_owned_by_human", actions[0]["blocker"])
        self.assertEqual("human", actions[0]["owner"])

    def test_stage1_and_unowned_items_route_normally(self):
        for owner in ("stage1", "none"):
            actions = _route(
                _pr(headRefName="pr-lifecycle-docs-20260919"),
                items=[self._stage_owned_item(owner, "STAGE1_INTAKE")],
            )
            self.assertEqual("CLOSE_STALE_LINEAGE", actions[0]["action"], owner)

    def test_terminal_owner_does_not_hold(self):
        actions = _route(
            _pr(headRefName="pr-lifecycle-docs-20260919"),
            items=[self._stage_owned_item("stage3", "TERMINAL")],
        )
        self.assertEqual("CLOSE_STALE_LINEAGE", actions[0]["action"])


class ExclusionTests(unittest.TestCase):
    def test_normalize_exclusion_forms(self):
        normalize = unblock._normalize_exclusion
        self.assertEqual(("owner/repo", 123), normalize("owner/repo#123"))
        self.assertEqual(("repo", 123), normalize("repo#123"))
        self.assertEqual((None, 123), normalize("#123"))
        self.assertEqual((None, 123), normalize("123"))
        self.assertEqual(("owner/repo", 42), normalize(" Owner/Repo #42 "))
        for bad in ("", "abc", "repo#", "repo#abc", None, 42):
            with self.assertRaises((ValueError, TypeError)):
                normalize(bad)

    def test_is_excluded_matches_repo_and_number(self):
        excl = unblock._normalized_exclusions(["abhimehro/personal-config#2237"], None)
        pr = {"number": 2237}
        other = {"number": 2244}
        self.assertTrue(unblock._is_excluded("abhimehro/personal-config", pr, excl))
        self.assertFalse(unblock._is_excluded("abhimehro/other-repo", pr, excl))
        self.assertFalse(unblock._is_excluded("abhimehro/personal-config", other, excl))

    def test_short_and_repoless_forms(self):
        by_short = unblock._normalized_exclusions(["Seatek_Analysis#692"], None)
        by_number = unblock._normalized_exclusions(["1206"], None)
        pr = {"number": 692}
        self.assertTrue(unblock._is_excluded("abhimehro/Seatek_Analysis", pr, by_short))
        self.assertFalse(unblock._is_excluded("abhimehro/Other_Repo", pr, by_short))
        self.assertTrue(unblock._is_excluded("any/repo", {"number": 1206}, by_number))

    def test_config_exclusions_validated(self):
        from pr_lifecycle_config import validate_unblock_config

        validate_unblock_config({"exclusions": ["a/b#1"]})
        validate_unblock_config({"exclusions": ["#123", "123", " a/b # 42 "]})
        validate_unblock_config({"exclusions": None})
        validate_unblock_config(None)
        for bad in (
            ["a/b#1", 7],
            "a/b#1",
            [""],
            ["a/b#notanumber"],
            ["a/b#"],
            ["#"],
            ["a b#1"],
            ["a/b##1"],
            ["a/b#1x"],
        ):
            with self.assertRaises(ValueError):
                validate_unblock_config({"exclusions": bad})


class HumanCommentHoldTests(unittest.TestCase):
    """Bot comments never hold a stale-lineage close; human comments do."""

    def _comment(self, login: object, body: str = "x") -> dict:
        return {
            "author": {"login": login},
            "body": body,
            "createdAt": "2026-10-01T00:00:00Z",
        }

    def test_snyk_bot_comment_does_not_hold(self):
        """pc#2417 shape: a Snyk summary comment must not be a human hold."""
        actions = _route(
            _pr(
                headRefName="pr-lifecycle-docs-20260919",
                comments=[self._comment("snyk-bot")],
            )
        )
        self.assertEqual("CLOSE_STALE_LINEAGE", actions[0]["action"])

    def test_known_bots_do_not_hold(self):
        for login in (
            "cursor[bot]",
            "coderabbitai[bot]",
            "octopus-review[bot]",
            "app/cursor",
            "dependabot[bot]",
            "github-actions[bot]",
        ):
            actions = _route(
                _pr(
                    headRefName="pr-lifecycle-docs-20260919",
                    comments=[self._comment(login)],
                )
            )
            self.assertEqual("CLOSE_STALE_LINEAGE", actions[0]["action"], login)

    def test_machine_body_under_human_login_does_not_hold(self):
        """Snyk PR-check comments post as the repo owner — still machine output."""
        snyk_body = (
            "### :white_check_mark: **Snyk checks have passed. "
            "No issues have been found so far.** "
            "![](https://res.cloudinary.com/snyk/image/upload/x.svg)"
        )
        actions = _route(
            _pr(
                headRefName="pr-lifecycle-docs-20260919",
                comments=[self._comment("abhimehro", snyk_body)],
            )
        )
        self.assertEqual("CLOSE_STALE_LINEAGE", actions[0]["action"])

    def test_human_comment_holds_close(self):
        actions = _route(
            _pr(
                headRefName="pr-lifecycle-docs-20260919",
                comments=[self._comment("abhimehro", "please leave this open")],
            )
        )
        self.assertNotIn("CLOSE_STALE_LINEAGE", [a.get("action") for a in actions])

    def test_human_login_containing_bot_hint_holds(self):
        """devin-smith/kilopascal/linearity are humans, not bots."""
        for login in (
            "devin-smith",
            "kilopascal",
            "linearity",
            "trunkit",
            "julesverne",
        ):
            actions = _route(
                _pr(
                    headRefName="pr-lifecycle-docs-20260919",
                    comments=[self._comment(login)],
                )
            )
            self.assertNotIn(
                "CLOSE_STALE_LINEAGE", [a.get("action") for a in actions], login
            )

    def test_unreadable_author_and_incomplete_history_hold(self):
        for pr in (
            _pr(
                headRefName="pr-lifecycle-docs-20260919",
                comments=[self._comment(None), self._comment("")],
            ),
            _pr(
                headRefName="pr-lifecycle-docs-20260919",
                comments_incomplete=True,
            ),
        ):
            actions = _route(pr)
            self.assertNotIn("CLOSE_STALE_LINEAGE", [a.get("action") for a in actions])


if __name__ == "__main__":
    unittest.main()
