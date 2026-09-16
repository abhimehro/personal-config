"""Fail-closed feed cascade: Stage 1 fingerprint + Stage 2/3 short-circuit."""

from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_feed_cascade as cascade  # noqa: E402
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
    def test_pause_on_stage1_fail(self) -> None:
        report = health.summarize(_ledger([], []), now=NOW)
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=0,
            docs_only_bookkeeping=True,
        )
        decision = cascade.stage3_cascade_decision(
            report, fp, stage2_feed_fail_same_utc_day=False
        )
        self.assertEqual(decision.action, "UPSTREAM_PAUSE")

    def test_pause_when_stage2_feed_fail(self) -> None:
        report = health.summarize(_ledger([_item()], []), now=NOW)
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=0,
            salvage_eligible_count=1,
        )
        decision = cascade.stage3_cascade_decision(
            report, fp, stage2_feed_fail_same_utc_day=True
        )
        self.assertEqual(decision.action, "UPSTREAM_PAUSE")

    def test_proceed_when_healthy(self) -> None:
        report = health.summarize(
            _ledger([_item()], [_work_item()]),
            now=NOW,
        )
        fp = cascade.grade_stage1_feed(
            stage2_queued_count=1,
            salvage_eligible_count=1,
        )
        decision = cascade.stage3_cascade_decision(
            report, fp, stage2_feed_fail_same_utc_day=False
        )
        self.assertEqual(decision.action, "PROCEED")


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
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "ledger.yaml"
            # Minimal mapping is enough for summarize() unit path; CLI loads
            # YAML and may need a fuller document — use example when present.
            data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
            # Force a starved baseline: eligible item, empty WI list.
            data["stage2_work_items"] = []
            data["items"] = [
                {
                    **item,
                    "author_type": "BOT",
                    "lifecycle_state": "STAGE3_RECONCILIATION",
                    "current_owner": "stage3",
                    "guardrail_outcome": "HOLD_CONTRACT",
                    "sensitive_paths": ["generated_output"],
                    "next_action": (
                        "Recover unique source only on a new focused draft"
                    ),
                }
                for item in (data.get("items") or [])[:1]
            ] or [_item()]
            ledger_path.write_text(
                yaml.safe_dump(data, sort_keys=False),
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
        self.assertIn(baseline.returncode, {0, 2})
        self.assertEqual(injected.returncode, 0, msg=injected.stderr + injected.stdout)
        self.assertIn('"action": "PROCEED"', injected.stdout)
        self.assertIn("s2-sample-feed-cascade", injected.stdout)


if __name__ == "__main__":
    unittest.main()
