"""Unit tests for pr_lifecycle_run plan shape and CLI emission."""

from __future__ import annotations

import json
import os
import runpy
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

from tests.pr_lifecycle_helpers import (
    SCRIPTS,
    import_lifecycle_run,
    make_health_report,
    make_item,
    make_ledger,
)

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

    def test_consecutive_query_failures_preserve_exclusions_in_stage_plans(
        self,
    ) -> None:
        for stage, action_name in (
            (1, "ENQUEUE_STAGE2_WI"),
            (3, "HANDOFF_MECHANICAL_TO_STAGE2"),
        ):
            with self.subTest(stage=stage):
                items = [
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
                    for n in range(1, 7)
                ]
                payloads = [
                    {"state": "MERGED"},
                    {"state": "OPEN", "headRefOid": "new-head"},
                ]
                runner = mock.Mock(
                    side_effect=[
                        *[
                            subprocess.CompletedProcess(
                                args=["gh"], returncode=0, stdout=json.dumps(payload)
                            )
                            for payload in payloads
                        ],
                        *[
                            subprocess.CompletedProcess(
                                args=["gh"], returncode=1, stdout=""
                            )
                            for _ in range(3)
                        ],
                    ]
                )
                ledger = make_ledger(items, [])
                result = produce_reselect_signals(ledger, runner=runner)
                with mock.patch.object(run.health, "summarize", real_health.summarize):
                    code, plan = _exec_stage(stage, ledger, producer_override=result)
                self.assertEqual(runner.call_count, 5)
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
                self.assertEqual(
                    [a["allowed_paths"] for a in actions], [["src/ledger.py"]] * 4
                )
                if stage == 1:
                    feed = next(
                        a for a in plan["actions"] if a["action"] == "FEED_CHECK"
                    )
                    self.assertEqual(feed["grade"], "PASS")
                    self.assertEqual(feed["enqueued"], 4)

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
                    runner = mock.Mock(
                        return_value=subprocess.CompletedProcess(
                            args=["gh", "pr", "view"],
                            returncode=0,
                            stdout=json.dumps(
                                {"state": "OPEN", "headRefOid": "abc", "files": files}
                            ),
                            stderr="",
                        )
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
                    if stage == 1:
                        feed = next(
                            a for a in plan["actions"] if a["action"] == "FEED_CHECK"
                        )
                        self.assertEqual(feed["grade"], "PASS")
                        self.assertEqual(feed["enqueued"], len(actions))

    def test_partial_signals_mix_live_exclusions_with_ledger_fallback(self):
        for stage, action_name in (
            (1, "ENQUEUE_STAGE2_WI"),
            (3, "HANDOFF_MECHANICAL_TO_STAGE2"),
        ):
            with self.subTest(stage=stage):
                items = [
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
                    for n in range(1, 6)
                ]
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
                degraded = [
                    a for a in plan["actions"] if a["action"] == "SIGNALS_DEGRADED"
                ]
                self.assertEqual(len(degraded), 1)
                self.assertEqual(degraded[0]["status"], "PARTIAL")
                if stage == 1:
                    feed = next(
                        a for a in plan["actions"] if a["action"] == "FEED_CHECK"
                    )
                    self.assertEqual(feed["grade"], "PASS")
                    self.assertEqual(feed["reselect_candidates"], 2)
                    self.assertEqual(feed["enqueued"], 2)
                    self.assertEqual(feed["condition"], "SIGNALS_DEGRADED")

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
                    3, make_ledger([], []), {}, signals_status=signal_status
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

    def test_each_missing_dependency_is_reported_without_importing_planner(
        self,
    ) -> None:
        for missing, packages in (
            ({"yaml"}, "pyyaml"),
            ({"jsonschema"}, "jsonschema"),
            ({"yaml", "jsonschema"}, "pyyaml, jsonschema"),
        ):
            with self.subTest(missing=missing):
                stderr = StringIO()
                with (
                    mock.patch(
                        "importlib.util.find_spec",
                        side_effect=lambda name, missing=missing: (
                            None if name in missing else mock.sentinel.spec
                        ),
                    ),
                    redirect_stderr(stderr),
                    self.assertRaises(SystemExit) as raised,
                ):
                    runpy.run_path(str(SCRIPTS / "pr_lifecycle_run.py"))
                self.assertEqual(raised.exception.code, 2)
                self.assertIn(
                    f"missing Python dependencies: {packages} (", stderr.getvalue()
                )
                self.assertIn(sys.executable, stderr.getvalue())
                self.assertIn(
                    "python3 -m pip install -r requirements.txt", stderr.getvalue()
                )
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_missing_yaml_exits_2_with_hint(self) -> None:
        """Run isolated (-I) without site-packages (-S) as a bare interpreter."""
        # -I ignores PYTHON* env vars and user site; drop PYTHONPATH as well.
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        flags = [sys.executable, "-I", "-S"]
        probe = subprocess.run(
            [*flags, "-c", "import yaml"],
            capture_output=True,
            env=env,
            check=False,
            timeout=60,
        )
        if probe.returncode == 0:
            self.skipTest("yaml importable under -I -S; cannot simulate missing deps")
        proc = subprocess.run(
            [*flags, str(SCRIPTS / "pr_lifecycle_run.py"), "--help"],
            capture_output=True,
            text=True,
            env=env,
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
