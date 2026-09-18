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
    next_heading = re.search(
        rf"^#{{1,{level}}} (?!#)", document[search_start:], re.M
    )
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

    def test_analysis_error_is_fail_closed_without_mutations(self) -> None:
        metrics = _two_column_table(_section(self.run_record, "## Metrics"))
        self.assertEqual(metrics["Analysis errors"], "1")
        for metric in (
            "Inventoried (triage)",
            "Product mutations",
            "Merged",
            "Closed",
            "Stage 2 queued (this run)",
            "Stage 3 handoffs (this run)",
            "GitHub PR mutations",
            "Ledger file CAS writes",
        ):
            with self.subTest(metric=metric):
                self.assertEqual(metrics[metric], "0")

        self.assertIn("Guardrail outcome for this run: `ANALYSIS_ERROR`", self.run_record)
        self.assertIn("69 / unchanged", self.run_record)
        self.assertIn("This run **did not** `commit`", self.run_record)

    def test_feed_fingerprint_matches_the_failed_run(self) -> None:
        metrics_section = _section(self.run_record, "## Metrics")
        fingerprint = _two_column_table(
            _section(metrics_section, "### Feed fingerprint (mandatory)")
        )
        self.assertEqual(
            fingerprint,
            {
                "stage2_queued_count": "0",
                "salvage_eligible_count": "0",
                "throughput_grade": "FAIL",
            },
        )
        self.assertIn("Throughput self-grade is **FAIL**", metrics_section)
        self.assertIn("starvation=false", metrics_section)

    def test_session_summary_agrees_with_the_full_record(self) -> None:
        summary_metrics = _two_column_table(self.session_report)
        full_metrics = _two_column_table(_section(self.run_record, "## Metrics"))
        for metric in (
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
        self.assertIn("`throughput_grade=FAIL`", self.session_report)
        self.assertIn("Lesson **0hf**", self.session_report)

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


if __name__ == "__main__":
    unittest.main()
