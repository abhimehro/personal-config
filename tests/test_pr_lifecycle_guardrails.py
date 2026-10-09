"""Tests for the deterministic guardrail path evaluator."""

from __future__ import annotations

import copy
import sys
import unittest
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from unittest import mock

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
        "author_type": "BOT",
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


class EvaluateLedgerTests(unittest.TestCase):
    def test_metadata_repair_preserves_revision_events_and_reports_no_flip(
        self,
    ) -> None:
        """Repair a security hold even when the outcome itself is unchanged."""
        now = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
        item = _item(
            classification="SECURITY",
            guardrail_outcome="REVIEW_SECURITY",
            guardrail_source="stand_in",
            sensitive_paths=["security_configuration"],
            risk_class="UNKNOWN",
            revision=7,
            updated_at_utc="2026-10-08T12:00:00Z",
        )
        ledger = {"items": [item], "events": [], "ledger_revision": 19}
        before = copy.deepcopy(ledger)
        with mock.patch.object(guardrails, "datetime") as clock:
            clock.now.return_value = now
            result, summary = guardrails.evaluate_ledger(ledger, None)

        self.assertIs(result, ledger)
        expected = copy.deepcopy(before)
        expected["items"][0].update(
            sensitive_paths=[],
            guardrail_source="path_eval",
            risk_class="SENSITIVE",
            updated_at_utc="2026-10-09T12:00:00Z",
        )
        self.assertEqual(expected, ledger)
        self.assertEqual(
            {
                "evaluated": 1,
                "outcomes_unchanged": 1,
                "skipped": 0,
                "by_outcome": {"REVIEW_SECURITY": 1, "PASS_ROUTINE": 0},
                "changes": [],
            },
            summary,
        )

        # A second evaluation must not refresh timestamps or count another repair.
        with mock.patch.object(guardrails, "datetime") as clock:
            clock.now.return_value = datetime(2026, 10, 10, tzinfo=timezone.utc)
            _, repeated = guardrails.evaluate_ledger(ledger, None, clear_standin=True)
        self.assertEqual(expected, ledger)
        self.assertEqual(0, repeated["evaluated"])
        self.assertEqual(1, repeated["skipped"])
        self.assertEqual([], repeated["changes"])

    def test_outcome_changes_preserve_item_revision(self) -> None:
        for revision, paths, outcome in product(
            (0, 1, 42),
            (["docs/a.md"], ["scripts/fix.sh"]),
            (None, "NOT_RUN"),
        ):
            with self.subTest(revision=revision, paths=paths, outcome=outcome):
                item = _item(
                    revision=revision, changed_paths=paths, guardrail_outcome=outcome
                )
                ledger = {"items": [item], "events": [], "ledger_revision": 10}
                _, summary = guardrails.evaluate_ledger(ledger, None)
                expected_outcome = (
                    "PASS_ROUTINE" if paths == ["docs/a.md"] else "REVIEW_SECURITY"
                )
                self.assertEqual(revision, item["revision"])
                self.assertEqual([], ledger["events"])
                self.assertEqual(10, ledger["ledger_revision"])
                self.assertEqual(1, summary["evaluated"])
                self.assertEqual(0, summary["outcomes_unchanged"])
                self.assertEqual(1, summary["by_outcome"][expected_outcome])
                self.assertEqual(
                    [
                        {
                            "key": item["key"],
                            "from": outcome,
                            "to": expected_outcome,
                            "sensitive_paths": (
                                []
                                if expected_outcome == "PASS_ROUTINE"
                                else ["shell_execution"]
                            ),
                        }
                    ],
                    summary["changes"],
                )

    def test_non_bot_items_remain_unchanged_in_mixed_ledger(self) -> None:
        excluded = [
            _item(author_type=author_type, guardrail_outcome="REVIEW_SECURITY")
            for author_type in ("HUMAN", "UNKNOWN", None)
        ]
        missing_author = _item()
        del missing_author["author_type"]
        excluded.append(missing_author)
        before = copy.deepcopy(excluded)
        bot = _item(guardrail_outcome="REVIEW_SECURITY", classification="DEPENDENCY")
        ledger = {"items": [*excluded, bot]}

        _, summary = guardrails.evaluate_ledger(ledger, None, clear_standin=True)

        self.assertEqual(before, excluded)
        self.assertEqual("PASS_ROUTINE", bot["guardrail_outcome"])
        self.assertEqual(1, summary["evaluated"])
        self.assertEqual(4, summary["skipped"])

    def test_preserves_revision_and_filters_repos(self) -> None:
        """revision is a projection of transition events — evaluation must
        not bump it without logging one (ledger consistency check)."""
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
        self.assertEqual(2, a["revision"])
        self.assertEqual(1, b["revision"])
        self.assertIn("updated_at_utc", a)
        self.assertNotIn("updated_at_utc", b)

    def test_evaluated_example_ledger_passes_validation(self) -> None:
        """End-to-end: run evaluation on a schema-valid ledger, then the
        real schema + runtime-record validators accept the write."""
        from pr_lifecycle_ledger import validate_runtime_records
        from pr_lifecycle_schema import validate_schema
        from pr_lifecycle_yaml import load_yaml

        from tests.pr_lifecycle_helpers import schema_valid_starved_ledger

        ledger = schema_valid_starved_ledger()
        item = ledger["items"][0]
        # Move the item back to STAGE1_INTAKE with a legal HANDOFF event so
        # the projected fields (state/owner/revision/handoffs) stay
        # consistent with the event log.
        return_event = {
            "event_id": "evt-2026-stage3-return-001",
            "kind": "HANDOFF",
            "item_key": item["key"],
            "from_owner": "stage3",
            "to_owner": "stage1",
            "from_state": "STAGE3_RECONCILIATION",
            "to_state": "STAGE1_INTAKE",
            "next_owner": "stage1",
            "terminal_disposition": None,
            "parent_event_id": None,
            "expected_item_revision": 1,
            "resulting_item_revision": 2,
            "idempotency_key": f"{item['key']}:evt-2026-stage3-return-001",
            "status": "PROJECTED",
            "created_at_utc": "2026-10-09T12:00:00Z",
            "acknowledged_at_utc": None,
            "reason": "Stage 3 handed it back for re-evaluation.",
        }
        ledger["events"].insert(2, return_event)
        item.update(
            {
                "author_type": "BOT",
                "lifecycle_state": "STAGE1_INTAKE",
                "current_owner": "stage1",
                "next_owner": "stage1",
                "revision": 2,
                "handoffs": [*item["handoffs"], "evt-2026-stage3-return-001"],
                "guardrail_outcome": "REVIEW_SECURITY",
                "changed_paths": ["docs/plan.md"],
            }
        )
        guardrails.evaluate_ledger(ledger, None, clear_standin=True)
        self.assertEqual("PASS_ROUTINE", item["guardrail_outcome"])
        self.assertEqual("path_eval", item["guardrail_source"])
        validate_schema(ledger)
        config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        validate_runtime_records(ledger, config)


