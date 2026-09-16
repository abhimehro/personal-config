"""Fail-closed feed cascade: Stage 1 fingerprint + Stage 2/3 short-circuit."""

from __future__ import annotations

import copy
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_feed_cascade as cascade  # noqa: E402
import pr_lifecycle_feed_cascade_verify as verifier  # noqa: E402
import pr_lifecycle_pipeline_health as health  # noqa: E402
import yaml  # noqa: E402

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
VERIFY = SCRIPTS / "pr_lifecycle_feed_cascade_verify.py"
EXAMPLE = ROOT / "tasks/pr-lifecycle-ledger.example.yaml"


def _item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "key": "abhimehro/demo#1@abc",
        "author_type": "BOT",
        "lifecycle_state": "STAGE3_RECONCILIATION",
        "current_owner": "stage3",
        "guardrail_outcome": "HOLD_CONTRACT",
        "sensitive_paths": ["generated_output"],
        "next_action": (
            "Recover unique source only on a new focused draft that "
            "excludes .jules/journals/"
        ),
    }
    base.update(overrides)
    return base


def _work_item(**overrides: object) -> dict[str, object]:
    sha = "0123456789abcdef0123456789abcdef01234567"
    base: dict[str, object] = {
        "work_item_id": "s2-20260916-demo",
        "source_item_key": f"abhimehro/demo#1@{sha}",
        "repository": "abhimehro/demo",
        "pr": 1,
        "base_sha": sha,
        "head_sha": sha,
        "allowed_paths": ["src/demo.py"],
        "prohibited_paths": [],
        "repair_description": "Repair the demo path.",
        "required_test_command": "python3 -m unittest",
        "expected_test_result": "ok",
        "acceptance_criteria": ["Allowed path changes only."],
        "provenance_urls": ["https://github.com/abhimehro/demo/pull/1"],
        "expiry_utc": "2026-09-18T12:00:00Z",
        "attempt_count": 0,
        "current_owner": "stage2",
        "creation_event_id": "evt-20260916-demo",
        "history": [],
    }
    base.update(overrides)
    return base


def _ledger(
    items: list[dict[str, object]],
    work_items: list[dict[str, object]],
    revision: int = 70,
) -> dict[str, object]:
    return {
        "ledger_revision": revision,
        "items": items,
        "stage2_work_items": work_items,
    }


def _run_verify_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFY), *args],
        check=False,
        capture_output=True,
        text=True,
    )


class TestStage1FeedFingerprint(unittest.TestCase):
    def test_fail_when_eligible_and_queued_zero(self) -> None:
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=3,
        )
        self.assertEqual(fp.throughput_grade, "FAIL")

    def test_pass_when_queued_or_drained(self) -> None:
        queued = cascade.grade_stage1_feed(
            stage2_queued_count=1,
            salvage_eligible_count=2,
        )
        drained = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=0,
        )
        self.assertEqual(queued.throughput_grade, "PASS")
        self.assertEqual(drained.throughput_grade, "PASS")

    def test_drain_failure_signals_fail_and_preserve_counts(self) -> None:
        cases = (
            ("docs-only", {"docs_only_bookkeeping": True}),
            (
                "unused product slots",
                {"product_slots_unused_while_bot_grew": True},
            ),
        )
        for label, signal in cases:
            with self.subTest(label):
                fingerprint = cascade.grade_stage1_feed(
                    stage2_queued_count=2,
                    salvage_eligible_count=3,
                    **signal,
                )
                self.assertEqual(fingerprint.throughput_grade, "FAIL")
                self.assertEqual(fingerprint.stage2_queued_count, 2)
                self.assertEqual(fingerprint.salvage_eligible_count, 3)


