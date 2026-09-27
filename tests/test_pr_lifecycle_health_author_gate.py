#!/usr/bin/env python3
"""Pipeline health: reselect author-gate and title-gate identity checks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_pipeline_health as health  # noqa: E402

from tests.pr_lifecycle_helpers import (  # noqa: E402
    make_item,
    make_ledger,
    make_queryable_item,
)

ALLOWED_MAINTAINER = health.ReselectAuthorGate(allowed_authors=("maintainer",))
ALLOWED_REPO_OWNERS = health.ReselectAuthorGate(
    allowed_authors=("abhimehro", "google-labs-jules[bot]")
)


class TestReselectAuthorGate(unittest.TestCase):
    """Author allowlist resolution, precedence, and title-gate behavior."""

    def test_ledger_author_formats_and_precedence(self) -> None:
        """Verify author formats, fallback order, and rejection of missing logins."""
        cases = (
            ({"author": {"login": " maintainer "}}, True),
            ({"author": " maintainer "}, True),
            ({"author_login": " maintainer "}, True),
            ({"author": {"login": ""}, "author_login": "maintainer"}, True),
            ({"author": {"login": 12}, "author_login": "maintainer"}, True),
            ({"author": {"login": "outsider"}, "author_login": "maintainer"}, False),
            ({"author": "outsider", "author_login": "maintainer"}, False),
            ({"author_login": 12}, False),
            ({}, False),
        )
        for author_fields, expected in cases:
            with self.subTest(author_fields=author_fields):
                item = make_item(
                    author_type="HUMAN",
                    changed_paths=["src/demo.py"],
                    next_action="CONFLICTING",
                    **author_fields,
                )
                self.assertEqual(
                    health.is_reselect_salvage_candidate(
                        item,
                        live=health.LivePrSignals(title="chore(qa): add tests"),
                        author_gate=ALLOWED_MAINTAINER,
                    ),
                    expected,
                )

    def test_live_author_overrides_ledger_author_in_both_directions(self) -> None:
        """Verify live authors can grant or revoke title-based eligibility."""
        for ledger_author, live_author, expected in (
            ("maintainer", "outsider", False),
            ("outsider", "maintainer", True),
        ):
            with self.subTest(ledger_author=ledger_author, live_author=live_author):
                item = make_item(
                    author_type="HUMAN",
                    author=ledger_author,
                    changed_paths=["src/demo.py"],
                    next_action="CONFLICTING",
                )
                signals = health.ReselectSignals(
                    titles_by_key={item["key"]: "chore(qa): tests"},
                    author_login_by_key={item["key"]: live_author},
                )
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=signals,
                        author_gate=ALLOWED_MAINTAINER,
                    ),
                    [item] if expected else [],
                )

    def test_author_allowlist_reloads_between_batches_but_not_between_items(
        self,
    ) -> None:
        """Verify each candidate batch loads one fresh author allowlist."""
        items = [
            make_item(
                key=f"demo#{n}@abc",
                author_type="HUMAN",
                author="maintainer",
                changed_paths=["src/demo.py"],
                next_action="CONFLICTING",
            )
            for n in (1, 2)
        ]
        signals = health.ReselectSignals(
            titles_by_key={item["key"]: "chore(qa): tests" for item in items}
        )
        with mock.patch.object(
            health,
            "_load_reselect_allowed_authors",
            side_effect=[("maintainer",), ("other",)],
        ) as loader:
            self.assertEqual(
                health.list_reselect_candidates(
                    make_ledger(items, []), signals=signals
                ),
                items,
            )
            loader.assert_called_once_with()
            self.assertEqual(
                health.list_reselect_candidates(
                    make_ledger(items, []), signals=signals
                ),
                [],
            )
            self.assertEqual(loader.call_count, 2)

    def test_explicit_empty_allowlist_does_not_fall_back_to_config(self) -> None:
        """Verify an explicit empty allowlist rejects authors without loading config."""
        item = make_item(
            author_type="HUMAN",
            author="abhimehro",
            changed_paths=["src/demo.py"],
            next_action="CONFLICTING",
        )
        signals = health.ReselectSignals(titles_by_key={item["key"]: "⚡ Bolt: test"})
        with mock.patch.object(health, "_load_reselect_allowed_authors") as loader:
            self.assertEqual(
                health.list_reselect_candidates(
                    make_ledger([item], []),
                    signals=signals,
                    author_gate=health.ReselectAuthorGate(allowed_authors=()),
                ),
                [],
            )
            self.assertEqual(
                health.list_reselect_candidates(
                    make_ledger([item], []),
                    signals=signals,
                    author_gate=health.ReselectAuthorGate(enabled=False),
                ),
                [item],
            )
        loader.assert_not_called()

    def test_explicit_config_authors_take_precedence_over_disk(self) -> None:
        """Verify supplied author configuration avoids reading the disk config."""
        config = {
            "bot_authors": ["custom[bot]"],
            "identity_classification": {"maintainer_token_logins": ["maintainer"]},
        }
        with mock.patch.object(health, "load_yaml") as load:
            self.assertEqual(
                health._load_reselect_allowed_authors(config),
                ("custom[bot]", "maintainer"),
            )
        load.assert_not_called()

    def test_disk_allowlist_supports_bot_only_and_maintainer_only_config(self) -> None:
        """Verify disk config can supply either bots or maintainers independently."""
        cases = (
            (
                {"bot_authors": ["custom[bot]"], "identity_classification": []},
                ("custom[bot]",),
            ),
            (
                {
                    "identity_classification": {
                        "maintainer_token_logins": ["maintainer"]
                    }
                },
                ("maintainer",),
            ),
        )
        for config, expected in cases:
            with self.subTest(config=config), mock.patch.object(
                health, "CONFIG_PATH"
            ) as path, mock.patch.object(health, "load_yaml", return_value=config):
                path.is_file.return_value = True
                self.assertEqual(health._load_reselect_allowed_authors({}), expected)

    def _title_gated_item(self, **overrides: Any) -> dict[str, Any]:
        """Human-authored item that qualifies only via a live allowed title."""
        fields = {
            "key": "abhimehro/demo#1@abc1234",
            "author": "abhimehro",
            "author_type": "HUMAN",
            "changed_paths": ["src/demo.py"],
            "next_action": "HOLD_CONTRACT CONFLICTING unique remaining",
        }
        fields.update(overrides)
        return make_item(**fields)

    def test_title_gate_accepts_allowed_live_logins(self) -> None:
        """Allowed maintainer/bot logins pass; an arbitrary human login fails."""
        item = self._title_gated_item()
        title = "⚡ Bolt: fix something"
        for login, expected in (
            ("abhimehro", True),
            ("google-labs-jules[bot]", True),
            ("random-external-user", False),
        ):
            with self.subTest(login=login):
                self.assertEqual(
                    health.is_reselect_salvage_candidate(
                        item,
                        live=health.LivePrSignals(title=title, author_login=login),
                        author_gate=ALLOWED_REPO_OWNERS,
                    ),
                    expected,
                )

    def test_title_gate_falls_back_to_ledger_author_and_fails_closed(self) -> None:
        """Missing live logins fall back to the ledger author; none fails closed."""
        item = self._title_gated_item()
        title = "⚡ Bolt: fix something"
        # Missing login signal with maintainer in ledger -> candidate.
        for blank in (None, ""):
            self.assertTrue(
                health.is_reselect_salvage_candidate(
                    item,
                    live=health.LivePrSignals(title=title, author_login=blank),
                    author_gate=ALLOWED_REPO_OWNERS,
                )
            )
        # Missing login signal with an external human in ledger -> rejected.
        human_item = self._title_gated_item(author="random-external-user")
        for blank in (None, ""):
            self.assertFalse(
                health.is_reselect_salvage_candidate(
                    human_item,
                    live=health.LivePrSignals(title=title, author_login=blank),
                    author_gate=ALLOWED_REPO_OWNERS,
                )
            )
        # No login signal and no ledger author -> rejected (gate fails closed).
        anon_item = {k: v for k, v in item.items() if k != "author"}
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                anon_item,
                live=health.LivePrSignals(title=title, author_login=None),
                author_gate=ALLOWED_REPO_OWNERS,
            )
        )

    def test_title_gate_disabled_and_bot_bypass(self) -> None:
        """A disabled gate bypasses logins; ledger BOT items bypass everything."""
        item = self._title_gated_item()
        title = "⚡ Bolt: fix something"
        # Author gate disabled -> candidate even with a random human login.
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item,
                live=health.LivePrSignals(
                    title=title, author_login="random-external-user"
                ),
                author_gate=health.ReselectAuthorGate(enabled=False),
            )
        )
        # Ledger-BOT item bypasses author gate and title check.
        bot_item = self._title_gated_item(
            key="abhimehro/demo#2@abc1234", author_type="BOT"
        )
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                bot_item,
                live=health.LivePrSignals(
                    title="non-matching title", author_login="random-user"
                ),
            )
        )

    def test_plausible_defers_identity_without_loading_config(self) -> None:
        """is_reselect_plausible keeps login-less items for the live lookup.

        A nonblank live author login wins over the ledger record, so the
        pre-query gate cannot disprove authorship and never loads the
        allowlist — the selector applies it once live signals exist.
        """
        for item in (
            make_queryable_item(author_type="HUMAN"),
            make_queryable_item(author_type="HUMAN", author="maintainer"),
            make_queryable_item(author_type="HUMAN", author="random-external-user"),
        ):
            with self.subTest(item=item["key"]):
                with mock.patch.object(
                    health,
                    "_load_reselect_allowed_authors",
                    side_effect=AssertionError("loader must not run"),
                ) as loader:
                    self.assertTrue(health.is_reselect_plausible(item))
                loader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
