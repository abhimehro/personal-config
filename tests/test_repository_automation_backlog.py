import os
import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch

# Stub out the optional third-party `yaml` dependency so this test remains
# stdlib-only (per AGENTS.md / CONTRIBUTING.md: tests must not require pip
# installs). `repository_automation_common` imports `yaml` at module load
# time, but `run_backlog_manager` itself does not use it.
sys.modules.setdefault("yaml", MagicMock())

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".github/scripts",
    )
)

from repository_automation_tasks import run_backlog_manager


class TestRunBacklogManager(TestCase):
    @patch("repository_automation_tasks.write_result")
    @patch("repository_automation_tasks.now_utc")
    @patch("repository_automation_tasks._fetch_backlog_items")
    def test_run_backlog_manager_success(self, mock_fetch, mock_now_utc, mock_write_result):
        from datetime import datetime, timezone

        mock_now_utc.return_value = datetime(2023, 10, 15, tzinfo=timezone.utc)
        issues = [
            {"number": 1, "title": "Issue 1", "updatedAt": "2023-10-10T00:00:00Z", "url": "url1"}
        ]
        prs = [
            {
                "number": 10,
                "title": "PR 1",
                "updatedAt": "2023-10-12T00:00:00Z",
                "url": "url2",
                "isDraft": False,
            }
        ]
        mock_fetch.return_value = (issues, prs)
        mock_write_result.return_value = {"status": "success"}

        config = {"backlog_manager": {"stale_days": 14}}
        result = run_backlog_manager(config)

        mock_write_result.assert_called_once()
        args, _kwargs = mock_write_result.call_args
        self.assertEqual(args[0], "backlog-manager")
        self.assertEqual(args[1][0], "success")
        self.assertIn("found 1 open issues and 1 open PRs", args[1][1])
        self.assertEqual(result, {"status": "success"})

    @patch("repository_automation_tasks.write_result")
    @patch("repository_automation_tasks.now_utc")
    @patch("repository_automation_tasks._fetch_backlog_items")
    def test_run_backlog_manager_warning(self, mock_fetch, mock_now_utc, mock_write_result):
        from datetime import datetime, timezone

        mock_now_utc.return_value = datetime(2023, 10, 15, tzinfo=timezone.utc)
        issues = [
            {"number": 1, "title": "Old Issue", "updatedAt": "2023-09-01T00:00:00Z", "url": "url1"}
        ]
        prs = [
            {
                "number": 10,
                "title": "Old PR",
                "updatedAt": "2023-09-15T00:00:00Z",
                "url": "url2",
                "isDraft": False,
            }
        ]
        mock_fetch.return_value = (issues, prs)
        mock_write_result.return_value = {"status": "success"}

        config = {"backlog_manager": {"stale_days": 14}}
        result = run_backlog_manager(config)

        mock_write_result.assert_called_once()
        args, _kwargs = mock_write_result.call_args
        self.assertEqual(args[0], "backlog-manager")
        self.assertEqual(args[1][0], "warning")
        body = args[2]
        self.assertIn("## Human review candidates", body)
        self.assertIn("- Issue #1 has been quiet for", body)
        self.assertIn("- PR #10 has been quiet for", body)
        data = args[3]
        self.assertEqual(len(data["stale_issues"]), 1)
        self.assertEqual(len(data["stale_pull_requests"]), 1)
        self.assertEqual(result, {"status": "success"})
