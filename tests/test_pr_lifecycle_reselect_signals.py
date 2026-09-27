#!/usr/bin/env python3
"""Tests for pr_lifecycle_reselect_signals.py producer."""

from __future__ import annotations

import copy
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
    def test_malformed_items_and_empty_ledgers_do_not_query_github(self) -> None:
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
        items = [
            make_item(
                key=f"demo#{n}@sha", repository="demo", pr=n, current_owner="human"
            )
            for n in range(1, 42)
        ]
        priority = make_item(
            key="demo#42@sha", repository="demo", pr=42, current_owner="stage1"
        )
        ledger = make_ledger([*items, priority], [])
        original = copy.deepcopy(ledger)
        self.assertEqual(prefilter_ledger_items(ledger), [priority, *items[:39]])
        self.assertEqual(prefilter_ledger_items(ledger, max_prs=1), [priority])
        self.assertEqual(prefilter_ledger_items(ledger, max_prs=0), [])
        self.assertEqual(ledger, original)

    def test_unusable_work_items_do_not_hide_candidates(self) -> None:
        item = make_item(repository="abhimehro/demo", pr=1)
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
    def test_nonpositive_budget_does_not_attempt_queries(self) -> None:
        ledger = make_ledger([make_item(repository="owner/repo", pr=1)], [])
        for budget in (0, -1):
            with self.subTest(budget=budget):
                runner = mock.Mock()
                with mock.patch(
                    "pr_lifecycle_reselect_signals.time.monotonic", return_value=10.0
                ):
                    result = produce_reselect_signals(
                        ledger, runner=runner, total_budget_s=budget
                    )
                runner.assert_not_called()
                self.assertEqual(result.status, "PARTIAL")
                self.assertEqual(result.queried_count, 0)
                self.assertEqual(result.failed_keys, ())
                self.assertEqual(result.signals, health.ReselectSignals())

    def test_producer_queries_only_prioritized_candidates_within_cap(self) -> None:
        items = [
            make_item(
                key=f"owner/repo#{n}@abc",
                repository="owner/repo",
                pr=n,
                current_owner=owner,
            )
            for n, owner in enumerate(("human", "stage3", "stage1"), start=1)
        ]
        ledger = make_ledger(items, [])
        original = copy.deepcopy(ledger)
        runner = mock.Mock(return_value=_make_completed_proc({"state": "CLOSED"}))
        result = produce_reselect_signals(ledger, runner=runner, max_prs=2)
        self.assertEqual(
            [call.args[0][3] for call in runner.call_args_list], ["2", "3"]
        )
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.queried_count, 2)
        self.assertEqual(
            result.signals.closed_keys, frozenset(item["key"] for item in items[1:])
        )
        self.assertEqual(ledger, original)

    def test_nonzero_exit_discards_even_valid_stdout(self) -> None:
        item = make_item(repository="owner/repo", pr=1)
        # A failed gh call must not supply an authoritative exclusion.
        runner = mock.Mock(
            return_value=_make_completed_proc({"state": "CLOSED"}, returncode=1)
        )
        result = produce_reselect_signals(make_ledger([item], []), runner=runner)
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.queried_count, 1)
        self.assertEqual(result.failed_keys, (item["key"],))
        self.assertEqual(result.signals, health.ReselectSignals())

    def test_mixed_failure_types_share_consecutive_failure_limit(self) -> None:
        items = [
            make_item(key=f"owner/repo#{n}@abc", repository="owner/repo", pr=n)
            for n in range(1, 5)
        ]
        runner = mock.Mock(
            side_effect=[
                _make_completed_proc("error", returncode=1),
                _make_completed_proc("{invalid"),
                _make_completed_proc("[]"),
                _make_completed_proc({"state": "OPEN"}),
            ]
        )
        result = produce_reselect_signals(make_ledger(items, []), runner=runner)
        self.assertEqual(result.status, "DEGRADED")
        self.assertEqual(runner.call_count, 3)
        self.assertEqual(result.queried_count, 3)
        self.assertEqual(result.failed_keys, tuple(item["key"] for item in items[:3]))
        self.assertEqual(result.signals, health.ReselectSignals())

    def test_blank_optional_fields_do_not_override_ledger_fallbacks(self) -> None:
        item = make_item(repository="owner/repo", pr=1)
        for title, head, author in (
            (None, None, None),
            ("  ", "\t", {"login": "  "}),
            (42, [], "maintainer"),
        ):
            with self.subTest(title=title, head=head, author=author):
                runner = mock.Mock(
                    return_value=_make_completed_proc(
                        {
                            "state": "OPEN",
                            "mergeable": "CONFLICTING",
                            "title": title,
                            "headRefOid": head,
                            "author": author,
                        }
                    )
                )
                result = produce_reselect_signals(
                    make_ledger([item], []), runner=runner
                )
                self.assertEqual(result.status, "OK")
                self.assertEqual(
                    result.signals,
                    health.ReselectSignals(
                        live_mergeable_by_key={item["key"]: "CONFLICTING"}
                    ),
                )

    def test_default_runner_uses_fixed_argv_and_configured_timeout(self) -> None:
        item = make_item(repository="abhimehro/demo", pr=1)
        with mock.patch(
            "pr_lifecycle_reselect_signals.subprocess.run",
            return_value=_make_completed_proc({"state": "OPEN"}),
        ) as process:
            result = produce_reselect_signals(
                make_ledger([item], []), per_call_timeout_s=2.5
            )
        process.assert_called_once_with(
            [
                "gh",
                "pr",
                "view",
                "1",
                "--repo",
                "abhimehro/demo",
                "--json",
                "state,mergeable,mergeStateStatus,title,headRefOid,author,files",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.5,
        )
        self.assertEqual(result.status, "OK")

    def test_invalid_json_and_non_object_payloads_fail_only_the_affected_key(
        self,
    ) -> None:
        items = [
            make_item(key=f"demo#{n}@sha", repository="demo", pr=n) for n in (1, 2)
        ]
        for payload in ("{invalid", "", "[]", "null", "42", '"OPEN"', "true"):
            with self.subTest(payload=payload):
                runner = mock.Mock(
                    side_effect=[
                        _make_completed_proc(payload),
                        _make_completed_proc({"state": "OPEN", "title": "healthy"}),
                    ]
                )
                result = produce_reselect_signals(make_ledger(items, []), runner=runner)
                self.assertEqual(result.status, "PARTIAL")
                self.assertEqual(result.queried_count, 2)
                self.assertEqual(result.failed_keys, (items[0]["key"],))
                self.assertEqual(
                    result.signals,
                    health.ReselectSignals(titles_by_key={items[1]["key"]: "healthy"}),
                )

    def test_timeout_is_sanitized_and_next_candidate_is_still_queried(self) -> None:
        items = [
            make_item(key=f"demo#{n}@sha", repository="demo", pr=n) for n in (1, 2)
        ]
        runner = mock.Mock(
            side_effect=[
                subprocess.TimeoutExpired(
                    "private-command", 2, output="private-output"
                ),
                _make_completed_proc({"state": "OPEN", "mergeable": "CONFLICTING"}),
            ]
        )
        with self.assertLogs("pr_lifecycle_reselect_signals", level="WARNING") as logs:
            result = produce_reselect_signals(make_ledger(items, []), runner=runner)
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.failed_keys, (items[0]["key"],))
        self.assertEqual(result.queried_count, 2)
        self.assertEqual(
            result.signals.live_mergeable_by_key, {items[1]["key"]: "CONFLICTING"}
        )
        self.assertIn("TimeoutExpired", "\n".join(logs.output))
        self.assertNotIn("private-", "\n".join(logs.output))

    def test_success_resets_consecutive_failure_threshold(self) -> None:
        items = [
            make_item(key=f"demo#{n}@sha", repository="demo", pr=n) for n in range(6)
        ]
        runner = mock.Mock(
            side_effect=[
                _make_completed_proc("error", returncode=1),
                _make_completed_proc("invalid-json"),
                _make_completed_proc({"state": "OPEN", "title": "first success"}),
                _make_completed_proc("null"),
                _make_completed_proc("error", returncode=1),
                _make_completed_proc({"state": "CLOSED"}),
            ]
        )
        result = produce_reselect_signals(make_ledger(items, []), runner=runner)
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.queried_count, 6)
        self.assertEqual(
            result.failed_keys, tuple(items[n]["key"] for n in (0, 1, 3, 4))
        )
        self.assertEqual(
            result.signals.titles_by_key, {items[2]["key"]: "first success"}
        )
        self.assertEqual(result.signals.closed_keys, frozenset({items[5]["key"]}))

    def test_budget_boundary_preserves_successful_signals(self) -> None:
        items = [
            make_item(key=f"demo#{n}@sha", repository="demo", pr=n) for n in (1, 2)
        ]
        runner = mock.Mock(
            return_value=_make_completed_proc(
                {"state": "OPEN", "title": "collected before budget expired"}
            )
        )
        # Start, first query, second-query budget check, final elapsed time.
        with mock.patch(
            "pr_lifecycle_reselect_signals.time.monotonic",
            side_effect=[10.0, 10.0, 15.0, 15.0],
        ):
            result = produce_reselect_signals(
                make_ledger(items, []), runner=runner, total_budget_s=5.0
            )
        runner.assert_called_once()
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.queried_count, 1)
        self.assertEqual(result.elapsed_s, 5.0)
        self.assertEqual(result.failed_keys, ())
        self.assertEqual(
            result.signals.titles_by_key,
            {items[0]["key"]: "collected before budget expired"},
        )

    def test_files_boundary_and_missing_files_preserve_ledger_fallback(self) -> None:
        item = make_item(
            repository="abhimehro/demo",
            pr=1,
            changed_paths=["src/ledger.py"],
            next_action="CONFLICTING",
        )
        cases = (
            ([], [], False, False),
            (
                [{"path": f"src/{n}.py"} for n in range(99)],
                [f"src/{n}.py" for n in range(99)],
                False,
                True,
            ),
            ([{"path": f"src/{n}.py"} for n in range(100)], None, True, True),
            ([{"path": "src/ok.py"}, {}], None, True, True),
            ([{"path": ""}], None, True, True),
            (None, None, False, True),
            ({}, None, False, True),
        )
        for files, expected_paths, truncated, eligible in cases:
            with self.subTest(files=files):
                result = produce_reselect_signals(
                    make_ledger([item], []),
                    runner=mock.Mock(
                        return_value=_make_completed_proc(
                            {"state": "OPEN", "files": files}
                        )
                    ),
                )
                self.assertEqual(result.status, "OK")
                self.assertEqual(
                    result.truncated_keys, (item["key"],) if truncated else ()
                )
                self.assertEqual(
                    result.signals.unique_paths_by_key,
                    None if expected_paths is None else {item["key"]: expected_paths},
                )
                self.assertEqual(
                    health.list_reselect_candidates(
                        make_ledger([item], []),
                        signals=result.signals,
                        allowed_authors=(),
                    ),
                    [item] if eligible else [],
                )

    def test_unknown_pr_state_does_not_leak_other_payload_fields(self) -> None:
        item = make_item(repository="abhimehro/demo", pr=1)
        for state in (None, "", "DRAFT", "unknown"):
            with self.subTest(state=state):
                payload = {
                    "state": state,
                    "mergeable": "CONFLICTING",
                    "title": "⚡ Bolt: stale",
                    "headRefOid": "new-head",
                    "author": {"login": "abhimehro"},
                    "files": [{"path": "src/demo.py"}],
                }
                result = produce_reselect_signals(
                    make_ledger([item], []),
                    runner=mock.Mock(return_value=_make_completed_proc(payload)),
                )
                self.assertEqual(result.status, "OK")
                self.assertEqual(result.signals, health.ReselectSignals())

    def test_merge_state_precedence_and_normalization(self) -> None:
        item = make_item(repository="abhimehro/demo", pr=1)
        cases = (
            (" mergeable ", " dirty ", "DIRTY"),
            (" conflicting ", " blocked ", "CONFLICTING"),
            ("UNKNOWN", " behind ", "BEHIND"),
            (None, "unstable", "UNSTABLE"),
            ("UNKNOWN", "has_hooks", "HAS_HOOKS"),
            ("UNKNOWN", "unrecognized", None),
        )
        for mergeable, merge_status, expected in cases:
            with self.subTest(mergeable=mergeable, merge_status=merge_status):
                result = produce_reselect_signals(
                    make_ledger([item], []),
                    runner=mock.Mock(
                        return_value=_make_completed_proc(
                            {
                                "state": " open ",
                                "mergeable": mergeable,
                                "mergeStateStatus": merge_status,
                            }
                        )
                    ),
                )
                self.assertEqual(
                    result.signals.live_mergeable_by_key,
                    {item["key"]: expected} if expected else None,
                )

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

    def test_three_failures_preserve_collected_exclusions(self) -> None:
        """Degradation must not reselect known closed or changed-head PRs."""
        items = [
            make_item(
                key=f"demo#{i}@sha",
                repository="demo",
                pr=i,
                head_sha="sha",
                changed_paths=["src/demo.py"],
                next_action="HOLD_CONTRACT CONFLICTING unique remaining",
            )
            for i in range(6)
        ]
        ledger = make_ledger(items, [])
        runner = mock.Mock(
            side_effect=[
                _make_completed_proc({"state": "CLOSED"}),
                _make_completed_proc(
                    {
                        "state": "OPEN",
                        "headRefOid": "new-sha",
                        "mergeable": "CONFLICTING",
                        "files": [{"path": f"src/{i}.py"} for i in range(100)],
                    }
                ),
                *[_make_completed_proc("error", returncode=1) for _ in range(3)],
            ]
        )

        result = produce_reselect_signals(ledger, runner=runner)

        self.assertEqual(result.status, "DEGRADED")
        self.assertEqual(result.queried_count, 5)
        self.assertEqual(runner.call_count, 5)
        self.assertEqual(result.failed_keys, tuple(item["key"] for item in items[2:5]))
        self.assertEqual(result.truncated_keys, (items[1]["key"],))
        self.assertGreaterEqual(result.elapsed_s, 0)
        self.assertEqual(
            result.signals,
            health.ReselectSignals(
                closed_keys=frozenset({items[0]["key"]}),
                live_head_sha_by_key={items[1]["key"]: "new-sha"},
            ),
        )
        self.assertEqual(
            health.list_reselect_candidates(ledger, allowed_authors=()), items
        )
        self.assertEqual(
            health.list_reselect_candidates(
                ledger, signals=result.signals, allowed_authors=()
            ),
            items[2:],
        )

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

    def test_budget_exhaustion_preserves_accumulated_signals(self) -> None:
        """Budget exhaustion after some queries returns PARTIAL with accumulated signals."""
        items = [
            make_item(key=f"demo#{i}@sha", repository="demo", pr=i) for i in range(3)
        ]
        ledger = make_ledger(items, [])

        call_count = 0
        mock_time = [0.0]  # Use list for mutable closure

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            # Simulate 50ms per call by advancing mock time
            mock_time[0] += 0.05
            return _make_completed_proc(
                {
                    "state": "OPEN",
                    "mergeable": "CONFLICTING",
                    "title": f"PR {call_count}",
                    "headRefOid": f"head{call_count}",
                    "author": {"login": "testuser"},
                }
            )

        with mock.patch("time.monotonic", side_effect=lambda: mock_time[0]):
            # total_budget_s = 0.1 allows ~2 calls (0.05 each) before timeout
            result = produce_reselect_signals(
                ledger, runner=runner, total_budget_s=0.1
            )

        self.assertEqual(result.status, "PARTIAL")
        # Should have queried 2 items before budget exhausted
        self.assertEqual(call_count, 2)
        self.assertEqual(result.queried_count, 2)
        # Accumulated signals should be preserved
        self.assertIn(items[0]["key"], result.signals.live_mergeable_by_key)
        self.assertIn(items[1]["key"], result.signals.live_mergeable_by_key)
        self.assertIn(items[0]["key"], result.signals.live_head_sha_by_key)
        self.assertIn(items[1]["key"], result.signals.live_head_sha_by_key)
        self.assertIn(items[0]["key"], result.signals.titles_by_key)
        self.assertIn(items[1]["key"], result.signals.titles_by_key)
        self.assertIn(items[0]["key"], result.signals.author_login_by_key)
        self.assertIn(items[1]["key"], result.signals.author_login_by_key)
        # Third item should not have signals
        self.assertNotIn(items[2]["key"], result.signals.live_mergeable_by_key)

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
