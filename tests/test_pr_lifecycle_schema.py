"""Tests for the normative PR lifecycle JSON Schema validator."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_schema as schema_mod
from pr_lifecycle_schema import validate_schema

EXAMPLE_LEDGER_PATH = ROOT / "tasks/pr-lifecycle-ledger.example.yaml"


class TestPrLifecycleSchema(unittest.TestCase):
    """Unit tests covering validate_schema functionality, errors, and edge cases."""

    def setUp(self) -> None:
        self.example_ledger = yaml.safe_load(
            EXAMPLE_LEDGER_PATH.read_text(encoding="utf-8")
        )

    def test_valid_example_ledger_passes(self) -> None:
        """Confirm that a valid example ledger passes validation with no exceptions."""
        validate_schema(self.example_ledger)

    def test_schema_file_read_oserror_raises_value_error(self) -> None:
        """Verify that OSError when reading schema file raises ValueError."""
        with mock.patch("pathlib.Path.read_text", side_effect=OSError("Read failure")):
            with self.assertRaisesRegex(ValueError, "invalid JSON Schema: Read failure"):
                validate_schema(self.example_ledger)

    def test_schema_file_invalid_json_raises_value_error(self) -> None:
        """Verify that JSONDecodeError in schema content raises ValueError."""
        with mock.patch("pathlib.Path.read_text", return_value="invalid { json"):
            with self.assertRaisesRegex(ValueError, "invalid JSON Schema:"):
                validate_schema(self.example_ledger)

    def test_root_missing_required_property_reports_root_location(self) -> None:
        """Verify that missing top-level required fields report root location."""
        ledger = copy.deepcopy(self.example_ledger)
        del ledger["schema_version"]
        with self.assertRaisesRegex(ValueError, r"^schema root: 'schema_version' is a required property"):
            validate_schema(ledger)

    def test_root_additional_properties_rejected(self) -> None:
        """Verify that top-level additional properties are rejected at root location."""
        ledger = copy.deepcopy(self.example_ledger)
        ledger["unrecognized_field"] = "unexpected"
        with self.assertRaisesRegex(ValueError, r"^schema root: Additional properties are not allowed"):
            validate_schema(ledger)

    def test_nested_item_error_reports_dotted_path(self) -> None:
        """Verify that errors inside items array report items.<index>.<field>."""
        ledger = copy.deepcopy(self.example_ledger)
        ledger["items"][0]["pr"] = 0  # minimum is 1 in schema
        with self.assertRaisesRegex(ValueError, r"^schema items\.0\.pr: 0 is less than the minimum of 1"):
            validate_schema(ledger)

    def test_nested_item_invalid_url_reports_dotted_path(self) -> None:
        """Verify that pattern mismatches report the nested field location."""
        ledger = copy.deepcopy(self.example_ledger)
        ledger["items"][0]["url"] = "ftp://invalid-url"
        with self.assertRaisesRegex(ValueError, r"^schema items\.0\.url:"):
            validate_schema(ledger)

    def test_nested_calibration_error_reports_dotted_path(self) -> None:
        """Verify that validation errors in calibration block report correct path."""
        ledger = copy.deepcopy(self.example_ledger)
        ledger["calibration"]["required_successful_runs"] = 5  # const is 7
        with self.assertRaisesRegex(
            ValueError, r"^schema calibration\.required_successful_runs: 7 was expected"
        ):
            validate_schema(ledger)

    def test_nested_stage2_work_item_error_reports_dotted_path(self) -> None:
        """Verify that validation errors in stage2_work_items report correct path."""
        ledger = copy.deepcopy(self.example_ledger)
        ledger["stage2_work_items"][0]["attempt_count"] = -1  # minimum is 0
        with self.assertRaisesRegex(
            ValueError,
            r"^schema stage2_work_items\.0\.attempt_count: -1 is less than the minimum of 0",
        ):
            validate_schema(ledger)

    def test_nested_event_error_reports_dotted_path(self) -> None:
        """Verify that validation errors in events report correct path."""
        ledger = copy.deepcopy(self.example_ledger)
        ledger["events"][0]["status"] = "INVALID_STATUS"
        with self.assertRaisesRegex(ValueError, r"^schema events\.0\.status:"):
            validate_schema(ledger)

    def test_nested_deep_field_error_reports_full_path(self) -> None:
        """A deeply nested schema violation reports the complete dotted path."""
        ledger = copy.deepcopy(self.example_ledger)
        ledger["items"][0]["attempts"]["evidence"] = -1
        with self.assertRaisesRegex(
            ValueError,
            r"^schema items\.0\.attempts\.evidence: -1 is less than the minimum of 0",
        ):
            validate_schema(ledger)

    def test_multiple_errors_are_sorted_deterministically(self) -> None:
        """With several violations, the same first error is reported every time."""
        ledger = copy.deepcopy(self.example_ledger)
        ledger["items"][0]["url"] = "not-a-url"
        ledger["items"][0]["head_sha"] = "short-sha"
        messages = []
        for _ in range(3):
            with self.assertRaises(ValueError) as ctx:
                validate_schema(copy.deepcopy(ledger))
            messages.append(str(ctx.exception))
        self.assertEqual(len(set(messages)), 1)
        self.assertRegex(messages[0], r"^schema items\.0\.(url|head_sha):")

    def test_empty_ledger_reports_root_error(self) -> None:
        """Verify that completely empty ledger dict fails at root."""
        with self.assertRaisesRegex(ValueError, r"^schema root:"):
            validate_schema({})


if __name__ == "__main__":
    unittest.main()
