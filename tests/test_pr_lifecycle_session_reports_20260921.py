"""Acceptance contracts for the September 21 records salvaged in PR #2482.

The PR only appends Markdown. Compare its summaries with the durable run
records and protect the lesson's exceptions without invoking live automation.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from tests.test_pr_lifecycle_run_records import _section, _two_column_table

ROOT = Path(__file__).resolve().parents[1]
REVIEW_HEADING = "## Stage 1 — 2026-09-21"
SALVAGE_HEADING = "## Run — 2026-09-21 17:00"
LESSON_HEADING = "## Lesson 0hq:"


class TestSessionReports20260921(unittest.TestCase):
    """Keep the appended summaries consistent with their source evidence."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.review_log = (ROOT / "tasks/review-session-reports.md").read_text(
            encoding="utf-8"
        )
        cls.salvage_log = (ROOT / "tasks/salvage-session-reports.md").read_text(
            encoding="utf-8"
        )
        cls.lessons = (ROOT / "tasks/lessons.md").read_text(encoding="utf-8")
        cls.review = _section(cls.review_log, REVIEW_HEADING)
        cls.salvage = _section(cls.salvage_log, SALVAGE_HEADING)
        cls.lesson = " ".join(_section(cls.lessons, LESSON_HEADING).split())
        cls.review_record = (ROOT / "tasks/pr-review-2026-09-21.md").read_text(
            encoding="utf-8"
        )
        cls.salvage_record = (
            ROOT / "tasks/pr-salvage-2026-09-21-1700.md"
        ).read_text(encoding="utf-8")

    def test_salvaged_entries_occur_exactly_once(self) -> None:
        """Repeated salvage must not duplicate the run or reuse its lesson ID."""
        for document, heading in (
            (self.review_log, REVIEW_HEADING),
            (self.salvage_log, SALVAGE_HEADING),
            (self.lessons, LESSON_HEADING),
        ):
            with self.subTest(heading=heading):
                self.assertEqual(
                    len(re.findall(rf"^{re.escape(heading)}(?=\s|$)", document, re.M)),
                    1,
                )

    def test_full_record_references_resolve_to_the_correct_stage(self) -> None:
        for summary, expected_path, stage in (
            (self.review, "tasks/pr-review-2026-09-21.md", "stage1"),
            (self.salvage, "tasks/pr-salvage-2026-09-21-1700.md", "stage2"),
        ):
            with self.subTest(stage=stage):
                references = re.findall(r"Full record: `([^`]+)`", summary)
                self.assertEqual(references, [expected_path])
                record = (ROOT / references[0]).read_text(encoding="utf-8")
                self.assertIn(f"- Stage: `{stage}`", record)
                self.assertIn("2026-09-21", record.splitlines()[0])

    def test_review_metrics_match_full_record(self) -> None:
        metrics = _two_column_table(self.review)
        full_metrics = _two_column_table(_section(self.review_record, "## Metrics"))
        expected_names = {
            "Inventoried (triage)",
            "Product mutations",
            "Merged",
            "Closed",
            "Stage 2 queued (this run)",
            "Stage 3 handoffs (this run)",
            "GitHub PR mutations",
            "Ledger file CAS writes",
            "Analysis errors",
        }
        self.assertEqual(set(metrics), expected_names)
        for name in expected_names:
            with self.subTest(metric=name):
                self.assertEqual(metrics[name], full_metrics[name])

    def test_review_outcome_totals_match_per_item_evidence(self) -> None:
        """Do not count branch updates or failed merge attempts as merges."""
        metrics = _two_column_table(self.review)
        evidence = _section(
            self.review_record, "## Mandatory per-item evidence, action, and outcome"
        )
        merged = re.findall(r"^\|.*\| MERGED_ROUTINE\b", evidence, re.M)
        closed = re.findall(r"^\|.*\| CLOSED_(?:NOOP|SUPERSEDED)\b", evidence, re.M)
        self.assertEqual(int(metrics["Merged"]), len(merged))
        self.assertEqual(int(metrics["Closed"]), len(closed))
        self.assertGreater(
            int(metrics["Product mutations"]), len(merged) + len(closed)
        )

    def test_feed_fingerprint_agrees_across_stage_handoff(self) -> None:
        fingerprint = _two_column_table(
            _section(self.review_record, "### Feed fingerprint (mandatory)")
        )
        self.assertEqual(
            fingerprint,
            {
                "stage2_queued_count": "0",
                "salvage_eligible_count": "0",
                "throughput_grade": "PASS",
            },
        )
        for field, value in fingerprint.items():
            with self.subTest(field=field):
                self.assertIn(f"{field}={value}", self.review)
                self.assertIn(f"{field}: {value}", self.salvage)

    def test_ledger_anchors_match_the_stage2_input_record(self) -> None:
        identity = _section(self.salvage_record, "## Identity")
        anchors = re.findall(r"`([0-9a-f]{40})`", identity)
        self.assertEqual(len(anchors), 2, "Expected the ledger blob and commit")
        for summary in (self.review, self.salvage):
            with self.subTest(stage=summary.splitlines()[0]):
                self.assertCountEqual(re.findall(r"`([0-9a-f]{40})`", summary), anchors)
        self.assertIn("then CAS **79**", self.review)
        self.assertIn("`ledger_revision=79`", self.salvage)
        self.assertIn("rev stays **79**", self.salvage)

    def test_empty_intake_does_not_claim_product_or_ledger_mutations(self) -> None:
        outcomes = " ".join(_section(self.salvage, "### Outcomes").split())
        for fact in (
            "EMPTY_INTAKE (structured no-recovery)",
            "Salvage drafts opened: **0**",
            "Infra-fix drafts: **0**",
            "Closed via API / autonomous merges / `request_reviewers`: **0 / 0 / skipped**",
            "New lessons: **0**",
            "Ledger CAS: **none**",
            "completed **0** eligible items",
            "Remaining `stage2_work_items`: **[]**",
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, outcomes)
        self.assertIn("`starvation=false`", self.salvage)
        self.assertNotIn("EMPTY_INTAKE_STARVATION", outcomes)

    def test_draft_head_evidence_matches_the_full_record(self) -> None:
        verification = " ".join(_section(self.salvage, "### Verification").split())
        drafts = re.findall(
            r"\[#(\d+)\]\((https://github\.com/[^)]+)\) "
            r"OPEN `isDraft=true` head `([0-9a-f]{8})`",
            verification,
        )
        self.assertEqual({number for number, _, _ in drafts}, {"460", "2246"})
        for number, url, head in drafts:
            with self.subTest(pr=number):
                rows = [
                    line
                    for line in self.salvage_record.splitlines()
                    if line.startswith("|") and f"]({url})" in line
                ]
                self.assertEqual(len(rows), 1)
                self.assertIn(f"head `{head}`", rows[0])
                self.assertIn("did not merge", rows[0])

    def test_handoff_preserves_stage_authority_and_retracted_work_boundary(self) -> None:
        handoff = " ".join(_section(self.salvage, "### Handoff").split())
        for guard in (
            "unmarked **and** every routine predicate passes",
            "Merge authority is never Stage 2",
            "Do not close because a replacement exists",
            "Do not execute the retracted processor WI",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, handoff)
        self.assertIn(
            "`s2-20260919-seriescorre-409-processor` **absent**", self.salvage
        )

    def test_lesson_pin_skew_does_not_exempt_real_codeql_findings(self) -> None:
        self.assertIn("Lesson **0hq**", self.review)
        self.assertIn("one logical pin", self.lesson)
        self.assertIn("init/autobuild/analyze all land", self.lesson)
        self.assertIn("Real CodeQL findings still block", self.lesson)
        self.assertIn("when every other routine predicate passes", self.lesson)
        for number, action in ((2247, "analyze"), (2249, "autobuild"), (2251, "init")):
            with self.subTest(pr=number):
                self.assertIn(f"/pull/{number})", self.lesson)
                self.assertRegex(
                    self.review_record,
                    rf"(?m)^\| \[#{number}\].*codeql-action/{action}\b",
                )

    def test_lesson_requires_fresh_sha_and_bounded_infra_exceptions(self) -> None:
        for guard in (
            "then `/trunk merge` on the **new** SHA",
            "Do not re-comment the old SHA",
            "Do not squash-bypass",
            "Do not record App/ruleset `HOLD_PLATFORM` while the PR is behind `main`",
            "SBOM **FAILURE** whose log is GitHub HTTP 504 downloading syft",
            "Do not re-comment `/trunk merge` on an unchanged SHA",
            "re-poll until `trunk-merged` or a new SHA appears",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, self.lesson)


if __name__ == "__main__":
    unittest.main()
