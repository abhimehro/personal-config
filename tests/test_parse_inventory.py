import unittest
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Ensure the project root is in the path so we can import parse_inventory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parse_inventory import (
    _parse_env_line,
    parse_inventory_lines,
    _is_pr_stale,
    _get_pr_category,
    _is_checks_failing,
    run_gh,
    _load_inventory_lines,
)

class TestParseInventory(unittest.TestCase):
    @staticmethod
    def _recent_iso(days=1):
        return (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    @staticmethod
    def _build_info(merge_state, updated_at, with_files=True):
        if not with_files:
            return {"files": []}
        return {
            "files": [{"filename": "foo.py"}],
            "mergeStateStatus": merge_state,
            "updatedAt": updated_at,
        }

    def test_parse_env_line_basic(self):
        env = {}
        _parse_env_line("FOO=bar", env)
        self.assertEqual(env, {"FOO": "bar"})

    def test_parse_env_line_with_export(self):
        env = {}
        _parse_env_line("export FOO=bar", env)
        self.assertEqual(env, {"FOO": "bar"})

    def test_parse_env_line_with_quotes(self):
        env = {}
        _parse_env_line("export FOO=\"bar\"", env)
        self.assertEqual(env, {"FOO": "bar"})

        env = {}
        _parse_env_line("export FOO='bar'", env)
        self.assertEqual(env, {"FOO": "bar"})

    def test_parse_env_line_comments_and_empty(self):
        env = {"FOO": "bar"}
        _parse_env_line("# export BAZ=qux", env)
        self.assertEqual(env, {"FOO": "bar"})

        _parse_env_line("   ", env)
        self.assertEqual(env, {"FOO": "bar"})

    def test_parse_inventory_lines(self):
        # Flat-table format matching tasks/pr-inventory.md (no ## section headers)
        lines = [
            "| Repo | PR | Author (API) | Branch (head) | Category | CI rollup | Conflicts | Age (created→) | Notes |\n",
            "| ---------------------------------------- | --- | ------------ | ----------- | ------- | --------- | --------- | -------------- | ----- |\n",
            "| repoA | 123 | some_user[bot] | branch | cat | C | none | 2026-05-03 | |\n",
            "| repoA | 456 | human | branch | cat | FAIL | none | 2026-05-03 | has-hints |\n",
            "| repoA | 789 | human | branch | cat | C | none | 2026-05-03 | |\n",
            "| repoB | 101 | another[bot] | branch | cat | C | none | 2026-05-03 | |\n",
        ]
        repos = parse_inventory_lines(lines)

        self.assertIn("repoA", repos)
        self.assertIn("repoB", repos)

        # repoA: 123 (bot) and 456 (human with hints), not 789 (human, no hints)
        self.assertEqual(len(repos["repoA"]), 2)
        self.assertEqual(repos["repoA"][0]["pr"], "123")
        self.assertEqual(repos["repoA"][0]["checks"], "C")

        self.assertEqual(repos["repoA"][1]["pr"], "456")
        self.assertEqual(repos["repoA"][1]["checks"], "FAIL")

        # repoB: 101 (bot)
        self.assertEqual(len(repos["repoB"]), 1)
        self.assertEqual(repos["repoB"][0]["pr"], "101")
        self.assertEqual(repos["repoB"][0]["checks"], "C")

    def test_parse_inventory_lines_missing_repo(self):
        # Flat-table row with empty repo column and no section header: should be skipped
        lines = [
            "| | 123 | some_user[bot] | branch | cat | FAIL | none | 2026-05-03 | has-hints |\n",
        ]
        repos = parse_inventory_lines(lines)
        self.assertEqual(repos, {})

    def test_parse_inventory_lines_malformed(self):
        # Section-header establishes repo; row with too few columns is silently skipped
        lines = [
            "## repoA\n",
            "| repoA | 123 | bot[bot] | \n",  # Too few columns
        ]
        repos = parse_inventory_lines(lines)
        self.assertEqual(repos["repoA"], [])

    # --- _is_pr_stale ---

    def test_is_pr_stale_old_date(self):
        self.assertTrue(_is_pr_stale("2020-01-01T00:00:00Z"))

    def test_is_pr_stale_recent_date(self):
        recent = self._recent_iso(days=5)
        self.assertFalse(_is_pr_stale(recent))

    def test_is_pr_stale_empty(self):
        self.assertFalse(_is_pr_stale(""))

    def test_is_pr_stale_none(self):
        self.assertFalse(_is_pr_stale(None))

    def test_load_inventory_lines_file_not_found(self):
        lines = _load_inventory_lines("nonexistent_file_xyz_123.txt")
        self.assertEqual(lines, [])

    # --- _is_checks_failing ---

    def test_is_checks_failing_fail(self):
        self.assertTrue(_is_checks_failing("FAIL"))

    def test_is_checks_failing_pending(self):
        self.assertTrue(_is_checks_failing("PENDING"))

    def test_is_checks_failing_unstable(self):
        self.assertTrue(_is_checks_failing("U"))

    def test_is_checks_failing_passing(self):
        self.assertFalse(_is_checks_failing("C"))

    # --- _get_pr_category ---

    def test_get_pr_category_superseded_no_files(self):
        info = self._build_info("CLEAN", self._recent_iso(), with_files=False)
        self.assertEqual(_get_pr_category(info, "C"), "SUPERSEDED")

    def test_get_pr_category_superseded_missing_files_key(self):
        self.assertEqual(_get_pr_category({}, "C"), "SUPERSEDED")

    def test_get_pr_category_stale(self):
        info = self._build_info("CLEAN", "2020-01-01T00:00:00Z")
        self.assertEqual(_get_pr_category(info, "FAIL"), "STALE")

    def test_get_pr_category_conflicting_dirty(self):
        info = self._build_info("DIRTY", self._recent_iso())
        self.assertEqual(_get_pr_category(info, "C"), "CONFLICTING")

    def test_get_pr_category_conflicting_explicit(self):
        info = self._build_info("CONFLICTING", self._recent_iso())
        self.assertEqual(_get_pr_category(info, "C"), "CONFLICTING")

    def test_get_pr_category_ready(self):
        info = self._build_info("CLEAN", self._recent_iso())
        self.assertEqual(_get_pr_category(info, "C"), "READY")

    def test_get_pr_category_none_recent_clean_failing(self):
        # Recent PR + CLEAN merge state + failing checks → no category assigned
        info = self._build_info("CLEAN", self._recent_iso())
        self.assertIsNone(_get_pr_category(info, "FAIL"))

    # --- run_gh ---

    @patch("parse_inventory._load_gh_token_env", return_value={})
    @patch("parse_inventory.subprocess.run")
    def test_run_gh_success(self, mock_run, _mock_env):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"files": [{"filename": "foo.py"}], "updatedAt": "2026-05-03T00:00:00Z"}'
        mock_run.return_value = mock_result
        result = run_gh("repoA", 123)
        self.assertIsNotNone(result)
        self.assertEqual(result["files"][0]["filename"], "foo.py")

    @patch("parse_inventory._load_gh_token_env", return_value={})
    @patch("parse_inventory.subprocess.run")
    def test_run_gh_nonzero(self, mock_run, _mock_env):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "error"
        mock_run.return_value = mock_result
        self.assertIsNone(run_gh("repoA", 123))

    @patch("parse_inventory._load_gh_token_env", return_value={})
    @patch("parse_inventory.subprocess.run")
    def test_run_gh_invalid_json(self, mock_run, _mock_env):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid json"
        mock_run.return_value = mock_result
        self.assertIsNone(run_gh("repoA", 123))



    @patch("parse_inventory._load_gh_token_env", return_value={})
    @patch("parse_inventory.subprocess.run")
    def test_run_gh_returncode_not_zero(self, mock_run, _mock_env):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = '{"files": []}'
        mock_run.return_value = mock_result
        self.assertIsNone(run_gh("repoA", 123))


if __name__ == '__main__':
    unittest.main()
