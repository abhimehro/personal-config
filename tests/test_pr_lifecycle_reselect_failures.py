#!/usr/bin/env python3
"""Tests for pr_lifecycle_reselect_signals.py failure and budget statuses."""

from __future__ import annotations

import json
import subprocess
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
    SignalQueryLimits,
    produce_reselect_signals,
)

from tests.pr_lifecycle_helpers import (  # noqa: E402
    make_gh_proc,
    make_ledger,
    make_queryable_item,
    stub_gh_runner,
)


class TestReselectFailureStatuses(unittest.TestCase):
    def test_nonzero_exit_discards_even_valid_stdout(self) -> None:
        """Verify failed gh calls cannot contribute authoritative live signals."""
        item = make_queryable_item(repository="owner/repo", pr=1)
        # A nonzero exit with well-formed JSON stdout must still be rejected:
        # results entries pass through verbatim (unlike the payload kwarg).
        runner = stub_gh_runner(
            results=[
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view"],
                    returncode=1,
                    stdout=json.dumps({"state": "CLOSED"}),
                    stderr="",
                )
            ]
        )
        result = produce_reselect_signals(make_ledger([item], []), runner=runner)
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.queried_count, 1)
        self.assertEqual(result.failed_keys, (item["key"],))
        self.assertEqual(result.signals, health.ReselectSignals())

    def test_mixed_failure_types_share_consecutive_failure_limit(self) -> None:
        """Verify command and payload failures share the degradation threshold."""
        items = [
            make_queryable_item(
                key=f"owner/repo#{n}@abc", repository="owner/repo", pr=n
            )
            for n in range(1, 5)
        ]
        runner = mock.Mock(
            side_effect=stub_gh_runner(
                results=[
                    make_gh_proc("error", returncode=1),
                    make_gh_proc("{invalid"),
                    make_gh_proc("[]"),
                    make_gh_proc({"state": "OPEN"}),
                ]
            )
        )
        result = produce_reselect_signals(make_ledger(items, []), runner=runner)
        self.assertEqual(result.status, "DEGRADED")
        # The view call fails before the base-sha lookup runs for each key.
        self.assertEqual(runner.call_count, 3)
        self.assertEqual(result.queried_count, 3)
        self.assertEqual(result.failed_keys, tuple(item["key"] for item in items[:3]))
        self.assertEqual(result.signals, health.ReselectSignals())

    def test_invalid_json_and_non_object_payloads_fail_only_the_affected_key(
        self,
    ) -> None:
        """Verify malformed payloads do not prevent later PRs from contributing."""
        items = [
            make_queryable_item(key=f"demo#{n}@sha", repository="demo", pr=n)
            for n in (1, 2)
        ]
        for payload in ("{invalid", "", "[]", "null", "42", '"OPEN"', "true"):
            with self.subTest(payload=payload):
                runner = stub_gh_runner(
                    results=[
                        make_gh_proc(payload),
                        make_gh_proc({"state": "OPEN", "title": "healthy"}),
                    ]
                )
                result = produce_reselect_signals(make_ledger(items, []), runner=runner)
                self.assertEqual(result.status, "PARTIAL")
                self.assertEqual(result.queried_count, 2)
                self.assertEqual(result.failed_keys, (items[0]["key"],))
                self.assertEqual(
                    result.signals.titles_by_key,
                    {items[1]["key"]: "healthy"},
                )

    def test_base_sha_enrichment_failures_are_advisory(self) -> None:
        """A failed `gh api` base lookup drops only the enrichment, not the key."""
        items = [
            make_queryable_item(key=f"demo#{n}@sha", repository="demo", pr=n)
            for n in (1, 2)
        ]
        payload = {"state": "OPEN", "title": "healthy"}

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            if "api" in cmd:
                if cmd[2].endswith("pulls/1"):
                    return make_gh_proc("error", returncode=1)
                return make_gh_proc("not-a-sha\n")
            return make_gh_proc(payload)

        result = produce_reselect_signals(make_ledger(items, []), runner=runner)
        # Nonzero exit and non-SHA stdout both drop just the base field.
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.queried_count, 2)
        self.assertEqual(result.failed_keys, ())
        self.assertEqual(
            result.signals.titles_by_key,
            {items[0]["key"]: "healthy", items[1]["key"]: "healthy"},
        )
        self.assertIsNone(result.signals.live_base_sha_by_key)

    def test_consecutive_base_failures_do_not_degrade(self) -> None:
        """A systemic `gh api` outage cannot trip the consecutive-failure breaker."""
        items = [
            make_queryable_item(key=f"demo#{n}@sha", repository="demo", pr=n)
            for n in range(1, 6)
        ]
        payload = {"state": "OPEN", "mergeable": "CONFLICTING", "title": "ok"}

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            if "api" in cmd:
                return make_gh_proc("error", returncode=1)
            return make_gh_proc(payload)

        result = produce_reselect_signals(make_ledger(items, []), runner=runner)
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.queried_count, 5)
        self.assertEqual(result.failed_keys, ())
        self.assertEqual(len(result.signals.live_mergeable_by_key), 5)
        self.assertIsNone(result.signals.live_base_sha_by_key)

    def test_base_lookup_missing_gh_is_advisory(self) -> None:
        """FileNotFoundError on the api call drops the enrichment, not the key."""
        item = make_queryable_item(key="demo#1@sha", repository="demo", pr=1)

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            if "api" in cmd:
                raise FileNotFoundError("gh vanished mid-scan")
            return make_gh_proc({"state": "OPEN", "title": "kept"})

        result = produce_reselect_signals(make_ledger([item], []), runner=runner)
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.failed_keys, ())
        self.assertEqual(result.signals.titles_by_key, {item["key"]: "kept"})
        self.assertIsNone(result.signals.live_base_sha_by_key)

    def test_per_pr_failure_results_in_partial_status(self) -> None:
        """Per-PR failure -> PARTIAL, and failed key absent from every map."""
        item1 = make_queryable_item(key="demo#1@sha", repository="demo", pr=1)
        item2 = make_queryable_item(key="demo#2@sha", repository="demo", pr=2)
        ledger = make_ledger([item1, item2], [])

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            if "api" in cmd:
                return make_gh_proc("b" * 40)
            if "1" in cmd:
                return make_gh_proc("", returncode=1)
            return make_gh_proc(
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
        item = make_queryable_item(key="demo#1@sha", repository="demo", pr=1)

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            raise FileNotFoundError("gh not found")

        result = produce_reselect_signals(make_ledger([item], []), runner=runner)
        self.assertEqual(result.status, "DEGRADED")
        self.assertEqual(result.signals, health.ReselectSignals())
        self.assertEqual(result.failed_keys, (item["key"],))

    def test_three_consecutive_failures_cause_degraded(self) -> None:
        """3 consecutive failures -> DEGRADED with empty signals."""
        items = [
            make_queryable_item(key=f"demo#{i}@sha", repository="demo", pr=i)
            for i in range(4)
        ]
        ledger = make_ledger(items, [])

        call_count = 0

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            return make_gh_proc("error", returncode=1)

        result = produce_reselect_signals(ledger, runner=runner)
        self.assertEqual(result.status, "DEGRADED")
        self.assertEqual(result.signals, health.ReselectSignals())
        self.assertEqual(call_count, 3)  # stopped after 3 failures
        self.assertEqual(len(result.failed_keys), 3)

    def test_three_failures_preserve_collected_exclusions(self) -> None:
        """Degradation must not reselect known closed or changed-head PRs."""
        items = [
            make_queryable_item(
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
            side_effect=stub_gh_runner(
                results=[
                    make_gh_proc({"state": "CLOSED"}),
                    make_gh_proc(
                        {
                            "state": "OPEN",
                            "headRefOid": "new-sha",
                            "mergeable": "CONFLICTING",
                            "files": [{"path": f"src/{i}.py"} for i in range(100)],
                        }
                    ),
                    *[make_gh_proc("error", returncode=1) for _ in range(3)],
                ]
            )
        )

        result = produce_reselect_signals(ledger, runner=runner)

        self.assertEqual(result.status, "DEGRADED")
        self.assertEqual(result.queried_count, 5)
        # Two calls per successful item; failures never reach the api call.
        self.assertEqual(runner.call_count, 7)
        self.assertEqual(result.failed_keys, tuple(item["key"] for item in items[2:5]))
        self.assertEqual(result.truncated_keys, (items[1]["key"],))
        self.assertGreaterEqual(result.elapsed_s, 0)
        self.assertEqual(
            result.signals,
            health.ReselectSignals(
                closed_keys=frozenset({items[0]["key"]}),
                live_head_sha_by_key={items[1]["key"]: "new-sha"},
                live_base_sha_by_key={items[1]["key"]: "b" * 40},
                live_mergeable_by_key={items[1]["key"]: "CONFLICTING"},
            ),
        )
        self.assertEqual(
            health.list_reselect_candidates(
                ledger, author_gate=health.ReselectAuthorGate(allowed_authors=())
            ),
            items,
        )
        self.assertEqual(
            health.list_reselect_candidates(
                ledger,
                signals=result.signals,
                author_gate=health.ReselectAuthorGate(allowed_authors=()),
            ),
            items[2:],
        )

    def test_budget_boundary_preserves_successful_signals(self) -> None:
        """Verify budget exhaustion retains signals from completed queries."""
        items = [
            make_queryable_item(key=f"demo#{n}@sha", repository="demo", pr=n)
            for n in (1, 2)
        ]
        runner = mock.Mock(
            side_effect=stub_gh_runner(
                {"state": "OPEN", "title": "collected before budget expired"}
            )
        )
        # Start, first query, second-query budget check, final elapsed time.
        with mock.patch(
            "pr_lifecycle_reselect_signals.time.monotonic",
            side_effect=[10.0, 10.0, 15.0, 15.0],
        ):
            result = produce_reselect_signals(
                make_ledger(items, []),
                runner=runner,
                limits=SignalQueryLimits(total_budget_s=5.0),
            )
        # The one completed item ran its view and base-sha calls.
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.queried_count, 1)
        self.assertEqual(result.elapsed_s, 5.0)
        self.assertEqual(result.failed_keys, ())
        self.assertEqual(
            result.signals.titles_by_key,
            {items[0]["key"]: "collected before budget expired"},
        )

    def test_budget_exhaustion_results_in_partial_status(self) -> None:
        """Budget exhaustion stops querying and returns PARTIAL with accumulated signals."""
        items = [
            make_queryable_item(key=f"demo#{i}@sha", repository="demo", pr=i)
            for i in range(5)
        ]
        ledger = make_ledger(items, [])

        call_count = 0

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            return make_gh_proc(
                {
                    "state": "OPEN",
                    "mergeable": "CONFLICTING",
                    "title": f"PR {call_count}",
                }
            )

        # total_budget_s = 0.0 forces timeout before subsequent items
        result = produce_reselect_signals(
            ledger, runner=runner, limits=SignalQueryLimits(total_budget_s=0.0)
        )
        self.assertEqual(result.status, "PARTIAL")
        # Zero budget: the check runs before the first query.
        self.assertEqual(call_count, 0)
        self.assertEqual(result.queried_count, 0)

    def test_budget_exhaustion_preserves_accumulated_signals(self) -> None:
        """Budget exhaustion after some queries returns PARTIAL with accumulated signals."""
        items = [
            make_queryable_item(key=f"demo#{i}@sha", repository="demo", pr=i)
            for i in range(3)
        ]
        ledger = make_ledger(items, [])

        call_count = 0
        mock_time = [0.0]  # Use list for mutable closure

        def runner(cmd: list[str], t: float) -> subprocess.CompletedProcess[str]:
            if "api" in cmd:
                return make_gh_proc("b" * 40)
            nonlocal call_count
            call_count += 1
            # Simulate 50ms per view call by advancing mock time
            mock_time[0] += 0.05
            return make_gh_proc(
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
                ledger, runner=runner, limits=SignalQueryLimits(total_budget_s=0.1)
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
        self.assertEqual(
            result.signals.live_mergeable_by_key,
            {items[0]["key"]: "CONFLICTING", items[1]["key"]: "CONFLICTING"},
        )
        self.assertIn(items[1]["key"], result.signals.titles_by_key)
        self.assertIn(items[0]["key"], result.signals.author_login_by_key)
        self.assertIn(items[1]["key"], result.signals.author_login_by_key)
        # Third item should not have signals
        self.assertNotIn(items[2]["key"], result.signals.live_mergeable_by_key)

    def test_producer_never_raises_on_arbitrary_runner_exception(self) -> None:
        """Producer never raises, even when runner raises an unhandled exception."""
        item = make_queryable_item(key="demo#1@sha", repository="demo", pr=1)

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
        item = make_queryable_item(key="demo#1@sha", repository="demo", pr=1)
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