class TestStage2Cascade(unittest.TestCase):
    def test_starvation_is_feed_fail(self) -> None:
        report = health.summarize(_ledger([_item()], []), now=NOW)
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=report.salvage_eligible_count,
        )
        decision = cascade.stage2_cascade_decision(
            report, fp, usable_work_item_count=0
        )
        self.assertEqual(decision.action, "FEED_FAIL")
        self.assertIn(decision.label, {"EMPTY_INTAKE_STARVATION", "FEED_FAIL"})

    def test_claim_when_complete_wi_present(self) -> None:
        report = health.summarize(
            _ledger([_item()], [_work_item()]),
            now=NOW,
        )
        self.assertFalse(report.starvation)
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=1,
            salvage_eligible_count=report.salvage_eligible_count,
        )
        claimable = cascade.claimable_work_items(
            _ledger([_item()], [_work_item()]),
            now=NOW,
        )
        decision = cascade.stage2_cascade_decision(
            report, fp, usable_work_item_count=len(claimable)
        )
        self.assertEqual(decision.action, "PROCEED")
        self.assertEqual(len(claimable), 1)
        self.assertEqual(claimable[0]["work_item_id"], "s2-20260916-demo")

    def test_claim_prior_wi_before_zero_queue_fingerprint(self) -> None:
        """Leftover complete WIs must be claimed even if today's feed queued 0."""
        report = health.summarize(
            _ledger([_item()], [_work_item()]),
            now=NOW,
        )
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=1,
        )
        decision = cascade.stage2_cascade_decision(
            report, fp, usable_work_item_count=1
        )
        self.assertEqual(decision.action, "PROCEED")
        self.assertEqual(decision.label, "CLAIM")

    def test_materializable_item_takes_precedence_over_starvation(self) -> None:
        report = health.summarize(_ledger([_item()], []), now=NOW)
        fingerprint = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=1,
        )
        decision = cascade.stage2_cascade_decision(
            report,
            fingerprint,
            usable_work_item_count=0,
            stage2_owned_materializable=1,
        )
        self.assertTrue(report.starvation)
        self.assertEqual(decision.action, "PROCEED")
        self.assertEqual(decision.label, "CLAIM")

    def test_fingerprint_starvation_reports_feed_counts(self) -> None:
        report = health.summarize(_ledger([], []), now=NOW)
        fingerprint = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=4,
        )
        decision = cascade.stage2_cascade_decision(
            report, fingerprint, usable_work_item_count=0
        )
        self.assertEqual(decision.action, "FEED_FAIL")
        self.assertEqual(decision.label, "FEED_FAIL")
        self.assertIn("queued=0, eligible=4", decision.reason)

    def test_missing_or_nonstarvation_fail_fingerprint_is_empty(self) -> None:
        report = health.summarize(_ledger([], []), now=NOW)
        docs_failure = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=0,
            docs_only_bookkeeping=True,
        )
        for label, fingerprint in (
            ("missing", None),
            ("non-starvation failure", docs_failure),
        ):
            with self.subTest(label):
                decision = cascade.stage2_cascade_decision(
                    report, fingerprint, usable_work_item_count=0
                )
                self.assertEqual(decision.action, "EMPTY_INTAKE")
                self.assertEqual(decision.label, "EMPTY_INTAKE")

    def test_empty_intake_when_nothing_eligible(self) -> None:
        blocked = _item(guardrail_outcome="REVIEW_SECURITY")
        report = health.summarize(_ledger([blocked], []), now=NOW)
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=0,
        )
        decision = cascade.stage2_cascade_decision(
            report, fp, usable_work_item_count=0
        )
        self.assertEqual(decision.action, "EMPTY_INTAKE")


class TestStage3Cascade(unittest.TestCase):
    """Single matrix avoids CodeScene Code Duplication across pause/proceed."""

    def test_stage3_decision_matrix(self) -> None:
        healthy = health.summarize(
            _ledger([_item()], [_work_item()]),
            now=NOW,
        )
        starved = health.summarize(_ledger([_item()], []), now=NOW)
        empty = health.summarize(_ledger([], []), now=NOW)
        cases = (
            (
                "pause on stage1 fail",
                empty,
                cascade.grade_stage1_feed(
                    stage2_queued_count=0,
                    salvage_eligible_count=0,
                    docs_only_bookkeeping=True,
                ),
                False,
                "UPSTREAM_PAUSE",
                "Stage 1 throughput_grade FAIL",
            ),
            (
                "pause when stage2 feed fail",
                healthy,
                cascade.grade_stage1_feed(
                    stage2_queued_count=0,
                    salvage_eligible_count=1,
                ),
                True,
                "UPSTREAM_PAUSE",
                "Stage 2 stopped on FEED_FAIL",
            ),
            (
                "pause on health starvation",
                starved,
                cascade.grade_stage1_feed(
                    stage2_queued_count=1,
                    salvage_eligible_count=1,
                ),
                False,
                "UPSTREAM_PAUSE",
                "EMPTY_INTAKE",
            ),
            (
                "pause when fingerprint missing",
                healthy,
                None,
                False,
                "UPSTREAM_PAUSE",
                "Missing same-day",
            ),
            (
                "proceed when healthy",
                healthy,
                cascade.grade_stage1_feed(
                    stage2_queued_count=1,
                    salvage_eligible_count=1,
                ),
                False,
                "PROCEED",
                "Upstream feed healthy",
            ),
        )
        for label, report, fingerprint, s2_fail, expected, reason in cases:
            with self.subTest(label):
                decision = cascade.stage3_cascade_decision(
                    report,
                    fingerprint,
                    stage2_feed_fail_same_utc_day=s2_fail,
                )
                self.assertEqual(decision.action, expected)
                self.assertIn(reason, decision.reason)


