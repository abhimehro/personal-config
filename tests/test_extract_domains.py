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
    process_allowlist_files,
    process_denylist_files,
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





class TestProcessAllowlistFiles(unittest.TestCase):
    @patch("builtins.print")
    def test_process_allowlist_files_all_exist(self, _mock_print):
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(
                os.path.join(temp_dir, "CD-Control-D-Bypass.json"),
                "w",
                encoding="utf-8",
            ) as file:
                json.dump({"rules": [{"PK": "bypass.com", "action": {"do": 1}}]}, file)

            with open(
                os.path.join(temp_dir, "CD-Most-Abused-TLDs.json"),
                "w",
                encoding="utf-8",
            ) as file:
                json.dump({"rules": [{"PK": "tld.com", "action": {"do": 1}}]}, file)

            result = process_allowlist_files(temp_dir)
            self.assertEqual(result, {"bypass.com", "tld.com"})

    @patch("builtins.print")
    def test_process_allowlist_files_missing_file(self, _mock_print):
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(
                os.path.join(temp_dir, "CD-Control-D-Bypass.json"),
                "w",
                encoding="utf-8",
            ) as file:
                json.dump({"rules": [{"PK": "bypass.com", "action": {"do": 1}}]}, file)

            result = process_allowlist_files(temp_dir)
            self.assertEqual(result, {"bypass.com"})

    @patch("builtins.print")
    def test_process_allowlist_files_no_files(self, _mock_print):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = process_allowlist_files(temp_dir)
            self.assertEqual(result, set())


class TestProcessDenylistFiles(unittest.TestCase):
    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = os.path.join(temp_dir, "CD-Microsoft-Tracker.json")
            with open(file1, "w", encoding="utf-8") as f:
                json.dump({"rules": [{"PK": "ms1.com"}, {"PK": "ms2.com"}]}, f)

            file2 = os.path.join(temp_dir, "CD-Apple-Tracker.json")
            with open(file2, "w", encoding="utf-8") as f:
                json.dump({"rules": [{"PK": "apple1.com"}]}, f)

            result = process_denylist_files(temp_dir)
            self.assertEqual(result, {"ms1.com", "ms2.com", "apple1.com"})

    def test_no_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = process_denylist_files(temp_dir)
            self.assertEqual(result, set())

    @patch("adguard.scripts.extract_domains.extract_domains_from_file")
    def test_worker_exception(self, mock_extract):
        # Sequential process_denylist_files swallows per-file exceptions.
        mock_extract.side_effect = Exception("Mocked exception")

        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = os.path.join(temp_dir, "CD-Microsoft-Tracker.json")
            with open(file1, "w", encoding="utf-8") as f:
                f.write("mock")

            result = process_denylist_files(temp_dir)
            self.assertEqual(result, set())
            mock_extract.assert_called_once()


if __name__ == "__main__":
    unittest.main()
