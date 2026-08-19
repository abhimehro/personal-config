import copy
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_validation as validator


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
        calibration["approved_by"] = "abhimehro"
        calibration["approved_at_utc"] = "2026-08-19T09:00:00Z"
        calibration["approval_evidence_urls"] = [
            "https://github.com/abhimehro/personal-config/pull/2026"
        ]
        for ordinal in range(4, 8):
            ledger["events"].append(
                {
                    "event_id": f"evt-calibration-v12-00{ordinal}",
                    "kind": "CALIBRATION",
                    "item_key": None,
                    "from_owner": "stage3",
                    "to_owner": "stage3",
                    "expected_item_revision": 0,
                    "resulting_item_revision": 0,
                    "idempotency_key": f"__calibration__:evt-calibration-v12-00{ordinal}",
                    "status": "ACKNOWLEDGED",
                    "created_at_utc": f"2026-08-{12 + ordinal}T08:00:00Z",
                    "acknowledged_at_utc": f"2026-08-{12 + ordinal}T08:00:01Z",
                    "policy_revision": "pr-lifecycle-v1.2",
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

    def test_duplicate_yaml_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "duplicate.yaml"
            path.write_text("schema_version: '1.1'\nschema_version: '1.1'\n", encoding="utf-8")
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
        provenance["stage2_work_items"][0]["provenance_urls"] = ["http://example.test/source"]
        self.assert_invalid(provenance, "schema stage2_work_items.0.provenance_urls.0")

        approval = self.approved_example()
        approval["calibration"]["approval_evidence_urls"] = ["http://example.test/approval"]
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
        self.assert_invalid(ledger, "projection revision lacks latest event")

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


if __name__ == "__main__":
    unittest.main()
