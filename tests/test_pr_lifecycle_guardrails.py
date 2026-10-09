"""Tests for the deterministic guardrail path evaluator."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_guardrails as guardrails


def _item(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "key": "owner/repo#1@abc",
        "repository": "owner/repo",
        "pr": 1,
        "lifecycle_state": "STAGE1_INTAKE",
        "guardrail_outcome": "NOT_RUN",
        "changed_paths": ["docs/readme.md"],
        "revision": 1,
    }
    item.update(overrides)
    return item


class ClassifyPathTests(unittest.TestCase):
    def test_sensitive_classes_match(self) -> None:
        cases = {
            ".github/workflows/ci.yml": "workflows_and_permissions",
            ".env.production": "secrets",
            "uv.lock": "lockfiles_and_major_dependencies",
            "scripts/maint.sh": "shell_execution",
            "docs/cursor-automations/exports/x.json": "generated_output",
            "schemas/ledger.schema.json": "public_api_contracts",
            "src/db/migrations/0001.py": "database_migrations",
            "configs/proxy.toml": "network_and_browser_origins",
        }
        for path, expected in cases.items():
            self.assertIn(expected, guardrails.classify_path(path), path)

    def test_plain_files_match_nothing(self) -> None:
        for path in ("README.md", "src/main.py", "tests/test_x.py", "docs/a.md"):
            self.assertEqual(set(), guardrails.classify_path(path), path)

    def test_all_rule_classes_exist_in_config_taxonomy(self) -> None:
        from pr_lifecycle_yaml import load_yaml

        config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        taxonomy = set(
            (config.get("sensitive_path_taxonomy") or {}).get("classes") or []
        )
        rule_classes = {name for name, _ in guardrails._PATH_RULES}
        self.assertEqual(set(), rule_classes - taxonomy)


class EvaluateItemTests(unittest.TestCase):
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
            )
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])
        self.assertEqual([], patch["sensitive_paths"])
        self.assertEqual("ROUTINE", patch["risk_class"])

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
                    sensitive_paths=["shell_execution"],
                    risk_class="SENSITIVE",
                    changed_paths=["scripts/x.sh"],
                )
            )
        )


class EvaluateLedgerTests(unittest.TestCase):
    def test_bumps_revision_and_filters_repos(self) -> None:
        ledger = {
            "items": [
                _item(
                    repository="owner/a",
                    pr=1,
                    changed_paths=["scripts/x.sh"],
                    revision=2,
                ),
                _item(
                    repository="owner/b",
                    pr=2,
                    changed_paths=["scripts/x.sh"],
                    revision=1,
                ),
            ]
        }
        _, summary = guardrails.evaluate_ledger(ledger, {"owner/a"})
        self.assertEqual(1, summary["evaluated"])
        a, b = ledger["items"]
        self.assertEqual(3, a["revision"])
        self.assertEqual(1, b["revision"])
        self.assertIn("updated_at_utc", a)


if __name__ == "__main__":
    unittest.main()
