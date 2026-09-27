#!/usr/bin/env python3
"""Tests for pr_lifecycle_reselect_signals.py ledger prefiltering."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_pipeline_health as health  # noqa: E402
from pr_lifecycle_reselect_signals import (  # noqa: E402
    prefilter_ledger_items,
    produce_reselect_signals,
)

from tests.pr_lifecycle_helpers import (  # noqa: E402
    make_ledger,
    make_queryable_item,
    make_work_item,
    stub_gh_runner,
)

ALLOWED_GATE = health.ReselectAuthorGate(allowed_authors=("abhimehro",))


class TestPrefilterLedgerItems(unittest.TestCase):
    def test_malformed_items_and_empty_ledgers_do_not_query_github(self) -> None:
        """Verify unusable ledger entries yield empty signals without gh calls."""
        for items in (None, {}, "invalid", [None, "invalid", {}]):
            with self.subTest(items=items):
                runner = mock.Mock()
                result = produce_reselect_signals(
                    {"items": items, "stage2_work_items": []}, runner=runner
                )
                runner.assert_not_called()
                self.assertEqual(result.status, "OK")
                self.assertEqual(result.queried_count, 0)
                self.assertEqual(result.signals, health.ReselectSignals())

    def test_priority_is_applied_before_cap_without_mutating_ledger(self) -> None:
        """Verify owner priority precedes the cap and leaves the ledger intact."""
        items = [
            make_queryable_item(
                key=f"demo#{n}@sha", repository="demo", pr=n, current_owner="human"
            )
            for n in range(1, 42)
        ]
        priority = make_queryable_item(
            key="demo#42@sha", repository="demo", pr=42, current_owner="stage1"
        )
        ledger = make_ledger([*items, priority], [])
        original = copy.deepcopy(ledger)
        self.assertEqual(prefilter_ledger_items(ledger), [priority, *items[:39]])
        self.assertEqual(prefilter_ledger_items(ledger, max_prs=1), [priority])
        self.assertEqual(prefilter_ledger_items(ledger, max_prs=0), [])
        self.assertEqual(ledger, original)

    def test_unusable_work_items_do_not_hide_candidates(self) -> None:
        """Verify expired or invalid work items do not suppress candidate PRs."""
        item = make_queryable_item(repository="abhimehro/demo", pr=1)
        cases = (
            {"expiry_utc": "2000-01-01T00:00:00Z"},
            {"expiry_utc": "not-a-date"},
            {"required_test_command": ""},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                work_item = make_work_item(
                    source_item_key="abhimehro/demo#1@older-head",
                    **{"expiry_utc": "2999-01-01T00:00:00Z", **overrides},
                )
                self.assertEqual(
                    prefilter_ledger_items(make_ledger([item], [work_item])), [item]
                )

    def test_prefilter_excludes_ineligible_records(self) -> None:
        """Prefilter excludes never-touch, TERMINAL, stage2-owned, NON_SALVAGE, and already-queued items."""
        valid_candidate = make_queryable_item(
            key="abhimehro/demo#1@abc",
            repository="abhimehro/demo",
            pr=1,
            author="abhimehro",
            author_type="HUMAN",  # Non-BOT kept on an allowlisted ledger author.
            next_action="Some routine action without conflicting",  # No CONFLICTING in next_action kept!
        )
        # Each negative is otherwise fully queryable so only its named gate
        # excludes it (shared anchors/paths via make_queryable_item).
        never_touch = make_queryable_item(
            key="abhimehro/Seatek_Analysis#692@abc",
            repository="abhimehro/Seatek_Analysis",
            pr=692,
        )
        terminal = make_queryable_item(
            key="abhimehro/demo#2@abc",
            repository="abhimehro/demo",
            pr=2,
            lifecycle_state="TERMINAL",
        )
        stage2_owner = make_queryable_item(
            key="abhimehro/demo#3@abc",
            repository="abhimehro/demo",
            pr=3,
            current_owner="stage2",
        )
        stage2_state = make_queryable_item(
            key="abhimehro/demo#4@abc",
            repository="abhimehro/demo",
            pr=4,
            lifecycle_state="STAGE2_QUEUED",
        )
        non_salvage = make_queryable_item(
            key="abhimehro/demo#5@abc",
            repository="abhimehro/demo",
            pr=5,
            guardrail_outcome="REVIEW_SECURITY",
        )
        already_queued = make_queryable_item(
            key="abhimehro/demo#6@abc",
            repository="abhimehro/demo",
            pr=6,
        )
        existing_wi = make_work_item(
            source_item_key="abhimehro/demo#6@other-head",
            expiry_utc="2999-01-01T00:00:00Z",
        )
        missing_key = {"repository": "abhimehro/demo", "pr": 7}
        missing_repo = {"key": "abhimehro/demo#8@abc", "pr": 8}
        missing_pr = {"key": "abhimehro/demo#9@abc", "repository": "abhimehro/demo"}

        items = [
            valid_candidate,
            never_touch,
            terminal,
            stage2_owner,
            stage2_state,
            non_salvage,
            already_queued,
            missing_key,
            missing_repo,
            missing_pr,
        ]
        ledger = make_ledger(items, [existing_wi])
        survivors = prefilter_ledger_items(ledger, author_gate=ALLOWED_GATE)

        self.assertEqual(len(survivors), 1)
        self.assertEqual(survivors[0]["key"], valid_candidate["key"])

    def test_prefilter_drops_records_failing_non_live_gates(self) -> None:
        """Records that cannot pass non-live gates never consume a query slot."""
        base = {
            "repository": "abhimehro/demo",
            "next_action": "CONFLICTING",
        }
        outsider_author = make_queryable_item(
            key="abhimehro/demo#11@abc",
            pr=11,
            author="random-external-user",
            author_type="HUMAN",
            **base,
        )
        no_paths = make_queryable_item(
            key="abhimehro/demo#12@abc",
            pr=12,
            changed_paths=[],
            **base,
        )
        journal_only = make_queryable_item(
            key="abhimehro/demo#13@abc",
            pr=13,
            changed_paths=[".jules/journal.md"],
            **base,
        )
        missing_base = make_queryable_item(
            key="abhimehro/demo#14@abc",
            pr=14,
            base_sha="",
            **base,
        )
        missing_head = make_queryable_item(
            key="abhimehro/demo#15@abc",
            pr=15,
            head_sha="  ",
            **base,
        )
        plausible = make_queryable_item(
            key="abhimehro/demo#16@abc",
            pr=16,
            **base,
        )
        ledger = make_ledger(
            [
                outsider_author,
                no_paths,
                journal_only,
                missing_base,
                missing_head,
                plausible,
            ],
            [],
        )
        self.assertEqual(
            prefilter_ledger_items(ledger, author_gate=ALLOWED_GATE), [plausible]
        )

    def test_prefilter_cap_spends_lookups_only_on_plausible_records(self) -> None:
        """Non-candidates ahead in ledger order must not consume the live cap."""
        implausible = [
            make_queryable_item(
                key=f"abhimehro/demo#{n}@abc",
                repository="abhimehro/demo",
                pr=n,
                author="random-external-user",
                author_type="HUMAN",
            )
            for n in range(1, 41)
        ]
        # A BOT item with a non-conflicting ledger action still gains
        # eligibility from a live DIRTY state once it is queried.
        plausible_bot = make_queryable_item(
            key="abhimehro/demo#41@abc",
            repository="abhimehro/demo",
            pr=41,
            next_action="needs verification",
        )
        ledger = make_ledger([*implausible, plausible_bot], [])
        self.assertEqual(
            prefilter_ledger_items(ledger, author_gate=ALLOWED_GATE),
            [plausible_bot],
        )
        runner = mock.Mock(
            side_effect=stub_gh_runner(
                {"state": "OPEN", "mergeable": "UNKNOWN", "mergeStateStatus": "DIRTY"}
            )
        )
        result = produce_reselect_signals(ledger, runner=runner)
        # One pr-view plus one base-sha lookup per queried candidate.
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(
            result.signals.live_mergeable_by_key, {plausible_bot["key"]: "DIRTY"}
        )

    def test_prefilter_orders_stage1_and_stage3_items_first(self) -> None:
        """Prefilter keeps ledger order but places stage1 and stage3 owned items first."""
        other1 = make_queryable_item(
            key="demo#1@a", repository="demo", pr=1, current_owner="human"
        )
        stage3_item = make_queryable_item(
            key="demo#2@b", repository="demo", pr=2, current_owner="stage3"
        )
        other2 = make_queryable_item(
            key="demo#3@c", repository="demo", pr=3, current_owner="none"
        )
        stage1_item = make_queryable_item(
            key="demo#4@d", repository="demo", pr=4, current_owner="stage1"
        )

        ledger = make_ledger([other1, stage3_item, other2, stage1_item], [])
        survivors = prefilter_ledger_items(ledger, max_prs=10)
        keys = [s["key"] for s in survivors]
        self.assertEqual(keys, ["demo#2@b", "demo#4@d", "demo#1@a", "demo#3@c"])

    def test_prefilter_honors_max_prs_cap(self) -> None:
        """Prefilter applies max_prs limit."""
        items = [
            make_queryable_item(key=f"demo#{n}@a", repository="demo", pr=n)
            for n in range(10)
        ]
        ledger = make_ledger(items, [])
        survivors = prefilter_ledger_items(ledger, max_prs=3)
        self.assertEqual(len(survivors), 3)


if __name__ == "__main__":
    unittest.main()