class TestClaimableWorkItems(unittest.TestCase):
    def test_filters_malformed_expired_and_wrong_owner_entries(self) -> None:
        first = _work_item(work_item_id="first")
        second = _work_item(work_item_id="second")
        invalid = (
            "not-a-mapping",
            _work_item(
                work_item_id="expired",
                expiry_utc="2026-09-16T12:00:00Z",
            ),
            _work_item(work_item_id="wrong-owner", current_owner="stage3"),
            _work_item(work_item_id="incomplete", acceptance_criteria=[]),
        )
        ledger = _ledger([], [first, *invalid, second])  # type: ignore[list-item]
        claimable = cascade.claimable_work_items(ledger, now=NOW)
        self.assertEqual(
            [item["work_item_id"] for item in claimable],
            ["first", "second"],
        )
        self.assertIs(claimable[0], first)
        self.assertIs(claimable[1], second)

    def test_missing_or_nonlist_work_items_are_not_claimable(self) -> None:
        cases: tuple[dict[str, Any], ...] = (
            {},
            {"stage2_work_items": None},
            {"stage2_work_items": {}},
            {"stage2_work_items": "queued"},
        )
        for ledger in cases:
            with self.subTest(raw=ledger.get("stage2_work_items")):
                self.assertEqual(
                    cascade.claimable_work_items(ledger, now=NOW),
                    [],
                )


class TestSampleEmissionAndClaim(unittest.TestCase):
    """Sample Stage 1 WI emission → Stage 2 claim without live CAS."""

    def test_inject_sample_clears_starvation_and_is_claimable(self) -> None:
        starved = _ledger([_item()], [])
        before = health.summarize(starved, now=NOW)
        self.assertTrue(before.starvation)
        after_ledger = copy.deepcopy(starved)
        after_ledger["stage2_work_items"] = [_work_item()]
        after = health.summarize(after_ledger, now=NOW)
        self.assertFalse(after.starvation)
        claimable = cascade.claimable_work_items(after_ledger, now=NOW)
        self.assertEqual(len(claimable), 1)
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=1,
            salvage_eligible_count=after.salvage_eligible_count,
        )
        s2 = cascade.stage2_cascade_decision(
            after, fp, usable_work_item_count=len(claimable)
        )
        self.assertEqual(s2.action, "PROCEED")
        self.assertNotEqual(s2.label, "EMPTY_INTAKE")

    def test_verify_cli_inject_sample(self) -> None:
        if not EXAMPLE.is_file():
            self.skipTest("example ledger missing")
        # Reuse the health-suite starved fixture (event↔item integrity).
        sys.path.insert(0, str(ROOT / "tests"))
        from test_pr_lifecycle_pipeline_health import (  # noqa: E402
            _schema_valid_starved_ledger,
        )

        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "ledger.yaml"
            ledger_path.write_text(
                yaml.safe_dump(_schema_valid_starved_ledger(), sort_keys=False),
                encoding="utf-8",
            )
            original = ledger_path.read_bytes()
            baseline = _run_verify_cli("--ledger", str(ledger_path))
            injected = _run_verify_cli(
                "--ledger", str(ledger_path), "--inject-sample"
            )
            self.assertEqual(ledger_path.read_bytes(), original)
        self.assertEqual(
            baseline.returncode,
            2,
            msg=baseline.stderr + baseline.stdout,
        )
        self.assertEqual(
            injected.returncode,
            0,
            msg=injected.stderr + injected.stdout,
        )
        self.assertIn('"action": "PROCEED"', injected.stdout)
        self.assertIn("s2-sample-feed-cascade", injected.stdout)
        injected_path = Path(
            next(
                line.split("=", 1)[1]
                for line in injected.stdout.splitlines()
                if line.startswith("injected_sample_path=")
            )
        )
        self.assertFalse(injected_path.exists())


