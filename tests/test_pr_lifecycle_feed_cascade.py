"""Heal-forward feed cascade: Stage 1 fingerprint + Stage 2/3 continue."""

from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_feed_cascade as cascade  # noqa: E402
import pr_lifecycle_feed_cascade_verify as verify_mod  # noqa: E402
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

    def test_docs_only_is_fail(self) -> None:
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=0,
            docs_only_bookkeeping=True,
        )
        self.assertEqual(fp.throughput_grade, "FAIL")


class TestStage2Cascade(unittest.TestCase):
    def test_starvation_is_feed_fail(self) -> None:
        """Starved Stage 2 feeds must heal and continue."""
        report = health.summarize(_ledger([_item()], []), now=NOW)
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=report.salvage_eligible_count,
        )
        decision = cascade.stage2_cascade_decision(report, fp, usable_work_item_count=0)
        self.assertEqual(decision.action, "HEAL_THEN_PROCEED")
        self.assertIn(decision.label, {"EMPTY_INTAKE_STARVATION", "FEED_FAIL"})
        self.assertTrue(cascade.unhealthy_stage2_feed(decision))

    def test_claim_when_complete_wi_present(self) -> None:
        """A complete work item must remain immediately claimable."""
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
        decision = cascade.stage2_cascade_decision(report, fp, usable_work_item_count=1)
        self.assertEqual(decision.action, "PROCEED")
        self.assertEqual(decision.label, "CLAIM")

    def test_claim_when_owned_without_wi(self) -> None:
        """Owned Stage-2 items CLAIM even when starvation is still true."""
        owned = _item(
            current_owner="stage2",
            lifecycle_state="STAGE2_QUEUED",
        )
        remainder = _item(key="abhimehro/demo#2@def")
        report = health.summarize(
            _ledger([owned, remainder], []),
            now=NOW,
        )
        self.assertTrue(report.starvation)
        self.assertEqual(report.stage2_owned_item_count, 1)
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=report.salvage_eligible_count,
        )
        decision = cascade.stage2_cascade_decision(
            report,
            fp,
            usable_work_item_count=0,
            stage2_owned_materializable=report.stage2_owned_item_count,
        )
        self.assertEqual(decision.action, "PROCEED")
        self.assertEqual(decision.label, "CLAIM")

    def test_empty_intake_when_nothing_eligible(self) -> None:
        """No eligible remainder must produce an empty-intake decision."""
        blocked = _item(guardrail_outcome="REVIEW_SECURITY")
        report = health.summarize(_ledger([blocked], []), now=NOW)
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=0,
        )
        decision = cascade.stage2_cascade_decision(report, fp, usable_work_item_count=0)
        self.assertEqual(decision.action, "EMPTY_INTAKE")

    def test_unhealthy_feed_requires_stage2_failure_label(self) -> None:
        cases = (
            ("FEED_FAIL", "HEAL_THEN_PROCEED", True),
            ("EMPTY_INTAKE_STARVATION", "HEAL_THEN_PROCEED", True),
            ("UPSTREAM_HEAL", "HEAL_THEN_PROCEED", False),
            ("CLAIM", "PROCEED", False),
            ("EMPTY_INTAKE", "EMPTY_INTAKE", False),
        )
        for label, action, expected in cases:
            with self.subTest(label):
                decision = cascade.CascadeDecision(action, label, "test")
                self.assertEqual(cascade.unhealthy_stage2_feed(decision), expected)


class TestStage3Cascade(unittest.TestCase):
    """Single matrix avoids CodeScene Code Duplication across pause/proceed."""

    def test_stage3_decision_matrix(self) -> None:
        """Stage 3 must heal unhealthy feeds and proceed on healthy ones."""
        healthy = health.summarize(
            _ledger([_item()], [_work_item()]),
            now=NOW,
        )
        starved = health.summarize(_ledger([_item()], []), now=NOW)
        empty = health.summarize(_ledger([], []), now=NOW)
        cases = (
            (
                "heal on stage1 fail",
                empty,
                cascade.grade_stage1_feed(
                    stage2_queued_count=0,
                    salvage_eligible_count=0,
                    docs_only_bookkeeping=True,
                ),
                False,
                ("HEAL_THEN_PROCEED", "UPSTREAM_HEAL"),
            ),
            (
                "heal when stage2 feed fail",
                starved,
                cascade.grade_stage1_feed(
                    stage2_queued_count=0,
                    salvage_eligible_count=1,
                ),
                True,
                ("HEAL_THEN_PROCEED", "UPSTREAM_HEAL"),
            ),
            (
                "heal when fingerprint missing",
                healthy,
                None,
                False,
                ("HEAL_THEN_PROCEED", "UPSTREAM_HEAL"),
            ),
            (
                "proceed when healthy",
                healthy,
                cascade.grade_stage1_feed(
                    stage2_queued_count=1,
                    salvage_eligible_count=1,
                ),
                False,
                ("PROCEED", "COMPLETE"),
            ),
        )
        for label, report, fingerprint, s2_fail, expected in cases:
            with self.subTest(label):
                decision = cascade.stage3_cascade_decision(
                    report,
                    fingerprint,
                    stage2_feed_fail_same_utc_day=s2_fail,
                )
                self.assertEqual((decision.action, decision.label), expected)


