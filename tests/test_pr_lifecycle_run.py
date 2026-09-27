"""Unit tests for pr_lifecycle_run plan shape and CLI emission."""

from __future__ import annotations

import json
import subprocess
import sys
import types
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import mock

from tests.pr_lifecycle_helpers import SCRIPTS, import_lifecycle_run, make_health_report

run = import_lifecycle_run()

_report = make_health_report

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import pr_lifecycle_pipeline_health as real_health
from pr_lifecycle_reselect_signals import SignalsResult, produce_reselect_signals


class RunPlanTests(unittest.TestCase):
    def test_stage2_never_merges_in_plan(self):
        """Verify Stage 2 plans exclude merge authority."""
        ledger = {"ledger_revision": 9, "items": []}
        config = {"lifecycle": {}}

        class FakeReport:
            salvage_eligible_count = 0
            stage2_work_item_count = 0
            starvation = False
            reason = "ok"

        with (
            mock.patch.object(run.health, "summarize", return_value=FakeReport()),
            mock.patch.object(
                run.feed_mod,
                "build_feed",
                return_value={
                    "empty_with_stock": False,
                    "reason": "FEED_OK",
                    "work_item_count": 0,
                    "eligible_stock_count": 0,
                    "work_items": [],
                },
            ),
        ):
            plan = run.build_stage_plan(2, ledger, config)
        self.assertFalse(plan.get("stage2_may_merge"))
        self.assertFalse(plan.get("calibration_enabled"))
        self.assertEqual(plan["stage"], 2)

    def test_stage3_mentions_advisory_bot_threads(self):
        ledger = {"ledger_revision": 9, "items": []}
        config = {"lifecycle": {}}

        class FakeReport:
            salvage_eligible_count = 0
            stage2_work_item_count = 0
            starvation = False
            reason = "ok"

        with mock.patch.object(run.health, "summarize", return_value=FakeReport()):
            plan = run.build_stage_plan(3, ledger, config)
        blob = str(plan).lower()
        self.assertIn("advisory", blob)
        self.assertFalse(plan.get("calibration_enabled"))

    def test_stage1_uses_bounded_reconciliation_and_always_checks_feed(self):
        """Verify Stage 1 bounds reconciliation and always checks the feed."""
        ledger = {"ledger_revision": 11, "items": []}
        action = {"action": "TERMINAL_CLOSED", "key": "owner/repo#1@sha"}
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(
                run.reconcile_mod, "collect_actions", return_value=[action]
            ) as collect,
        ):
            plan = run.build_stage_plan(1, ledger, {"lifecycle": {}})
        collect.assert_called_once_with(ledger, {"lifecycle": {}}, limit=40)
        self.assertEqual(plan["actions"][0], action)
        self.assertEqual(plan["actions"][-1]["action"], "FEED_CHECK")
        self.assertIn("schema-aware only", " ".join(plan["allowed_commands"]))

    def test_stage2_materializes_work_items_without_merge_authority(self):
        """Verify Stage 2 materializes intake without merge authority."""
        work_item = {"source_key": "owner/repo#1@sha", "reason": "SALVAGE_ELIGIBLE"}
        feed_payload = {
            "empty_with_stock": False,
            "reason": "FEED_OK",
            "work_item_count": 1,
            "eligible_stock_count": 1,
            "work_items": [work_item],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 2}, {})
        self.assertEqual(plan["actions"][0]["action"], "FEED_SUMMARY")
        self.assertEqual(plan["actions"][1], {"action": "SALVAGE_WI", "wi": work_item})
        self.assertIsNone(plan["stop_class"])
        self.assertFalse(plan["stage2_may_merge"])

    def test_stage2_empty_feed_with_stock_is_a_logic_stop(self):
        """Verify eligible stock with an empty feed triggers a logic stop."""
        feed_payload = {
            "empty_with_stock": True,
            "reason": "EMPTY_FEED_WITH_ELIGIBLE_STOCK",
            "work_item_count": 0,
            "eligible_stock_count": 2,
            "non_never_touch_stock_count": 2,
            "work_items": [],
        }
        with (
            mock.patch.object(run.health, "summarize", return_value=_report()),
            mock.patch.object(run.feed_mod, "build_feed", return_value=feed_payload),
        ):
            plan = run.build_stage_plan(2, {"ledger_revision": 2}, {})
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "EMPTY_FEED_WITH_ELIGIBLE_STOCK")

    def test_invalid_stage_fails_closed_with_no_allowed_commands(self):
        with mock.patch.object(run.health, "summarize", return_value=_report()):
            plan = run.build_stage_plan(99, {"ledger_revision": 2}, {})
        self.assertEqual(plan["stop_class"], "LOGIC_STOP")
        self.assertEqual(plan["reason"], "invalid stage 99")
        self.assertEqual(plan["allowed_commands"], [])
        self.assertEqual(plan["actions"], [])

    def test_status_document_is_a_bounded_summary(self):
        plan = {
            "stage": 2,
            "ledger_revision": 12,
            "reason": "FEED_OK",
            "stop_class": None,
            "pipeline_health": {"starvation": False},
            "actions": [{"action": "FEED_SUMMARY"}, {"action": "SALVAGE_WI"}],
        }
        status = run.write_status_doc(plan, "run-fixed")
        self.assertEqual(status["run_id"], "run-fixed")
        self.assertEqual(status["action_count"], 2)
        self.assertFalse(status["calibration_enabled"])
        self.assertNotIn("actions", status)


