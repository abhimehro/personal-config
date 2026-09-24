"""Unit tests for pr_lifecycle_run plan shape and CLI emission."""

from __future__ import annotations

import json
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from tests.pr_lifecycle_helpers import import_lifecycle_run, make_health_report

run = import_lifecycle_run()

_report = make_health_report


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