class GuardrailSourceSchemaTests(unittest.TestCase):
    def test_all_documented_sources_are_accepted(self) -> None:
        from pr_lifecycle_schema import validate_schema
        from pr_lifecycle_yaml import load_yaml

        for source in ("path_eval", "stand_in", "manual", "review", "human", "octopus"):
            with self.subTest(source=source):
                ledger = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")
                ledger["items"][0]["guardrail_source"] = source
                validate_schema(ledger)

    def test_source_is_optional_for_existing_ledgers(self) -> None:
        from pr_lifecycle_schema import validate_schema
        from pr_lifecycle_yaml import load_yaml

        ledger = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")
        for item in ledger["items"]:
            item.pop("guardrail_source", None)
        validate_schema(ledger)

    def test_invalid_sources_are_rejected_at_the_item_field(self) -> None:
        from pr_lifecycle_schema import validate_schema
        from pr_lifecycle_yaml import load_yaml

        for source in ("", "PATH_EVAL", "unknown", None, 1, True, [], {}):
            with self.subTest(source=source):
                ledger = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")
                ledger["items"][0]["guardrail_source"] = source
                with self.assertRaisesRegex(
                    ValueError, r"schema items\.0\.guardrail_source:"
                ):
                    validate_schema(ledger)


class ArgParseTests(unittest.TestCase):
    def test_json_flag_accepted(self) -> None:
        args = guardrails.build_parser().parse_args(["--json"])
        self.assertTrue(args.json_out)
        self.assertFalse(args.apply)
        self.assertFalse(args.clear_standin)

    def test_clear_stand_in_flag_accepted(self) -> None:
        args = guardrails.build_parser().parse_args(
            ["--apply", "--json", "--clear-stand-in"]
        )
        self.assertTrue(args.clear_standin)


if __name__ == "__main__":
    unittest.main()
