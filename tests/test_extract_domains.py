import json
import os

# Adjust the import path since the script is in adguard/scripts/
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add the project root to sys.path so we can import the script
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from adguard.scripts.extract_domains import (
    _is_allowlist_rule,
    extract_allowlist_domains_from_file,
    extract_domains_from_file,
    extract_all_denylist_domains,
    extract_all_allowlist_domains,
)


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


class TestIsAllowlistRule(unittest.TestCase):
    def test_valid_allowlist_rule(self):
        rule = {"PK": "example.com", "action": {"do": 1}}
        self.assertTrue(_is_allowlist_rule(rule))

    def test_missing_pk(self):
        rule = {"action": {"do": 1}}
        self.assertFalse(_is_allowlist_rule(rule))

    def test_missing_action(self):
        rule = {"PK": "example.com"}
        self.assertFalse(_is_allowlist_rule(rule))

    def test_action_not_dict(self):
        # Edge case: action is present but not a dictionary
        self.assertFalse(_is_allowlist_rule({"PK": "example.com", "action": 1}))
        self.assertFalse(_is_allowlist_rule({"PK": "example.com", "action": "allow"}))
        self.assertFalse(_is_allowlist_rule({"PK": "example.com", "action": []}))
        self.assertFalse(_is_allowlist_rule({"PK": "example.com", "action": None}))

    def test_missing_do(self):
        rule = {"PK": "example.com", "action": {"other": 1}}
        self.assertFalse(_is_allowlist_rule(rule))

    def test_do_not_one(self):
        rule = {"PK": "example.com", "action": {"do": 0}}
        self.assertFalse(_is_allowlist_rule(rule))


class TestExtractAllowlistDomainsFromFile(unittest.TestCase):
    def test_happy_path(self):
        json_data = json.dumps(
            {
                "rules": [
                    {"PK": "example.com", "action": {"do": 1}},
                    {"PK": "test.com", "action": {"do": 0}},
                    {"PK": "anotherexample.com", "action": {"do": 1}},
                ]
            }
        )
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(json_data)
            temp_path = tf.name

        try:
            result = extract_allowlist_domains_from_file(temp_path)
            self.assertEqual(result, ["example.com", "anotherexample.com"])
        finally:
            os.remove(temp_path)

    @patch("builtins.print")
    def test_missing_file(self, mock_print):
        missing_path = "nonexistent_file_12345.json"
        result = extract_allowlist_domains_from_file(missing_path)
        self.assertEqual(result, [])
        mock_print.assert_called_once()
        self.assertIn(f"Error reading {missing_path}", mock_print.call_args[0][0])

    @patch("builtins.print")
    def test_invalid_json(self, mock_print):
        invalid_json = "this is not json"
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(invalid_json)
            temp_path = tf.name

        try:
            result = extract_allowlist_domains_from_file(temp_path)
            self.assertEqual(result, [])
            mock_print.assert_called_once()
            self.assertIn(f"Error reading {temp_path}", mock_print.call_args[0][0])
        finally:
            os.remove(temp_path)


class TestExtractAllDenylistDomains(unittest.TestCase):
    @patch("adguard.scripts.extract_domains.extract_domains_from_file")
    @patch("concurrent.futures.as_completed")
    @patch("concurrent.futures.ProcessPoolExecutor")
    @patch("os.path.exists")
    def test_extract_all_denylist_domains(self, mock_exists, mock_executor_cls, mock_as_completed, mock_extract):
        mock_exists.side_effect = lambda path: True
        mock_extract.side_effect = lambda path: [f"domain-{os.path.basename(path)}"]

        # Set up mock executor
        mock_executor = mock_executor_cls.return_value
        mock_executor.__enter__.return_value = mock_executor

        class MockFuture:
            def __init__(self, path):
                self.path = path
            def result(self):
                return [f"domain-{os.path.basename(self.path)}"]

        mock_executor.submit.side_effect = lambda fn, path: MockFuture(path)
        mock_as_completed.side_effect = lambda future_map: list(future_map.keys())

        tracker_files = ["file1.json", "file2.json"]
        result = extract_all_denylist_domains("/mock_dir", tracker_files)
        self.assertEqual(result, {"domain-file1.json", "domain-file2.json"})


class TestExtractAllAllowlistDomains(unittest.TestCase):
    @patch("adguard.scripts.extract_domains.extract_allowlist_domains_from_file")
    @patch("os.path.exists")
    def test_extract_all_allowlist_domains(self, mock_exists, mock_extract):
        mock_exists.side_effect = lambda path: "CD-Control-D-Bypass.json" in path
        mock_extract.return_value = ["allowed.com"]

        result = extract_all_allowlist_domains("/mock_dir")
        self.assertEqual(result, {"allowed.com"})


if __name__ == "__main__":
    unittest.main()
