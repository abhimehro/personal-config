"""Tests for evaluate_item logic."""

from __future__ import annotations

import copy
import sys
import unittest
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_guardrails as guardrails  # noqa: E402
from tests.pr_lifecycle_helpers import guardrail_item as _item  # noqa: E402


class EvaluateItemTests(unittest.TestCase):
    """Tests for evaluate_item logic."""

    def test_missing_author_type_never_evaluated(self) -> None:
        for paths, clear_standin in product(
            (["docs/a.md"], ["scripts/fix.sh"]), (False, True)
        ):
            with self.subTest(paths=paths, clear_standin=clear_standin):
                item = _item(classification="SECURITY", changed_paths=paths)
                del item["author_type"]
                before = copy.deepcopy(item)
                self.assertIsNone(guardrails.evaluate_item(item, clear_standin))
                self.assertEqual(before, item)

    def test_security_identity_overrides_nonsticky_paths(self) -> None:
        """Generated output exemptions cannot drain identity-based holds."""
        for paths, classes in (
            (["docs/a.md"], []),
            (["generated/report.md"], ["generated_output"]),
        ):
            for outcome, source, clear_standin in product(
                (None, "NOT_RUN", "REVIEW_SECURITY"),
                (None, "stand_in", "path_eval"),
                (False, True),
            ):
                with self.subTest(
                    paths=paths,
                    outcome=outcome,
                    source=source,
                    clear_standin=clear_standin,
                ):
                    item = _item(
                        classification="SECURITY",
                        changed_paths=paths,
                        guardrail_outcome=outcome,
                        guardrail_source=source,
                        risk_class="UNKNOWN",
                    )
                    before = copy.deepcopy(item)
                    self.assertEqual(
                        {
                            "sensitive_paths": classes,
                            "guardrail_outcome": "PASS_ROUTINE",
                            "guardrail_source": "path_eval",
                            "risk_class": "ROUTINE",
                        },
                        guardrails.evaluate_item(item, clear_standin),
                    )
                    self.assertEqual(before, item)

    def test_security_identity_does_not_bypass_eligibility(self) -> None:
        """Security classification must respect non-path holds and ownership."""
        exclusions = [
            {"author_type": "HUMAN"},
            {"author_type": "UNKNOWN"},
            {"lifecycle_state": "TERMINAL"},
            {"changed_paths": []},
            {"changed_paths": None},
            {"changed_paths": "docs/a.md"},
            *({"current_owner": owner} for owner in ("human", "stage2", "stage3")),
            *(
                {"guardrail_source": source}
                for source in ("manual", "review", "human", "octopus")
            ),
            *(
                {"guardrail_outcome": outcome}
                for outcome in (
                    "HOLD_PLATFORM",
                    "HOLD_CANONICAL",
                    "CLOSE_NONSECURITY_NOOP",
                    "ANALYSIS_ERROR",
                    "PASS_ROUTINE",
                )
            ),
        ]
        for overrides, clear_standin in product(exclusions, (False, True)):
            with self.subTest(overrides=overrides, clear_standin=clear_standin):
                item = _item(classification="SECURITY", **overrides)
                before = copy.deepcopy(item)
                self.assertIsNone(guardrails.evaluate_item(item, clear_standin))
                self.assertEqual(before, item)

    def test_security_identity_retains_sorted_path_evidence(self) -> None:
        item = _item(
            classification="SECURITY",
            changed_paths=["scripts/fix.sh", "generated/report.md", ".env", ".env"],
        )
        self.assertEqual(
            {
                "sensitive_paths": ["generated_output", "secrets", "shell_execution"],
                "guardrail_outcome": "REVIEW_SECURITY",
                "guardrail_source": "path_eval",
                "risk_class": "SENSITIVE",
            },
            guardrails.evaluate_item(item, clear_standin=True),
        )

    def test_not_run_with_shell_path_becomes_review_security(self) -> None:
        patch = guardrails.evaluate_item(
            _item(changed_paths=["scripts/report-daemons-watchdog.sh"])
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("REVIEW_SECURITY", patch["guardrail_outcome"])
        self.assertEqual(["shell_execution"], patch["sensitive_paths"])
        self.assertEqual("SENSITIVE", patch["risk_class"])

    def test_generated_output_alone_is_not_sticky(self) -> None:
        patch = guardrails.evaluate_item(_item(changed_paths=["generated/report.md"]))
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])
        self.assertEqual(["generated_output"], patch["sensitive_paths"])

    def test_jules_markdown_journals_are_docs(self) -> None:
        for path in (
            ".jules/sentinel.md",
            ".Jules/sentinel.md",
            ".jules/journal/2026-10-09.md",
            "pkg/.jules/notes.MD",
        ):
            self.assertEqual(set(), guardrails.classify_path(path), path)
        self.assertIn("generated_output", guardrails.classify_path(".jules/cache.json"))
        patch = guardrails.evaluate_item(
            _item(
                classification="SECURITY",
                guardrail_outcome="REVIEW_SECURITY",
                sensitive_paths=["generated_output"],
                changed_paths=[".jules/sentinel.md"],
            )
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])
        self.assertEqual([], patch["sensitive_paths"])

    def test_empty_paths_keep_current_outcome(self) -> None:
        self.assertIsNone(guardrails.evaluate_item(_item(changed_paths=[])))
        self.assertIsNone(guardrails.evaluate_item(_item(changed_paths=None)))

    def test_already_correct_item_returns_none(self) -> None:
        self.assertIsNone(
            guardrails.evaluate_item(
                _item(
                    guardrail_outcome="REVIEW_SECURITY",
                    guardrail_source="path_eval",
                    sensitive_paths=["shell_execution"],
                    risk_class="SENSITIVE",
                    changed_paths=["scripts/x.sh"],
                )
            )
        )

    def test_non_bot_authors_never_evaluated(self) -> None:
        """Human/unknown-authored items stay untouched (ledger contract
        forbids ROUTINE on them; forced holds are out of scope)."""
        for author_type in ("HUMAN", "UNKNOWN", None):
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(
                        author_type=author_type,
                        guardrail_outcome="REVIEW_SECURITY",
                        changed_paths=["docs/a.md"],
                    ),
                    clear_standin=True,
                ),
                author_type,
            )
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(author_type=author_type, changed_paths=["x.sh"])
                ),
                author_type,
            )

    def test_security_classification_alone_is_not_a_hold(self) -> None:
        """classification=SECURITY does not hold a path-clean item."""
        patch = guardrails.evaluate_item(
            _item(
                classification="SECURITY",
                changed_paths=["docs/a.md", "src/main.py"],
            )
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])
        self.assertEqual("ROUTINE", patch["risk_class"])
        held = guardrails.evaluate_item(
            _item(
                classification="SECURITY",
                guardrail_outcome="REVIEW_SECURITY",
                sensitive_paths=[],
                changed_paths=["src/main.py"],
            ),
            evidence=guardrails.GuardrailEvidence(
                diff_text=(
                    "diff --git a/src/main.py b/src/main.py\n"
                    "+++ b/src/main.py\n"
                    "@@\n"
                    "+subprocess.run(cmd, shell=True)\n"
                )
            ),
        )
        self.assertIsNotNone(held)
        assert held is not None
        self.assertEqual("REVIEW_SECURITY", held["guardrail_outcome"])
        self.assertIn("shell_execution", held["sensitive_paths"])
        # Non-SECURITY classifications still clear normally.
        for classification in ("DEPENDENCY", "UI", "UNKNOWN"):
            patch = guardrails.evaluate_item(
                _item(
                    classification=classification,
                    guardrail_outcome="REVIEW_SECURITY",
                    changed_paths=["docs/a.md"],
                ),
                clear_standin=True,
            )
            self.assertIsNotNone(patch, classification)
            assert patch is not None
            self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])

    def test_protected_guardrail_source_never_cleared(self) -> None:
        """A hold stamped by a real review survives even --clear-stand-in."""
        for source in ("manual", "review", "human", "octopus"):
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(
                        guardrail_outcome="REVIEW_SECURITY",
                        guardrail_source=source,
                        changed_paths=["docs/a.md"],
                    ),
                    clear_standin=True,
                ),
                source,
            )

    def test_sentinel_title_standin_is_re_evaluated(self) -> None:
        """Stage 1's morning Sentinel-title stand-in re-evaluates from paths/diff."""
        standin_action = (
            "Stage 1 2026-10-17 AM: REVIEW_SECURITY (security-themed Sentinel title; "
            "Desk standing order: security PRs never PASS_ROUTINE). "
            "Path-only guardrail had downgraded; hold for security review."
        )
        routine_item = _item(
            classification="SECURITY",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="manual",
            next_action=standin_action,
            changed_paths=[
                "scripts/export_comparison_sheets.py",
                "scripts/tests/test_export_comparison_sheets_security.py",
            ],
        )
        patch = guardrails.evaluate_item(
            routine_item,
            evidence=guardrails.GuardrailEvidence(
                diff_text=(
                    "diff --git a/scripts/export_comparison_sheets.py "
                    "b/scripts/export_comparison_sheets.py\n"
                    "+++ b/scripts/export_comparison_sheets.py\n"
                    "@@\n"
                    "+log.exception('Unexpected error loading raw file %s', raw_file)\n"
                )
            ),
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])
        self.assertEqual([], patch["sensitive_paths"])

        real_sec_item = _item(
            classification="SECURITY",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="manual",
            next_action=standin_action,
            changed_paths=[
                ".jules/sentinel.md",
                "src/hydrograph_seatek_analysis/utils/security.py",
            ],
        )
        sec_patch = guardrails.evaluate_item(real_sec_item)
        self.assertIsNotNone(sec_patch)
        assert sec_patch is not None
        self.assertEqual("REVIEW_SECURITY", sec_patch["guardrail_outcome"])
        self.assertEqual(["security_configuration"], sec_patch["sensitive_paths"])

    def test_github_agent_command_and_instruction_files_sticky(self) -> None:
        for path in (
            ".github/commands/gemini-invoke.toml",
            ".github/copilot-instructions.md",
            ".github/jules-review-rules.md",
            ".github/hooks/pre-push.sh",
            ".github/agents/review.agent.md",
            ".claude/settings.json",
            ".mcp.json",
        ):
            self.assertIn(
                "workflows_and_permissions",
                guardrails.classify_path(path),
                path,
            )

    def test_agent_instruction_and_prompt_surfaces_sticky(self) -> None:
        for path in (
            ".agents/skills/x/SKILL.md",
            "AGENTS.md",
            "CLAUDE.md",
            ".cursorrules",
            "docs/cursor-automations/prompts/daily-pr-review.md",
            "docs/cursor-automations/exports/daily-pr-review.json",
        ):
            self.assertIn(
                "workflows_and_permissions",
                guardrails.classify_path(path),
                path,
            )


if __name__ == "__main__":
    unittest.main()