"""Integration tests wiring live reselect signals into run stage plans."""

from __future__ import annotations

import functools
import json
import subprocess
import sys
import types
import unittest
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import mock

from tests.pr_lifecycle_helpers import (
    SCRIPTS,
    import_lifecycle_run,
    make_item,
    make_ledger,
    stub_gh_runner,
)

run = import_lifecycle_run()

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import pr_lifecycle_pipeline_health as real_health
from pr_lifecycle_reselect_signals import SignalsResult, produce_reselect_signals


def _patch_run_runtime(stack: ExitStack, tmp: str, ledger: dict[str, Any]) -> None:
    """Patch run module log dir, ledger IO, and health stubs."""
    stack.enter_context(mock.patch.object(run, "LOG_DIR", Path(tmp)))
    stack.enter_context(mock.patch.object(run, "_run_id", return_value="test-run"))
    stack.enter_context(
        mock.patch.object(run, "load_yaml", side_effect=[{"lifecycle": {}}, ledger])
    )
    stack.enter_context(mock.patch.object(run, "validate_config"))
    stack.enter_context(
        mock.patch.object(
            run.cas,
            "run_preflight",
            return_value={"ledger_path": "ledger.yaml"},
            create=True,
        )
    )
    for name in (
        "list_reselect_candidates",
        "signal_value",
        "is_never_touch_key",
        "non_journal_paths",
    ):
        stack.enter_context(
            mock.patch.object(run.health, name, getattr(real_health, name))
        )


def _patch_producer(stack: ExitStack, producer_override: Any) -> None:
    """Install the producer override: callable or fixed SignalsResult."""
    if producer_override is None:
        return
    if callable(producer_override):
        stack.enter_context(
            mock.patch.object(run, "produce_reselect_signals", producer_override)
        )
        return
    stack.enter_context(
        mock.patch.object(
            run, "produce_reselect_signals", return_value=producer_override
        )
    )


def _exec_stage(
    stage: int,
    ledger: dict[str, Any],
    *,
    producer_override: Any = None,
    no_live_signals: bool = False,
) -> tuple[int, dict[str, Any]]:
    with TemporaryDirectory() as tmp:
        with ExitStack() as stack:
            _patch_run_runtime(stack, tmp, ledger)
            _patch_producer(stack, producer_override)
            out = StringIO()
            with redirect_stdout(out):
                exit_code = run.run_stage(
                    stage,
                    dry_run=True,
                    write_status=False,
                    no_live_signals=no_live_signals,
                )
            return exit_code, json.loads(out.getvalue())


def _stage_candidate_items(stage: int, count: int) -> list[dict[str, Any]]:
    """Ledger items that survive the non-live prefilter gates."""
    return [
        make_item(
            key=f"owner/repo#{n}@abc",
            repository="owner/repo",
            pr=n,
            head_sha="abc",
            base_sha="def",
            current_owner=f"stage{stage}",
            changed_paths=["src/ledger.py"],
            next_action="CONFLICTING",
        )
        for n in range(1, count + 1)
    ]


