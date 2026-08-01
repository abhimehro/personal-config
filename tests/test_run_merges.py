import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_merges import _fetch_all_pr_data_parallel, _fetch_pr_data, get_diff, run_gh


class TestRunMerges(unittest.TestCase):
    def test_run_gh_success_json(self):
        with (
            patch("run_merges.load_gh_token_env", return_value={}) as _mock_env,
            patch("subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"key": "value"}'
            mock_run.return_value = mock_result

            result = run_gh(["gh", "test"])
            self.assertEqual(result, {"key": "value"})
            args, kwargs = mock_run.call_args
            self.assertIsInstance(args[0], list)
            self.assertEqual(args[0][0], "gh")
            self.assertFalse(kwargs.get("shell", False))
            self.assertIsNotNone(kwargs.get("timeout"))

    def test_run_gh_success_string(self):
        with (
            patch("run_merges.load_gh_token_env", return_value={}) as _mock_env,
            patch("subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "plain text output"
            mock_run.return_value = mock_result

            result = run_gh(["gh", "test"])
            self.assertEqual(result, "plain text output")

    def test_run_gh_failure(self):
        with (
            patch("run_merges.load_gh_token_env", return_value={}) as _mock_env,
            patch("subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_run.return_value = mock_result

            result = run_gh(["gh", "test"])
            self.assertIsNone(result)

    @patch("run_merges.run_gh")
    def test_get_diff_success(self, mock_run_gh):
        mock_run_gh.return_value = "diff output"
        res = get_diff("owner/repo", "123")
        self.assertEqual(res, "diff output")
        mock_run_gh.assert_called_once_with(
            ["gh", "pr", "diff", "123", "-R", "owner/repo"]
        )

    @patch("run_merges.run_gh")
    def test_get_diff_not_string(self, mock_run_gh):
        mock_run_gh.return_value = {"some": "json"}
        res = get_diff("owner/repo", "123")
        self.assertEqual(res, "")

    @patch("run_merges.get_diff")
    @patch("run_merges.run_gh")
    def test_fetch_pr_data_clean(self, mock_run_gh, mock_get_diff):
        mock_run_gh.return_value = {"mergeStateStatus": "CLEAN"}
        mock_get_diff.return_value = "some diff"

        repo, pr, title, info, diff = _fetch_pr_data(("owner/myrepo", "1", "title"))

        self.assertEqual(repo, "owner/myrepo")
        self.assertEqual(pr, "1")
        self.assertEqual(title, "title")
        self.assertEqual(info, {"mergeStateStatus": "CLEAN"})
        self.assertEqual(diff, "some diff")

        mock_run_gh.assert_called_once_with(
            [
                "gh",
                "pr",
                "view",
                "1",
                "-R",
                "owner/myrepo",
                "--json",
                "mergeStateStatus",
            ]
        )
        mock_get_diff.assert_called_once_with("owner/myrepo", "1")

    @patch("run_merges.get_diff")
    @patch("run_merges.run_gh")
    def test_fetch_pr_data_dirty(self, mock_run_gh, mock_get_diff):
        mock_run_gh.return_value = {"mergeStateStatus": "DIRTY"}

        repo, pr, title, info, diff = _fetch_pr_data(("owner/myrepo", "1", "title"))

        self.assertEqual(info, {"mergeStateStatus": "DIRTY"})
        self.assertEqual(diff, "")
        mock_get_diff.assert_not_called()

    @patch("run_merges.get_diff")
    @patch("run_merges.run_gh")
    def test_fetch_pr_data_no_info(self, mock_run_gh, mock_get_diff):
        mock_run_gh.return_value = None

        repo, pr, title, info, diff = _fetch_pr_data(("owner/myrepo", "1", "title"))

        self.assertIsNone(info)
        self.assertEqual(diff, "")
        mock_get_diff.assert_not_called()

    def test_fetch_pr_data_invalid_reference(self):
        with self.assertRaises(ValueError):
            _fetch_pr_data(("myrepo", "1", "title"))

    @patch("run_merges._fetch_pr_data")
    def test_fetch_all_pr_data_parallel(self, mock_fetch):
        mock_fetch.side_effect = lambda item: (item[0], item[1], item[2], None, "")
        result = _fetch_all_pr_data_parallel(
            [("owner/a", "1", "t1"), ("owner/b", "2", "t2")]
        )
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
