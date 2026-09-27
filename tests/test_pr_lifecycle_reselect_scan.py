#!/usr/bin/env python3
"""Tests for the pr_lifecycle_reselect_signals.py scan loop mechanics."""

from __future__ import annotations

import copy
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


def _view_calls(runner: mock.Mock) -> list[str]:
    """Return the PR argument of each `gh pr view` call the runner saw."""
    return [call.args[0][3] for call in runner.call_args_list if "view" in call.args[0]]


class TestReselectScanMechanics(unittest.TestCase):
    def test_non_open_success_resets_failure_streak(self) -> None:
        """Verify successful non-open lookups reset consecutive query failures."""
        # A successful lookup still counts as recovery when it yields no open PR.
        items = [
            make_queryable_item(
                key=f"owner/repo#{n}@abc", repository="owner/repo", pr=n
            )
            for n in range(1, 7)
        ]
        for state in ("CLOSED", "MERGED", "UNKNOWN"):
            with self.subTest(state=state):
                runner = mock.Mock(
                    side_effect=stub_gh_runner(
                        results=[
                            make_gh_proc("error", returncode=1),
                            make_gh_proc("error", returncode=1),
                            make_gh_proc({"state": state}),
                            make_gh_proc("error", returncode=1),
                            make_gh_proc("error", returncode=1),
                            make_gh_proc({"state": "OPEN", "title": "recovered"}),
                        ]
                    )
                )
                result = produce_reselect_signals(make_ledger(items, []), runner=runner)
                self.assertEqual(result.status, "PARTIAL")
                self.assertEqual(result.queried_count, 6)
                # Failures fail on the view call alone; only the OPEN payload
                # also fetches base — non-OPEN states skip the api call.
                self.assertEqual(runner.call_count, 7)
                self.assertEqual(
                    result.failed_keys, tuple(items[n]["key"] for n in (0, 1, 3, 4))
                )
                self.assertEqual(
                    result.signals.titles_by_key, {items[5]["key"]: "recovered"}
                )
                self.assertEqual(
                    result.signals.closed_keys,
                    None if state == "UNKNOWN" else frozenset({items[2]["key"]}),
                )

    def test_last_inflight_query_can_finish_after_total_budget(self) -> None:
        """Verify a final query started within budget can finish with OK status."""
        item = make_queryable_item(repository="owner/repo", pr=1)
        runner = mock.Mock(
            side_effect=stub_gh_runner({"state": "OPEN", "title": "collected"})
        )
        # The budget gates starting a query; completing the final query is a full scan.
        with mock.patch(
            "pr_lifecycle_reselect_signals.time.monotonic",
            side_effect=[10.0, 14.0, 20.0],
        ):
            result = produce_reselect_signals(
                make_ledger([item], []),
                runner=runner,
                limits=SignalQueryLimits(per_call_timeout_s=8.0, total_budget_s=5.0),
            )
        # view + base-sha calls share the configured per-call timeout.
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(runner.call_args.args[1], 8.0)
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.queried_count, 1)
        self.assertEqual(result.elapsed_s, 10.0)
        self.assertEqual(result.signals.titles_by_key, {item["key"]: "collected"})

    def test_later_scan_does_not_reuse_closed_state_or_query_failures(self) -> None:
        """Verify scans collect fresh signals and failures without ledger mutation."""
        items = [
            make_queryable_item(
                key=f"owner/repo#{n}@abc", repository="owner/repo", pr=n
            )
            for n in (1, 2)
        ]
        ledger = make_ledger(items, [])
        original = copy.deepcopy(ledger)
        runner = mock.Mock(
            side_effect=stub_gh_runner(
                results=[
                    make_gh_proc({"state": "CLOSED"}),
                    make_gh_proc("error", returncode=1),
                    make_gh_proc({"state": "OPEN", "headRefOid": "new-head"}),
                    make_gh_proc({"state": "OPEN", "files": []}),
                ]
            )
        )
        first = produce_reselect_signals(ledger, runner=runner)
        second = produce_reselect_signals(ledger, runner=runner)
        self.assertEqual(first.status, "PARTIAL")
        self.assertEqual(first.failed_keys, (items[1]["key"],))
        self.assertEqual(first.signals.closed_keys, frozenset({items[0]["key"]}))
        self.assertEqual(second.status, "OK")
        self.assertEqual(second.queried_count, 2)
        self.assertEqual(second.failed_keys, ())
        self.assertEqual(
            second.signals,
            health.ReselectSignals(
                live_head_sha_by_key={items[0]["key"]: "new-head"},
                live_base_sha_by_key={
                    items[0]["key"]: "b" * 40,
                    items[1]["key"]: "b" * 40,
                },
                unique_paths_by_key={items[1]["key"]: []},
            ),
        )
        # 2 calls per OPEN item (view + base), view only for CLOSED, 1 for
        # the failed one, across scans.
        self.assertEqual(runner.call_count, 6)
        self.assertEqual(ledger, original)

    def test_missing_ledger_paths_still_get_a_live_lookup(self) -> None:
        """Empty changed_paths stays plausible; the live file list decides."""
        item = make_queryable_item(
            repository="owner/repo", pr=1, changed_paths=[]
        )
        runner = mock.Mock(
            side_effect=stub_gh_runner(
                {
                    "state": "OPEN",
                    "mergeable": "CONFLICTING",
                    "files": [{"path": "src/fix.py"}],
                }
            )
        )
        ledger = make_ledger([item], [])
        result = produce_reselect_signals(ledger, runner=runner)
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.queried_count, 1)
        self.assertEqual(
            result.signals.unique_paths_by_key, {item["key"]: ["src/fix.py"]}
        )
        self.assertEqual(
            health.list_reselect_candidates(
                ledger,
                signals=result.signals,
                author_gate=health.ReselectAuthorGate(allowed_authors=()),
            ),
            [item],
        )

    def test_nonpositive_budget_does_not_attempt_queries(self) -> None:
        """Verify zero or negative budgets return PARTIAL without querying gh."""
        ledger = make_ledger([make_queryable_item(repository="owner/repo", pr=1)], [])
        for budget in (0, -1):
            with self.subTest(budget=budget):
                runner = mock.Mock()
                with mock.patch(
                    "pr_lifecycle_reselect_signals.time.monotonic", return_value=10.0
                ):
                    result = produce_reselect_signals(
                        ledger,
                        runner=runner,
                        limits=SignalQueryLimits(total_budget_s=budget),
                    )
                runner.assert_not_called()
                self.assertEqual(result.status, "PARTIAL")
                self.assertEqual(result.queried_count, 0)
                self.assertEqual(result.failed_keys, ())
                self.assertEqual(result.signals, health.ReselectSignals())

    def test_producer_queries_only_prioritized_candidates_within_cap(self) -> None:
        """Verify producer queries respect owner priority, order, and the PR cap."""
        items = [
            make_queryable_item(
                key=f"owner/repo#{n}@abc",
                repository="owner/repo",
                pr=n,
                current_owner=owner,
            )
            for n, owner in enumerate(("human", "stage3", "stage1"), start=1)
        ]
        ledger = make_ledger(items, [])
        original = copy.deepcopy(ledger)
        runner = mock.Mock(side_effect=stub_gh_runner({"state": "CLOSED"}))
        result = produce_reselect_signals(
            ledger, runner=runner, limits=SignalQueryLimits(max_prs=2)
        )
        self.assertEqual(_view_calls(runner), ["2", "3"])
        # The cap clipped one candidate, so coverage is PARTIAL even though
        # every queried PR resolved cleanly.
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.queried_count, 2)
        self.assertEqual(result.candidate_count, 3)
        self.assertEqual(
            result.signals.closed_keys, frozenset(item["key"] for item in items[1:])
        )
        self.assertEqual(ledger, original)

    def test_default_runner_uses_fixed_argv_and_configured_timeout(self) -> None:
        """Verify the default runner passes fixed gh arguments and the timeout."""
        item = make_queryable_item(repository="abhimehro/demo", pr=1)

        def fake_run(
            cmd: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            if "api" in cmd:
                return make_gh_proc("a" * 40)
            return make_gh_proc({"state": "OPEN"})

        with mock.patch(
            "pr_lifecycle_reselect_signals.subprocess.run",
            side_effect=fake_run,
        ) as process:
            result = produce_reselect_signals(
                make_ledger([item], []),
                limits=SignalQueryLimits(per_call_timeout_s=2.5),
            )
        # The base SHA ships via `gh api` because `gh pr view --json` lacks
        # baseRefOid on gh older than v2.63.0.
        self.assertEqual(process.call_count, 2)
        process.assert_any_call(
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
        process.assert_any_call(
            [
                "gh",
                "api",
                "repos/abhimehro/demo/pulls/1",
                "--jq",
                ".base.sha",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.5,
        )
        self.assertEqual(result.status, "OK")

    def test_timeout_is_sanitized_and_next_candidate_is_still_queried(self) -> None:
        """Verify timeouts log no private output and allow the next query."""
        items = [
            make_queryable_item(key=f"demo#{n}@sha", repository="demo", pr=n)
            for n in (1, 2)
        ]
        runner = mock.Mock(
            side_effect=stub_gh_runner(
                results=[
                    subprocess.TimeoutExpired(
                        "private-command", 2, output="private-output"
                    ),
                    make_gh_proc({"state": "OPEN", "mergeable": "CONFLICTING"}),
                ]
            )
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
        """Verify an intervening success prevents degradation across failure runs."""
        items = [
            make_queryable_item(key=f"demo#{n}@sha", repository="demo", pr=n)
            for n in range(6)
        ]
        runner = mock.Mock(
            side_effect=stub_gh_runner(
                results=[
                    make_gh_proc("error", returncode=1),
                    make_gh_proc("invalid-json"),
                    make_gh_proc({"state": "OPEN", "title": "first success"}),
                    make_gh_proc("null"),
                    make_gh_proc("error", returncode=1),
                    make_gh_proc({"state": "CLOSED"}),
                ]
            )
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


if __name__ == "__main__":
    unittest.main()
