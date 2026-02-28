import unittest
from unittest.mock import patch, mock_open
import sys
import os
import json
from pathlib import Path

# Explicitly add the script directory to sys.path so we can import it
script_dir = Path(__file__).parent.parent / "adguard" / "scripts"
sys.path.append(str(script_dir.resolve()))

from consolidate_adblock_lists import load_json_file, create_json_structure

class TestLoadJsonFile(unittest.TestCase):

    @patch('builtins.open', new_callable=mock_open, read_data='{"key": "value"}')
    def test_valid_json_happy_path(self, mock_file):
        # 1. Valid JSON file (happy path, returns expected dict)
        result = load_json_file('dummy_path.json')
        self.assertEqual(result, {"key": "value"})
        mock_file.assert_called_once_with('dummy_path.json', 'r', encoding='utf-8')

    @patch('builtins.open')
    def test_file_not_found_error(self, mock_file):
        # 2. FileNotFoundError (file does not exist)
        mock_file.side_effect = FileNotFoundError("No such file or directory")

        # Suppress print output for clean test output
        with patch('sys.stdout', new_callable=unittest.mock.MagicMock):
            result = load_json_file('nonexistent_path.json')

        self.assertIsNone(result)

    @patch('builtins.open', new_callable=mock_open, read_data='{invalid_json: 123')
    def test_json_decode_error(self, mock_file):
        # 3. json.JSONDecodeError (malformed JSON)
        with patch('sys.stdout', new_callable=unittest.mock.MagicMock):
            result = load_json_file('malformed_path.json')

        self.assertIsNone(result)

    @patch('builtins.open')
    def test_permission_error(self, mock_file):
        # 4. PermissionError (file not readable)
        mock_file.side_effect = PermissionError("Permission denied")

        with patch('sys.stdout', new_callable=unittest.mock.MagicMock):
            result = load_json_file('unreadable_path.json')

        self.assertIsNone(result)

    @patch('builtins.open', new_callable=mock_open, read_data='')
    def test_empty_file(self, mock_file):
        # 5. Empty file (0 bytes)
        with patch('sys.stdout', new_callable=unittest.mock.MagicMock):
            result = load_json_file('empty_path.json')

        self.assertIsNone(result)

    @patch('builtins.open', new_callable=mock_open, read_data='["item1", "item2"]')
    def test_valid_json_unexpected_type(self, mock_file):
        # 6. Valid JSON, unexpected type (array or primitive instead of dict)
        result = load_json_file('array_path.json')

        # The function should just parse whatever JSON returns, in this case a list
        self.assertEqual(result, ["item1", "item2"])
        self.assertIsInstance(result, list)


class TestCreateJsonStructure(unittest.TestCase):

    def test_happy_path(self):
        """Test with valid domains, group name, and action_do integer."""
        domains = {"example.com", "test.com", "apple.com"}
        group_name = "Comprehensive Allowlist"
        action_do = 1

        result = create_json_structure(domains, group_name, action_do)

        # Verify group metadata
        self.assertEqual(result["group"]["group"], group_name)
        self.assertEqual(result["group"]["action"]["do"], action_do)
        self.assertEqual(result["group"]["action"]["status"], 1)

        # Verify rules structure and sorting
        self.assertEqual(len(result["rules"]), 3)
        self.assertEqual(result["rules"][0]["PK"], "apple.com")
        self.assertEqual(result["rules"][0]["action"]["do"], action_do)
        self.assertEqual(result["rules"][1]["PK"], "example.com")
        self.assertEqual(result["rules"][2]["PK"], "test.com")

    def test_single_domain(self):
        """Verify correct structure with exactly one domain."""
        result = create_json_structure({"solo.com"}, "Single", 1)
        self.assertEqual(len(result["rules"]), 1)
        self.assertEqual(result["rules"][0]["PK"], "solo.com")

    def test_empty_domains(self):
        """Test the 'zero state' behavior with an empty domains set."""
        result = create_json_structure(set(), "Empty List", 0)

        self.assertEqual(result["group"]["group"], "Empty List")
        self.assertEqual(result["group"]["action"]["do"], 0)
        self.assertEqual(result["rules"], [])

    def test_invalid_input_types(self):
        """Document the current contract handling invalid input types.
        Currently, integers passed to group_name are preserved as integers
        and not cast to strings. Action_do accepts strings natively.

        # NOTE: If input validation is added later (e.g., raising TypeError),
        # update this test to assert the new expected behavior.
        """
        # Passing an integer where a string group name is expected
        result_int_group = create_json_structure({"domain.com"}, 12345, "0")
        self.assertEqual(result_int_group["group"]["group"], 12345)

        # Passing a string where an action_do integer is expected
        self.assertEqual(result_int_group["rules"][0]["action"]["do"], "0")

    def test_json_serialization_safety(self):
        """Verify that characters potentially breaking JSON formatting
        are handled safely when dumped by the json module."""
        nasty_group_name = 'Test "quotes" and \\backslashes\\ and \n newlines'
        domains = {'weird"domain.com'}

        result = create_json_structure(domains, nasty_group_name, 0)

        # Dump to JSON string and parse it back to verify serialization works
        json_string = json.dumps(result)
        parsed_result = json.loads(json_string)

        self.assertEqual(parsed_result["group"]["group"], nasty_group_name)
        self.assertEqual(parsed_result["rules"][0]["PK"], "weird\"domain.com")


if __name__ == "__main__":
    unittest.main()
