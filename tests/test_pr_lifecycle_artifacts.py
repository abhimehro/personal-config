import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_config as config_validator  # noqa: E402
import pr_lifecycle_validation as validator  # noqa: E402
from pr_lifecycle_ledger import validate_transition_table  # noqa: E402
from sync_cursor_export_prompts import (  # noqa: E402
    PromptIncludeError,
    expand_prompt_source,
)


class TestPrLifecycleArtifacts(unittest.TestCase):
    def example(self):
        return validator.load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")

    def write_ledger(self, ledger):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "runtime-ledger.yaml"
        path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
        return path

    def approved_example(self):
        ledger = copy.deepcopy(self.example())
        calibration = ledger["calibration"]
        calibration["status"] = "APPROVED"
        calibration["successful_run_count"] = 7
        calibration["policy_revision"] = "pr-lifecycle-v1.4"
        calibration["invalidated_by_revision"] = None
        calibration["approved_by"] = "abhimehro"
        calibration["approved_at_utc"] = "2026-08-19T09:00:00Z"
        calibration["approval_evidence_urls"] = [
            "https://github.com/abhimehro/personal-config/pull/2026"
        ]
        for ordinal in range(1, 8):
            ledger["events"].append(
                {
                    "event_id": f"evt-calibration-v13-00{ordinal}",
                    "kind": "CALIBRATION",
                    "item_key": None,
                    "from_owner": "stage3",
                    "to_owner": "stage3",
                    "from_state": None,
                    "to_state": None,
                    "next_owner": "stage3",
                    "terminal_disposition": None,
                    "parent_event_id": None,
                    "expected_item_revision": 0,
                    "resulting_item_revision": 0,
                    "idempotency_key": f"__calibration__:evt-calibration-v13-00{ordinal}",
                    "status": "ACKNOWLEDGED",
                    "created_at_utc": f"2026-08-{12 + ordinal}T08:00:00Z",
                    "acknowledged_at_utc": f"2026-08-{12 + ordinal}T08:00:01Z",
                    "policy_revision": "pr-lifecycle-v1.4",
                    "successful": True,
                    "reason": "Complete report-only reconciliation.",
                }
            )
        return ledger

    def assert_invalid(self, ledger, message):
        with self.assertRaisesRegex(ValueError, message):
            validator.validate(self.write_ledger(ledger))

    def test_nonempty_example_and_source_exports_validate(self):
        validator.validate(
            ROOT / "tasks/pr-lifecycle-ledger.example.yaml",
            include_exports=True,
        )

    def test_validate_does_not_run_export_prompt_gate(self):
        with mock.patch.object(
            validator,
            "validate_exports_and_prompts",
            side_effect=AssertionError("export gate must not run during CAS"),
        ):
            validator.validate(self.write_ledger(self.example()))

    def test_validate_include_exports_invokes_prompt_gate(self):
        # fmt: off
        # Keep the `as gate` line wrapped under 79 chars: the export-authority
        # merge gate patches this exact line, so black must not rejoin it.
        with mock.patch.object(
            validator, "validate_exports_and_prompts"
        ) as gate:
            validator.validate(
                self.write_ledger(self.example()), include_exports=True
            )
            gate.assert_called_once()
        # fmt: on

    def test_export_validation_reports_prompt_include_errors(self):
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        with mock.patch.object(
            config_validator,
            "expand_prompt_includes",
            side_effect=PromptIncludeError("include missing: _shared.md"),
        ):
            with self.assertRaisesRegex(
                ValueError,
                r"daily-pr-review\.json: include missing: _shared\.md",
            ):
                config_validator.validate_exports_and_prompts(config)

    def test_main_pointer_cannot_be_used_as_runtime_ledger(self):
        with self.assertRaisesRegex(ValueError, "schema root"):
            validator.validate(ROOT / "tasks/pr-lifecycle-ledger.yaml")

    def test_active_pointer_selects_an_allowed_write_primitive(self):
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        pointer = validator.load_yaml(ROOT / "tasks/pr-lifecycle-ledger.yaml")
        validator.validate_bootstrap_pointer(pointer, config)

        pointer["runtime_ledger"]["selected_write_primitive"] = "unsupported"
        with self.assertRaisesRegex(ValueError, "unsupported primitive"):
            validator.validate_bootstrap_pointer(pointer, config)

    def test_validator_cli_requires_a_fetched_runtime_ledger_path(self):
        result = subprocess.run(
            [sys.executable, "scripts/validate_pr_lifecycle_artifacts.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_ledger", result.stderr)

    def test_duplicate_yaml_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "duplicate.yaml"
            path.write_text(
                "schema_version: '1.1'\nschema_version: '1.1'\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "duplicate YAML key"):
                validator.load_yaml(path)

    def test_terminal_item_requires_terminal_disposition_and_no_owner(self):
        ledger = self.example()
        ledger["items"][1]["current_owner"] = "stage1"
        self.assert_invalid(ledger, "lifecycle state and owner disagree")

    def test_nonterminal_item_requires_next_owner(self):
        ledger = self.example()
        ledger["items"][0]["next_owner"] = "none"
        self.assert_invalid(ledger, "nonterminal record requires next owner")

    def test_all_url_fields_reject_non_https_values(self):
        evidence = self.example()
        evidence["items"][0]["evidence_urls"] = ["http://example.test/evidence"]
        self.assert_invalid(evidence, "schema items.0.evidence_urls.0")

        provenance = self.example()
        provenance["stage2_work_items"][0]["provenance_urls"] = [
            "http://example.test/source"
        ]
        self.assert_invalid(provenance, "schema stage2_work_items.0.provenance_urls.0")

        approval = self.approved_example()
        approval["calibration"]["approval_evidence_urls"] = [
            "http://example.test/approval"
        ]
        self.assert_invalid(approval, "schema calibration.approval_evidence_urls.0")

    def test_calibration_approval_requires_seven_events(self):
        ledger = self.approved_example()
        ledger["calibration"]["successful_run_count"] = 6
        ledger["events"].pop()
        self.assert_invalid(ledger, "schema calibration.successful_run_count")

    def test_calibration_approval_passes_with_seven_current_events(self):
        validator.validate(self.write_ledger(self.approved_example()))

    def test_stale_policy_cannot_retain_approved_calibration(self):
        ledger = self.approved_example()
        ledger["calibration"]["policy_revision"] = "pr-lifecycle-v1.1"
        self.assert_invalid(ledger, "stale policy")

    def test_event_projection_must_match_item_revision(self):
        ledger = self.example()
        ledger["items"][0]["revision"] = 2
        self.assert_invalid(ledger, "projection revision disagrees")

    def test_stage2_can_return_routine_results_to_stage1(self):
        for state in ("STAGE2_QUEUED", "STAGE2_ACTIVE"):
            validate_transition_table(
                {
                    "event_id": f"evt-test-{state.lower()}-stage1",
                    "from_state": state,
                    "to_state": "STAGE1_INTAKE",
                }
            )

    def test_acknowledgement_and_cancellation_do_not_increment_revision(self):
        validator.validate(self.write_ledger(self.example()))
        ledger = self.example()
        receipt = ledger["events"][1]
        receipt["kind"] = "CANCELLATION"
        receipt["status"] = "CANCELLED"
        validator.validate(self.write_ledger(ledger))

    def test_receipts_require_a_parent_transition(self):
        for kind, status in (
            ("ACKNOWLEDGEMENT", "ACKNOWLEDGED"),
            ("CANCELLATION", "CANCELLED"),
        ):
            ledger = self.example()
            ledger["events"][1]["kind"] = kind
            ledger["events"][1]["status"] = status
            ledger["events"][1]["parent_event_id"] = None
            self.assert_invalid(ledger, "parent_event_id")

    def test_in_place_handoff_status_mutation_is_not_a_receipt(self):
        ledger = self.example()
        ledger["events"][0]["status"] = "ACKNOWLEDGED"
        self.assert_invalid(ledger, "schema events.0.status")

    def test_terminal_item_requires_terminal_event(self):
        ledger = self.example()
        ledger["events"].pop(2)
        ledger["items"][1]["handoffs"] = []
        ledger["items"][1]["revision"] = 0
        self.assert_invalid(ledger, "terminal record requires terminal event")

    def test_stage2_command_requires_explicit_runtime_ledger_path(self):
        command = self.example()["stage2_work_items"][0]["required_test_command"]
        self.assertEqual(
            command,
            'python3 scripts/validate_pr_lifecycle_artifacts.py "$RUNTIME_LEDGER_PATH"',
        )

    def test_verified_zero_requires_authoritative_evidence(self):
        ledger = self.example()
        ledger["repository_merge_methods"][0]["required_checks_verified_zero"] = False
        self.assert_invalid(ledger, "empty checks require verified-zero proof")

    def test_legacy_config_keys_and_contract_drift_fail_closed(self):
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        config["merge_strategy"] = "squash"
        with self.assertRaisesRegex(ValueError, "legacy lifecycle keys"):
            validator.validate_config(config)

        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        config["lifecycle"]["stages"]["stage1_review"]["schedule"] = "0 14 * * *"
        with self.assertRaisesRegex(ValueError, "approved contract"):
            validator.validate_config(config)

        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        del config["repos"]
        with self.assertRaisesRegex(ValueError, "config.repos"):
            validator.validate_config(config)

    def test_active_config_requires_fetched_runtime_ledger_argument(self):
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        self.assertEqual(
            config["lifecycle"]["validation_command"],
            'python3 scripts/validate_pr_lifecycle_artifacts.py "$RUNTIME_LEDGER_PATH"',
        )
        self.assertNotEqual(
            config["lifecycle"]["validation_command"],
            "python3 scripts/validate_pr_lifecycle_artifacts.py",
        )
        config["lifecycle"][
            "validation_command"
        ] = "python3 scripts/validate_pr_lifecycle_artifacts.py"
        with self.assertRaisesRegex(
            ValueError, "must require fetched runtime ledger path"
        ):
            validator.validate_config(config)

    def test_rebalance_config_keys_are_allowed_but_unknown_keys_fail_closed(self):
        """Accept supported rebalance settings and reject unknown lifecycle keys."""
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        lifecycle = config["lifecycle"]
        self.assertEqual(lifecycle["packet_expiry_close_days"], 7)
        self.assertEqual(lifecycle["stage2_intake"], "self_fed")
        self.assertFalse(lifecycle["lineage"]["open_as_draft"])
        validator.validate_config(config)

        lifecycle["unexpected_rebalance_option"] = True
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            validator.validate_config(config)

    def test_stage_prompts_require_each_runtime_continuity_marker(self):
        """Reject each stage prompt when any runtime continuity marker is missing."""
        markers = (
            "docs/automated-pr-lifecycle.md",
            "docs/pr-lifecycle-runtime-ledger.md",
            "Memory is enabled",
            "Dashboard-referenced MCP set",
            "ledger, run records, and lessons",
        )
        prompts = ROOT / "docs/cursor-automations/prompts"
        for name in (
            "daily-pr-review.md",
            "daily-pr-salvage.md",
            "daily-pr-completion.md",
            "daily-pr-completion.calibration.md",
        ):
            text = " ".join((prompts / name).read_text(encoding="utf-8").split())
            config_validator.validate_prompt(text, name)
            for marker in markers:
                with self.subTest(name=name, missing=marker):
                    self.assertIn(marker, text)
                    with self.assertRaisesRegex(ValueError, "runtime continuity marker"):
                        config_validator.validate_prompt(text.replace(marker, ""), name)
            with self.subTest(name=name, bootstrap_only=True):
                with self.assertRaisesRegex(ValueError, "runtime continuity marker"):
                    config_validator.validate_prompt(
                        "docs/automated-pr-lifecycle.md "
                        "scripts/pr_lifecycle_run.py --stage 1",
                        name,
                    )

    def test_calibration_prompt_keeps_legacy_continuity_markers(self):
        """Require the full continuity contract for calibration prompts."""
        calibration = " ".join(
            (
                "docs/automated-pr-lifecycle.md",
                "docs/pr-lifecycle-runtime-ledger.md",
                "Memory is enabled",
                "Dashboard-referenced MCP set",
                "ledger, run records, and lessons",
            )
        )
        config_validator.validate_prompt(
            calibration, "daily-pr-completion.calibration.md"
        )
        with self.assertRaisesRegex(ValueError, "runtime continuity marker"):
            config_validator.validate_prompt(
                "docs/automated-pr-lifecycle.md scripts/pr_lifecycle_run.py --stage 3",
                "daily-pr-completion.calibration.md",
            )

    def test_enabled_memory_is_required_for_all_cursor_exports(self):
        """Verify every Cursor automation export enables memory."""
        exports = ROOT / "docs/cursor-automations/exports"
        for path in sorted(exports.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(data["memoryEnabled"], path.name)

    def test_stage_prompts_bind_runtime_ledger_and_stage(self):
        """Require stage identity, runtime ledger authority, and revision checks."""
        prompts = ROOT / "docs/cursor-automations/prompts"
        for name, stage in (
            ("daily-pr-review.md", "Stage 1"),
            ("daily-pr-salvage.md", "Stage 2"),
            ("daily-pr-completion.md", "Stage 3"),
        ):
            with self.subTest(name):
                text = " ".join((prompts / name).read_text(encoding="utf-8").split())
                self.assertIn("You are **" + stage, text)
                self.assertIn(
                    "automation/pr-lifecycle-ledger:pr-lifecycle-ledger.yaml",
                    text,
                )
                self.assertIn("non-authoritative bootstrap pointer", text)
                self.assertIn("revision-checked events", text)
                self.assertIn("docs/automated-pr-lifecycle.md", text)

    def test_identity_policy_versions_hyphen_and_slash_prefixes(self):
        """Verify agent branch prefixes and aligned identity policy revisions."""
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        prefixes = config["identity_classification"]["branch_prefixes"]
        for agent in ("jules", "bolt", "palette", "sentinel"):
            self.assertIn(f"{agent}/", prefixes)
            self.assertIn(f"{agent}-", prefixes)
        self.assertEqual(
            config["identity_classification"]["revision"],
            config["lifecycle"]["policy_inputs"]["identity_classification_revision"],
        )
        self.assertEqual(config["lifecycle"]["policy_revision"], "pr-lifecycle-v1.4")
        self.assertEqual(
            config["lifecycle"]["policy_inputs"]["prompt_revision"],
            "pr-lifecycle-v1.4",
        )

    def test_stage_prompts_name_role_based_tools(self):
        """Verify each stage names its tools, handoffs, and action limits."""
        review = (
            ROOT / "docs/cursor-automations/prompts/daily-pr-review.md"
        ).read_text(encoding="utf-8")
        self.assertIn("scripts/pr_identity.py", review)
        self.assertIn("complete Stage 2 work item", review)
        self.assertIn("CHANGES_REQUESTED", review)
        salvage = (
            ROOT / "docs/cursor-automations/prompts/daily-pr-salvage.md"
        ).read_text(encoding="utf-8")
        self.assertIn("fix-ci", salvage)
        self.assertIn(
            "Never approve, request review, mark ready, merge, close",
            salvage,
        )
        calibration = (
            ROOT / "docs/cursor-automations/prompts/daily-pr-completion.calibration.md"
        ).read_text(encoding="utf-8")
        self.assertIn("read-only", calibration)
        self.assertIn("pr-lifecycle-docs-", calibration)
        completion = (
            ROOT / "docs/cursor-automations/prompts/daily-pr-completion.md"
        ).read_text(encoding="utf-8")
        self.assertIn("TRUNK_QUEUE", completion)
        self.assertIn(
            "required-check configuration cannot be read, hold rather than act",
            completion,
        )

    def test_authoritative_ruleset_reads_clear_pending_merge_method_holds(self):
        """Verify discovered merge methods clear holds and retain check evidence."""
        ledger = self.example()
        verified = ledger["repository_merge_methods"]
        self.assertTrue(
            all(entry["discovery_status"] == "VERIFIED" for entry in verified)
        )
        self.assertTrue(all(entry["hold_reason"] is None for entry in verified))
        self.assertTrue(
            all(entry["required_checks_verified_zero"] for entry in verified[1:6])
        )
        self.assertFalse(verified[6]["required_checks_verified_zero"])
        self.assertTrue(verified[6]["required_checks"])


class TestStagePromptSafeguards(unittest.TestCase):
    """Expanded stage prompts preserve execution and handoff safeguards."""

    def _prompt(self, name: str) -> str:
        """Return the expanded source of a named lifecycle automation prompt."""
        return expand_prompt_source(ROOT / "docs/cursor-automations/prompts" / name)

    def test_review_prompt_routes_mechanical_repairs(self):
        """Require bounded Stage 2 repair handoffs and replacement PR re-ingestion."""
        review = " ".join(self._prompt("daily-pr-review.md").split())
        self.assertIn("bounded mechanical repair", review)
        self.assertIn("create exactly one complete Stage 2 work item", review)
        self.assertIn("Re-ingest Stage 2 salvage replacement PRs", review)

    def test_review_prompt_guardrails(self):
        """Require validated runtime state and protection for sensitive human work."""
        review = " ".join(self._prompt("daily-pr-review.md").split())
        self.assertIn("take no lifecycle action or calibration step", review)
        self.assertIn("selected CAS path", review)
        self.assertIn(
            "Sticky sensitive-path classification still blocks",
            review,
        )
        self.assertIn(
            "never auto-acts on security-sensitive or ordinary human-authored work",
            review,
        )
        self.assertIn("run record", review)

    def test_salvage_prompt_draft_only_and_structured_outcome(self):
        """Require draft verification, provenance, and structured failure records."""
        salvage = " ".join(self._prompt("daily-pr-salvage.md").split())
        self.assertIn(
            "Never approve, request review, mark ready, merge, close",
            salvage,
        )
        self.assertIn("structured failed-recovery record", salvage)
        self.assertIn("re-read `isDraft`", salvage)
        self.assertIn("provenance to the original before handing off", salvage)

    def test_completion_calibration_requires_progress(self):
        """Require bounded repair progress before counting calibration success."""
        calibration = " ".join(
            self._prompt("daily-pr-completion.calibration.md").split()
        )
        self.assertIn(
            "report-only for approve/merge/close/comment/branch mutations",
            calibration,
        )
        self.assertIn("route a bounded repair", calibration.lower())
        self.assertIn(
            "A docs-only wrap-up is not a successful calibration run",
            calibration,
        )
        self.assertIn("must not increment `successful_run_count`", calibration)

    def test_completion_prompt_rechecks_queue_predicates(self):
        """Require fresh queue evidence and a stop after queue submission failure."""
        completion = " ".join(self._prompt("daily-pr-completion.md").split())
        self.assertIn(
            "Re-read every predicate independently of Stage 2's recovery notes",
            completion,
        )
        self.assertIn("TRUNK_QUEUE", completion)
        self.assertIn(
            "If approval succeeds and queue submission fails, record the failure and stop",
            completion,
        )
        self.assertIn(
            "required-check configuration cannot be read, hold rather than act",
            completion,
        )

    def test_lifecycle_contract_sha_match_exception(self):
        """Preserve documented exceptions to skipping unchanged PR revisions."""
        contract = (ROOT / "docs/automated-pr-lifecycle.md").read_text(encoding="utf-8")
        self.assertIn("SHA_MATCH skip applies only", contract)
        self.assertIn("canonical-pick", contract)
        self.assertIn("product-mutation", contract)
        self.assertIn("salvage only", contract)

    def test_lifecycle_contract_trunk_stale_vs_main(self):
        contract = (ROOT / "docs/automated-pr-lifecycle.md").read_text(encoding="utf-8")
        self.assertIn("Trunk queue: stale vs main", contract)
        self.assertIn("stale-vs-main", contract)
        self.assertIn("update_pull_request_branch", contract)
        self.assertNotIn(
            "cannot prepare a test branch (GitHub App or ruleset)",
            contract,
        )
        salvage_spec = (ROOT / "docs/automated-pr-salvage-agent.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("stale-vs-main", salvage_spec)
        review_spec = (ROOT / "docs/automated-pr-review-agent.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("stale-vs-main", review_spec)
        completion_spec = (ROOT / "docs/automated-pr-completion-agent.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("stale-vs-main", completion_spec)
        copilot = (ROOT / ".github/copilot-instructions.md").read_text(encoding="utf-8")
        self.assertIn("stale-vs-main", copilot)
        cursor_rules = (ROOT / ".cursorrules").read_text(encoding="utf-8")
        self.assertIn("stale-vs-main", cursor_rules)
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("stale-vs-main", contributing)

    def test_policy_revision_stays_v14(self):
        config = validator.load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
        self.assertEqual(config["lifecycle"]["policy_revision"], "pr-lifecycle-v1.4")
        self.assertEqual(
            config["lifecycle"]["policy_inputs"]["prompt_revision"],
            "pr-lifecycle-v1.4",
        )
        self.assertEqual(
            config["lifecycle"]["policy_inputs"]["sensitive_path_taxonomy_revision"],
            "2026-08-19",
        )


if __name__ == "__main__":
    unittest.main()
