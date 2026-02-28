import unittest
from unittest.mock import patch, mock_open
import sys
import os

# Add the script's directory to sys.path so we can import it
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../adguard/scripts')))

from consolidate_adblock_lists import load_json_file

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

if __name__ == '__main__':
    unittest.main()
