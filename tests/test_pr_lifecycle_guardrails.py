"""Tests for the deterministic guardrail path evaluator."""

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

import pr_lifecycle_guardrails as guardrails

from tests.pr_lifecycle_helpers import guardrail_item as _item


class ClassifyPathTests(unittest.TestCase):
    def test_sensitive_classes_match(self) -> None:
        cases = {
            ".github/workflows/ci.yml": "workflows_and_permissions",
            ".env.production": "secrets",
            "uv.lock": "lockfiles_and_major_dependencies",
            "scripts/maint.sh": "shell_execution",
            "docs/cursor-automations/exports/x.json": "workflows_and_permissions",
            "schemas/ledger.schema.json": "public_api_contracts",
            "src/db/migrations/0001.py": "database_migrations",
            "configs/proxy.toml": "network_and_browser_origins",
        }
        for path, expected in cases.items():
            self.assertIn(expected, guardrails.classify_path(path), path)

    def test_plain_files_match_nothing(self) -> None:
        for path in ("README.md", "src/main.py", "tests/test_x.py", "docs/a.md"):
            self.assertEqual(set(), guardrails.classify_path(path), path)

    def test_editor_and_agent_dirs_match(self) -> None:
        """Directory patterns match files inside them (Octopus regression)."""
        for path in (
            ".cursor/hooks.json",
            ".devin/hooks.json",
            ".vscode/settings.json",
            ".idea/workspace.xml",
            ".gitignore",
            "sub/dir/.cursor/rules/x.mdc",
        ):
            self.assertIn(
                "file_read_write_boundaries", guardrails.classify_path(path), path
            )

    def test_nested_requirements_and_api_dirs_match(self) -> None:
        """requirements/ and api/ directory contents classify too."""
        self.assertIn(
            "lockfiles_and_major_dependencies",
            guardrails.classify_path("requirements/dev.txt"),
        )
        for path in ("api/spec.json", "apis/v1/openapi.yaml"):
            self.assertIn("public_api_contracts", guardrails.classify_path(path), path)

    def test_all_rule_classes_exist_in_config_taxonomy(self) -> None:
        from pr_lifecycle_yaml import load_yaml

        config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        taxonomy = set(
            (config.get("sensitive_path_taxonomy") or {}).get("classes") or []
        )
        rule_classes = {name for name, _ in guardrails._PATH_RULES}
        self.assertEqual(set(), rule_classes - taxonomy)


class EvaluateItemTests(unittest.TestCase):
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
                            "guardrail_outcome": "REVIEW_SECURITY",
                            "guardrail_source": "path_eval",
                            "risk_class": "SENSITIVE",
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
                    "HOLD_CONTRACT",
                    "HOLD_EVIDENCE",
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

    def test_docs_only_clears_stand_in_review(self) -> None:
        patch = guardrails.evaluate_item(
            _item(
                guardrail_outcome="REVIEW_SECURITY",
                sensitive_paths=["security_configuration"],
                changed_paths=["docs/plan.md", "tasks/today.md"],
            ),
            clear_standin=True,
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])
        self.assertEqual([], patch["sensitive_paths"])
        self.assertEqual("ROUTINE", patch["risk_class"])

    def test_review_security_preserved_without_clear_standin(self) -> None:
        """REVIEW_SECURITY is sticky by default; only the opt-in clears it."""
        patch = guardrails.evaluate_item(
            _item(
                guardrail_outcome="REVIEW_SECURITY",
                sensitive_paths=["security_configuration"],
                changed_paths=["docs/plan.md", "tasks/today.md"],
            )
        )
        self.assertIsNone(patch)

    def test_owned_items_never_evaluated(self) -> None:
        for owner in ("human", "stage2", "stage3"):
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(current_owner=owner, changed_paths=["scripts/x.sh"]),
                    clear_standin=True,
                ),
                owner,
            )
        self.assertIsNotNone(
            guardrails.evaluate_item(
                _item(current_owner="stage1", changed_paths=["scripts/x.sh"])
            )
        )

    def test_generated_output_alone_is_not_sticky(self) -> None:
        patch = guardrails.evaluate_item(
            _item(changed_paths=[".jules/journal/2026-10-09.md"])
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])
        self.assertEqual(["generated_output"], patch["sensitive_paths"])

    def test_terminal_and_manual_outcomes_untouched(self) -> None:
        for outcome in (
            "PASS_ROUTINE",
            "HOLD_CONTRACT",
            "HOLD_EVIDENCE",
            "HOLD_PLATFORM",
            "HOLD_CANONICAL",
            "CLOSE_NONSECURITY_NOOP",
            "ANALYSIS_ERROR",
        ):
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(
                        guardrail_outcome=outcome,
                        changed_paths=["scripts/x.sh"],
                    )
                ),
                outcome,
            )
        self.assertIsNone(
            guardrails.evaluate_item(
                _item(lifecycle_state="TERMINAL", changed_paths=["x.sh"])
            )
        )

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

    def test_security_classification_is_sticky(self) -> None:
        """classification=SECURITY keeps the hold without sticky paths —
        a Sentinel fix can touch only ordinary files (Grok dry-run: the
        flag would have flipped ~30 Sentinel fixes)."""
        patch = guardrails.evaluate_item(
            _item(
                classification="SECURITY",
                changed_paths=["docs/a.md", "src/main.py"],
            )
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("REVIEW_SECURITY", patch["guardrail_outcome"])
        self.assertEqual("SENSITIVE", patch["risk_class"])
        # And an existing REVIEW_SECURITY on a SECURITY-classed item is
        # never drained by --clear-stand-in: evaluation may re-stamp
        # provenance, but the hold itself stays.
        held = guardrails.evaluate_item(
            _item(
                classification="SECURITY",
                guardrail_outcome="REVIEW_SECURITY",
                sensitive_paths=[],
                changed_paths=["docs/a.md"],
            ),
            clear_standin=True,
        )
        self.assertIsNotNone(held)
        assert held is not None
        self.assertEqual("REVIEW_SECURITY", held["guardrail_outcome"])
        self.assertEqual("SENSITIVE", held["risk_class"])
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
