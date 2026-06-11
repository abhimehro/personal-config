import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_vulnerability_fix import _load_function_only


class TestCategorizeReady(unittest.TestCase):
    def setUp(self):
        self.mod = _load_function_only(
            "categorize_ready.py",
            {
                "run_gh",
                "_load_gh_token_env",
                "fetch_pr_info",
                "get_category_from_title",
            },
        )

    @patch("subprocess.run")
    def test_run_gh_invalid_json(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "This is not valid JSON"
        mock_run.return_value = mock_result

        result = self.mod.run_gh(["gh", "pr", "view", "123"])

        self.assertIsNone(result)

    @patch("subprocess.run")
    def test_run_gh_non_zero_exit(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Error"
        mock_run.return_value = mock_result

        result = self.mod.run_gh(["gh", "pr", "view", "123"])

        self.assertIsNone(result)

    @patch("subprocess.run")
    def test_run_gh_valid_json(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"title": "test", "state": "open"}'
        mock_run.return_value = mock_result

        result = self.mod.run_gh(["gh", "pr", "view", "123"])

        self.assertEqual(result, {"title": "test", "state": "open"})

    def _assert_fetch_pr_info(self, mock_return_value, expected_info):
        self.mod.run_gh = MagicMock(return_value=mock_return_value)
        pr_string = "owner/repo#123"
        pr, info = self.mod.fetch_pr_info(pr_string)

        self.mod.run_gh.assert_called_once_with(
            [
                "gh",
                "pr",
                "view",
                "123",
                "-R",
                "owner/repo",
                "--json",
                "title,mergeStateStatus",
            ]
        )

        self.assertEqual(pr, pr_string)
        self.assertEqual(info, expected_info)

    def test_fetch_pr_info_success(self):
        self._assert_fetch_pr_info(
            {"title": "Test PR", "mergeStateStatus": "CLEAN"},
            {"title": "Test PR", "mergeStateStatus": "CLEAN"},
        )

    def test_fetch_pr_info_failure(self):
        self._assert_fetch_pr_info(None, None)

    def test_get_category_from_title_security(self):
        self.assertEqual(
            self.mod.get_category_from_title("Fix security vulnerability"), "SECURITY"
        )
        self.assertEqual(
            self.mod.get_category_from_title("Update sentinel policies"), "SECURITY"
        )

    def test_get_category_from_title_dependency(self):
        self.assertEqual(
            self.mod.get_category_from_title("Bump dependabot version"), "DEPENDENCY"
        )

    def test_get_category_from_title_ci(self):
        self.assertEqual(
            self.mod.get_category_from_title("chore: update build script"), "CI/INFRA"
        )

    def test_get_category_from_title_feature(self):
        self.assertEqual(
            self.mod.get_category_from_title("Add new user dashboard"),
            "PERFORMANCE/REFACTOR/UI/FEATURE",
        )


if __name__ == "__main__":
    unittest.main()
