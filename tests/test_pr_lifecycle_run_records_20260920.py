"""Acceptance contracts for the three records salvaged in PR #2407.

These are historical documents, not executable pipeline changes. Check their
handoff evidence locally without replaying actions or querying live PR state.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from tests.test_pr_lifecycle_run_records import _section, _two_column_table

ROOT = Path(__file__).resolve().parents[1]
RECORDS = {
    "stage1": "pr-review-2026-09-20.md",
    "stage2": "pr-salvage-2026-09-20-1700.md",
    "stage3": "pr-completion-2026-09-20.md",
}


class TestRunRecords20260920(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = {
            stage: (ROOT / "tasks" / name).read_text(encoding="utf-8")
            for stage, name in RECORDS.items()
        }

    def test_records_identify_the_same_day_and_distinct_stages(self) -> None:
        for stage, document in self.records.items():
            with self.subTest(stage=stage):
                self.assertIn("2026-09-20", document.splitlines()[0])
                identity = _section(document, "## Identity")
                self.assertIn(f"- Stage: `{stage}`", identity)
                self.assertIn("pr-lifecycle-v1.4", identity)
                self.assertRegex(identity, r"2026-09-20T\d{2}:\d{2}:\d{2}Z")
                self.assertIn("## Metrics", document)

    def test_feed_fingerprint_is_preserved_across_all_stages(self) -> None:
        fingerprint = _two_column_table(
            _section(self.records["stage1"], "### Feed fingerprint (mandatory)")
        )
        self.assertEqual(
            fingerprint,
            {
                "stage2_queued_count": "2",
                "salvage_eligible_count": "0",
                "throughput_grade": "PASS",
            },
        )
        for stage in ("stage2", "stage3"):
            document = self.records[stage]
            with self.subTest(stage=stage):
                self.assertIn(RECORDS["stage1"], document)
                for field, value in fingerprint.items():
                    self.assertRegex(document, rf"{field}(?:=|: ){value}\b")

    def test_stage2_consumes_exactly_the_work_items_queued_by_stage1(self) -> None:
        queued = _section(
            self.records["stage1"], "### Stage 2 work items CAS-written"
        )
        recovered = _section(
            self.records["stage2"], "## Per-item evidence, action, and outcome"
        )
        pattern = r"`(s2-20260920-[^`]+)`"
        expected = {
            "s2-20260920-personalconfig-2116-run-merges",
            "s2-20260920-personalconfig-2030-pr-reference",
        }
        for stage, section in (("stage1", queued), ("stage2", recovered)):
            with self.subTest(stage=stage):
                work_items = re.findall(pattern, section)
                self.assertCountEqual(work_items, expected)
        metrics = _section(self.records["stage2"], "## Metrics")
        self.assertIn("completed **2** eligible items", metrics)
        self.assertIn("Remaining `stage2_work_items`: **[]**", metrics)
        self.assertIn("empty remainder after both WIs", metrics)

    def test_ledger_commit_and_blob_survive_the_stage2_to_stage3_handoff(self) -> None:
        identity2 = _section(self.records["stage2"], "## Identity")
        identity3 = _section(self.records["stage3"], "## Identity")
        written = re.search(
            r"CAS-wrote rev \*\*(\d+)\*\* commit\s+`([0-9a-f]{40})` blob"
            r"\s+`([0-9a-f]{40})`",
            identity2,
        )
        fetched = re.search(
            r"fetched rev \*\*(\d+)\*\* commit\s+`([0-9a-f]{40})` blob"
            r"\s+`([0-9a-f]{40})`",
            identity3,
        )
        self.assertIsNotNone(written, "Stage 2 must identify its durable output")
        self.assertIsNotNone(fetched, "Stage 3 must identify its live input")
        self.assertEqual(written.groups(), fetched.groups())
        self.assertEqual(written.group(1), "77")

    def test_salvage_noop_preserves_the_stronger_main_and_original(self) -> None:
        evidence = _section(
            self.records["stage2"], "## Per-item evidence, action, and outcome"
        )
        row = next(line for line in evidence.splitlines() if "#2116@" in line)
        for required in (
            "**no draft**",
            "`CLOSE_NONSECURITY_NOOP`",
            "actual **none**",
            "Original stays OPEN",
            "Stage 2 must not",
        ):
            with self.subTest(required=required):
                self.assertIn(required, row)

    def test_salvage_draft_repair_and_ack_do_not_authorize_source_closure(self) -> None:
        evidence = _section(
            self.records["stage2"], "## Per-item evidence, action, and outcome"
        )
        row = next(line for line in evidence.splitlines() if "#2030@" in line)
        self.assertIn("converted back to draft", row)
        self.assertIn("Re-read `isDraft=true`", row)
        self.assertIn("actual `pr_reference.py` only", row)
        handoffs = _section(
            self.records["stage3"], "## Revision-checked handoffs and human decisions"
        )
        ack = next(line for line in handoffs.splitlines() if "pc #2030@" in line)
        outgoing = _section(self.records["stage2"], "## Stage 3 / Stage 1 handoff")
        self.assertIn("evt-s2-20260920-personalconfig-2030-h", outgoing)
        self.assertIn("ACK of `evt-s2-20260920-personalconfig-2030-h`", ack)
        self.assertIn("5 → 5", ack)
        self.assertIn("Keep #2030 open", ack)
        self.assertIn("Do not merge drafts or close source", ack)

    def test_terminal_projection_is_not_counted_as_a_new_github_close(self) -> None:
        document = self.records["stage3"]
        metrics = _two_column_table(_section(document, "## Metrics"))
        self.assertEqual(metrics["Cheap CLOSED_* projections"], "1")
        self.assertEqual(metrics["Reconciliations (live, acted)"], "2")
        for metric in (
            "Product mutations (state-changing GitHub)",
            "Merged this run",
            "Closed this run",
            "Decision packets",
            "Stage 2 work items created",
        ):
            with self.subTest(metric=metric):
                self.assertEqual(metrics[metric], "0")
        evidence = _section(
            document, "## Mandatory per-item evidence, action, and outcome record"
        )
        row = next(line for line in evidence.splitlines() if "#643@" in line)
        self.assertIn("GitHub-already-CLOSED", row)
        self.assertIn("Stage 3 did not close the GitHub PR", row)
        self.assertIn("ACK of the 643 reingest was not duplicated", row)

    def test_remaining_stage3_inventory_agrees_with_metrics_without_duplicates(self) -> None:
        document = self.records["stage3"]
        inventory = _section(document, "### Remaining Stage-3-owned")
        keys = re.findall(r"^\| `([^`]+)` \|", inventory, re.M)
        metrics = _two_column_table(_section(document, "## Metrics"))
        self.assertEqual(len(keys), int(metrics["Remaining Stage-3-owned"]))
        self.assertEqual(len(keys), len(set(keys)), "Duplicate owned ledger keys")

    def test_clean_mergeability_does_not_erase_unresolved_discussion_blockers(self) -> None:
        section = _section(
            self.records["stage3"], "## Overflow product mutations (not ledger rows)"
        )
        for number in (2238, 2234):
            with self.subTest(pr=number):
                row = next(
                    line for line in section.splitlines() if f"#{number}]" in line
                )
                self.assertIn("unresolved", row)
                self.assertIn("threads", row)
        self.assertIn("None this run (0/15)", section)


if __name__ == "__main__":
    unittest.main()
