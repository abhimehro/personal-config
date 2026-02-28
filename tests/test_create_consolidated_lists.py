import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import os
import sys

# Ensure the module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from adguard.scripts.create_consolidated_lists import process_allowlist_files

class TestProcessAllowlistFiles(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for sandbox
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def tearDown(self):
        # Cleanup temporary directory
        self.temp_dir.cleanup()

    def create_json_file(self, filename, data):
        filepath = self.base_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return filepath

    @patch('builtins.print')
    def test_happy_path_both_files_present(self, mock_print):
        """Test with both bypass and TLD files present and valid."""
        bypass_data = {
            "rules": [
                {"PK": "bypass1.com", "action": {"do": 1}},
                {"PK": "bypass2.com", "action": {"do": 1}},
                {"PK": "ignored.com", "action": {"do": 0}} # Should be ignored
            ]
        }
        tlds_data = {
            "rules": [
                {"PK": "tld1.org", "action": {"do": 1}},
                {"PK": "tld2.net", "action": {"do": 1}}
            ]
        }
        self.create_json_file("CD-Control-D-Bypass.json", bypass_data)
        self.create_json_file("CD-Most-Abused-TLDs.json", tlds_data)

        result = process_allowlist_files(self.base_dir)

        expected_domains = {"bypass1.com", "bypass2.com", "tld1.org", "tld2.net"}
        self.assertEqual(result, expected_domains)

    @patch('builtins.print')
    def test_missing_bypass_file(self, mock_print):
        """Test with missing bypass file but valid TLD file."""
        tlds_data = {
            "rules": [
                {"PK": "tld1.org", "action": {"do": 1}}
            ]
        }
        self.create_json_file("CD-Most-Abused-TLDs.json", tlds_data)

        result = process_allowlist_files(self.base_dir)

        self.assertEqual(result, {"tld1.org"})

    @patch('builtins.print')
    def test_missing_tlds_file(self, mock_print):
        """Test with missing TLD file but valid bypass file."""
        bypass_data = {
            "rules": [
                {"PK": "bypass1.com", "action": {"do": 1}}
            ]
        }
        self.create_json_file("CD-Control-D-Bypass.json", bypass_data)

        result = process_allowlist_files(self.base_dir)

        self.assertEqual(result, {"bypass1.com"})

    @patch('builtins.print')
    def test_both_files_missing(self, mock_print):
        """Test when neither file exists."""
        result = process_allowlist_files(self.base_dir)
        self.assertEqual(result, set())

    @patch('builtins.print')
    def test_invalid_json_syntax(self, mock_print):
        """Test handling of malformed JSON."""
        # Create a malformed bypass file
        filepath = self.base_dir / "CD-Control-D-Bypass.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("{ invalid json ")

        # Valid TLDs file
        tlds_data = {
            "rules": [
                {"PK": "tld1.org", "action": {"do": 1}}
            ]
        }
        self.create_json_file("CD-Most-Abused-TLDs.json", tlds_data)

        result = process_allowlist_files(self.base_dir)

        # The invalid JSON should be caught and logged (skipped),
        # but the valid TLDs file should still be processed.
        self.assertEqual(result, {"tld1.org"})

    @patch('builtins.print')
    def test_empty_allowlists(self, mock_print):
        """Test with valid JSON but empty rules arrays."""
        empty_data = {"rules": []}
        self.create_json_file("CD-Control-D-Bypass.json", empty_data)
        self.create_json_file("CD-Most-Abused-TLDs.json", empty_data)

        result = process_allowlist_files(self.base_dir)
        self.assertEqual(result, set())

    @patch('builtins.print')
    def test_unexpected_data_structures(self, mock_print):
        """Test with unexpected data structures."""
        # Missing 'rules' key
        bypass_data = {"other_key": "value"}
        # 'rules' is not a list
        tlds_data = {"rules": {"not_a_list": "value"}}

        self.create_json_file("CD-Control-D-Bypass.json", bypass_data)
        self.create_json_file("CD-Most-Abused-TLDs.json", tlds_data)

        # Assuming extract_domains_from_file handles these safely
        # based on `if 'rules' in data` and iterating over `rules`.
        # Note: if 'rules' is a dict, iterating over it might yield keys,
        # but then `if 'PK' in rule` would look for 'PK' in the string key,
        # which will be false. So it should safely return empty.
        result = process_allowlist_files(self.base_dir)
        self.assertEqual(result, set())

    @patch('builtins.print')
    def test_duplicate_entries(self, mock_print):
        """Test that duplicate domains across files are deduplicated."""
        bypass_data = {
            "rules": [
                {"PK": "duplicate.com", "action": {"do": 1}},
                {"PK": "bypass1.com", "action": {"do": 1}}
            ]
        }
        tlds_data = {
            "rules": [
                {"PK": "duplicate.com", "action": {"do": 1}},
                {"PK": "tld1.org", "action": {"do": 1}}
            ]
        }
        self.create_json_file("CD-Control-D-Bypass.json", bypass_data)
        self.create_json_file("CD-Most-Abused-TLDs.json", tlds_data)

        result = process_allowlist_files(self.base_dir)

        expected_domains = {"duplicate.com", "bypass1.com", "tld1.org"}
        self.assertEqual(result, expected_domains)


if __name__ == '__main__':
    unittest.main()
