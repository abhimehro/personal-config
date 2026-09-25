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
from tests.pr_lifecycle_helpers import (  # noqa: E402
    make_item,
    make_ledger,
    make_work_item,
)

class ReselectCandidateTests(unittest.TestCase):
    def test_reselect_rejects_terminal_and_non_salvage_outcomes(self) -> None:
        """Verify terminal and non-salvage outcomes cannot be reselected."""
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
        """Verify reselection requires unique paths outside the journal."""
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
        """Verify Palette shell execution uses only allowlisted paths."""
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
        """Verify bot title prefixes reject unrelated human titles."""
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
        """Verify candidate signals resolve from a source PR prefix."""
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
        """Verify conflicting Palette shell work qualifies for reselection."""
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
        """Verify protected Seatek and ctrld PRs cannot be reselected."""
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
        """Verify security review and lockfile-only work stays blocked."""
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
        """Verify live mergeability must be conflicting or dirty."""
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
        """Verify live mergeability takes priority over stale action text."""
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
        """Verify an explicit empty path signal blocks stale path fallback."""
        item = make_item(
            changed_paths=["src/old.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        selected = health.list_reselect_candidates(
            make_ledger([item], []),
            signals=health.ReselectSignals(unique_paths_by_key={item["key"]: []}),
        )
        self.assertEqual(selected, [])

    def test_exact_empty_signal_overrides_positive_source_prefix_signal(self) -> None:
        """A current SHA with no unique paths cannot reuse stale PR metadata."""
        item = make_item(
            key="abhimehro/demo#1@new",
            changed_paths=["src/old.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        selected = health.list_reselect_candidates(
            make_ledger([item], []),
            signals=health.ReselectSignals(
                unique_paths_by_key={
                    "abhimehro/demo#1": ["src/previous.py"],
                    item["key"]: [],
                }
            ),
        )
        self.assertEqual(selected, [])

    def test_exact_live_mergeability_overrides_stale_prefix_and_action(self) -> None:
        """A current mergeable SHA must not inherit a stale conflicting signal."""
        item = make_item(
            key="abhimehro/demo#1@new",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        selected = health.list_reselect_candidates(
            make_ledger([item], []),
            signals=health.ReselectSignals(
                live_mergeable_by_key={
                    "abhimehro/demo#1": "CONFLICTING",
                    item["key"]: "MERGEABLE",
                }
            ),
        )
        self.assertEqual(selected, [])

    def test_palette_shell_allowlist_keeps_other_sticky_holds(self) -> None:
        """An allowed wrap path cannot bypass a separate sensitive-path hold."""
        item = make_item(
            sensitive_paths=["shell_execution", "security_configuration"],
            next_action="Palette wrap CONFLICTING unique remaining",
        )
        self.assertFalse(
            health.is_reselect_salvage_candidate(
                item, unique_remaining_paths=["maintenance/bin/refresh.sh"]
            )
        )

    def test_stage2_owned_or_queued_item_cannot_be_reselected(self) -> None:
        """Reselection must not duplicate work already assigned to Stage 2."""
        base = make_item(
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        for overrides in (
            {"current_owner": "stage2"},
            {"current_owner": "stage1", "lifecycle_state": "STAGE2_QUEUED"},
            {"current_owner": "stage1", "lifecycle_state": "STAGE2_ACTIVE"},
        ):
            with self.subTest(overrides=overrides):
                self.assertFalse(
                    health.is_reselect_salvage_candidate({**base, **overrides})
                )

    def test_palette_shell_sticky_rejects_near_match_paths(self) -> None:
        """Verify Palette path matching rejects similar but unlisted paths."""
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

    def test_palette_shell_sticky_requires_wrap_not_bare_palette(self) -> None:
        """Verify bare-Palette and prohibited-wrap actions keep the shell hold."""
        for next_action in (
            "Palette colors CONFLICTING unique remaining",
            "Palette: do not wrap; CONFLICTING unique remaining",
        ):
            with self.subTest(next_action=next_action):
                item = make_item(
                    sensitive_paths=["shell_execution", "generated_output"],
                    next_action=next_action,
                )
                self.assertFalse(
                    health.is_reselect_salvage_candidate(
                        item,
                        unique_remaining_paths=["maintenance/bin/refresh.sh"],
                    )
                )

    def test_title_allowlist_for_non_bot_ledger_author(self) -> None:
        """Verify the title allowlist can classify a non-bot ledger author."""
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
        """Verify candidate listing honors its requested limit."""
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

    def test_expired_work_item_does_not_block_reselect(self) -> None:
        """Verify only a still-usable work item suppresses reselection."""
        item = make_item(
            key="abhimehro/demo#1@abc",
            changed_paths=["src/demo.py"],
            next_action="HOLD_CONTRACT CONFLICTING unique remaining",
        )
        expired = make_ledger(
            [item], [make_work_item(expiry_utc="2026-01-01T00:00:00Z")]
        )
        usable = make_ledger(
            [item], [make_work_item(expiry_utc="2999-01-01T00:00:00Z")]
        )
        self.assertEqual(len(health.list_reselect_candidates(expired)), 1)
        self.assertEqual(len(health.list_reselect_candidates(usable)), 0)


if __name__ == "__main__":
    unittest.main()
