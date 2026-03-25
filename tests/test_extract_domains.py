import json
import os

# Adjust the import path since the script is in adguard/scripts/
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

# Add the project root to sys.path so we can import the script
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from adguard.scripts.extract_domains import extract_domains_from_file


class TestExtractDomainsFromFile(unittest.TestCase):

    def test_happy_path(self):
        """Happy path: valid JSON, rules key exists, extracts only PK values, preserves order."""
        json_data = json.dumps(
            {"rules": [{"PK": "example.com", "other": "data"}, {"PK": "test.com"}]}
        )
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(json_data)
            temp_path = tf.name

        try:
            result = extract_domains_from_file(temp_path)
            self.assertEqual(result, ["example.com", "test.com"])
        finally:
            os.remove(temp_path)

    def test_partial_data(self):
        """Partial data: some rules missing PK, function skips those entries cleanly."""
        json_data = json.dumps(
            {
                "rules": [
                    {"PK": "valid.com"},
                    {"other_key": "no-pk"},
                    {"PK": "also-valid.com"},
                ]
            }
        )
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(json_data)
            temp_path = tf.name

        try:
            result = extract_domains_from_file(temp_path)
            self.assertEqual(result, ["valid.com", "also-valid.com"])
        finally:
            os.remove(temp_path)

    def test_missing_rules(self):
        """Missing rules: valid JSON without rules, returns empty list."""
        json_data = json.dumps({"different_key": [{"PK": "example.com"}]})
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(json_data)
            temp_path = tf.name

        try:
            result = extract_domains_from_file(temp_path)
            self.assertEqual(result, [])
        finally:
            os.remove(temp_path)

    def test_empty_rules(self):
        """Empty rules: valid JSON with empty rules list, returns empty list."""
        json_data = json.dumps({"rules": []})
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(json_data)
            temp_path = tf.name

        try:
            result = extract_domains_from_file(temp_path)
            self.assertEqual(result, [])
        finally:
            os.remove(temp_path)

    @patch("builtins.print")
    def test_invalid_json(self, mock_print):
        """Invalid JSON: prints an error, returns empty list."""
        invalid_json = "this is not json"
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(invalid_json)
            temp_path = tf.name

        try:
            result = extract_domains_from_file(temp_path)
            self.assertEqual(result, [])
            mock_print.assert_called_once()
            self.assertIn(f"Error reading {temp_path}", mock_print.call_args[0][0])
        finally:
            os.remove(temp_path)

    @patch("builtins.print")
    def test_missing_file(self, mock_print):
        """Missing file: prints an error, returns empty list."""
        missing_path = "nonexistent_file_12345.json"
        result = extract_domains_from_file(missing_path)
        self.assertEqual(result, [])
        mock_print.assert_called_once()
        self.assertIn(f"Error reading {missing_path}", mock_print.call_args[0][0])

    @patch("builtins.print")
    def test_unexpected_shape(self, mock_print):
        """Unexpected shape: rules is not a list, gracefully fails and returns empty list."""
        json_data = json.dumps({"rules": 12345})
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(json_data)
            temp_path = tf.name

        try:
            result = extract_domains_from_file(temp_path)
            self.assertEqual(result, [])
            mock_print.assert_called_once()
            self.assertIn(f"Error reading {temp_path}", mock_print.call_args[0][0])
        finally:
            os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
