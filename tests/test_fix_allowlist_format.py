import unittest
import json
from unittest.mock import patch, mock_open
import tempfile
import os

# Adjust the import path since the script is in adguard/scripts/
import sys
from pathlib import Path

# Add the project root to sys.path so we can import the script
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from adguard.scripts.import_fix_allowlist_format import extract_allowlist_domains_from_file


class TestExtractAllowlistDomainsFromFile(unittest.TestCase):

    def test_valid_json_multiple_entries_do_1(self):
        json_data = json.dumps({
            "rules": [
                {"PK": "example.com", "action": {"do": 1}},
                {"PK": "test.com", "action": {"do": 1}}
            ]
        })
        with patch('builtins.open', mock_open(read_data=json_data)):
            result = extract_allowlist_domains_from_file('dummy.json')
        self.assertEqual(result, ["example.com", "test.com"])

    def test_valid_json_mix_do_values(self):
        json_data = json.dumps({
            "rules": [
                {"PK": "allow.com", "action": {"do": 1}},
                {"PK": "block.com", "action": {"do": 0}},
                {"PK": "null-do.com", "action": {"do": None}}
            ]
        })
        with patch('builtins.open', mock_open(read_data=json_data)):
            result = extract_allowlist_domains_from_file('dummy.json')
        self.assertEqual(result, ["allow.com"])

    def test_valid_json_empty_rules_list(self):
        json_data = json.dumps({"rules": []})
        with patch('builtins.open', mock_open(read_data=json_data)):
            result = extract_allowlist_domains_from_file('dummy.json')
        self.assertEqual(result, [])

    def test_valid_json_no_rules_key(self):
        json_data = json.dumps({"other_key": "value"})
        with patch('builtins.open', mock_open(read_data=json_data)):
            result = extract_allowlist_domains_from_file('dummy.json')
        self.assertEqual(result, [])

    def test_entry_missing_pk_key(self):
        json_data = json.dumps({
            "rules": [
                {"action": {"do": 1}},  # Missing PK
                {"PK": "valid.com", "action": {"do": 1}}
            ]
        })
        with patch('builtins.open', mock_open(read_data=json_data)):
            result = extract_allowlist_domains_from_file('dummy.json')
        self.assertEqual(result, ["valid.com"])

    def test_entry_missing_action_key(self):
        json_data = json.dumps({
            "rules": [
                {"PK": "no-action.com"},
                {"PK": "valid.com", "action": {"do": 1}}
            ]
        })
        with patch('builtins.open', mock_open(read_data=json_data)):
            result = extract_allowlist_domains_from_file('dummy.json')
        self.assertEqual(result, ["valid.com"])

    @patch('builtins.print')
    def test_file_not_found(self, mock_print):
        # We don't mock open here, so it actually raises FileNotFoundError
        result = extract_allowlist_domains_from_file('nonexistent_file.json')
        self.assertEqual(result, [])
        mock_print.assert_called_once()
        self.assertIn("Error reading nonexistent_file.json", mock_print.call_args[0][0])

    @patch('builtins.print')
    def test_invalid_json_content(self, mock_print):
        invalid_json = "this is not json"
        with patch('builtins.open', mock_open(read_data=invalid_json)):
            result = extract_allowlist_domains_from_file('dummy.json')
        self.assertEqual(result, [])
        mock_print.assert_called_once()
        self.assertIn("Error reading dummy.json", mock_print.call_args[0][0])

    @patch('builtins.print')
    def test_empty_file(self, mock_print):
        with patch('builtins.open', mock_open(read_data="")):
            result = extract_allowlist_domains_from_file('dummy.json')
        self.assertEqual(result, [])
        mock_print.assert_called_once()
        self.assertIn("Error reading dummy.json", mock_print.call_args[0][0])

    def test_entry_where_do_is_not_1(self):
        json_data = json.dumps({
            "rules": [
                {"PK": "zero.com", "action": {"do": 0}},
                {"PK": "two.com", "action": {"do": 2}},
                {"PK": "string.com", "action": {"do": "1"}}, # Assuming strict equality
            ]
        })
        with patch('builtins.open', mock_open(read_data=json_data)):
            result = extract_allowlist_domains_from_file('dummy.json')
        self.assertEqual(result, [])

    # Integration Test
    def test_integration_with_tempfile(self):
        json_data = json.dumps({
            "rules": [
                {"PK": "temp.com", "action": {"do": 1}}
            ]
        })

        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tf:
            tf.write(json_data)
            temp_path = tf.name

        try:
            result = extract_allowlist_domains_from_file(temp_path)
            self.assertEqual(result, ["temp.com"])
        finally:
            os.remove(temp_path)

if __name__ == '__main__':
    unittest.main()
