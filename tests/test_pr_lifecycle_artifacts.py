import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_validation as validator  # noqa: E402


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
        validator.validate(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")

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

    def test_enabled_memory_is_required_for_all_cursor_exports(self):
        exports = ROOT / "docs/cursor-automations/exports"
        for path in sorted(exports.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(data["memoryEnabled"], path.name)

    def test_export_prompts_preserve_dashboard_mcp_reference(self):
        prompts = ROOT / "docs/cursor-automations/prompts"
        for path in sorted(prompts.glob("daily-pr-*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertIn("Dashboard-referenced MCP set", text)
            self.assertIn("`gh`", text)

    def test_identity_policy_versions_hyphen_and_slash_prefixes(self):
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
        review = (
            ROOT / "docs/cursor-automations/prompts/daily-pr-review.md"
        ).read_text(encoding="utf-8")
        self.assertIn("jules-", review)
        self.assertIn("feat/", review)
        self.assertIn("pr-lifecycle-docs-", review)
        salvage = (
            ROOT / "docs/cursor-automations/prompts/daily-pr-salvage.md"
        ).read_text(encoding="utf-8")
        self.assertIn("fix-merge-conflicts", salvage)
        self.assertIn("pr-lifecycle-docs-", salvage)
        calibration = (
            ROOT / "docs/cursor-automations/prompts/daily-pr-completion.calibration.md"
        ).read_text(encoding="utf-8")
        self.assertIn("read-only", calibration)
        self.assertIn("pr-lifecycle-docs-", calibration)
        completion = (
            ROOT / "docs/cursor-automations/prompts/daily-pr-completion.md"
        ).read_text(encoding="utf-8")
        self.assertIn("pr-lifecycle-docs-", completion)

    def test_authoritative_ruleset_reads_clear_pending_merge_method_holds(self):
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


class TestStage1ThroughputGate(unittest.TestCase):
    def _prompt(self, name: str) -> str:
        return (ROOT / "docs/cursor-automations/prompts" / name).read_text(
            encoding="utf-8"
        )

    def test_review_prompt_sha_match_reselect(self):
        review = self._prompt("daily-pr-review.md")
        self.assertIn("SHA_MATCH skip only", review)
        self.assertIn("Stage-1-executable", review)
        self.assertIn("canonical-pick", review)

    def test_review_prompt_hold_platform_is_salvage_only(self):
        review = self._prompt("daily-pr-review.md")
        self.assertIn("HOLD_PLATFORM is salvage-only", review)
        self.assertIn("generated_output", review)

    def test_review_prompt_throughput_fail_when_unused_slots(self):
        review = self._prompt("daily-pr-review.md")
        self.assertIn("FAIL", review)
        self.assertIn("product mutations", review)
        self.assertIn("bookkeeping", review)

    def test_salvage_prompt_empty_intake_stop(self):
        salvage = self._prompt("daily-pr-salvage.md")
        self.assertIn("empty intake", salvage)
        self.assertIn("Do not invent recoveries", salvage)

    def test_completion_calibration_bounce_back(self):
        calibration = self._prompt("daily-pr-completion.calibration.md")
        self.assertIn("router", calibration)
        self.assertIn("back to Stage 1", calibration)
        self.assertIn("file-collision", calibration)

    def test_completion_prompt_bounce_back(self):
        completion = self._prompt("daily-pr-completion.md")
        self.assertIn("back to Stage 1", completion)
        self.assertIn("canonical-pick", completion)

    def test_lifecycle_contract_sha_match_exception(self):
        contract = (ROOT / "docs/automated-pr-lifecycle.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("SHA_MATCH skip applies only", contract)
        self.assertIn("canonical-pick", contract)
        self.assertIn("product-mutation", contract)
        self.assertIn("salvage only", contract)

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
