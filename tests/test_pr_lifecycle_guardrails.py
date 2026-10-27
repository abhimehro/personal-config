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

import pr_lifecycle_guardrails as guardrails  # noqa: E402

from tests.pr_lifecycle_helpers import guardrail_item as _item  # noqa: E402


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
                    expected_stamp = {
                        "head_sha": item["head_sha"],
                        "basis": "non_executable_paths",
                        "diff_sha256": None,
                    }
                    self.assertEqual(
                        {
                            "sensitive_paths": classes,
                            "guardrail_outcome": "PASS_ROUTINE",
                            "guardrail_source": "path_eval",
                            "risk_class": "ROUTINE",
                            "guardrail_evidence": expected_stamp,
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
                )
            ),
            {
                "guardrail_outcome": "PASS_ROUTINE",
                "guardrail_evidence": {
                    "head_sha": "a" * 40,
                    "basis": "non_executable_paths",
                    "diff_sha256": None,
                },
            },
        ]
        for overrides, clear_standin in product(exclusions, (False, True)):
            with self.subTest(overrides=overrides, clear_standin=clear_standin):
                values = (
                    overrides
                    if isinstance(overrides, dict)
                    else {"guardrail_outcome": overrides}
                )
                item = _item(classification="SECURITY", **values)
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
                "guardrail_evidence": None,
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

    def test_review_security_without_sensitive_paths_clears(self) -> None:
        """A path-clean REVIEW_SECURITY downgrades without an extra flag."""
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

    def test_human_review_items_never_evaluated(self) -> None:
        """risk_class=HUMAN_REVIEW is the ledger's human-hold marker (pc#2276
        shape): a BOT item with clean paths must keep the hold, even under
        --clear-stand-in, because a path classifier cannot judge a human's
        reasons."""
        for clear in (False, True):
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(
                        risk_class="HUMAN_REVIEW",
                        changed_paths=["docs/readme.md"],
                    ),
                    clear_standin=clear,
                ),
                f"NOT_RUN item, clear_standin={clear}",
            )
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(
                        guardrail_outcome="REVIEW_SECURITY",
                        risk_class="HUMAN_REVIEW",
                        changed_paths=["docs/readme.md"],
                    ),
                    clear_standin=clear,
                ),
                f"REVIEW_SECURITY item, clear_standin={clear}",
            )

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

    def test_terminal_and_manual_outcomes_untouched(self) -> None:
        for outcome in (
            {
                "guardrail_outcome": "PASS_ROUTINE",
                "guardrail_evidence": {
                    "head_sha": "a" * 40,
                    "basis": "head_bound_diff",
                    "diff_sha256": "d" * 64,
                },
            },
            "HOLD_CONTRACT",
            "HOLD_EVIDENCE",
            "HOLD_PLATFORM",
            "HOLD_CANONICAL",
            "CLOSE_NONSECURITY_NOOP",
            "ANALYSIS_ERROR",
        ):
            values = (
                outcome if isinstance(outcome, dict) else {"guardrail_outcome": outcome}
            )
            self.assertIsNone(
                guardrails.evaluate_item(
                    _item(
                        changed_paths=["scripts/x.sh"],
                        **values,
                    )
                ),
                values["guardrail_outcome"],
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

    def test_security_classification_alone_is_not_a_hold(self) -> None:
        """classification=SECURITY does not hold a path-clean item."""
        diff_text = "+++ b/src/main.py\n+print('ready')\n"
        patch = guardrails.evaluate_item(
            _item(
                classification="SECURITY",
                changed_paths=["docs/a.md", "src/main.py"],
            ),
            evidence=guardrails.GuardrailEvidence(
                diff_text=diff_text,
                head_sha="a" * 40,
                diff_sha256=guardrails.diff_sha256(diff_text),
            ),
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
                ),
                head_sha=routine_item["head_sha"],
                diff_sha256=guardrails.diff_sha256(
                    "diff --git a/scripts/export_comparison_sheets.py "
                    "b/scripts/export_comparison_sheets.py\n"
                    "+++ b/scripts/export_comparison_sheets.py\n"
                    "@@\n"
                    "+log.exception('Unexpected error loading raw file %s', raw_file)\n"
                ),
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


class DependabotEligibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.item = _item(
            author={"login": "dependabot[bot]", "identity_source": "github_api"},
            changed_paths=[".github/workflows/ci.yml"],
            guardrail_outcome="REVIEW_SECURITY",
        )
        self.evidence_fields = {
            "diff_text": "+++ b/.github/workflows/ci.yml\n+uses: actions/checkout@"
            + "a" * 40,
            "title": "Bump actions/checkout from 4.1.1 to 4.1.2",
            "required_checks_green": True,
            "mergeable": True,
        }

    def test_missing_or_uncertain_evidence_is_ineligible(self) -> None:
        self.assertFalse(guardrails.dependabot_routine_eligible(self.item, None))
        for overrides in (
            {"diff_text": None},
            {"diff_fetch_failed": True},
            {"mergeable": None},
            {"mergeable": False},
            {"required_checks_green": None},
            {"required_checks_green": False},
            {"title": "Update action"},
            {"diff_text": "+# from 4.1.1 to 4.2.0"},
        ):
            with self.subTest(overrides=overrides):
                evidence = guardrails.GuardrailEvidence(
                    **(self.evidence_fields | overrides)
                )
                self.assertFalse(
                    guardrails.dependabot_routine_eligible(self.item, evidence)
                )

    def test_path_lanes_cannot_mix_or_include_non_workflow_files(self) -> None:
        evidence = guardrails.GuardrailEvidence(**self.evidence_fields)
        for paths in (
            [],
            None,
            "uv.lock",
            [".github/workflows/ci.yml", "uv.lock"],
            [".github/workflows/ci.yml", "README.md"],
            [".github/actions/setup/action.yml"],
            [".github/workflows/README.md"],
            ["uv.lock", "src/main.py"],
            ["deploy/requirements.txt"],
        ):
            with self.subTest(paths=paths):
                item = {**self.item, "changed_paths": paths}
                self.assertFalse(guardrails.dependabot_routine_eligible(item, evidence))

    def test_multiple_workflows_or_lockfiles_can_be_routine(self) -> None:
        evidence = guardrails.GuardrailEvidence(**self.evidence_fields)
        for paths in (
            [".github/workflows/ci.yml", ".github/workflows/build.yaml"],
            ["uv.lock", "pkg/poetry.lock"],
        ):
            with self.subTest(paths=paths):
                self.assertTrue(
                    guardrails.dependabot_routine_eligible(
                        {**self.item, "changed_paths": paths}, evidence
                    )
                )

    def test_missing_or_other_author_identity_is_ineligible(self) -> None:
        evidence = guardrails.GuardrailEvidence(**self.evidence_fields)
        for author in (
            None,
            "dependabot[bot]",
            {},
            {"login": None},
            {"login": "renovate[bot]"},
        ):
            with self.subTest(author=author):
                self.assertFalse(
                    guardrails.dependabot_routine_eligible(
                        {**self.item, "author": author}, evidence
                    )
                )

    def test_routine_dependency_exemption_cannot_clear_security_diff_signals(
        self,
    ) -> None:
        for paths in ([".github/workflows/ci.yml"], ["uv.lock"]):
            with self.subTest(paths=paths):
                item = {**self.item, "changed_paths": paths}
                diff = "+++ b/" + paths[0] + "\n+eval(untrusted_input)\n"
                evidence = guardrails.GuardrailEvidence(
                    **(self.evidence_fields | {"diff_text": diff})
                )
                patch = guardrails.evaluate_item(item, evidence=evidence)
                self.assertIsNotNone(patch)
                self.assertEqual("REVIEW_SECURITY", patch["guardrail_outcome"])
                self.assertEqual(["shell_execution"], patch["sensitive_paths"])

    def test_valid_dependabot_evidence_cannot_override_review_or_ownership(
        self,
    ) -> None:
        evidence = guardrails.GuardrailEvidence(**self.evidence_fields)
        for overrides in (
            {"author_type": "HUMAN"},
            {"author_type": "UNKNOWN"},
            {"risk_class": "HUMAN_REVIEW"},
            {"lifecycle_state": "TERMINAL"},
            *({"current_owner": owner} for owner in ("human", "stage2", "stage3")),
            *(
                {"guardrail_source": source}
                for source in ("manual", "review", "human", "octopus")
            ),
        ):
            with self.subTest(overrides=overrides):
                item = self.item | overrides
                before = copy.deepcopy(item)
                self.assertIsNone(guardrails.evaluate_item(item, evidence=evidence))
                self.assertEqual(before, item)


class DependabotAndDiffTests(unittest.TestCase):
    _SHA = "0123456789abcdef0123456789abcdef01234567"

    def _dependabot(self, paths: list[str], **evidence: object) -> dict[str, object]:
        item = _item(
            changed_paths=paths,
            guardrail_outcome="REVIEW_SECURITY",
            author={"login": "dependabot[bot]", "identity_source": "github_api"},
        )
        payload = {
            "diff_text": (
                "diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml\n"
                "+++ b/.github/workflows/ci.yml\n"
                "@@\n"
                f"-        uses: actions/checkout@{self._SHA}\n"
                f"+        uses: actions/checkout@{self._SHA}\n"
            ),
            "required_checks_green": True,
            "mergeable": True,
            "title": "Bump actions/checkout from 4.1.1 to 4.1.2",
        }
        payload.update(evidence)
        diff_text = payload["diff_text"]
        if isinstance(diff_text, str) and diff_text:
            payload["head_sha"] = item["head_sha"]
            payload["diff_sha256"] = guardrails.diff_sha256(diff_text)
        patch = guardrails.evaluate_item(
            item, evidence=guardrails.GuardrailEvidence(**payload)
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        return patch

    def test_dependabot_patch_workflow_is_routine(self) -> None:
        patch = self._dependabot([".github/workflows/ci.yml"])
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])
        self.assertEqual([], patch["sensitive_paths"])

    def test_dependabot_lockfile_minor_is_routine(self) -> None:
        patch = self._dependabot(
            ["uv.lock"],
            title="Bump example from 1.2.3 to 1.3.0",
            diff_text="diff --git a/uv.lock b/uv.lock\n+++ b/uv.lock\n@@\n+version = 1\n",
        )
        self.assertEqual("PASS_ROUTINE", patch["guardrail_outcome"])

    def test_dependabot_major_permissions_unpinned_and_red_ci_stay_held(self) -> None:
        cases = (
            {"title": "Bump actions/checkout from 4.1.1 to 5.0.0"},
            {
                "diff_text": (
                    "diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml\n"
                    "+++ b/.github/workflows/ci.yml\n"
                    "@@\n"
                    " permissions:\n"
                    "-  contents: read\n"
                    "+  contents: write\n"
                    f"+        uses: actions/checkout@{self._SHA}\n"
                )
            },
            {
                "diff_text": (
                    "diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml\n"
                    "+++ b/.github/workflows/ci.yml\n"
                    "@@\n"
                    "+        uses: actions/checkout@v4\n"
                )
            },
            {"required_checks_green": False},
            {"mergeable": False},
            {"required_checks_green": None},
        )
        for overrides in cases:
            with self.subTest(overrides=sorted(overrides)):
                patch = self._dependabot([".github/workflows/ci.yml"], **overrides)
                self.assertEqual("REVIEW_SECURITY", patch["guardrail_outcome"])

    def test_non_dependabot_workflow_stays_held(self) -> None:
        patch = guardrails.evaluate_item(
            _item(
                changed_paths=[".github/workflows/ci.yml"],
                author={"login": "renovate[bot]"},
            )
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("REVIEW_SECURITY", patch["guardrail_outcome"])

    def test_mixed_workflow_and_source_is_not_the_dependabot_lane(self) -> None:
        patch = self._dependabot([".github/workflows/ci.yml", "src/main.py"])
        self.assertEqual("REVIEW_SECURITY", patch["guardrail_outcome"])
        self.assertIn("workflows_and_permissions", patch["sensitive_paths"])

    def test_advisory_failure_does_not_block_required_green(self) -> None:
        checks = [
            {
                "name": "Codacy Static Code Analysis",
                "conclusion": "FAILURE",
                "status": "COMPLETED",
            },
            {"name": "jules/review", "conclusion": "FAILURE", "status": "COMPLETED"},
            {"name": "test", "conclusion": "SUCCESS", "status": "COMPLETED"},
        ]
        patterns = ["Codacy Static Code Analysis", "jules/review", "CodeScene*"]
        self.assertTrue(guardrails.required_checks_green(checks, patterns))
        self.assertFalse(
            guardrails.required_checks_green(
                [
                    {"name": "test", "conclusion": "FAILURE", "status": "COMPLETED"},
                    {"name": "review", "conclusion": "SUCCESS", "status": "COMPLETED"},
                ],
                ["review"],
            )
        )
        self.assertIsNone(guardrails.required_checks_green([], patterns))
        self.assertFalse(
            guardrails.required_checks_green(
                [{"name": "build", "status": "IN_PROGRESS", "conclusion": ""}],
                patterns,
            )
        )

    def test_diff_security_behavior_holds_and_journal_mentions_do_not(self) -> None:
        code = (
            "diff --git a/src/main.py b/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@\n"
            "+html.escape(raw_user_input)\n"
        )
        self.assertIn("security_configuration", guardrails.diff_security_signals(code))
        journal = (
            "diff --git a/.jules/sentinel.md b/.jules/sentinel.md\n"
            "+++ b/.jules/sentinel.md\n"
            "@@\n"
            "+subprocess.run(cmd, shell=True)\n"
        )
        self.assertEqual(set(), guardrails.diff_security_signals(journal))
        test_fixture = (
            "diff --git a/Tests/RepoPromptTests/Security/MCPTerminalRecordSanitizationTests.swift "
            "b/Tests/RepoPromptTests/Security/MCPTerminalRecordSanitizationTests.swift\n"
            "+++ b/Tests/RepoPromptTests/Security/MCPTerminalRecordSanitizationTests.swift\n"
            "@@\n"
            '+let sessionToken = "session-secret-token-12345"\n'
        )
        self.assertEqual(set(), guardrails.diff_security_signals(test_fixture))
        comment = (
            "diff --git a/src/main.py b/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@\n"
            "+# do not call eval( on user input\n"
        )
        self.assertEqual(set(), guardrails.diff_security_signals(comment))

    def test_failed_diff_fetch_keeps_an_existing_security_hold(self) -> None:
        patch = guardrails.evaluate_item(
            _item(
                classification="SECURITY",
                guardrail_outcome="REVIEW_SECURITY",
                changed_paths=["src/main.py"],
            ),
            evidence=guardrails.GuardrailEvidence(diff_fetch_failed=True),
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("REVIEW_SECURITY", patch["guardrail_outcome"])

    def test_stamped_sentinel_hold_is_not_re_evaluated(self) -> None:
        item = _item(
            guardrail_outcome="REVIEW_SECURITY",
            changed_paths=["src/main.py"],
            classification="REFACTOR",
            next_action=f"{guardrails.SENTINEL_HOLD_MARKER}: stays held",
        )
        self.assertIsNone(
            guardrails.evaluate_item(
                item,
                evidence=guardrails.GuardrailEvidence(
                    diff_text="+++ b/src/main.py\n+return 1\n",
                    title="🛡️ Sentinel: [security improvement]",
                    head_ref="sentinel/fix-loaders",
                ),
            )
        )

    def test_shell_path_stays_held_even_with_a_clean_diff(self) -> None:
        patch = guardrails.evaluate_item(
            _item(
                classification="UNKNOWN",
                changed_paths=["scripts/fix.sh"],
            ),
            evidence=guardrails.GuardrailEvidence(diff_text=""),
        )
        self.assertIsNotNone(patch)
        assert patch is not None
        self.assertEqual("REVIEW_SECURITY", patch["guardrail_outcome"])
        self.assertEqual(["shell_execution"], patch["sensitive_paths"])

    def test_clearance_rule_names(self) -> None:
        journal = _item(
            guardrail_outcome="REVIEW_SECURITY",
            changed_paths=[".jules/sentinel.md", "src/clean.py"],
            classification="SECURITY",
        )
        diff_text = "+++ b/src/clean.py\n+print('clean')\n"
        patch = guardrails.evaluate_item(
            journal,
            evidence=guardrails.GuardrailEvidence(
                diff_text=diff_text,
                head_sha=journal["head_sha"],
                diff_sha256=guardrails.diff_sha256(diff_text),
            ),
        )
        self.assertEqual("jules_journal", guardrails.clearance_rule(journal, patch))
        labeled = _item(
            guardrail_outcome="REVIEW_SECURITY",
            classification="CI_INFRA",
            changed_paths=["README.md"],
        )
        patch = guardrails.evaluate_item(labeled)
        self.assertEqual(
            "classification_without_sensitive_path",
            guardrails.clearance_rule(labeled, patch),
        )


if __name__ == "__main__":
    unittest.main()