def _live_payload(payload: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    """Wrap a gh payload dict in a successful CompletedProcess."""
    return subprocess.CompletedProcess(
        args=["gh"], returncode=0, stdout=json.dumps(payload)
    )


def _title_gated_item() -> dict[str, Any]:
    """Non-BOT ledger item whose eligibility depends on live title/author."""
    return {
        "key": "owner/repo#42@abcd1234abcd1234abcd1234abcd1234abcd1234",
        "repository": "owner/repo",
        "pr": 42,
        "author": "abhimehro",
        "head_sha": "abcd1234abcd1234abcd1234abcd1234abcd1234",
        "base_sha": "1111222233334444555566667777888899990000",
        "current_owner": "stage1",
        "lifecycle_state": "OPEN",
        "guardrail_outcome": "HOLD_CONTRACT",
        "next_action": "conflict markers in src/foo.py",
        "changed_paths": ["src/foo.py"],
        "unique_remaining_paths": ["src/foo.py"],
    }


def _dependabot_item(**overrides: Any) -> dict[str, Any]:
    """BOT ledger item plausible for a live query."""
    fields = {
        "key": "owner/repo#43@abcd1234abcd1234abcd1234abcd1234abcd1234",
        "repository": "owner/repo",
        "pr": 43,
        "author": "dependabot[bot]",
        "author_type": "BOT",
        "head_sha": "abcd1234abcd1234abcd1234abcd1234abcd1234",
        "base_sha": "1111222233334444555566667777888899990000",
        "current_owner": "stage1",
        "lifecycle_state": "OPEN",
        "guardrail_outcome": "HOLD_CONTRACT",
        "next_action": "HOLD_CONTRACT CONFLICTING conflict markers in src/foo.py",
        "changed_paths": ["src/foo.py"],
        "unique_remaining_paths": ["src/foo.py"],
    }
    fields.update(overrides)
    return fields


def _open_payload(mergeable: str, merge_state: str) -> dict[str, Any]:
    """Live OPEN payload matching the ledger anchors of the test items."""
    return {
        "state": "OPEN",
        "mergeable": mergeable,
        "mergeStateStatus": merge_state,
        "title": "bump deps",
        "headRefOid": "abcd1234abcd1234abcd1234abcd1234abcd1234",
        "baseRefOid": "1111222233334444555566667777888899990000",
        "author": {"login": "dependabot[bot]"},
        "files": [{"path": "src/foo.py"}],
    }


def _namespace_runner(payload: dict[str, Any]):
    """Runner stub returning a namespace-shaped gh result for one payload.

    `gh pr view` gets the payload; the `gh api` base-sha enrichment gets the
    payload's embedded baseRefOid so live and ledger anchors stay in sync.
    """
    base_sha = payload.get("baseRefOid", "b" * 40)

    def runner(cmd, timeout=None):
        if "api" in cmd:
            return types.SimpleNamespace(
                returncode=0, stdout=f"{base_sha}\n", stderr=""
            )
        return types.SimpleNamespace(
            returncode=0, stdout=json.dumps(payload), stderr=""
        )

    return runner


class ReselectSignalsTests(unittest.TestCase):
    """Integration and unit tests for live reselect signal wiring."""

    def _assert_consecutive_failures_keep_exclusions(
        self, stage: int, action_name: str
    ) -> None:
        items = _stage_candidate_items(stage, 6)
        payloads = [
            {"state": "MERGED"},
            {"state": "OPEN", "headRefOid": "new-head"},
        ]
        runner = mock.Mock(
            side_effect=stub_gh_runner(
                results=[
                    *[_live_payload(payload) for payload in payloads],
                    *[
                        subprocess.CompletedProcess(
                            args=["gh"], returncode=1, stdout=""
                        )
                        for _ in range(3)
                    ],
                ]
            )
        )
        ledger = make_ledger(items, [])
        result = produce_reselect_signals(ledger, runner=runner)
        with mock.patch.object(run.health, "summarize", real_health.summarize):
            code, plan = _exec_stage(stage, ledger, producer_override=result)
        # Successful items run a view plus a base-sha call; failures stop early.
        self.assertEqual(runner.call_count, 7)
        self.assertEqual(code, 0)
        self.assertIsNone(plan["stop_class"])
        self.assertEqual(plan["signals_status"], "DEGRADED")
        self.assertEqual(plan["signals_queried"], 5)
        self.assertEqual(
            plan["signals_failed_keys"], [item["key"] for item in items[2:5]]
        )
        self.assertEqual(plan["pipeline_health"]["reselect_candidate_count"], 4)
        actions = [a for a in plan["actions"] if a["action"] == action_name]
        # Failed and unqueried keys use the ledger; known exclusions survive.
        self.assertEqual(
            [a["source_key"] for a in actions],
            [item["key"] for item in items[2:]],
        )
        self.assertEqual([a["allowed_paths"] for a in actions], [["src/ledger.py"]] * 4)
        if stage == 1:
            feed = next(a for a in plan["actions"] if a["action"] == "FEED_CHECK")
            self.assertEqual(feed["grade"], "PASS")
            self.assertEqual(feed["enqueued"], 4)

    def test_consecutive_query_failures_preserve_exclusions_in_stage_plans(
        self,
    ) -> None:
        for stage, action_name in (
            (1, "ENQUEUE_STAGE2_WI"),
            (3, "HANDOFF_MECHANICAL_TO_STAGE2"),
        ):
            with self.subTest(stage=stage):
                self._assert_consecutive_failures_keep_exclusions(stage, action_name)

    def test_live_file_completeness_controls_stage1_and_stage3_actions(self) -> None:
        cases = (
            ([], [], False),
            ([{"path": ".jules/bolt.md"}], [], False),
            ([{"path": "src/live.py"}], ["src/live.py"], False),
            ([{"path": f"src/{n}.py"} for n in range(100)], ["src/ledger.py"], True),
        )
        for stage, action_name in (
            (1, "ENQUEUE_STAGE2_WI"),
            (3, "HANDOFF_MECHANICAL_TO_STAGE2"),
        ):
            for files, expected_paths, truncated in cases:
                with self.subTest(
                    stage=stage, file_count=len(files), truncated=truncated
                ):
                    item = make_item(
                        repository="abhimehro/demo",
                        pr=1,
                        head_sha="abc",
                        base_sha="def",
                        current_owner=f"stage{stage}",
                        next_action="CONFLICTING",
                        changed_paths=["src/ledger.py"],
                    )
                    runner = stub_gh_runner(
                        {"state": "OPEN", "headRefOid": "abc", "files": files}
                    )
                    result = produce_reselect_signals(
                        make_ledger([item], []), runner=runner
                    )
                    with mock.patch.object(
                        run.health, "summarize", real_health.summarize
                    ):
                        code, plan = _exec_stage(
                            stage, make_ledger([item], []), producer_override=result
                        )
                    self.assertEqual(code, 0)
                    self.assertEqual(plan["signals_status"], "OK")
                    self.assertEqual(
                        plan["signals_truncated_keys"],
                        [item["key"]] if truncated else [],
                    )
                    self.assertEqual(
                        plan["pipeline_health"]["reselect_candidate_count"],
                        int(bool(expected_paths)),
                    )
                    actions = [a for a in plan["actions"] if a["action"] == action_name]
                    self.assertEqual(len(actions), int(bool(expected_paths)))
                    if actions:
                        self.assertEqual(actions[0]["source_key"], item["key"])
                        self.assertEqual(actions[0]["allowed_paths"], expected_paths)
                        # The proposal carries the fetched live base anchor.
                        self.assertEqual(actions[0]["base_sha"], "b" * 40)
                    if stage == 1:
                        feed = next(
                            a for a in plan["actions"] if a["action"] == "FEED_CHECK"
                        )
                        self.assertEqual(feed["grade"], "PASS")
                        self.assertEqual(feed["enqueued"], len(actions))

    def _assert_partial_mix(self, stage: int, action_name: str) -> None:
        items = _stage_candidate_items(stage, 5)
        result = SignalsResult(
            signals=real_health.ReselectSignals(
                live_mergeable_by_key={items[0]["key"]: "MERGEABLE"},
                closed_keys=frozenset({items[1]["key"]}),
                live_head_sha_by_key={items[2]["key"]: "new-head"},
                unique_paths_by_key={items[3]["key"]: ["src/live.py"]},
            ),
            status="PARTIAL",
            queried_count=5,
            failed_keys=(items[4]["key"],),
            truncated_keys=(items[0]["key"],),
            elapsed_s=1.25,
        )
        ledger = make_ledger(items, [])
        producer = mock.Mock(return_value=result)
        with mock.patch.object(run.health, "summarize", real_health.summarize):
            code, plan = _exec_stage(stage, ledger, producer_override=producer)
        producer.assert_called_once_with(ledger)
        self.assertEqual(code, 0)
        self.assertIsNone(plan["stop_class"])
        self.assertEqual(plan["signals_status"], "PARTIAL")
        self.assertEqual(plan["signals_queried"], 5)
        self.assertEqual(plan["signals_failed_keys"], [items[4]["key"]])
        self.assertEqual(plan["signals_truncated_keys"], [items[0]["key"]])
        self.assertEqual(plan["signals_elapsed_s"], 1.25)
        self.assertEqual(plan["pipeline_health"]["reselect_candidate_count"], 2)
        actions = [a for a in plan["actions"] if a["action"] == action_name]
        self.assertEqual(
            [a["source_key"] for a in actions],
            [items[3]["key"], items[4]["key"]],
        )
        self.assertEqual(
            [a["allowed_paths"] for a in actions],
            [["src/live.py"], ["src/ledger.py"]],
        )
        degraded = [a for a in plan["actions"] if a["action"] == "SIGNALS_DEGRADED"]
        self.assertEqual(len(degraded), 1)
        self.assertEqual(degraded[0]["status"], "PARTIAL")
        if stage == 1:
            feed = next(a for a in plan["actions"] if a["action"] == "FEED_CHECK")
            self.assertEqual(feed["grade"], "PASS")
            self.assertEqual(feed["reselect_candidates"], 2)
            self.assertEqual(feed["enqueued"], 2)
            self.assertEqual(feed["condition"], "SIGNALS_DEGRADED")

    def test_partial_signals_mix_live_exclusions_with_ledger_fallback(self):
        for stage, action_name in (
            (1, "ENQUEUE_STAGE2_WI"),
            (3, "HANDOFF_MECHANICAL_TO_STAGE2"),
        ):
            with self.subTest(stage=stage):
                self._assert_partial_mix(stage, action_name)

    def test_degraded_signals_do_not_mask_incomplete_work_item_stop(self):
        item = make_item(
            repository="owner/repo",
            pr=1,
            current_owner="stage1",
            changed_paths=["src/demo.py"],
            next_action="CONFLICTING",
        )
        # Missing base/head SHAs permit eligibility but prevent a complete WI.
        for status in ("OK", "PARTIAL", "DEGRADED", "SKIPPED"):
            with self.subTest(status=status):
                code, plan = _exec_stage(
                    1,
                    make_ledger([item], []),
                    producer_override=SignalsResult(status=status),
                )
                self.assertEqual(code, 2)
                self.assertEqual(plan["stop_class"], "LOGIC_STOP")
                self.assertEqual(plan["reason"], "FEED_CHECK_FAIL")
                feed = next(a for a in plan["actions"] if a["action"] == "FEED_CHECK")
                self.assertEqual(feed["grade"], "FAIL")
                self.assertEqual(feed["signals_status"], status)
                self.assertEqual(feed["reselect_candidates"], 1)
                self.assertEqual(feed["enqueued"], 0)
                self.assertEqual(
                    feed["skipped_incomplete"],
                    [
                        {
                            "source_key": item["key"],
                            "reason": "INCOMPLETE_WI_FIELDS",
                        }
                    ],
                )

    def test_status_and_issue_body_expose_signal_condition_only_when_degraded(self):
        for signal_status in ("OK", "PARTIAL", "DEGRADED", "SKIPPED"):
            with self.subTest(signal_status=signal_status):
                plan = run.build_stage_plan(
                    3,
                    make_ledger([], []),
                    {},
                    signals_result=SignalsResult(status=signal_status),
                )
                status = run.write_status_doc(plan, "test-run")
                body = run._issue_body(status)
                self.assertEqual(status["signals_status"], signal_status)
                self.assertIn(f"signals_status: {signal_status}\n", body)
                if signal_status in {"PARTIAL", "DEGRADED"}:
                    self.assertEqual(status["condition"], "SIGNALS_DEGRADED")
                    self.assertIn("condition: SIGNALS_DEGRADED\n", body)
                else:
                    self.assertNotIn("condition", status)
                    self.assertNotIn("SIGNALS_DEGRADED", body)
                self.assertNotIn("signals_error", status)

    def test_no_live_signals_preserves_stage3_ledger_handoff(self):
        item = make_item(
            repository="owner/repo",
            pr=1,
            head_sha="abc",
            base_sha="def",
            changed_paths=["src/demo.py"],
            next_action="CONFLICTING",
        )
        producer = mock.Mock()
        code, plan = _exec_stage(
            3, make_ledger([item], []), producer_override=producer, no_live_signals=True
        )
        producer.assert_not_called()
        self.assertEqual(code, 0)
        self.assertEqual(plan["signals_status"], "SKIPPED")
        self.assertEqual(plan["signals_queried"], 0)
        self.assertEqual(plan["signals_failed_keys"], [])
        self.assertEqual(plan["signals_truncated_keys"], [])
        self.assertNotIn("condition", plan)
        actions = [
            a for a in plan["actions"] if a["action"] == "HANDOFF_MECHANICAL_TO_STAGE2"
        ]
        self.assertEqual([a["source_key"] for a in actions], [item["key"]])

    def test_main_forwards_live_signals_flag_and_stage_exit_code(self):
        for flags, expected in (([], False), (["--no-live-signals"], True)):
            with (
                self.subTest(flags=flags),
                mock.patch.object(run, "run_stage", return_value=2) as run_stage,
            ):
                self.assertEqual(
                    run.main(["--stage", "3", "--dry-run", "--write-status", *flags]), 2
                )
                run_stage.assert_called_once_with(
                    3, dry_run=True, write_status=True, no_live_signals=expected
                )

    def test_stage1_and_stage3_invoke_producer_and_pass_signals(self):
        """Stage 1 and Stage 3 invoke producer and attach signals to plan."""
        fake_signals = real_health.ReselectSignals()
        result_payload = SignalsResult(
            signals=fake_signals,
            status="OK",
            queried_count=2,
            failed_keys=(),
            truncated_keys=(),
            elapsed_s=0.5,
        )
        mock_producer = mock.Mock(return_value=result_payload)

        # Stage 1
        ledger = {"ledger_revision": 1, "items": []}
        code, plan = _exec_stage(1, ledger, producer_override=mock_producer)
        self.assertEqual(code, 0)
        mock_producer.assert_called_with(ledger)
        self.assertEqual(plan["signals_status"], "OK")
        self.assertEqual(plan["signals_queried"], 2)
        feed_check = next(a for a in plan["actions"] if a.get("action") == "FEED_CHECK")
        self.assertEqual(feed_check["signals_status"], "OK")

        # Stage 3
        mock_producer.reset_mock()
        code, plan = _exec_stage(3, ledger, producer_override=mock_producer)
        self.assertEqual(code, 0)
        mock_producer.assert_called_with(ledger)
        self.assertEqual(plan["signals_status"], "OK")
        self.assertEqual(plan["signals_queried"], 2)

    def test_stage2_skips_live_signals_producer(self):
        """Stage 2 never calls live signals producer and reports SKIPPED."""
        mock_producer = mock.Mock()
        ledger = {"ledger_revision": 1, "items": []}
        code, plan = _exec_stage(2, ledger, producer_override=mock_producer)
        self.assertEqual(code, 0)
        mock_producer.assert_not_called()
        self.assertEqual(plan["signals_status"], "SKIPPED")

    def test_producer_raises_fails_open_with_degraded_status(self):
        """Producer exceptions fail open, yield DEGRADED status, exit 0, and emit action."""
        mock_producer = mock.Mock(side_effect=RuntimeError("producer timeout"))
        ledger = {"ledger_revision": 1, "items": []}
        with self.assertLogs(run.LOGGER, level="WARNING") as logs:
            code, plan = _exec_stage(1, ledger, producer_override=mock_producer)
        self.assertEqual(code, 0)
        output = "\n".join(logs.output)
        self.assertIn("PR_LIFECYCLE_RUN_WARNING", output)
        self.assertIn("RuntimeError", output)
        # Only the type is logged; exception text may carry sensitive output.
        self.assertNotIn("producer timeout", output)
        self.assertEqual(plan["signals_error"], "RuntimeError")
        self.assertEqual(plan["signals_status"], "DEGRADED")
        self.assertEqual(plan.get("condition"), "SIGNALS_DEGRADED")
        feed_check = next(a for a in plan["actions"] if a.get("action") == "FEED_CHECK")
        self.assertEqual(feed_check.get("condition"), "SIGNALS_DEGRADED")
        action_names = [a.get("action") for a in plan["actions"]]
        self.assertIn("SIGNALS_DEGRADED", action_names)
        degraded = next(
            a for a in plan["actions"] if a.get("action") == "SIGNALS_DEGRADED"
        )
        self.assertEqual(degraded["status"], "DEGRADED")
        self.assertEqual(action_names.count("SIGNALS_DEGRADED"), 1)
        status = run.write_status_doc(plan, "run-deg")
        self.assertEqual(status.get("condition"), "SIGNALS_DEGRADED")
        self.assertEqual(status.get("signals_error"), "RuntimeError")

    def test_no_live_signals_flag_skips_producer(self):
        """--no-live-signals skips live fetch and reports status SKIPPED."""
        mock_producer = mock.Mock()
        ledger = {"ledger_revision": 1, "items": []}
        code, plan = _exec_stage(
            1, ledger, producer_override=mock_producer, no_live_signals=True
        )
        self.assertEqual(code, 0)
        mock_producer.assert_not_called()
        self.assertEqual(plan["signals_status"], "SKIPPED")

        parser = run.build_parser()
        args = parser.parse_args(["--stage", "1", "--no-live-signals"])
        self.assertTrue(args.no_live_signals)

    def test_e2e_title_gated_item_enqueued_with_live_signals(self):
        """Title-gated non-BOT item enqueues under live signals."""
        item = _title_gated_item()
        ledger = {"ledger_revision": 1, "items": [item]}
        payload = _open_payload("CONFLICTING", "DIRTY")
        payload["title"] = "⚡️ Bolt: optimize widget cache"
        payload["author"] = {"login": "abhimehro"}

        code, plan = _exec_stage(
            1,
            ledger,
            producer_override=lambda ledger_in: produce_reselect_signals(
                ledger_in, runner=_namespace_runner(payload)
            ),
        )
        self.assertEqual(code, 0)
        self.assertEqual(plan["signals_status"], "OK")
        enqueues = [
            a for a in plan["actions"] if a.get("action") == "ENQUEUE_STAGE2_WI"
        ]
        self.assertEqual(len(enqueues), 1)
        self.assertEqual(enqueues[0]["source_key"], item["key"])
        self.assertEqual(enqueues[0]["allowed_paths"], ["src/foo.py"])
        feed_check = next(a for a in plan["actions"] if a.get("action") == "FEED_CHECK")
        self.assertEqual(feed_check["grade"], "PASS")
        self.assertEqual(feed_check["reselect_candidates"], 1)
        self.assertEqual(feed_check["enqueued"], 1)

    def test_e2e_title_gated_item_dropped_under_degraded_signals(self):
        """The same title-gated item is not enqueued under DEGRADED signals."""
        item = _title_gated_item()
        ledger = {"ledger_revision": 1, "items": [item]}

        degraded_result = SignalsResult(
            signals=real_health.ReselectSignals(),
            status="DEGRADED",
            queried_count=1,
            failed_keys=(item["key"],),
        )
        code, plan_degraded = _exec_stage(1, ledger, producer_override=degraded_result)
        self.assertEqual(code, 0)
        self.assertEqual(plan_degraded["signals_status"], "DEGRADED")
        degraded_enqueues = [
            a
            for a in plan_degraded["actions"]
            if a.get("action") == "ENQUEUE_STAGE2_WI"
        ]
        self.assertEqual(len(degraded_enqueues), 0)
        feed_check_deg = next(
            a for a in plan_degraded["actions"] if a.get("action") == "FEED_CHECK"
        )
        self.assertEqual(feed_check_deg["grade"], "PASS")
        self.assertEqual(feed_check_deg["reselect_candidates"], 0)
        self.assertEqual(feed_check_deg["enqueued"], 0)
        self.assertTrue(
            any(a.get("action") == "SIGNALS_DEGRADED" for a in plan_degraded["actions"])
        )

    def test_ledger_conflicting_live_mergeable_no_enqueue(self):
        """Ledger CONFLICTING item with live MERGEABLE signal is not enqueued."""
        item = _dependabot_item(
            key="owner/repo#42@abcd1234abcd1234abcd1234abcd1234abcd1234",
            pr=42,
        )
        ledger = {"ledger_revision": 1, "items": [item]}

        code, plan = _exec_stage(
            1,
            ledger,
            producer_override=lambda ledger_in: produce_reselect_signals(
                ledger_in, runner=_namespace_runner(_open_payload("MERGEABLE", "CLEAN"))
            ),
        )
        self.assertEqual(code, 0)
        enqueues = [
            a for a in plan["actions"] if a.get("action") == "ENQUEUE_STAGE2_WI"
        ]
        self.assertEqual(len(enqueues), 0)
        feed_check = next(a for a in plan["actions"] if a.get("action") == "FEED_CHECK")
        self.assertEqual(feed_check["reselect_candidates"], 0)
        self.assertEqual(feed_check["enqueued"], 0)

    def test_stage3_hold_contract_live_mergeable_no_handoff(self):
        """Stage 3 HOLD_CONTRACT item with live MERGEABLE is not handed off, CONFLICTING is."""
        item = _dependabot_item(
            current_owner="stage3", lifecycle_state="STAGE3_RECONCILIATION"
        )
        ledger = {"ledger_revision": 1, "items": [item]}

        for mergeable, merge_state, expected in (
            ("MERGEABLE", "CLEAN", 0),
            ("CONFLICTING", "DIRTY", 1),
        ):
            with self.subTest(mergeable=mergeable):
                runner = _namespace_runner(_open_payload(mergeable, merge_state))
                code, plan = _exec_stage(
                    3,
                    ledger,
                    producer_override=functools.partial(
                        produce_reselect_signals, runner=runner
                    ),
                )
                self.assertEqual(code, 0)
                handoffs = [
                    a
                    for a in plan["actions"]
                    if a.get("action") == "HANDOFF_MECHANICAL_TO_STAGE2"
                ]
                self.assertEqual(len(handoffs), expected)
                if expected:
                    self.assertEqual(handoffs[0]["source_key"], item["key"])


if __name__ == "__main__":
    unittest.main()
