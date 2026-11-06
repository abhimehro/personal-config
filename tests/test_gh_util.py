import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

from gh_util import run_gh


class TestGhUtil(unittest.TestCase):
    @patch("gh_util.load_gh_token_env", return_value={"GH_TOKEN": "secret"})
    @patch("subprocess.run")
    def test_run_gh_success_json(self, mock_run, _mock_env):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"title": "test", "state": "open"}'
        mock_run.return_value = mock_result

        result = run_gh(["gh", "pr", "view", "123"])

        self.assertEqual(result, {"title": "test", "state": "open"})
        mock_run.assert_called_once_with(
            ["gh", "pr", "view", "123"],
            capture_output=True,
            text=True,
            env={"GH_TOKEN": "secret"},
            timeout=120,
            check=False,
        )

    @patch("gh_util.load_gh_token_env", return_value={})
    @patch("subprocess.run")
    def test_run_gh_invalid_json_default(self, mock_run, _mock_env):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"
        mock_run.return_value = mock_result

        result = run_gh(["gh", "pr", "diff"])
        self.assertIsNone(result)

    @patch("gh_util.load_gh_token_env", return_value={})
    @patch("subprocess.run")
    def test_run_gh_invalid_json_raw_fallback(self, mock_run, _mock_env):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "plain diff string"
        mock_run.return_value = mock_result

        result = run_gh(["gh", "pr", "diff"], raw_fallback=True)
        self.assertEqual(result, "plain diff string")

    @patch("gh_util.load_gh_token_env", return_value={})
    @patch("subprocess.run")
    def test_run_gh_non_zero_exit(self, mock_run, _mock_env):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Error"
        mock_run.return_value = mock_result

        result = run_gh(["gh", "pr", "view", "123"])
        self.assertIsNone(result)

    @patch("gh_util.load_gh_token_env", return_value={})
    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["gh"], timeout=120))
    def test_run_gh_timeout(self, mock_run, _mock_env):
        result = run_gh(["gh", "pr", "view", "123"])
        self.assertIsNone(result)

    @patch("gh_util.load_gh_token_env", return_value={})
    @patch("subprocess.run", side_effect=OSError("Command not found"))
    def test_run_gh_oserror(self, mock_run, _mock_env):
        result = run_gh(["gh", "pr", "view", "123"])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
