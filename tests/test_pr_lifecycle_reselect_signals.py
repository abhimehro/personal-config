#!/usr/bin/env python3
"""Tests for pr_lifecycle_reselect_signals.py producer."""

from __future__ import annotations

import json
import subprocess
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
from pr_lifecycle_reselect_signals import (  # noqa: E402
    prefilter_ledger_items,
    produce_reselect_signals,
)

from tests.pr_lifecycle_helpers import (  # noqa: E402
    make_item,
    make_ledger,
    make_work_item,
)


def _make_completed_proc(
    stdout_dict: dict[str, Any] | str, returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    stdout = (
        json.dumps(stdout_dict) if isinstance(stdout_dict, dict) else str(stdout_dict)
    )
    return subprocess.CompletedProcess(
        args=["gh", "pr", "view"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


class TestPrefilterLedgerItems(unittest.TestCase):
    def test_prefilter_excludes_ineligible_records(self) -> None:
        """Prefilter excludes never-touch, TERMINAL, stage2-owned, NON_SALVAGE, and already-queued items."""
        valid_candidate = make_item(
            key="abhimehro/demo#1@abc",
            repository="abhimehro/demo",
            pr=1,
            author_type="HUMAN",  # Keeping non-BOT items!
            next_action="Some routine action without conflicting",  # No CONFLICTING in next_action kept!
        )
        never_touch = make_item(
            key="abhimehro/Seatek_Analysis#692@abc",
            repository="abhimehro/Seatek_Analysis",
            pr=692,
        )
        terminal = make_item(
            key="abhimehro/demo#2@abc",
            repository="abhimehro/demo",
            pr=2,
            lifecycle_state="TERMINAL",
        )
        stage2_owner = make_item(
            key="abhimehro/demo#3@abc",
            repository="abhimehro/demo",
            pr=3,
            current_owner="stage2",
        )
        stage2_state = make_item(
            key="abhimehro/demo#4@abc",
            repository="abhimehro/demo",
            pr=4,
            lifecycle_state="STAGE2_QUEUED",
        )
        non_salvage = make_item(
            key="abhimehro/demo#5@abc",
            repository="abhimehro/demo",
            pr=5,
            guardrail_outcome="REVIEW_SECURITY",
        )
        already_queued = make_item(
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
        survivors = prefilter_ledger_items(ledger)

        self.assertEqual(len(survivors), 1)
        self.assertEqual(survivors[0]["key"], valid_candidate["key"])

    def test_prefilter_orders_stage1_and_stage3_items_first(self) -> None:
        """Prefilter keeps ledger order but places stage1 and stage3 owned items first."""
        other1 = make_item(
            key="demo#1@a", repository="demo", pr=1, current_owner="human"
        )
        stage3_item = make_item(
            key="demo#2@b", repository="demo", pr=2, current_owner="stage3"
        )
        other2 = make_item(
            key="demo#3@c", repository="demo", pr=3, current_owner="none"
        )
        stage1_item = make_item(
            key="demo#4@d", repository="demo", pr=4, current_owner="stage1"
        )

        ledger = make_ledger([other1, stage3_item, other2, stage1_item], [])
        survivors = prefilter_ledger_items(ledger, max_prs=10)
        keys = [s["key"] for s in survivors]
        self.assertEqual(keys, ["demo#2@b", "demo#4@d", "demo#1@a", "demo#3@c"])

    def test_prefilter_honors_max_prs_cap(self) -> None:
        """Prefilter applies max_prs limit."""
        items = [
            make_item(key=f"demo#{n}@a", repository="demo", pr=n) for n in range(10)
        ]
        ledger = make_ledger(items, [])
        survivors = prefilter_ledger_items(ledger, max_prs=3)
        self.assertEqual(len(survivors), 3)


class TestProduceReselectSignals(unittest.TestCase):
    def test_successful_mapping_of_all_fields(self) -> None:
        """Live PR response populates mergeable, title, headRefOid, author, and non-journal files."""
        item = make_item(
            key="abhimehro/personal-config#100@old-sha",
            repository="abhimehro/personal-config",
            pr=100,
        )
        ledger = make_ledger([item], [])

        fake_resp = {
            "state": "OPEN",
            "mergeable": "CONFLICTING",
            "mergeStateStatus": "DIRTY",
            "title": "⚡ Bolt: optimize startup",
            "headRefOid": "live-sha-999",
            "author": {"login": "google-labs-jules[bot]"},
            "files": [
                {"path": ".jules/journal.md"},
                {"path": "scripts/startup.sh"},
            ],
        }

        def fake_runner(
            cmd: list[str], timeout_s: float
        ) -> subprocess.CompletedProcess[str]:
            self.assertIn("100", cmd)
            self.assertIn("abhimehro/personal-config", cmd)
            return _make_completed_proc(fake_resp)

        result = produce_reselect_signals(ledger, runner=fake_runner)

        self.assertEqual(result.status, "OK")
        self.assertEqual(result.queried_count, 1)
        self.assertEqual(result.failed_keys, ())
        self.assertEqual(result.truncated_keys, ())
        self.assertGreaterEqual(result.elapsed_s, 0.0)

        signals = result.signals
        key = item["key"]
        self.assertEqual(signals.live_mergeable_by_key, {key: "CONFLICTING"})
        self.assertEqual(signals.titles_by_key, {key: "⚡ Bolt: optimize startup"})
        self.assertEqual(signals.live_head_sha_by_key, {key: "live-sha-999"})
        self.assertEqual(signals.author_login_by_key, {key: "google-labs-jules[bot]"})
        self.assertEqual(signals.unique_paths_by_key, {key: ["scripts/startup.sh"]})

    def test_mergeable_and_merge_state_status_priority(self) -> None:
        """Mapping: CONFLICTING, DIRTY, MERGEABLE, other authoritative mergeStateStatus; UNKNOWN -> omitted."""
        cases = (
            ("CONFLICTING", "CLEAN", "CONFLICTING"),
            ("UNKNOWN", "DIRTY", "DIRTY"),
            ("MERGEABLE", "CLEAN", "MERGEABLE"),
            ("UNKNOWN", "BLOCKED", "BLOCKED"),  # authoritative mergeStateStatus wins
            ("UNKNOWN", "UNKNOWN", None),  # UNKNOWN is omitted
        )
        for mergeable, m_status, expected in cases:
            with self.subTest(mergeable=mergeable, m_status=m_status):
                item = make_item(key="demo#1@sha", repository="demo", pr=1)
                ledger = make_ledger([item], [])
                resp = {
                    "state": "OPEN",
                    "mergeable": mergeable,
                    "mergeStateStatus": m_status,
                    "title": "demo title",
                }
                result = produce_reselect_signals(
                    ledger, runner=lambda cmd, t, resp=resp: _make_completed_proc(resp)
                )
                if expected:
                    self.assertEqual(
                        result.signals.live_mergeable_by_key, {item["key"]: expected}
                    )
                else:
                    self.assertIsNone(result.signals.live_mergeable_by_key)

    def test_files_truncation_and_journal_only(self) -> None:
        """Files >= 100 -> omitted from unique_paths_by_key, in truncated_keys; journal only -> []."""
        # Truncated case
        item1 = make_item(key="demo#1@sha", repository="demo", pr=1)
        resp1 = {
            "state": "OPEN",
            "mergeable": "CONFLICTING",
            "files": [{"path": f"src/file_{i}.py"} for i in range(100)],
        }
        res1 = produce_reselect_signals(
            make_ledger([item1], []), runner=lambda cmd, t: _make_completed_proc(resp1)
        )
        self.assertIsNone(res1.signals.unique_paths_by_key)
        self.assertEqual(res1.truncated_keys, (item1["key"],))

        # Journal-only case
        item2 = make_item(key="demo#2@sha", repository="demo", pr=2)
        resp2 = {
            "state": "OPEN",
            "mergeable": "CONFLICTING",
            "files": [{"path": ".jules/journal.md"}, {"path": "sub/.jules/note.md"}],
        }
        res2 = produce_reselect_signals(
            make_ledger([item2], []), runner=lambda cmd, t: _make_completed_proc(resp2)
        )
        self.assertEqual(res2.signals.unique_paths_by_key, {item2["key"]: []})
        self.assertEqual(res2.truncated_keys, ())

        # Corrupted / incomplete file entry case
        item3 = make_item(key="demo#3@sha", repository="demo", pr=3)
        resp3 = {
            "state": "OPEN",
            "mergeable": "CONFLICTING",
            "files": [{"path": "src/ok.py"}, "not-a-dict"],
        }
        res3 = produce_reselect_signals(
            make_ledger([item3], []), runner=lambda cmd, t: _make_completed_proc(resp3)
        )
        self.assertIsNone(res3.signals.unique_paths_by_key)
        self.assertEqual(res3.truncated_keys, (item3["key"],))

    def test_closed_or_merged_pr_emits_no_signals(self) -> None:
        """Closed or merged PR emits no signals for that key."""
        item = make_item(key="demo#1@sha", repository="demo", pr=1)
        resp = {
            "state": "MERGED",
            "mergeable": "MERGEABLE",
            "title": "⚡ Bolt: already merged",
            "files": [{"path": "src/demo.py"}],
        }
        result = produce_reselect_signals(
            make_ledger([item], []), runner=lambda cmd, t: _make_completed_proc(resp)
        )
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.queried_count, 1)
        self.assertEqual(result.failed_keys, ())
        self.assertIsNone(result.signals.live_mergeable_by_key)
        self.assertIsNone(result.signals.titles_by_key)
        self.assertIsNone(result.signals.unique_paths_by_key)
        self.assertEqual(result.signals.closed_keys, frozenset({item["key"]}))

    def test_closed_keys_only_for_authoritative_terminal_states(self) -> None:
        """CLOSED/MERGED populate closed_keys; missing/unknown state stays unclassified."""
        cases = (("CLOSED", True), ("merged", True), ("", False), ("DRAFT", False))
        for state, closed in cases:
            with self.subTest(state=state):
                item = make_item(key="demo#1@sha", repository="demo", pr=1)
                resp = {"state": state, "mergeable": "CONFLICTING"}
                result = produce_reselect_signals(
                    make_ledger([item], []),
                    runner=lambda cmd, t, resp=resp: _make_completed_proc(resp),
                )
                if closed:
                    self.assertEqual(
                        result.signals.closed_keys, frozenset({item["key"]})
                    )
                else:
                    self.assertIsNone(result.signals.closed_keys)
                self.assertIsNone(result.signals.live_mergeable_by_key)

    def test_per_pr_failure_results_in_partial_status(self) -> None:
        """Per-PR failure -> PARTIAL, and failed key absent from every map."""
        item1 = make_item(key="demo#1@sha", repository="demo", pr=1)
        item2 = make_item(key="demo#2@sha", repository="demo", pr=2)
        ledger = make_ledger([item1, item2], [])

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            if "1" in cmd:
                return _make_completed_proc("", returncode=1)
            return _make_completed_proc(
                {
                    "state": "OPEN",
                    "mergeable": "CONFLICTING",
                    "title": "Good PR",
                }
            )

        result = produce_reselect_signals(ledger, runner=runner)
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.failed_keys, (item1["key"],))
        self.assertEqual(result.queried_count, 2)
        # item1 must be absent from signals
        self.assertNotIn(item1["key"], result.signals.titles_by_key or {})
        # item2 is present
        self.assertIn(item2["key"], result.signals.titles_by_key or {})

    def test_file_not_found_causes_immediate_degraded(self) -> None:
        """FileNotFoundError (gh CLI missing) causes immediate DEGRADED with empty signals."""
        item = make_item(key="demo#1@sha", repository="demo", pr=1)

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            raise FileNotFoundError("gh not found")

        result = produce_reselect_signals(make_ledger([item], []), runner=runner)
        self.assertEqual(result.status, "DEGRADED")
        self.assertEqual(result.signals, health.ReselectSignals())
        self.assertEqual(result.failed_keys, (item["key"],))

    def test_three_consecutive_failures_cause_degraded(self) -> None:
        """3 consecutive failures -> DEGRADED with empty signals."""
        items = [
            make_item(key=f"demo#{i}@sha", repository="demo", pr=i) for i in range(4)
        ]
        ledger = make_ledger(items, [])

        call_count = 0

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            return _make_completed_proc("error", returncode=1)

        result = produce_reselect_signals(ledger, runner=runner)
        self.assertEqual(result.status, "DEGRADED")
        self.assertEqual(result.signals, health.ReselectSignals())
        self.assertEqual(call_count, 3)  # stopped after 3 failures
        self.assertEqual(len(result.failed_keys), 3)

    def test_budget_exhaustion_results_in_partial_status(self) -> None:
        """Budget exhaustion stops querying and returns PARTIAL with accumulated signals."""
        items = [
            make_item(key=f"demo#{i}@sha", repository="demo", pr=i) for i in range(5)
        ]
        ledger = make_ledger(items, [])

        call_count = 0

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            return _make_completed_proc(
                {
                    "state": "OPEN",
                    "mergeable": "CONFLICTING",
                    "title": f"PR {call_count}",
                }
            )

        # total_budget_s = 0.0 forces timeout before subsequent items
        result = produce_reselect_signals(ledger, runner=runner, total_budget_s=0.0)
        self.assertEqual(result.status, "PARTIAL")
        # Zero budget: the check runs before the first query.
        self.assertEqual(call_count, 0)
        self.assertEqual(result.queried_count, 0)

    def test_producer_never_raises_on_arbitrary_runner_exception(self) -> None:
        """Producer never raises, even when runner raises an unhandled exception."""
        item = make_item(key="demo#1@sha", repository="demo", pr=1)

        def bad_runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            raise RuntimeError("unexpected failure")

        with self.assertLogs("pr_lifecycle_reselect_signals", level="WARNING") as logs:
            result = produce_reselect_signals(
                make_ledger([item], []), runner=bad_runner
            )
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.failed_keys, (item["key"],))
        output = "\n".join(logs.output)
        self.assertIn("RuntimeError", output)
        self.assertNotIn("unexpected failure", output)

    def test_global_failure_logs_type_only_and_degrades(self) -> None:
        """An unexpected producer-level error degrades and logs only its type."""
        item = make_item(key="demo#1@sha", repository="demo", pr=1)
        with mock.patch(
            "pr_lifecycle_reselect_signals.prefilter_ledger_items",
            side_effect=KeyError("secret-ish detail"),
        ), self.assertLogs("pr_lifecycle_reselect_signals", level="WARNING") as logs:
            result = produce_reselect_signals(make_ledger([item], []))
        self.assertEqual(result.status, "DEGRADED")
        self.assertEqual(result.queried_count, 0)
        output = "\n".join(logs.output)
        self.assertIn("KeyError", output)
        self.assertNotIn("secret-ish detail", output)


if __name__ == "__main__":
    unittest.main()