class RunExecutionTests(unittest.TestCase):
    def test_run_stage_writes_plan_and_status_records(self):
        """Verify running a stage writes its plan and status records."""
        plan = {
            "stage": 1,
            "ledger_revision": 12,
            "pipeline_health": {"starvation": False},
            "actions": [{"action": "FEED_CHECK"}],
            "reason": "OK",
            "stop_class": None,
            "calibration_enabled": False,
            "stage2_may_merge": False,
            "allowed_commands": [],
        }
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            with (
                mock.patch.object(run, "LOG_DIR", log_dir),
                mock.patch.object(run, "_run_id", return_value="run-fixed"),
                mock.patch.object(
                    run, "load_yaml", side_effect=[{"lifecycle": {}}, {"items": []}]
                ),
                mock.patch.object(run, "validate_config"),
                mock.patch.object(
                    run.cas,
                    "run_preflight",
                    return_value={"ledger_path": "ledger.yaml"},
                    create=True,
                ),
                mock.patch.object(run, "build_stage_plan", return_value=plan.copy()),
            ):
                output = StringIO()
                with redirect_stdout(output):
                    result = run.run_stage(1, dry_run=True, write_status=True)
            self.assertEqual(result, 0)
            emitted = json.loads(output.getvalue())
            self.assertEqual(emitted["run_id"], "run-fixed")
            self.assertTrue(emitted["dry_run"])
            records = [
                json.loads(line)
                for line in (log_dir / "run-fixed.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(
                [record["event"] for record in records], ["plan", "status"]
            )
            status = json.loads(
                (log_dir / run.STATUS_PATH_ON_BRANCH).read_text(encoding="utf-8")
            )
            self.assertEqual(status["action_count"], 1)

    def test_run_stage_records_transient_preflight_failure(self):
        """Verify transient preflight failures receive a status record."""
        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            with (
                mock.patch.object(run, "LOG_DIR", log_dir),
                mock.patch.object(run, "_run_id", return_value="run-error"),
                mock.patch.object(
                    run, "load_yaml", side_effect=[{"lifecycle": {}}, OSError()]
                ),
                mock.patch.object(run, "validate_config"),
                mock.patch.object(
                    run.cas,
                    "run_preflight",
                    return_value={"ledger_path": "ledger.yaml"},
                    create=True,
                ),
            ):
                output = StringIO()
                with redirect_stdout(output):
                    result = run.run_stage(1, dry_run=True, write_status=False)
            self.assertEqual(result, 1)
            record = json.loads(output.getvalue())
            self.assertEqual(record["stop_class"], "TRANSIENT_RETRY")
            self.assertEqual(record["error"], "OSError")
            self.assertTrue((log_dir / "run-error.jsonl").is_file())

    def test_update_pinned_issue_edits_exact_title_match(self):
        listed = types.SimpleNamespace(
            returncode=0,
            stdout='[{"number": 17, "title": "PR pipeline status"}]',
        )
        edited = types.SimpleNamespace(returncode=0, stdout="")
        with mock.patch("subprocess.run", side_effect=[listed, edited]) as command:
            run.update_pinned_issue(
                {
                    "updated_at_utc": "2026-09-21T18:00:00Z",
                    "run_id": "run-fixed",
                    "stage": 1,
                    "ledger_revision": 12,
                    "reason": "OK",
                    "stop_class": None,
                }
            )
        self.assertEqual(command.call_count, 2)
        argv = command.call_args_list[1].args[0]
        self.assertEqual(argv[2:4], ["edit", "17"])
        self.assertIn("--repo", argv)

    def test_update_pinned_issue_creates_when_listing_is_malformed(self):
        listed = types.SimpleNamespace(returncode=0, stdout="not-json")
        created = types.SimpleNamespace(returncode=0, stdout="")
        with mock.patch("subprocess.run", side_effect=[listed, created]) as command:
            run.update_pinned_issue(
                {
                    "updated_at_utc": "2026-09-21T18:00:00Z",
                    "run_id": "run-fixed",
                    "stage": None,
                    "reason": "manual --status refresh",
                    "stop_class": None,
                }
            )
        self.assertEqual(command.call_args_list[1].args[0][2], "create")

    def test_main_requires_stage_when_not_refreshing_status(self):
        error = StringIO()
        with redirect_stderr(error):
            result = run.main([])
        self.assertEqual(result, 1)
        self.assertIn("--stage is required", error.getvalue())


def _exec_stage(
    stage: int,
    ledger: dict[str, Any],
    *,
    producer_override: Any = None,
    no_live_signals: bool = False,
) -> tuple[int, dict[str, Any]]:
    with TemporaryDirectory() as tmp:
        log_dir = Path(tmp)
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(run, "LOG_DIR", log_dir))
            stack.enter_context(
                mock.patch.object(run, "_run_id", return_value="test-run")
            )
            stack.enter_context(
                mock.patch.object(
                    run, "load_yaml", side_effect=[{"lifecycle": {}}, ledger]
                )
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
            stack.enter_context(
                mock.patch.object(
                    run.health,
                    "list_reselect_candidates",
                    real_health.list_reselect_candidates,
                )
            )
            stack.enter_context(
                mock.patch.object(run.health, "signal_value", real_health.signal_value)
            )
            stack.enter_context(
                mock.patch.object(
                    run.health, "is_never_touch_key", real_health.is_never_touch_key
                )
            )
            stack.enter_context(
                mock.patch.object(
                    run.health, "non_journal_paths", real_health.non_journal_paths
                )
            )
            if producer_override is not None:
                if callable(producer_override):
                    stack.enter_context(
                        mock.patch.object(
                            run, "produce_reselect_signals", producer_override
                        )
                    )
                else:
                    stack.enter_context(
                        mock.patch.object(
                            run,
                            "produce_reselect_signals",
                            return_value=producer_override,
                        )
                    )
            out = StringIO()
            with redirect_stdout(out):
                exit_code = run.run_stage(
                    stage,
                    dry_run=True,
                    write_status=False,
                    no_live_signals=no_live_signals,
                )
            return exit_code, json.loads(out.getvalue())


class ReselectSignalsTests(unittest.TestCase):
    """Integration and unit tests for live reselect signal wiring."""

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
        """Title-gated non-BOT item enqueues under live signals, drops under DEGRADED."""
        item = {
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
            "unique_remaining_paths": ["src/foo.py"],
        }
        ledger = {"ledger_revision": 1, "items": [item]}

        def stub_runner(cmd, timeout=None):
            return types.SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "state": "OPEN",
                        "mergeable": "CONFLICTING",
                        "mergeStateStatus": "DIRTY",
                        "title": "⚡️ Bolt: optimize widget cache",
                        "headRefOid": "abcd1234abcd1234abcd1234abcd1234abcd1234",
                        "author": {"login": "abhimehro"},
                        "files": [{"path": "src/foo.py"}],
                    }
                ),
                stderr="",
            )

        # 1. Under live signals: enqueued and FEED_CHECK PASS
        code, plan = _exec_stage(
            1,
            ledger,
            producer_override=lambda ledger_in: produce_reselect_signals(
                ledger_in, runner=stub_runner
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

        # 2. Same item under DEGRADED signals: not enqueued, FEED_CHECK PASS
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
        item = {
            "key": "owner/repo#42@abcd1234abcd1234abcd1234abcd1234abcd1234",
            "repository": "owner/repo",
            "pr": 42,
            "author": "dependabot[bot]",
            "author_type": "BOT",
            "head_sha": "abcd1234abcd1234abcd1234abcd1234abcd1234",
            "base_sha": "1111222233334444555566667777888899990000",
            "current_owner": "stage1",
            "lifecycle_state": "OPEN",
            "guardrail_outcome": "HOLD_CONTRACT",
            "next_action": "conflict markers in src/foo.py",
            "unique_remaining_paths": ["src/foo.py"],
        }
        ledger = {"ledger_revision": 1, "items": [item]}

        def stub_runner_clean(cmd, timeout=None):
            return types.SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "state": "OPEN",
                        "mergeable": "MERGEABLE",
                        "mergeStateStatus": "CLEAN",
                        "title": "bump deps",
                        "headRefOid": "abcd1234abcd1234abcd1234abcd1234abcd1234",
                        "author": {"login": "dependabot[bot]"},
                        "files": [{"path": "src/foo.py"}],
                    }
                ),
                stderr="",
            )

        code, plan = _exec_stage(
            1,
            ledger,
            producer_override=lambda ledger_in: produce_reselect_signals(
                ledger_in, runner=stub_runner_clean
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
        item = {
            "key": "owner/repo#43@abcd1234abcd1234abcd1234abcd1234abcd1234",
            "repository": "owner/repo",
            "pr": 43,
            "author": "dependabot[bot]",
            "author_type": "BOT",
            "head_sha": "abcd1234abcd1234abcd1234abcd1234abcd1234",
            "base_sha": "1111222233334444555566667777888899990000",
            "current_owner": "stage3",
            "lifecycle_state": "STAGE3_RECONCILIATION",
            "guardrail_outcome": "HOLD_CONTRACT",
            "next_action": "conflict markers in src/foo.py",
            "unique_remaining_paths": ["src/foo.py"],
        }
        ledger = {"ledger_revision": 1, "items": [item]}

        def stub_runner_merg(cmd, timeout=None):
            return types.SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "state": "OPEN",
                        "mergeable": "MERGEABLE",
                        "mergeStateStatus": "CLEAN",
                        "title": "bump deps",
                        "headRefOid": "abcd1234abcd1234abcd1234abcd1234abcd1234",
                        "author": {"login": "dependabot[bot]"},
                        "files": [{"path": "src/foo.py"}],
                    }
                ),
                stderr="",
            )

        def stub_runner_conf(cmd, timeout=None):
            return types.SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "state": "OPEN",
                        "mergeable": "CONFLICTING",
                        "mergeStateStatus": "DIRTY",
                        "title": "bump deps",
                        "headRefOid": "abcd1234abcd1234abcd1234abcd1234abcd1234",
                        "author": {"login": "dependabot[bot]"},
                        "files": [{"path": "src/foo.py"}],
                    }
                ),
                stderr="",
            )

        # When live is MERGEABLE: no handoff
        code, plan_merg = _exec_stage(
            3,
            ledger,
            producer_override=lambda ledger_in: produce_reselect_signals(
                ledger_in, runner=stub_runner_merg
            ),
        )
        self.assertEqual(code, 0)
        handoffs_merg = [
            a
            for a in plan_merg["actions"]
            if a.get("action") == "HANDOFF_MECHANICAL_TO_STAGE2"
        ]
        self.assertEqual(len(handoffs_merg), 0)

        # When live is CONFLICTING: handoff emitted
        code, plan_conf = _exec_stage(
            3,
            ledger,
            producer_override=lambda ledger_in: produce_reselect_signals(
                ledger_in, runner=stub_runner_conf
            ),
        )
        self.assertEqual(code, 0)
        handoffs_conf = [
            a
            for a in plan_conf["actions"]
            if a.get("action") == "HANDOFF_MECHANICAL_TO_STAGE2"
        ]
        self.assertEqual(len(handoffs_conf), 1)
        self.assertEqual(handoffs_conf[0]["source_key"], item["key"])


class TestDependencyPreflight(unittest.TestCase):
    """Missing runtime deps fail fast with an install hint, not a traceback."""

    def test_missing_yaml_exits_2_with_hint(self) -> None:
        """Run with -S (no site-packages) to simulate a bare interpreter."""
        proc = subprocess.run(
            [sys.executable, "-S", str(SCRIPTS / "pr_lifecycle_run.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn(
            "PR_LIFECYCLE_RUN_ERROR: missing Python dependencies", proc.stderr
        )
        self.assertIn("pyyaml", proc.stderr)
        self.assertIn("requirements.txt", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
