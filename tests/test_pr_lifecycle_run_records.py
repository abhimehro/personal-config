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


class TestLifecycleRunRecords20261004(unittest.TestCase):
    """Acceptance contracts for the documentation-only October 4 run.

    These assert consistency of the recorded evidence, not live GitHub state
    or the reconcile implementation shipped separately in PR #2416.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.review = (ROOT / "tasks/pr-review-2026-10-04-1500.md").read_text(
            encoding="utf-8"
        )
        cls.completion = (ROOT / "tasks/pr-completion-2026-10-04.md").read_text(
            encoding="utf-8"
        )
        cls.review_summary = _section(
            SESSION_REPORTS.read_text(encoding="utf-8"), "# Stage 1 — 2026-10-04"
        )
        cls.completion_summary = _section(
            (ROOT / "tasks/completion-session-reports.md").read_text(encoding="utf-8"),
            "## Stage Run Record — 2026-10-04",
        )
        lessons = LESSONS.read_text(encoding="utf-8")
        cls.reconcile_lesson = _section(lessons, "## Lesson 0ht:")
        cls.handoff_lesson = _section(lessons, "## Lesson 0hu:")

    def table_rows(self, document: str, heading: str) -> list[dict[str, str]]:
        """Read a record table and fail clearly if a row loses a field."""
        rows = [
            [cell.strip().strip("`*") for cell in line.strip("|").split("|")]
            for line in _section(document, heading).splitlines()
            if line.startswith("|")
        ]
        self.assertGreaterEqual(len(rows), 3, heading)
        header, separator, *data = rows
        self.assertEqual(len(header), len(set(header)), "Duplicate table column")
        self.assertEqual(len(separator), len(header))
        for row in data:
            self.assertEqual(len(row), len(header), f"Malformed row: {row}")
            self.assertTrue(all(row), f"Missing evidence field: {row}")
        return [dict(zip(header, row)) for row in data]

    def evidence_rows(self) -> list[dict[str, str]]:
        return self.table_rows(
            self.completion,
            "## Mandatory per-item evidence, action, and outcome record",
        )

    def test_cas_revision_deltas_and_parent_chain_match_summary(self) -> None:
        rows = self.table_rows(self.review, "## Ledger CAS")
        self.assertEqual(len(rows), 2)
        summary = _two_column_table(self.review_summary)
        for row, metric in zip(
            rows, ("First CAS transitions", "Second CAS transitions")
        ):
            with self.subTest(step=row["Step"]):
                before, after = map(int, row["Revision"].split(" → "))
                self.assertEqual(after - before, int(row["Applied"]))
                self.assertEqual(row["Applied"], summary[metric])
                self.assertIn(row["Revision"], self.review_summary)
                for field in ("Commit", "Blob", "Parent"):
                    self.assertRegex(row[field], r"^[0-9a-f]{40}$")
                for field in ("Commit", "Blob"):
                    self.assertIn(row[field], self.review_summary)
        self.assertEqual(
            rows[0]["Revision"].split(" → ")[1],
            rows[1]["Revision"].split(" → ")[0],
        )
        self.assertEqual(rows[1]["Parent"], rows[0]["Commit"])
        self.assertEqual(int(summary["Ledger CAS writes"]), len(rows))

    def test_completion_reads_the_final_review_tip_without_advancing_it(self) -> None:
        final_cas = self.table_rows(self.review, "## Ledger CAS")[-1]
        revision = final_cas["Revision"].split(" → ")[1]
        identity = _section(self.completion, "## Identity")
        self.assertIn(f"**{revision} / {revision}** (unchanged)", identity)
        for document in (identity, self.completion_summary):
            for field in ("Commit", "Blob"):
                with self.subTest(field=field, document=document[:40]):
                    self.assertIn(final_cas[field], document)
        handoffs = self.table_rows(
            self.completion, "## Revision-checked handoffs and human decisions"
        )
        self.assertEqual(len(handoffs), 2)
        for row in handoffs:
            self.assertEqual(
                row["Expected → resulting revision"], f"{revision} → {revision}"
            )
            self.assertEqual(row["Event ID / idempotency key"], "none issued")

    def test_run_ids_and_full_record_references_agree(self) -> None:
        for record, summary, path in (
            (self.review, self.review_summary, "tasks/pr-review-2026-10-04-1500.md"),
            (
                self.completion,
                self.completion_summary,
                "tasks/pr-completion-2026-10-04.md",
            ),
        ):
            with self.subTest(path=path):
                run_ids = set(re.findall(r"20261004T\d{6}Z-[0-9a-f]{8}", summary))
                self.assertEqual(len(run_ids), 1)
                self.assertIn(next(iter(run_ids)), record)
                self.assertIn(f"`{path}`", summary)
                self.assertTrue((ROOT / path).is_file())
        review_id = re.search(r"20261004T\d{6}Z-[0-9a-f]{8}", self.review).group()
        self.assertIn(
            review_id, _section(self.completion, "## Inputs and reconciliation")
        )

    def test_empty_feed_is_not_confused_with_stage3_reselect_stock(self) -> None:
        feed = " ".join(_section(self.review, "## Feed").split())
        self.assertIn("`FEED_CHECK` grade PASS", feed)
        self.assertIn("`reselect_candidates` 0", feed)
        self.assertIn("`enqueued_count` 0", feed)
        self.assertIn("`salvage_eligible_count` 0", feed)
        self.assertIn("`reselect_candidate_count` 6 is Stage-3-owned", feed)
        metrics = _two_column_table(self.review_summary)
        for metric in (
            "Stage-1 reselect candidates",
            "Stage 2 queued (this run)",
            "Salvage-eligible remainder",
            "GitHub PR mutations",
        ):
            self.assertEqual(metrics[metric], "0", metric)
        inputs = " ".join(
            _section(self.completion, "## Inputs and reconciliation").split()
        )
        self.assertIn("`reselect_candidate_count` 7", inputs)
        self.assertIn("not `FEED_FAIL` while salvage-eligible remainder is 0", inputs)
        self.assertIn("does not invent a Stage 2 report", inputs)

    def test_completion_zero_actions_agree_with_summary(self) -> None:
        metrics = dict(
            re.findall(
                r"^- ([^:\n]+): (.+)$", _section(self.completion, "## Metrics"), re.M
            )
        )
        summary = _two_column_table(self.completion_summary)
        for detailed, summarized in (
            ("Merged", "Merged"),
            ("Closed", "Closed"),
            ("Decision packets created", "Decision packets"),
            ("Stage 2 work items created", "Stage 2 work items"),
            ("Ledger CAS writes", "Ledger file CAS writes"),
            ("Analysis errors", "Analysis errors"),
        ):
            with self.subTest(metric=detailed):
                self.assertEqual(metrics[detailed], "0")
                self.assertEqual(summary[summarized], metrics[detailed])
        self.assertEqual(metrics["Drafts created"], "0")
        self.assertEqual(
            metrics["State-changing actions, including failed attempts and retries"],
            "0 / 15",
        )
        self.assertEqual(summary["Product mutations"], "0")
        self.assertEqual(metrics["Calibration change"], "none")
        self.assertEqual(summary["Calibration change"], "none")

    def test_handoffs_preserve_existing_salvage_and_open_originals(self) -> None:
        expected = {
            "personal-config #2090": (2318, 2320),
            "email-security-pipeline #1633": (1704,),
            "repoprompt-ce #396": (424,),
            "personal-config #2237": (2406,),
            "personal-config #2244": (2407,),
        }
        rows = [
            row
            for row in self.evidence_rows()
            if "HANDOFF_MECHANICAL_TO_STAGE2" in row["Proposed route / actual action"]
        ]
        self.assertCountEqual([row["Repository / PR"] for row in rows], expected)
        summary = _two_column_table(self.completion_summary)
        self.assertEqual(len(rows), int(summary["Mechanical handoffs withheld"]))
        for row in rows:
            with self.subTest(pr=row["Repository / PR"]):
                self.assertIn("not CAS-written", row["Proposed route / actual action"])
                self.assertIn("handoff skipped (0hu)", row["Guardrail outcome"])
                self.assertEqual(row["Owner before → after"], "stage3 → stage3")
                self.assertEqual(
                    row["Provenance or canonical relation"], "leave original OPEN"
                )
                outcome = row["Final observed outcome / calibration correctness"]
                self.assertTrue(outcome.startswith("OPEN;"))
                self.assertIn("`MERGEABLE`/`UNSTABLE", outcome)
                self.assertEqual(
                    set(map(int, re.findall(r"#(\d+)", outcome))),
                    set(expected[row["Repository / PR"]]),
                )

    def test_sticky_reconcile_rows_remain_unapplied_and_uniquely_anchored(self) -> None:
        rows = self.evidence_rows()
        keys = [row["Ledger key"] for row in rows]
        self.assertEqual(len(keys), len(set(keys)))
        for row in rows:
            key = re.fullmatch(
                r"abhimehro/([^#]+)#(\d+)@[0-9a-f]{40}", row["Ledger key"]
            )
            self.assertIsNotNone(key, row["Ledger key"])
            repository, number = key.groups()
            self.assertEqual(row["Repository / PR"], f"{repository} #{number}")
            self.assertEqual(row["Changed paths"], "none")
        sticky = [
            row
            for row in rows
            if "REVIEW_SECURITY" in row["Classification / risk / sticky paths"]
        ]
        summary = _two_column_table(self.completion_summary)
        self.assertEqual(len(sticky), 6)
        self.assertEqual(len(sticky), int(summary["Reconcile dry-run (withheld)"]))
        self.assertEqual(summary["Reconciliations (live, acted)"], "0")
        for row in sticky:
            with self.subTest(key=row["Ledger key"]):
                self.assertEqual(row["Guardrail outcome"], "reconcile withheld")
                self.assertIn("not applied", row["Proposed route / actual action"])
                self.assertEqual(row["Owner before → after"], "unchanged")
                self.assertIn(
                    "anchor frozen",
                    row["Final observed outcome / calibration correctness"],
                )

    def test_two_2077_anchors_do_not_collapse_onto_the_shared_live_head(self) -> None:
        rows = [
            row
            for row in self.evidence_rows()
            if row["Repository / PR"] == "personal-config #2077"
        ]
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["Ledger key"], rows[1]["Ledger key"])
        live_heads = []
        for row in rows:
            live_head = re.search(
                r"live head `([0-9a-f]+)`", row["Observed vs ledger base/head SHA"]
            ).group(1)
            live_heads.append(live_head)
            self.assertFalse(row["Ledger key"].split("@")[1].startswith(live_head))
            self.assertIn("not applied", row["Proposed route / actual action"])
        self.assertEqual(live_heads[0], live_heads[1])

    def test_closed_security_anchors_are_not_reported_as_reintaken(self) -> None:
        rows = [
            row
            for row in self.evidence_rows()
            if "observed CLOSED" in row["Classification / risk / sticky paths"]
        ]
        self.assertCountEqual(
            [row["Repository / PR"] for row in rows],
            ["personal-config #2034", "personal-config #2100"],
        )
        for row in rows:
            self.assertIn("not applied", row["Proposed route / actual action"])
            self.assertEqual(
                row["Final observed outcome / calibration correctness"],
                "CLOSED anchor frozen",
            )
        self.assertIn("They are not SHA re-intake", " ".join(self.review.split()))

    def test_new_lessons_preserve_schema_and_duplicate_handoff_guards(self) -> None:
        for lesson, requirements in (
            (
                self.reconcile_lesson,
                (
                    "Rekey `key`, event `item_key`, and `idempotency_key`",
                    "if that key is taken, skip the item",
                    "Do not bump item revision without an event",
                    "`REVIEW_SECURITY` and non-bot head moves per item",
                    "MERGED/CLOSED live state never falls through to SHA re-intake",
                ),
            ),
            (
                self.handoff_lesson,
                (
                    "already a `STAGE1_INTAKE` item, skip the handoff",
                    "leave the original OPEN",
                    "A replacement that is not `MERGEABLE`/`CLEAN` stays unmerged",
                    "Swift salvage on Linux stays `HOLD_PLATFORM`",
                    "Do not apply reconcile actions that move sticky `REVIEW_SECURITY`",
                    "two keys on the same live head",
                    "Do not spend the daily cap on Observed-CLOSED `CLOSED_NOOP`",
                ),
            ),
        ):
            normalized = " ".join(lesson.split())
            for requirement in requirements:
                with self.subTest(requirement=requirement):
                    self.assertIn(requirement, normalized)
        self.assertIn("Lesson **0ht**", self.review_summary)
        self.assertIn("Lesson **0hu**", self.completion_summary)


if __name__ == "__main__":
    unittest.main()
