"""Reselect candidate predicates for the Option 3 Stage 1 enqueue path."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_pipeline_health as health  # noqa: E402
from tests.pr_lifecycle_helpers import make_item, make_ledger  # noqa: E402

class ReselectCandidateTests(unittest.TestCase):
    def test_reselect_rejects_terminal_and_non_salvage_outcomes(self) -> None:
        base = make_item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        for outcome in (
            "REVIEW_SECURITY",
            "HOLD_PLATFORM",
            "HOLD_CANONICAL",
            "PASS_ROUTINE",
            "CLOSE_NONSECURITY_NOOP",
            "ANALYSIS_ERROR",
        ):
            with self.subTest(outcome=outcome):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        {**base, "guardrail_outcome": outcome}
                    )
                )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                {**base, "lifecycle_state": "TERMINAL"}
            )
        )

    def test_reselect_requires_non_journal_unique_remaining_paths(self) -> None:
        item = make_item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT DIRTY unique remaining",
        )
        self.assertTrue(health.is_reselect_salvage_candidate(item))
        for paths in ([], [".jules/journal.md"], ["notes/.jules/journal.md"]):
            with self.subTest(paths=paths):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        item, unique_remaining_paths=paths
                    )
                )
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, unique_remaining_paths=[".jules/journal.md", "src/unique.py"]
            )
        )

    def test_palette_shell_sticky_requires_only_allowlisted_paths(self) -> None:
        item = make_item(
            sensitive_paths=["shell_execution"],
            next_action="Palette wrap CONFLICTING unique remaining",
        )
        allowed = (
            "analytics_dashboard.sh",
            "maintenance/bin/refresh.sh",
            "docs/cursor-automations/prompts/daily-pr-review.md",
        )
        for path in allowed:
            with self.subTest(allowed=path):
                self.assertTrue(
                    health.is_reselect_salvage_candidate(
                        item, unique_remaining_paths=[".jules/journal.md", path]
                    )
                )
        for paths in (
            [".jules/journal.md"],
            ["maintenance/bin/refresh.sh", "scripts/deploy.sh"],
            ["maintenance/bin/refresh.py"],
        ):
            with self.subTest(blocked=paths):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        item, unique_remaining_paths=paths
                    )
                )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                {**item, "next_action": "CONFLICTING unique remaining"},
                unique_remaining_paths=["maintenance/bin/refresh.sh"],
            )
        )

    def test_title_bot_prefixes_do_not_admit_arbitrary_human_titles(self) -> None:
        item = make_item(
            author_type="HUMAN",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        for prefix in (
            "⚡ Bolt",
            "🎨 Palette",
            "salvage(",
            "chore(qa)",
            "chore(repo-health)",
        ):
            with self.subTest(prefix=prefix):
                self.assertTrue(
                    health.is_reselect_salvage_candidate(
                        item, title=f"  {prefix} focused repair"
                    )
                )
        for title in (None, "Human repair", "Review ⚡ Bolt repair"):
            with self.subTest(title=title):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(item, title=title)
                )

    def test_reselect_candidate_lookup_accepts_source_prefix_metadata(self) -> None:
        key = "abhimehro/demo#7@abc"
        item = make_item(
            key=key,
            author_type="HUMAN",
            changed_paths=["src/demo.py"],
            next_action="Needs live verification",
        )
        ledger = make_ledger([item, make_item(key="", changed_paths=["src/other.py"])], [])
        selected = health.list_reselect_candidates(
            ledger,
            signals=health.ReselectSignals(
                live_mergeable_by_key={"abhimehro/demo#7": "DIRTY"},
                titles_by_key={"abhimehro/demo#7": "⚡ Bolt: repair"},
                unique_paths_by_key={"abhimehro/demo#7": ["src/unique.py"]},
            ),
        )
        self.assertEqual([entry["key"] for entry in selected], [key])

    def test_palette_conflicting_soft_shell_sticky_is_reselect(self) -> None:
        item = make_item(
            key="abhimehro/personal-config#2069@abc",
            sensitive_paths=["shell_execution", "generated_output"],
            changed_paths=[
                "maintenance/bin/analytics_dashboard.sh",
                "docs/cursor-automations/prompts/daily-pr-salvage.md",
            ],
            next_action=(
                "HOLD_CONTRACT Palette wrap + analytics_dashboard.sh CONFLICTING."
            ),
        )
        self.assertTrue(health.is_reselect_salvage_candidate(item))
        # Soft sticky still blocks classic salvage_eligible (monitor unchanged).
        self.assertFalse(health.is_salvage_eligible(item))

    def test_never_touch_seatek_692_and_ctrld_1206(self) -> None:
        base = make_item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                {**base, "key": "abhimehro/Seatek_Analysis#692@dead"}
            )
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                {
                    **base,
                    "key": "abhimehro/ctrld-sync#1206@dead",
                    "sensitive_paths": ["security_configuration"],
                }
            )
        )
        self.assertTrue(health.is_never_touch_key("abhimehro/ctrld-sync#1206@dead"))

    def test_review_security_and_lockfile_only_blocked(self) -> None:
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                make_item(
                    guardrail_outcome="REVIEW_SECURITY",
                    next_action="CONFLICTING security twin",
                    changed_paths=["validate_data.py"],
                )
            )
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                make_item(
                    sensitive_paths=["lockfiles_and_major_dependencies"],
                    changed_paths=["uv.lock"],
                    next_action="HOLD_CONTRACT CONFLICTING lockfile major-dep",
                )
            )
        )

    def test_live_mergeable_required_conflicting_or_dirty(self) -> None:
        item = make_item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT do not merge without unique language",
        )
        self.assertFalse(health.is_reselect_salvage_candidate(item))
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, live_mergeable="CONFLICTING")
        )
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, live_mergeable="DIRTY", unique_remaining_paths=["src/demo.py"]
            )
        )

    def test_live_mergeability_overrides_stale_conflicting_action(self) -> None:
        item = make_item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(item, live_mergeable="MERGEABLE")
        )
        self.assertTrue(
            health.is_reselect_salvage_candidate(item, live_mergeable="dirty")
        )

    def test_explicit_empty_unique_signal_does_not_reselect_stale_paths(self) -> None:
        item = make_item(
            changed_paths=["src/old.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        selected = health.list_reselect_candidates(
            make_ledger([item], []),
            signals=health.ReselectSignals(unique_paths_by_key={item["key"]: []}),
        )
        self.assertEqual(selected, [])

    def test_palette_shell_sticky_rejects_near_match_paths(self) -> None:
        item = make_item(
            sensitive_paths=["shell_execution", "generated_output"],
            next_action="Palette wrap DIRTY unique remaining",
        )
        for path in (
            "maintenance/bin/refresh.py",
            "docs/cursor-automations-copy/prompt.md",
            "scripts/deploy.sh",
        ):
            with self.subTest(path=path):
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        item,
                        unique_remaining_paths=["maintenance/bin/refresh.sh", path],
                    )
                )

    def test_title_allowlist_for_non_bot_ledger_author(self) -> None:
        item = make_item(
            author_type="HUMAN",
            changed_paths=["maintenance/bin/analytics_dashboard.sh"],
            sensitive_paths=["shell_execution", "generated_output"],
            next_action="Palette wrap CONFLICTING",
        )
        self.assertFalse(health.is_reselect_salvage_candidate(item))
        self.assertTrue(
            health.is_reselect_salvage_candidate(
                item, title="🎨 Palette: wrap analytics dashboard"
            )
        )

    def test_list_reselect_candidates_respects_limit(self) -> None:
        items = [
            make_item(
                key=f"abhimehro/personal-config#{n}@abc",
                pr=n,
                changed_paths=["src/demo.py"],
                next_action="HOLD_CONTRACT CONFLICTING unique remaining",
                sensitive_paths=["generated_output"],
            )
            for n in (100, 101, 102)
        ]
        ledger = make_ledger(items, [])
        got = health.list_reselect_candidates(ledger, limit=2)
        self.assertEqual(len(got), 2)



if __name__ == "__main__":
    unittest.main()
