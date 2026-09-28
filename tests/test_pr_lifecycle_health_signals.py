#!/usr/bin/env python3
"""Pipeline health: live signal overrides for reselect candidacy.

Covers title/mergeable/path/head/base signal semantics — which live signals
override ledger values, which exclude, and which merely refresh anchors.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_pipeline_health as health  # noqa: E402

from tests.pr_lifecycle_helpers import (  # noqa: E402
    make_item,
    make_ledger,
)

ALLOWED_MAINTAINER = health.ReselectAuthorGate(allowed_authors=("maintainer",))
NO_AUTHORS = health.ReselectAuthorGate(allowed_authors=())


class TestLiveSignalOverrides(unittest.TestCase):
    """Title, path, mergeable, and SHA signals vs. ledger fallbacks."""

    def test_exact_title_signal_overrides_prefix_even_when_empty(self) -> None:
        """Verify exact-key titles override PR prefixes, including empty titles."""
        item = make_item(
            author_type="HUMAN",
            author_login="maintainer",
            next_action="CONFLICTING",
            changed_paths=["src/demo.py"],
        )
        prefix = "abhimehro/demo#1"
        cases = (
            ({prefix: "chore(qa): tests"}, True),
            ({prefix: "chore(qa): tests", item["key"]: ""}, False),
            ({prefix: "chore(qa): tests", item["key"]: "feat: unrelated"}, False),
            ({prefix: "feat: unrelated", item["key"]: "chore(qa): tests"}, True),
        )
        for titles, expected in cases:
            with self.subTest(titles=titles):
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=health.ReselectSignals(titles_by_key=titles),
                        author_gate=ALLOWED_MAINTAINER,
                    ),
                    [item] if expected else [],
                )

    def test_live_path_override_rechecks_sensitive_path_allowlist(self) -> None:
        """Verify live paths must satisfy the sensitive-path allowlist."""
        item = make_item(
            next_action="DIRTY Palette wrap",
            sensitive_paths=["shell_execution"],
            changed_paths=["scripts/analytics_dashboard.sh"],
        )
        cases = (
            (["scripts/analytics_dashboard.sh"], True),
            ([".jules/notes.md", "scripts/analytics_dashboard.sh"], True),
            (["scripts/unrelated.sh"], False),
            (["scripts/analytics_dashboard.sh", "scripts/unrelated.sh"], False),
            ([], False),
        )
        for paths, expected in cases:
            with self.subTest(paths=paths):
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=health.ReselectSignals(
                            unique_paths_by_key={item["key"]: paths}
                        ),
                        author_gate=NO_AUTHORS,
                    ),
                    [item] if expected else [],
                )

    def test_disabling_author_gate_preserves_other_exclusions(self) -> None:
        """Verify bypassing author checks retains title, head, and state gates."""
        cases = (
            ({}, "chore(qa): tests", "abc", True),
            ({}, "feat: unrelated", "abc", False),
            ({}, None, "abc", False),
            ({}, "chore(qa): tests", "new-head", False),
            ({"lifecycle_state": "TERMINAL"}, "chore(qa): tests", "abc", False),
            ({"current_owner": "stage2"}, "chore(qa): tests", "abc", False),
            (
                {"guardrail_outcome": "REVIEW_SECURITY"},
                "chore(qa): tests",
                "abc",
                False,
            ),
        )
        for overrides, title, head, expected in cases:
            with self.subTest(overrides=overrides, title=title, head=head):
                item = make_item(
                    author_type="HUMAN",
                    head_sha="abc",
                    changed_paths=["src/demo.py"],
                    next_action="CONFLICTING",
                    **overrides,
                )
                signals = health.ReselectSignals(
                    titles_by_key={item["key"]: title},
                    live_head_sha_by_key={item["key"]: head},
                )
                with mock.patch.object(
                    health, "_load_reselect_allowed_authors"
                ) as load:
                    candidates = health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=signals,
                        author_gate=health.ReselectAuthorGate(enabled=False),
                    )
                load.assert_not_called()
                self.assertEqual(candidates, [item] if expected else [])

    def test_live_exclusions_do_not_consume_candidate_limit(self) -> None:
        """Verify excluded PRs leave room for eligible candidates under the cap."""
        items = [
            make_item(
                key=f"owner/repo#{n}@abc",
                head_sha="abc",
                next_action="CONFLICTING",
                changed_paths=["src/demo.py"],
            )
            for n in range(1, 6)
        ]
        signals = health.ReselectSignals(
            closed_keys=frozenset({items[0]["key"]}),
            live_head_sha_by_key={items[1]["key"]: "new-head"},
            live_mergeable_by_key={items[2]["key"]: "MERGEABLE"},
        )
        self.assertEqual(
            health.list_reselect_candidates(
                make_ledger(items, []),
                signals=signals,
                limit=1,
                author_gate=NO_AUTHORS,
            ),
            [items[3]],
        )

    def test_all_authoritative_nonconflict_states_override_stale_ledger(self) -> None:
        """Verify known live nonconflict states override stale conflict text."""
        item = make_item(changed_paths=["src/demo.py"], next_action="CONFLICTING")
        for state in (
            "MERGEABLE",
            "CLEAN",
            "BLOCKED",
            "BEHIND",
            "UNSTABLE",
            "HAS_HOOKS",
        ):
            with self.subTest(state=state):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        item,
                        live=health.LivePrSignals(mergeable=f"  {state.lower()}  "),
                        author_gate=NO_AUTHORS,
                    )
                )

    def test_live_head_requires_nonempty_matching_ledger_head(self) -> None:
        """Verify supplied live heads require a nonempty, normalized SHA match."""
        for ledger_head, live_head, expected in (
            (None, "abc", False),
            ("", "abc", False),
            ("  ", "abc", False),
            ("abc", "", False),
            ("abc", "  ", False),
            (" ABC ", " abc ", True),
            (None, None, True),
        ):
            with self.subTest(ledger_head=ledger_head, live_head=live_head):
                item = make_item(
                    head_sha=ledger_head,
                    changed_paths=["src/demo.py"],
                    next_action="CONFLICTING",
                )
                self.assertEqual(
                    health.is_reselect_salvage_candidate(
                        item,
                        live=health.LivePrSignals(head_sha=live_head),
                        author_gate=NO_AUTHORS,
                    ),
                    expected,
                )

    def test_live_base_drift_does_not_exclude(self) -> None:
        """Verify a live base SHA differing from the ledger anchor still passes.

        baseRefOid tracks the moving tip of the base branch, so routine merges
        advance it without invalidating the item; plan actions stamp the
        fetched live base as the proposal anchor instead.
        """
        for ledger_base, live_base in (
            (None, "abc"),
            ("", "abc"),
            ("abc", ""),
            ("abc", "drifted"),
            ("abc", "abc"),
            (None, None),
        ):
            with self.subTest(ledger_base=ledger_base, live_base=live_base):
                item = make_item(
                    base_sha=ledger_base,
                    changed_paths=["src/demo.py"],
                    next_action="CONFLICTING",
                )
                self.assertTrue(
                    health.is_reselect_salvage_candidate(
                        item,
                        live=health.LivePrSignals(base_sha=live_base),
                        author_gate=NO_AUTHORS,
                    )
                )
        item = make_item(
            base_sha="base9999",
            changed_paths=["src/demo.py"],
            next_action="CONFLICTING",
        )
        self.assertEqual(
            health.list_reselect_candidates(
                make_ledger([item], []),
                signals=health.ReselectSignals(
                    live_base_sha_by_key={item["key"]: "drifted"}
                ),
                author_gate=NO_AUTHORS,
            ),
            [item],
        )

    def test_full_key_head_and_author_signals_override_prefix_values(self) -> None:
        """Verify exact-key head and author signals take precedence over prefixes."""
        item = make_item(
            head_sha="abc",
            author_type="HUMAN",
            changed_paths=["src/demo.py"],
            next_action="CONFLICTING",
        )
        key = item["key"]
        prefix = "abhimehro/demo#1"
        # Prefix-only signals apply to a current head; exact-head signals win.
        cases = (
            ({prefix: "abc"}, {prefix: "maintainer"}, True),
            ({prefix: "abc", key: "different"}, {prefix: "maintainer"}, False),
            ({prefix: "different", key: "abc"}, {prefix: "maintainer"}, True),
            ({prefix: "abc"}, {prefix: "maintainer", key: "outsider"}, False),
            ({prefix: "abc"}, {prefix: "outsider", key: "maintainer"}, True),
        )
        for heads, authors, expected in cases:
            with self.subTest(heads=heads, authors=authors):
                signals = health.ReselectSignals(
                    titles_by_key={prefix: "chore(qa): tests"},
                    live_head_sha_by_key=heads,
                    author_login_by_key=authors,
                )
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=signals,
                        author_gate=ALLOWED_MAINTAINER,
                    ),
                    [item] if expected else [],
                )

    def test_closed_signal_does_not_exclude_another_head_or_pr(self) -> None:
        """Verify closed signals do not exclude unrelated PR keys or revisions."""
        item = make_item(changed_paths=["src/demo.py"], next_action="CONFLICTING")
        for closed_key in (
            "abhimehro/demo#1@old-head",
            "abhimehro/demo#10",
            "other/demo#1",
        ):
            with self.subTest(closed_key=closed_key):
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=health.ReselectSignals(
                            closed_keys=frozenset({closed_key})
                        ),
                        author_gate=NO_AUTHORS,
                    ),
                    [item],
                )

    def test_title_prefix_normalization(self) -> None:
        """Titles with FE0F, no space, extra spaces, and lowercase all match; feat: Bolt and Bolted do not."""
        matching_titles = (
            "⚡ Bolt: test something",
            "⚡Bolt: test something",
            "⚡\ufe0f Bolt: test variation selector",
            "⚡\ufe0e Bolt: test variation selector",
            "⚡\ufe0fBolt: test compact",
            "⚡\u200bBolt: zero width space",
            "⚡\u200c\u200dBolt: zwnj and zwj",
            "⚡\u2060Bolt: word joiner",
            "⚡   bolt: extra spaces and lowercase",
            "🎨 Palette: update css",
            "🎨Palette: update css",
            "🎨\ufe0f Palette: variation selector",
            "🎨\ufe0fPalette: variation selector",
            "🎨\u200bPalette: zero width space",
            "salvage(pc-100): test salvage",
            "chore(qa): update tests",
            "chore(repo-health): clean up repo",
        )
        non_matching_titles = (
            "feat: Bolt",
            "Bolted",
            "feat: ⚡ Bolt",
            "fix: palette",
            "chore: qa",
            "random title",
            "",
            None,
        )
        for title in matching_titles:
            with self.subTest(matching_title=title):
                self.assertTrue(
                    health._title_is_reselect_bot(title),
                    f"Expected title to match: {title!r}",
                )
        for title in non_matching_titles:
            with self.subTest(non_matching_title=title):
                self.assertFalse(
                    health._title_is_reselect_bot(title),
                    f"Expected title NOT to match: {title!r}",
                )

    def test_live_mergeable_unknown_falls_back_to_next_action(self) -> None:
        """live_mergeable='UNKNOWN' falls back to next_action; 'MERGEABLE' excludes."""
        item = make_item(
            key="abhimehro/demo#1@abc",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        # UNKNOWN should fall back to next_action (which has CONFLICTING) -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(mergeable="UNKNOWN")
            )
        )
        # empty or None should fall back to next_action -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(mergeable="")
            )
        )
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(mergeable=None)
            )
        )
        # MERGEABLE is authoritative -> excluded (not in CONFLICTING/DIRTY)
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(mergeable="MERGEABLE")
            )
        )
        # CLEAN is authoritative -> excluded
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(mergeable="CLEAN")
            )
        )
        # DIRTY and CONFLICTING are authoritative -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(mergeable="DIRTY")
            )
        )
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(mergeable="CONFLICTING")
            )
        )

    def test_head_sha_mismatch_excludes_item(self) -> None:
        """Head-SHA mismatch excludes item; matching or omitted signal is unchanged."""
        item = make_item(
            key="abhimehro/demo#1@abc1234",
            head_sha="abc1234",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        # Matching head SHA -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(head_sha="abc1234")
            )
        )
        # Case-insensitive match -> candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(head_sha="ABC1234")
            )
        )
        # No signal (None) -> unchanged candidate
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(head_sha=None)
            )
        )
        # Mismatch -> excluded
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                item, live=health.LivePrSignals(head_sha="def5678")
            )
        )

        # In list_reselect_candidates with ReselectSignals
        ledger = make_ledger([item], [])
        match_signals = health.ReselectSignals(
            live_head_sha_by_key={item["key"]: "abc1234"}
        )
        self.assertEqual(
            len(health.list_reselect_candidates(ledger, signals=match_signals)), 1
        )
        mismatch_signals = health.ReselectSignals(
            live_head_sha_by_key={item["key"]: "drifted_sha"}
        )
        self.assertEqual(
            len(health.list_reselect_candidates(ledger, signals=mismatch_signals)), 0
        )

    @mock.patch.object(
        health, "_load_reselect_allowed_authors", return_value=("abhimehro",)
    )
    def test_summarize_threads_signals(self, _allowed_authors: mock.Mock) -> None:
        """summarize() with signals reflects live candidate count."""
        # Non-BOT item that qualifies only with title signal
        item = make_item(
            key="abhimehro/demo#1@abc1234",
            author_type="HUMAN",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        ledger = make_ledger([item], [])

        # Without signals: titles_by_key is empty, title=None -> 0 reselect candidates
        report_default = health.summarize(ledger)
        self.assertEqual(report_default.reselect_candidate_count, 0)

        # With title signal: qualifies as candidate
        signals = health.ReselectSignals(
            titles_by_key={item["key"]: "⚡ Bolt: live title"},
            author_login_by_key={item["key"]: "abhimehro"},
        )
        report_with_signals = health.summarize(ledger, signals=signals)
        self.assertEqual(report_with_signals.reselect_candidate_count, 1)


if __name__ == "__main__":
    unittest.main()
