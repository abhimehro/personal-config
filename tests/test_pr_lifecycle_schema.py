"""Tests for PR lifecycle schema validation (scripts/pr_lifecycle_schema.py)."""

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

import pr_lifecycle_schema as schema  # noqa: E402


class TestPrLifecycleSchema(unittest.TestCase):
    """Test suite for validate_schema in scripts/pr_lifecycle_schema.py."""

    def setUp(self) -> None:
        example_path = ROOT / "tasks/pr-lifecycle-ledger.example.yaml"
        self.valid_ledger = yaml.safe_load(example_path.read_text(encoding="utf-8"))

    def test_valid_ledger_passes_validation(self) -> None:
        """A compliant ledger dictionary validates without raising ValueError."""
        # Returns None on successful validation
        self.assertIsNone(schema.validate_schema(self.valid_ledger))

    def test_missing_schema_file_raises_value_error(self) -> None:
        """An OSError when reading the schema file raises ValueError."""
        with mock.patch("pathlib.Path.read_text", side_effect=OSError("File not found")):
            with self.assertRaisesRegex(ValueError, "invalid JSON Schema: File not found"):
                schema.validate_schema(self.valid_ledger)

    def test_invalid_json_schema_file_raises_value_error(self) -> None:
        """A JSONDecodeError when reading the schema file raises ValueError."""
        with mock.patch("pathlib.Path.read_text", return_value="invalid json {"):
            with self.assertRaisesRegex(ValueError, "invalid JSON Schema:"):
                schema.validate_schema(self.valid_ledger)

    def test_root_level_error_reports_root_location(self) -> None:
        """A top-level schema violation sets location to 'root'."""
        ledger = copy.deepcopy(self.valid_ledger)
        # Violate required top-level property
        del ledger["schema_version"]
        with self.assertRaisesRegex(ValueError, r"^schema root: 'schema_version' is a required property"):
            schema.validate_schema(ledger)

    def test_root_level_additional_property_reports_root_location(self) -> None:
        """An unexpected top-level property sets location to 'root'."""
        ledger = copy.deepcopy(self.valid_ledger)
        ledger["unexpected_key"] = "bad"
        with self.assertRaisesRegex(ValueError, r"^schema root: Additional properties are not allowed"):
            schema.validate_schema(ledger)

    def test_nested_item_field_error_reports_dotted_location(self) -> None:
        """A schema violation inside items list reports dotted path like items.0.url."""
        ledger = copy.deepcopy(self.valid_ledger)
        ledger["items"][0]["url"] = "http://insecure.example.com"
        with self.assertRaisesRegex(ValueError, r"^schema items\.0\.url:"):
            schema.validate_schema(ledger)

    def test_nested_deep_field_error_reports_full_path(self) -> None:
        """A deeply nested schema violation reports the complete dotted path."""
        ledger = copy.deepcopy(self.valid_ledger)
        ledger["items"][0]["attempts"]["evidence"] = -1
        with self.assertRaisesRegex(ValueError, r"^schema items\.0\.attempts\.evidence: -1 is less than the minimum of 0"):
            schema.validate_schema(ledger)

    def test_multiple_errors_are_sorted_deterministically(self) -> None:
        """Multiple validation errors are sorted so the first error is chosen deterministically."""
        ledger = copy.deepcopy(self.valid_ledger)
        # Introduce multiple errors across different locations
        ledger["items"][0]["url"] = "not-a-url"
        ledger["items"][0]["head_sha"] = "short-sha"
        with self.assertRaises(ValueError) as ctx:
            schema.validate_schema(ledger)
        # Should raise a ValueError with 'schema ...'
        self.assertTrue(str(ctx.exception).startswith("schema "))


if __name__ == "__main__":
    unittest.main()
