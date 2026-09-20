"""Contract tests for durable PR lifecycle run records."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_RECORD = ROOT / "tasks/pr-review-2026-09-18.md"
SESSION_REPORTS = ROOT / "tasks/review-session-reports.md"
LESSONS = ROOT / "tasks/lessons.md"


def _section(document: str, heading: str) -> str:
    """Return a Markdown section, excluding the next same-level heading."""
    level = len(heading) - len(heading.lstrip("#"))
    start = document.index(heading)
    search_start = start + len(heading)
    next_heading = re.search(rf"^#{{1,{level}}} (?!#)", document[search_start:], re.M)
    if next_heading is None:
        return document[start:]
    return document[start : search_start + next_heading.start()]


def _two_column_table(section: str) -> dict[str, str]:
    """Parse all two-column Markdown rows in a section."""
    rows: dict[str, str] = {}
    for left, right in re.findall(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|$", section, re.M):
        if left in {"Metric", "Field"} or set(left) == {"-"}:
            continue
        rows[left.strip(" `")] = right.strip().strip("`*")
    return rows


class TestStage1RunRecord20260918(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_record = RUN_RECORD.read_text(encoding="utf-8")
        reports = SESSION_REPORTS.read_text(encoding="utf-8")
        cls.session_report = _section(reports, "## Stage 1 — 2026-09-18")
        lessons = LESSONS.read_text(encoding="utf-8")
        cls.lesson = _section(lessons, "## Lesson 0hf:")

    def test_opening_analysis_error_then_drain_metrics(self) -> None:
        metrics = _two_column_table(_section(self.run_record, "## Metrics"))
        self.assertEqual(metrics["Inventoried (triage)"], "147")
        self.assertEqual(metrics["Product mutations"], "21")
        self.assertEqual(metrics["Merged"], "17")
        self.assertEqual(metrics["Closed"], "0")
        self.assertEqual(metrics["Stage 2 queued (this run)"], "0")
        self.assertEqual(metrics["Stage 3 handoffs (this run)"], "0")
        self.assertEqual(metrics["GitHub PR mutations"], "21")
        self.assertEqual(metrics["Ledger file CAS writes"], "0")
        self.assertEqual(metrics["Analysis errors"], "1")

        self.assertIn(
            "Guardrail outcome for this run: `ANALYSIS_ERROR`", self.run_record
        )
        self.assertIn("69 / unchanged", self.run_record)
        self.assertIn("This run **did not** `commit`", self.run_record)

    def test_feed_fingerprint_matches_the_utc_day_run(self) -> None:
        metrics_section = _section(self.run_record, "## Metrics")
        fingerprint = _two_column_table(
            _section(metrics_section, "### Feed fingerprint (mandatory)")
        )
        self.assertEqual(
            fingerprint,
            {
                "stage2_queued_count": "0",
                "salvage_eligible_count": "0",
                "throughput_grade": "PASS",
            },
        )
        self.assertIn("Throughput self-grade is **PASS**", metrics_section)
        self.assertIn("starvation=false", metrics_section)

    def test_session_summary_agrees_with_the_full_record(self) -> None:
        summary_metrics = _two_column_table(self.session_report)
        full_metrics = _two_column_table(_section(self.run_record, "## Metrics"))
        for metric in (
            "Inventoried (triage)",
            "Product mutations",
            "Merged",
            "Closed",
            "Stage 2 queued (this run)",
            "Stage 3 handoffs (this run)",
            "GitHub PR mutations",
            "Ledger file CAS writes",
            "Analysis errors",
        ):
            with self.subTest(metric=metric):
                self.assertEqual(summary_metrics[metric], full_metrics[metric])

        self.assertIn("`tasks/pr-review-2026-09-18.md`", self.session_report)
        self.assertIn("`throughput_grade=PASS`", self.session_report)
        self.assertIn("Lesson **0hf**", self.session_report)
        self.assertIn("Lesson **0hi**", self.session_report)

    def test_preflight_examples_always_include_the_required_output(self) -> None:
        for name, document in (
            (RUN_RECORD.name, self.run_record),
            (LESSONS.name, self.lesson),
        ):
            examples = [
                line
                for line in document.splitlines()
                if "scripts/pr_lifecycle_ledger_cas.py preflight" in line
            ]
            self.assertGreaterEqual(len(examples), 1, name)
            for example in examples:
                with self.subTest(document=name, example=example):
                    self.assertRegex(example, r"\bpreflight\s+--out\s+\S+")

    def test_export_sync_recovery_stays_outside_the_docs_lineage(self) -> None:
        normalized_record = " ".join(self.run_record.split())
        normalized_lesson = " ".join(self.lesson.split())

        self.assertIn("sync_cursor_export_prompts.py --check", self.lesson)
        self.assertIn("sync_cursor_export_prompts.py --write", self.lesson)
        self.assertIn("reviewed non-lineage", normalized_lesson)
        self.assertIn("must **not** silently sync exports", normalized_lesson)

        self.assertIn(
            "**no** silent `sync_cursor_export_prompts.py --write`",
            normalized_record,
        )
        self.assertIn(
            "wrap-only export drift is not a policy-revision change",
            normalized_record,
        )
        self.assertIn("**not** reset to `REPORT_ONLY`", normalized_record)

    def test_downstream_unblock_does_not_claim_2224_is_still_queued(self) -> None:
        downstream = _section(self.run_record, "## Downstream unblock")
        self.assertIn("0cf4928e", downstream)
        self.assertIn("merged, not queued", downstream)
        self.assertNotIn("Queued on Trunk:", downstream)
        self.assertIn("Do **not** disable Stage 1", downstream)
        self.assertIn("0 17 * * *", downstream)
        self.assertIn("Lesson **0hk**", self.session_report)
        self.assertIn("already landed", self.session_report)
        self.assertIn("**not** Trunk-queued", self.session_report)

    def test_lesson_0hk_keeps_stage1_enabled(self) -> None:
        lessons = LESSONS.read_text(encoding="utf-8")
        lesson = _section(lessons, "## Lesson 0hk:")
        self.assertIn("Do not disable Stage 1", lesson)
        self.assertIn("0 17 * * *", lesson)
        self.assertIn("GetAutomation", lesson)
        self.assertIn("verified 2026-09-16", lesson)
        self.assertIn("#2224/#2225/#2226", lesson)
        self.assertIn("not a fourth", lesson)

    def test_live_dashboard_enablement_is_not_the_2026_09_16_disabled_snapshot(
        self,
    ) -> None:
        checklist = ROOT / "docs/cursor-automations/dashboard-application-checklist.md"
        live = _section(checklist.read_text(encoding="utf-8"), "## Live Dashboard IDs")
        self.assertIn("verified 2026-09-18", live)
        self.assertNotIn("Enablement (2026-09-16)", live)
        self.assertIn("Do **not** disable Stage 1", live)
        self.assertIn("historical and must not be applied", live)
        stage1_line = next(
            line
            for line in live.splitlines()
            if "`77c168e0-7f6b-42de-bad6-da4e4e640b79`" in line
        )
        self.assertIn("**enabled**", stage1_line)
        completion_line = next(
            line
            for line in live.splitlines()
            if "`66a8e7a8-9c42-11f1-ba66-0e7d0216e441`" in line
        )
        self.assertIn("**enabled**", completion_line)
        cal_line = next(
            line
            for line in live.splitlines()
            if "`d9d2c058-9c42-11f1-ba66-0e7d0216e441`" in line
        )
        self.assertIn("**disabled**", cal_line)


if __name__ == "__main__":
    unittest.main()