class TestSampleEmissionAndClaim(unittest.TestCase):
    """Sample Stage 1 WI emission → Stage 2 claim without live CAS."""

    def test_inject_sample_clears_starvation_and_is_claimable(self) -> None:
        """Injecting a valid work item must clear starvation for claiming."""
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

    def test_verify_exit_claim_beats_starvation(self) -> None:
        """A materializable Stage 2 claim must yield a successful exit."""
        owned = _item(
            current_owner="stage2",
            lifecycle_state="STAGE2_QUEUED",
        )
        remainder = _item(key="abhimehro/demo#2@def")
        snapshot = verify_mod._build_snapshot(
            _ledger([owned, remainder], []),
            now=NOW,
        )
        self.assertEqual(snapshot.stage2_decision.action, "PROCEED")
        self.assertEqual(verify_mod._verify_exit_code(snapshot), 0)

    def test_verify_owned_item_claims_without_salvage_remainder(self) -> None:
        """Stage-2-owned stock is work even when health is not starved."""
        owned = _item(
            current_owner="stage2",
            lifecycle_state="STAGE2_QUEUED",
        )

        snapshot = verify_mod._build_snapshot(_ledger([owned], []), now=NOW)

        self.assertFalse(snapshot.health.starvation)
        self.assertEqual(snapshot.claimable, [])
        self.assertEqual(
            (snapshot.stage2_decision.action, snapshot.stage2_decision.label),
            ("PROCEED", "CLAIM"),
        )
        self.assertEqual(verify_mod._verify_exit_code(snapshot), 0)

    def test_verify_leftover_stock_is_not_todays_queue(self) -> None:
        """Leftover WIs CLAIM without minting a Stage 1 PASS queue count."""
        snapshot = verify_mod._build_snapshot(
            _ledger([_item()], [_work_item()]),
            now=NOW,
        )
        self.assertEqual(snapshot.fingerprint.stage2_queued_count, 0)
        self.assertEqual(snapshot.stage2_decision.action, "PROCEED")
        self.assertEqual(snapshot.stage2_decision.label, "CLAIM")
        self.assertGreater(snapshot.health.stage2_work_item_count, 0)
        self.assertGreater(
            snapshot.health.stage2_work_item_count,
            snapshot.fingerprint.stage2_queued_count,
        )

    def test_verify_session_queue_counts_injected_sample(self) -> None:
        """Newly added session WIs grade today's queue, leftover does not."""
        leftover = verify_mod._build_snapshot(
            _ledger([_item()], [_work_item()]),
            now=NOW,
            session_queued_count=0,
        )
        injected = verify_mod._build_snapshot(
            _ledger([_item()], [_work_item()]),
            now=NOW,
            session_queued_count=1,
        )
        self.assertEqual(leftover.fingerprint.stage2_queued_count, 0)
        self.assertEqual(injected.fingerprint.stage2_queued_count, 1)
        self.assertEqual(leftover.stage2_decision.label, "CLAIM")
        self.assertEqual(injected.stage2_decision.label, "CLAIM")
        self.assertNotEqual(
            leftover.fingerprint.stage2_queued_count,
            leftover.health.stage2_work_item_count,
        )

    def test_verify_cli_inject_sample(self) -> None:
        """The verifier CLI must accept an injected sample work item."""
        if not EXAMPLE.is_file():
            self.skipTest("example ledger missing")
        # Reuse the health-suite starved fixture (event↔item integrity).
        sys.path.insert(0, str(ROOT / "tests"))
        from pr_lifecycle_helpers import (  # noqa: E402
            schema_valid_starved_ledger as _schema_valid_starved_ledger,
        )

        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "ledger.yaml"
            ledger_path.write_text(
                yaml.safe_dump(_schema_valid_starved_ledger(), sort_keys=False),
                encoding="utf-8",
            )
            baseline = subprocess.run(
                [sys.executable, str(VERIFY), "--ledger", str(ledger_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            injected = subprocess.run(
                [
                    sys.executable,
                    str(VERIFY),
                    "--ledger",
                    str(ledger_path),
                    "--inject-sample",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
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
        self.assertIn('"stage2_queued_count": 1', injected.stdout)


if __name__ == "__main__":
    unittest.main()
