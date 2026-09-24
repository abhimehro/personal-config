import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_merges import (
    _fetch_all_pr_data_parallel,
    get_diff,
    review_queue,
    run_gh,
)


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

    def test_run_gh_timeout(self):
        import subprocess

        with (
            patch("run_merges.load_gh_token_env", return_value={}),
            patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["gh", "test"], timeout=120),
            ),
        ):
            result = run_gh(["gh", "test"])
            self.assertIsNone(result)

    def test_run_gh_oserror(self):
        with (
            patch("run_merges.load_gh_token_env", return_value={}),
            patch("subprocess.run", side_effect=OSError("Command not found")),
        ):
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
    def test_fetch_all_pr_data_parallel(self, mock_run_gh, mock_get_diff):
        mock_run_gh.return_value = {
            "data": {
                "pr0": {"pullRequest": {"mergeStateStatus": "CLEAN"}},
                "pr1": {"pullRequest": {"mergeStateStatus": "DIRTY"}},
            }
        }
        mock_get_diff.side_effect = lambda repo, pr: "diff " + pr

        items = [("owner/repo1", "1", "title1"), ("owner/repo2", "2", "title2")]
        result = _fetch_all_pr_data_parallel(items)

        self.assertEqual(len(result), 2)

        # PR 1 (CLEAN)
        self.assertEqual(result[0][0], "owner/repo1")
        self.assertEqual(result[0][1], "1")
        self.assertEqual(result[0][3], {"mergeStateStatus": "CLEAN"})
        self.assertEqual(result[0][4], "diff 1")

        # PR 2 (DIRTY)
        self.assertEqual(result[1][3], {"mergeStateStatus": "DIRTY"})
        self.assertEqual(result[1][4], "")

        # Verify GraphQL call
        self.assertEqual(mock_run_gh.call_count, 1)
        args, _ = mock_run_gh.call_args
        self.assertIn("graphql", args[0])

        # Verify diff fetch call count
        self.assertEqual(mock_get_diff.call_count, 1)

    @patch("run_merges.run_gh")
    def test_fetch_all_pr_data_parallel_graphql_failure(self, mock_run_gh):
        mock_run_gh.return_value = None

        items = [("owner/repo1", "1", "title1")]
        result = _fetch_all_pr_data_parallel(items)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0][3])
        self.assertEqual(result[0][4], "")

    def test_fetch_all_pr_data_parallel_invalid_reference(self):
        with self.assertRaises(ValueError):
            _fetch_all_pr_data_parallel([("myrepo", "1", "title")])

    @patch("run_merges.subprocess.run")
    @patch("run_merges._fetch_all_pr_data_parallel")
    def test_review_queue_never_merges_without_lifecycle_decisions(
        self, mock_fetch, mock_run
    ):
        items = [("owner/repo", str(n), "routine title") for n in range(1, 5)]
        mock_fetch.return_value = [
            (*items[0], {"mergeStateStatus": "CLEAN"}, "safe-looking diff"),
            (*items[1], {"mergeStateStatus": "CLEAN"}, ""),
            (*items[2], None, ""),
            (*items[3], {"mergeStateStatus": "DIRTY"}, ""),
        ]

        results = review_queue(items)

        mock_fetch.assert_called_once_with(items)
        mock_run.assert_not_called()
        self.assertEqual(results["merged"], [])
        self.assertEqual([entry[1] for entry in results["escalated"]], ["1", "2", "3"])
        self.assertEqual([entry[1] for entry in results["conflicting"]], ["4"])
        self.assertIn("PR diff unavailable.", results["escalated"][1][3])
        self.assertIn("PR state unavailable", results["escalated"][2][3][0])


if __name__ == "__main__":
    unittest.main()
