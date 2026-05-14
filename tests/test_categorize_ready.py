import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_vulnerability_fix import _load_function_only

class TestCategorizeReady(unittest.TestCase):
    def setUp(self):
        self.mod = _load_function_only("categorize_ready.py", {"run_gh", "_load_gh_token_env"})

    @patch('subprocess.run')
    def test_run_gh_invalid_json(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "This is not valid JSON"
        mock_run.return_value = mock_result

        result = self.mod.run_gh(['gh', 'pr', 'view', '123'])

        self.assertIsNone(result)

    @patch('subprocess.run')
    def test_run_gh_non_zero_exit(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Error"
        mock_run.return_value = mock_result

        result = self.mod.run_gh(['gh', 'pr', 'view', '123'])

        self.assertIsNone(result)

    @patch('subprocess.run')
    def test_run_gh_valid_json(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"title": "test", "state": "open"}'
        mock_run.return_value = mock_result

        result = self.mod.run_gh(['gh', 'pr', 'view', '123'])

        self.assertEqual(result, {"title": "test", "state": "open"})

if __name__ == '__main__':
    unittest.main()
