"""Unit tests for PR lifecycle schema validation in scripts/pr_lifecycle_schema.py."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_schema as schema_mod  # noqa: E402
import pr_lifecycle_validation as validator  # noqa: E402


class TestPrLifecycleSchema(unittest.TestCase):
    """Test suite validating normative PR lifecycle JSON schema enforcement."""

    def load_example_ledger(self) -> dict:
        """Load the reference example ledger."""
        # ASSUMES: tasks/pr-lifecycle-ledger.example.yaml exists and is valid against the schema
        return validator.load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")

    def test_valid_ledger_passes_validation(self) -> None:
        """Ensure a fully conforming ledger dictionary passes without error."""
        ledger = self.load_example_ledger()
        # Should execute cleanly without raising any exception
        schema_mod.validate_schema(ledger)

    def test_missing_schema_file_raises_value_error(self) -> None:
        """Ensure an OSError when reading schema file raises ValueError fail-closed."""
        # SECURITY: If the schema file is unreadable or missing, fail closed immediately
        ledger = self.load_example_ledger()
        with mock.patch("pathlib.Path.read_text", side_effect=OSError("File not accessible")):
            with self.assertRaisesRegex(ValueError, "invalid JSON Schema: File not accessible"):
                schema_mod.validate_schema(ledger)

    def test_malformed_json_schema_raises_value_error(self) -> None:
        """Ensure invalid JSON syntax in schema file raises ValueError."""
        # SECURITY: Corrupted schema file must not fail open
        ledger = self.load_example_ledger()
        with mock.patch("pathlib.Path.read_text", return_value="[not valid json"):
            with self.assertRaisesRegex(ValueError, "invalid JSON Schema:"):
                schema_mod.validate_schema(ledger)

    def test_missing_root_required_property_fails(self) -> None:
        """Ensure missing required root properties report root-level schema error."""
        ledger = self.load_example_ledger()
        del ledger["schema_version"]
        with self.assertRaises(ValueError) as ctx:
            schema_mod.validate_schema(ledger)
        self.assertIn("schema root:", str(ctx.exception))
        self.assertIn("'schema_version' is a required property", str(ctx.exception))

    def test_additional_root_property_fails(self) -> None:
        """Ensure schema disallows additional properties at root."""
        ledger = self.load_example_ledger()
        ledger["unexpected_root_attr"] = "forbidden"
        with self.assertRaises(ValueError) as ctx:
            schema_mod.validate_schema(ledger)
        self.assertIn("schema root:", str(ctx.exception))
        self.assertIn("unexpected_root_attr", str(ctx.exception))

    def test_invalid_schema_version_const_fails(self) -> None:
        """Ensure schema version must match the expected constant '1.2'."""
        ledger = self.load_example_ledger()
        ledger["schema_version"] = "99.9"
        with self.assertRaises(ValueError) as ctx:
            schema_mod.validate_schema(ledger)
        self.assertIn("schema schema_version:", str(ctx.exception))
        self.assertIn("'1.2' was expected", str(ctx.exception))

    def test_nested_item_property_validation_failure(self) -> None:
        """Ensure invalid property on a nested item formats path accurately."""
        ledger = self.load_example_ledger()
        # Corrupt the head SHA of the first item to an invalid non-SHA string
        ledger["items"][0]["head_sha"] = "invalid-not-40-hex-chars"
        with self.assertRaises(ValueError) as ctx:
            schema_mod.validate_schema(ledger)
        self.assertIn("schema items.0.head_sha:", str(ctx.exception))
        self.assertIn("does not match", str(ctx.exception))

    def test_nested_item_missing_required_property_fails(self) -> None:
        """Ensure missing required property within an item is pinpointed."""
        ledger = self.load_example_ledger()
        del ledger["items"][0]["guardrail_outcome"]
        with self.assertRaises(ValueError) as ctx:
            schema_mod.validate_schema(ledger)
        self.assertIn("schema items.0:", str(ctx.exception))
        self.assertIn("'guardrail_outcome' is a required property", str(ctx.exception))

    def test_nested_event_property_validation_failure(self) -> None:
        """Ensure schema validates event definitions and reports event path."""
        ledger = self.load_example_ledger()
        ledger["events"][0]["status"] = "INVALID_STATUS"
        with self.assertRaises(ValueError) as ctx:
            schema_mod.validate_schema(ledger)
        self.assertIn("schema events.0.status:", str(ctx.exception))
        self.assertIn("'INVALID_STATUS' is not one of", str(ctx.exception))

    def test_calibration_approved_insufficient_runs_fails(self) -> None:
        """Ensure calibration state APPROVED requires at least 7 successful runs."""
        # SECURITY: Prevents premature or fraudulent promotion to APPROVED
        ledger = copy.deepcopy(self.load_example_ledger())
        calibration = ledger["calibration"]
        calibration["status"] = "APPROVED"
        calibration["successful_run_count"] = 3
        calibration["approved_by"] = "abhimehro"
        calibration["approved_at_utc"] = "2026-08-19T12:00:00Z"
        calibration["approval_evidence_urls"] = ["https://github.com/abhimehro/personal-config/pull/2026"]
        with self.assertRaises(ValueError) as ctx:
            schema_mod.validate_schema(ledger)
        self.assertIn("schema calibration.successful_run_count:", str(ctx.exception))
        self.assertIn("less than the minimum of 7", str(ctx.exception))

    def test_stage2_work_item_invalid_expiry_fails(self) -> None:
        """Ensure stage2 work items enforce ISO/RFC3339 timestamp pattern."""
        ledger = self.load_example_ledger()
        ledger["stage2_work_items"][0]["expiry_utc"] = "invalid-date"
        with self.assertRaises(ValueError) as ctx:
            schema_mod.validate_schema(ledger)
        self.assertIn("schema stage2_work_items.0.expiry_utc:", str(ctx.exception))

    def test_repository_merge_methods_invalid_enum_fails(self) -> None:
        """Ensure repository merge methods enforce valid merge method enum."""
        ledger = self.load_example_ledger()
        ledger["repository_merge_methods"][0]["method"] = "FAST_FORWARD"
        with self.assertRaises(ValueError) as ctx:
            schema_mod.validate_schema(ledger)
        self.assertIn("schema repository_merge_methods.0.method:", str(ctx.exception))
        self.assertIn("'FAST_FORWARD' is not one of", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