class TestVerifierHelpers(unittest.TestCase):
    def test_sample_work_item_is_complete_unexpired_and_utc(self) -> None:
        sample = verifier._sample_work_item(NOW)
        self.assertEqual(sample["expiry_utc"], "2026-09-18T12:00:00Z")
        self.assertTrue(set(health.REQUIRED_WORK_ITEM_FIELDS) <= sample.keys())
        self.assertEqual(sample["base_sha"], sample["head_sha"])
        self.assertEqual(
            cascade.claimable_work_items({"stage2_work_items": [sample]}, NOW),
            [sample],
        )

    def test_append_sample_copies_input_and_replaces_nonlist(self) -> None:
        source = {"items": [{"key": "original"}], "stage2_work_items": "bad"}
        sample = _work_item()
        mutated = verifier._append_sample(source, sample)
        mutated["items"][0]["key"] = "changed"
        self.assertEqual(source["items"][0]["key"], "original")
        self.assertEqual(source["stage2_work_items"], "bad")
        self.assertEqual(mutated["stage2_work_items"], [sample])

    def test_maybe_inject_preserves_source_and_removes_temp_file(self) -> None:
        source = _ledger([_item()], [])
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            injected = verifier._maybe_inject(source, inject=True, now=NOW)
        self.assertEqual(source["stage2_work_items"], [])
        self.assertIsNotNone(injected)
        self.assertEqual(len(injected["stage2_work_items"]), 1)
        temp_path = Path(stdout.getvalue().strip().split("=", 1)[1])
        self.assertFalse(temp_path.exists())

    def test_maybe_inject_false_returns_original_mapping(self) -> None:
        source = _ledger([], [])
        self.assertIs(
            verifier._maybe_inject(source, inject=False, now=NOW),
            source,
        )

    def test_reload_failure_reports_error_and_removes_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "injected.yaml"
            path.write_text("items: []\n", encoding="utf-8")
            stderr = io.StringIO()
            with patch.object(verifier, "load_yaml", side_effect=ValueError("bad")):
                with redirect_stderr(stderr):
                    result = verifier._reload_injected(path)
            self.assertIsNone(result)
            self.assertFalse(path.exists())
            self.assertIn("inject reload: bad", stderr.getvalue())

    def test_reload_nonmapping_reports_empty_and_removes_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "injected.yaml"
            path.write_text("items: []\n", encoding="utf-8")
            stderr = io.StringIO()
            with patch.object(verifier, "load_yaml", return_value=[]):
                with redirect_stderr(stderr):
                    result = verifier._reload_injected(path)
            self.assertIsNone(result)
            self.assertFalse(path.exists())
            self.assertIn("inject reload empty", stderr.getvalue())

    def test_build_snapshot_maps_starved_and_claimable_ledgers(self) -> None:
        cases = (
            ("starved", _ledger([_item()], []), "FEED_FAIL", "UPSTREAM_PAUSE"),
            (
                "claimable",
                _ledger([_item()], [_work_item()]),
                "PROCEED",
                "PROCEED",
            ),
        )
        for label, ledger, stage2_action, stage3_action in cases:
            with self.subTest(label):
                snapshot = verifier._build_snapshot(ledger, now=NOW)
                self.assertEqual(snapshot.stage2_decision.action, stage2_action)
                self.assertEqual(snapshot.stage3_decision.action, stage3_action)

    def test_verify_exit_code_matrix(self) -> None:
        starved = health.summarize(_ledger([_item()], []), now=NOW)
        clear = health.summarize(_ledger([], []), now=NOW)
        fingerprint = cascade.grade_stage1_feed(
            stage2_queued_count=0, salvage_eligible_count=0
        )
        proceed = cascade.CascadeDecision("PROCEED", "CLAIM", "claim")
        empty = cascade.CascadeDecision("EMPTY_INTAKE", "EMPTY_INTAKE", "empty")
        cases = (
            ("starved", starved, proceed, [_work_item()], 2),
            ("claimless proceed", clear, proceed, [], 1),
            ("empty intake", clear, empty, [], 0),
        )
        for label, report, stage2, claimable, expected in cases:
            with self.subTest(label):
                snapshot = verifier.DecisionSnapshot(
                    report, fingerprint, stage2, empty, claimable
                )
                self.assertEqual(verifier._verify_exit_code(snapshot), expected)

    def test_verify_ledger_prints_all_sections(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = verifier.verify_ledger(_ledger([], []), now=NOW)
        self.assertEqual(status, 0)
        for label in ("health", "fingerprint", "stage2", "stage3", "claimable"):
            self.assertIn(f"== {label} ==", stdout.getvalue())


class TestVerifierCliErrors(unittest.TestCase):
    def test_missing_ledger_exits_one_with_fetch_guidance(self) -> None:
        missing = ROOT / "does-not-exist-feed-cascade-ledger.yaml"
        result = _run_verify_cli("--ledger", str(missing))
        self.assertEqual(result.returncode, 1)
        self.assertIn("file not found. Fetch first", result.stderr)

    def test_invalid_runtime_ledger_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.yaml"
            path.write_text("items: []\nstage2_work_items: []\n", encoding="utf-8")
            result = _run_verify_cli("--ledger", str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("ledger validation failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
