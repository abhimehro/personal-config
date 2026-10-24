"""Hold markers and live-head checks for stale reconcile closes."""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pr_lifecycle_config import (  # noqa: E402
    is_excluded,
    normalize_exclusions,
)
from tests.pr_lifecycle_helpers import (  # noqa: E402
    load_reconcile_with_stubs,
    reconcile_item,
)

reconcile = load_reconcile_with_stubs()
NOW = datetime(2026, 10, 21, 18, 0, tzinfo=timezone.utc)
HEAD_SHA = "a" * 40
MOVED_SHA = "c" * 40
_OPEN_LIVE = {"state": "OPEN", "headRefOid": HEAD_SHA}


def _item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "key": "abhimehro/personal-config#99@" + HEAD_SHA,
        "repository": "abhimehro/personal-config",
        "pr": 99,
        "lifecycle_state": "WAITING_HUMAN",
        "author_type": "BOT",
        "current_owner": "human",
        "guardrail_outcome": "NOT_RUN",
        "changed_paths": ["README.md"],
        "updated_at_utc": "2026-09-01T00:00:00Z",
        "head_sha": HEAD_SHA,
    }
    base.update(overrides)
    return reconcile_item(now=NOW, **base)


def _classify(
    item_overrides: dict[str, object] | None = None,
    *,
    exclusions: frozenset[tuple[str | None, int]] = frozenset(),
):
    return reconcile._classify_stale(
        _item(**(item_overrides or {})),
        expiry_days=7,
        now=NOW,
        key="abhimehro/personal-config#99@" + HEAD_SHA,
        exclusions=exclusions,
    )


class ExclusionNormalizationTests(unittest.TestCase):
    def test_public_exclusion_helpers_preserve_forms_and_repo_matching(self) -> None:
        exclusions = normalize_exclusions(
            ["Owner/Repo#99", "REPO#100"], ["#101", "102"]
        )
        self.assertEqual(
            frozenset(
                {
                    ("owner/repo", 99),
                    ("repo", 100),
                    (None, 101),
                    (None, 102),
                }
            ),
            exclusions,
        )
        self.assertTrue(is_excluded("OWNER/REPO", 99, exclusions))
        self.assertTrue(is_excluded("owner/repo", 100, exclusions))
        self.assertTrue(is_excluded("another/project", 101, exclusions))
        self.assertFalse(is_excluded("another/project", 99, exclusions))


class StaleCloseHoldTests(unittest.TestCase):
    def test_human_review_repro_is_held(self) -> None:
        item = _item(
            risk_class="HUMAN_REVIEW",
            author_type="BOT",
            current_owner="human",
            guardrail_outcome="HOLD_CONTRACT",
            guardrail_source="manual",
            classification="SECURITY",
        )
        self.assertEqual(
            "human_review",
            reconcile.guards.stale_close_hold_reason(item, frozenset()),
        )
        self.assertIsNone(
            _classify(
                {
                    "risk_class": "HUMAN_REVIEW",
                    "guardrail_outcome": "HOLD_CONTRACT",
                    "guardrail_source": "manual",
                    "classification": "SECURITY",
                    "current_owner": "human",
                }
            )
        )

    def test_all_hold_outcomes_and_security_classification_are_held(self) -> None:
        for outcome in (
            "REVIEW_SECURITY",
            "HOLD_CONTRACT",
            "HOLD_CANONICAL",
            "HOLD_PLATFORM",
        ):
            with self.subTest(outcome=outcome):
                self.assertIsNone(_classify({"guardrail_outcome": outcome}))
        self.assertEqual(
            "classification_security",
            reconcile.guards.stale_close_hold_reason(
                _item(classification="SECURITY"), frozenset()
            ),
        )
        self.assertIsNone(_classify({"classification": "SECURITY"}))

    def test_protected_sources_and_forced_hold_notes_are_held(self) -> None:
        for source in ("manual", "review", "human", "octopus"):
            with self.subTest(source=source):
                item = _item(guardrail_source=source)
                self.assertEqual(
                    f"protected_source:{source}",
                    reconcile.guards.stale_close_hold_reason(item, frozenset()),
                )
                self.assertIsNone(_classify({"guardrail_source": source}))
        for note in (
            "HUMAN_HOLD: await review",
            "PR Desk forced hold for evidence",
        ):
            with self.subTest(note=note):
                item = _item(next_action=note)
                self.assertEqual(
                    "forced_hold_note",
                    reconcile.guards.stale_close_hold_reason(item, frozenset()),
                )
                self.assertIsNone(_classify({"next_action": note}))

    def test_repository_and_repo_less_exclusions_hold_stale_close(self) -> None:
        for exclusion in (
            "abhimehro/personal-config#99",
            "personal-config#99",
            "#99",
        ):
            with self.subTest(exclusion=exclusion):
                parsed = normalize_exclusions([exclusion])
                self.assertEqual(
                    "excluded",
                    reconcile.guards.stale_close_hold_reason(_item(), parsed),
                )
                self.assertIsNone(_classify(exclusions=parsed))

    def test_plain_expired_bot_closes_with_item_head_even_when_human_owned(
        self,
    ) -> None:
        for outcome in ("NOT_RUN", "PASS_ROUTINE"):
            with self.subTest(outcome=outcome):
                action = _classify({"guardrail_outcome": outcome})
                self.assertEqual("CLOSE_STALE", action["action"])
                self.assertEqual(HEAD_SHA, action["head_sha"])

    def test_human_authored_and_fresh_items_do_not_close(self) -> None:
        self.assertIsNone(_classify({"author_type": "HUMAN"}))
        self.assertIsNone(_classify({"updated_at_utc": "2026-10-19T00:00:00Z"}))

    def test_collect_actions_uses_configured_exclusions(self) -> None:
        item = _item()
        ledger = {"items": [item]}
        config = {
            "lifecycle": {
                "packet_expiry_close_days": 7,
                "unblock": {"exclusions": ["personal-config#99"]},
            }
        }
        live = {
            **_OPEN_LIVE,
            "baseRefOid": "b" * 40,
        }
        with mock.patch.object(reconcile, "_gh_pr_view", return_value=live):
            actions = reconcile.collect_actions(ledger, config, now=NOW)
        self.assertNotIn("CLOSE_STALE", [action["action"] for action in actions])


