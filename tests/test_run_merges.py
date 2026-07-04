import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
from importlib import import_module
from pathlib import Path
import sys

# Add the project root to sys.path so we can import run_merges
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_merges
from run_merges import (
    _parse_env_line,
    _get_parsed_env_vars,
    _load_gh_token_env,
    run_gh,
    get_diff,
    _fetch_pr_data,
)

class TestRunMerges(unittest.TestCase):
    def setUp(self):
        # Clear the lru_cache before each test
        _get_parsed_env_vars.cache_clear()

    def test_parse_env_line(self):
        env_dict = {}
        _parse_env_line("FOO=bar", env_dict)
        self.assertEqual(env_dict["FOO"], "bar")

        _parse_env_line("export BAZ=qux", env_dict)
        self.assertEqual(env_dict["BAZ"], "qux")

        _parse_env_line("# comment", env_dict)
        self.assertNotIn("#", env_dict)

        _parse_env_line("export QUUX='hello'", env_dict)
        self.assertEqual(env_dict["QUUX"], "hello")

        _parse_env_line("INVALID_LINE", env_dict)
        self.assertNotIn("INVALID_LINE", env_dict)

    @patch("builtins.open", new_callable=mock_open, read_data="FOO=bar\nexport BAZ=qux\n# comment")
    def test_get_parsed_env_vars(self, mock_file):
        parsed = _get_parsed_env_vars()
        self.assertEqual(parsed, {"FOO": "bar", "BAZ": "qux"})
        mock_file.assert_called_once_with("../email-security-pipeline/GH_TOKEN.env", "r")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_get_parsed_env_vars_file_not_found(self, mock_file):
        parsed = _get_parsed_env_vars()
        self.assertEqual(parsed, {})
        mock_file.assert_called_once_with("../email-security-pipeline/GH_TOKEN.env", "r")

    @patch("run_merges._get_parsed_env_vars")
    @patch.dict(os.environ, {"EXISTING": "val"}, clear=True)
    def test_load_gh_token_env(self, mock_get_parsed):
        mock_get_parsed.return_value = {"NEW_VAR": "new_val"}
        env = _load_gh_token_env()
        self.assertEqual(env.get("EXISTING"), "val")
        self.assertEqual(env.get("NEW_VAR"), "new_val")

    @patch("subprocess.run")
    @patch("run_merges._load_gh_token_env")
    def test_run_gh_success_json(self, mock_load_env, mock_run):
        mock_load_env.return_value = {"TEST_ENV": "1"}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"key": "value"}'
        mock_run.return_value = mock_result

        result = run_gh(["gh", "test"])
        self.assertEqual(result, {"key": "value"})
        mock_run.assert_called_once_with(["gh", "test"], capture_output=True, text=True, env={"TEST_ENV": "1"})

    @patch("subprocess.run")
    @patch("run_merges._load_gh_token_env")
    def test_run_gh_success_string(self, mock_load_env, mock_run):
        mock_load_env.return_value = {}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'plain text output'
        mock_run.return_value = mock_result

        result = run_gh(["gh", "test"])
        self.assertEqual(result, "plain text output")

    @patch("subprocess.run")
    @patch("run_merges._load_gh_token_env")
    def test_run_gh_failure(self, mock_load_env, mock_run):
        mock_load_env.return_value = {}
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        result = run_gh(["gh", "test"])
        self.assertIsNone(result)

    @patch("run_merges.run_gh")
    def test_get_diff_success(self, mock_run_gh):
        mock_run_gh.return_value = "diff output"
        res = get_diff("repo", "123")
        self.assertEqual(res, "diff output")
        mock_run_gh.assert_called_once_with(["gh", "pr", "diff", "123", "-R", "repo"])

    @patch("run_merges.run_gh")
    def test_get_diff_not_string(self, mock_run_gh):
        mock_run_gh.return_value = {"some": "json"}
        res = get_diff("repo", "123")
        self.assertEqual(res, "")

    @patch("run_merges.get_diff")
    @patch("run_merges.run_gh")
    def test_fetch_pr_data_clean(self, mock_run_gh, mock_get_diff):
        mock_run_gh.return_value = {"mergeStateStatus": "CLEAN"}
        mock_get_diff.return_value = "some diff"

        repo, pr, title, info, diff = _fetch_pr_data(("myrepo", "1", "title"))

        self.assertEqual(repo, "myrepo")
        self.assertEqual(pr, "1")
        self.assertEqual(title, "title")
        self.assertEqual(info, {"mergeStateStatus": "CLEAN"})
        self.assertEqual(diff, "some diff")

        mock_run_gh.assert_called_once_with(["gh", "pr", "view", "1", "-R", "myrepo", "--json", "mergeStateStatus"])
        mock_get_diff.assert_called_once_with("myrepo", "1")

    @patch("run_merges.get_diff")
    @patch("run_merges.run_gh")
    def test_fetch_pr_data_dirty(self, mock_run_gh, mock_get_diff):
        mock_run_gh.return_value = {"mergeStateStatus": "DIRTY"}

        repo, pr, title, info, diff = _fetch_pr_data(("myrepo", "1", "title"))

        self.assertEqual(info, {"mergeStateStatus": "DIRTY"})
        self.assertEqual(diff, "")
        mock_get_diff.assert_not_called()

    @patch("run_merges.get_diff")
    @patch("run_merges.run_gh")
    def test_fetch_pr_data_no_info(self, mock_run_gh, mock_get_diff):
        mock_run_gh.return_value = None

        repo, pr, title, info, diff = _fetch_pr_data(("myrepo", "1", "title"))

        self.assertIsNone(info)
        self.assertEqual(diff, "")
        mock_get_diff.assert_not_called()

if __name__ == "__main__":
    unittest.main()
