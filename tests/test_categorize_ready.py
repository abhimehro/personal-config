import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_vulnerability_fix import _load_function_only

class TestCategorizeReady(unittest.TestCase):
    def setUp(self):
        self.mod = _load_function_only("categorize_ready.py", {"run_gh", "_load_gh_token_env", "fetch_pr_info"})

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


    def test_fetch_pr_info_success(self):
        self.mod.run_gh = MagicMock(return_value={"title": "Test PR", "mergeStateStatus": "CLEAN"})
        pr_string = "owner/repo#123"
        pr, info = self.mod.fetch_pr_info(pr_string)

        self.mod.run_gh.assert_called_once_with([
            "gh",
            "pr",
            "view",
            "123",
            "-R",
            "owner/repo",
            "--json",
            "title,mergeStateStatus"
        ])

        self.assertEqual(pr, pr_string)
        self.assertEqual(info, {"title": "Test PR", "mergeStateStatus": "CLEAN"})

    def test_fetch_pr_info_failure(self):
        self.mod.run_gh = MagicMock(return_value=None)
        pr_string = "owner/repo#123"
        pr, info = self.mod.fetch_pr_info(pr_string)

        self.mod.run_gh.assert_called_once_with([
            "gh",
            "pr",
            "view",
            "123",
            "-R",
            "owner/repo",
            "--json",
            "title,mergeStateStatus"
        ])

        self.assertEqual(pr, pr_string)
        self.assertIsNone(info)

if __name__ == '__main__':
    unittest.main()