class LiveHeadCloseTests(unittest.TestCase):
    def _action(self) -> dict[str, object]:
        return {
            "action": "CLOSE_STALE",
            "key": "abhimehro/personal-config#99@" + HEAD_SHA,
            "repository": "owner/repo",
            "pr": 99,
            "head_sha": HEAD_SHA,
        }

    def test_missing_closed_and_moved_live_prs_skip_mutations(self) -> None:
        cases = (
            (None, "skip github close: live PR view unavailable"),
            (
                {"state": "CLOSED", "headRefOid": HEAD_SHA},
                "skip github close: live PR is not OPEN",
            ),
            (
                {"state": "OPEN", "headRefOid": MOVED_SHA},
                "skip github close: live head SHA changed",
            ),
        )
        for live, expected_step in cases:
            with self.subTest(live=live):
                with (
                    mock.patch.object(reconcile, "_gh_pr_view", return_value=live),
                    mock.patch.object(reconcile.subprocess, "run") as command,
                ):
                    steps, closed = reconcile._close_stale_github(self._action())
                self.assertEqual([expected_step], steps)
                self.assertFalse(closed)
                command.assert_not_called()

    def test_matching_live_head_runs_comment_label_close_and_confirmation(self) -> None:
        views = [
            {"state": "OPEN", "headRefOid": HEAD_SHA},
            {"state": "CLOSED", "headRefOid": HEAD_SHA},
        ]
        commands = [
            types.SimpleNamespace(returncode=0),
            types.SimpleNamespace(returncode=1),
            types.SimpleNamespace(returncode=0),
        ]
        with (
            mock.patch.object(reconcile, "_gh_pr_view", side_effect=views),
            mock.patch.object(
                reconcile.subprocess, "run", side_effect=commands
            ) as command,
        ):
            steps, closed = reconcile._close_stale_github(self._action())
        self.assertEqual(
            ["comment exit=0", "label exit=1", "close exit=0", "confirm=closed"],
            steps,
        )
        self.assertTrue(closed)
        self.assertEqual(
            [call.args[0][2] for call in command.call_args_list],
            ["comment", "edit", "close"],
        )

    def test_unconfirmed_live_head_skip_keeps_apply_item_nonterminal(self) -> None:
        item = _item()
        action = self._action()
        ledger = {"ledger_revision": 0, "events": [], "items": [item]}
        items_by_key = {item["key"]: item}
        with (
            mock.patch.object(
                reconcile,
                "_gh_pr_view",
                return_value={"state": "OPEN", "headRefOid": MOVED_SHA},
            ),
            mock.patch.object(reconcile.subprocess, "run") as command,
        ):
            result = reconcile._apply_one(ledger, action, items_by_key)
        self.assertIsNone(result)
        self.assertEqual("WAITING_HUMAN", item["lifecycle_state"])
        self.assertEqual([], ledger["events"])
        self.assertTrue(action["close_unconfirmed"])
        command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
