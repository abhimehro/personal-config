"""Producer wiring and end-to-end live-signal tests for run stage plans.

Split from test_pr_lifecycle_run_signals.py; shared helpers are imported from
that module.
"""

from __future__ import annotations

import functools
import unittest
from unittest import mock

from tests.test_pr_lifecycle_run_signals import (  # noqa: E402
    _dependabot_item,
    _exec_stage,
    _namespace_runner,
    _open_payload,
    _title_gated_item,
    produce_reselect_signals,
    real_health,
    run,
    SignalsResult,
)


class ProducerWiringTests(unittest.TestCase):
    """Producer invocation, flag plumbing, and e2e signal-driven actions."""

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
            base_enriched_count=2,
            candidate_count=2,
        )
        mock_producer = mock.Mock(return_value=result_payload)

        # Stage 1
        ledger = {"ledger_revision": 1, "items": []}
        code, plan = _exec_stage(1, ledger, producer_override=mock_producer)
        self.assertEqual(code, 0)
        mock_producer.assert_called_with(ledger)
        self.assertEqual(plan["signals_status"], "OK")
        self.assertEqual(plan["signals_queried"], 2)
        self.assertEqual(plan["signals_candidates"], 2)
        self.assertEqual(plan["signals_base_enriched"], 2)
        status_doc = run.write_status_doc(plan, "rid")
        self.assertEqual(status_doc["signals_base_enriched"], 2)
        self.assertEqual(status_doc["signals_queried"], 2)
        self.assertEqual(status_doc["signals_candidates"], 2)
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

    def _degraded_plan(self, result_payload):
        """Run stage 1 under a producer stub; return (plan, degraded note)."""
        ledger = {"ledger_revision": 1, "items": []}
        code, plan = _exec_stage(
            1, ledger, producer_override=mock.Mock(return_value=result_payload)
        )
        self.assertEqual(code, 0)
        note = next(
            a["note"] for a in plan["actions"] if a.get("action") == "SIGNALS_DEGRADED"
        )
        return plan, note

    def test_base_enrichment_gap_partial_reports_missing_base_note(self):
        """Zero base enrichments across clean views -> PARTIAL with a
        missing-base note (not the failed-keys note, which would mislead)."""
        plan, note = self._degraded_plan(
            SignalsResult(
                signals=real_health.ReselectSignals(),
                status="PARTIAL",
                queried_count=3,
                base_enriched_count=0,
                open_count=3,
            )
        )
        self.assertEqual(plan["signals_status"], "PARTIAL")
        self.assertEqual(plan["signals_base_enriched"], 0)
        self.assertIn("live base anchors missing", note)
        self.assertNotIn("failed keys", note)

    def test_candidate_cap_clip_partial_reports_coverage_note(self):
        """A clean scan clipped by max_prs -> PARTIAL naming the clipped
        coverage so unqueried surplus keys are not invisible."""
        plan, note = self._degraded_plan(
            SignalsResult(
                signals=real_health.ReselectSignals(),
                status="PARTIAL",
                queried_count=2,
                candidate_count=5,
            )
        )
        self.assertEqual(plan["signals_status"], "PARTIAL")
        self.assertEqual(plan["signals_candidates"], 5)
        self.assertIn("candidate cap clipped", note)
        self.assertIn("2 of 5", note)
        self.assertNotIn("failed keys", note)

    def test_budget_truncation_partial_reports_truncated_scan_note(self):
        """Budget elapsed mid-scan -> PARTIAL with a truncation note, not the
        failed-keys note (nothing failed; keys were simply never queried)."""
        plan, note = self._degraded_plan(
            SignalsResult(
                signals=real_health.ReselectSignals(),
                status="PARTIAL",
                queried_count=1,
                elapsed_s=120.0,
                timed_out=True,
            )
        )
        self.assertEqual(plan["signals_status"], "PARTIAL")
        self.assertTrue(plan["signals_timed_out"])
        self.assertIn("truncated by total budget", note)
        self.assertNotIn("failed keys", note)

    def test_mixed_truncation_and_failures_name_both_causes(self):
        """Budget elapsed *and* queries failed -> the note mentions both so
        real failures are not hidden behind the truncation wording."""
        _, note = self._degraded_plan(
            SignalsResult(
                signals=real_health.ReselectSignals(),
                status="PARTIAL",
                queried_count=3,
                failed_keys=("owner/repo#1",),
                timed_out=True,
            )
        )
        self.assertIn("failed keys", note)
        self.assertIn("truncated by total budget", note)
        self.assertIn("keys | live scan", note)

    def test_hard_degraded_after_success_names_abort_and_base_gap(self):
        """MAX_CONSECUTIVE_FAILURES after one clean view -> the note carries
        the failure, the abort, and the base gap with a 0/1 denominator."""
        plan, note = self._degraded_plan(
            SignalsResult(
                signals=real_health.ReselectSignals(),
                status="DEGRADED",
                queried_count=4,
                failed_keys=("a#1", "b#2", "c#3"),
                base_enriched_count=0,
                open_count=1,
            )
        )
        self.assertEqual(plan["signals_status"], "DEGRADED")
        self.assertIn("failed keys", note)
        self.assertIn("scan aborted", note)
        self.assertIn("0/1 enriched", note)
        self.assertNotIn("otherwise complete", note)

    def test_degraded_without_queries_suppresses_base_clause(self):
        """Producer-exception shape (nothing queried) -> abort named, the
        0/0 base clause suppressed."""
        _, note = self._degraded_plan(
            SignalsResult(
                signals=real_health.ReselectSignals(),
                status="DEGRADED",
                queried_count=0,
            )
        )
        self.assertIn("scan aborted", note)
        self.assertNotIn("enriched", note)

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
