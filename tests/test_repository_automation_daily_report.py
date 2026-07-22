import os
import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch

# Stub out the optional third-party `yaml` dependency so this test remains
# stdlib-only (per AGENTS.md / CONTRIBUTING.md: tests must not require pip
# installs). `repository_automation_common` imports `yaml` at module load
# time, but `run_daily_status_report` itself does not use it.
sys.modules.setdefault("yaml", MagicMock())

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".github/scripts",
    )
)

from repository_automation_tasks import run_daily_status_report


class TestRunDailyStatusReport(TestCase):
    def setUp(self):
        self.mock_load_results = patch("repository_automation_tasks.load_task_results").start()
        self.mock_iso_day = patch("repository_automation_tasks.iso_day").start()
        self.mock_report_lines = patch("repository_automation_tasks.daily_report_lines").start()
        self.mock_append = patch("repository_automation_tasks.append_publication_result").start()
        self.mock_write = patch("repository_automation_tasks.write_result").start()
        self.mock_overall_status = patch("repository_automation_tasks.overall_status").start()
        self.addCleanup(patch.stopall)

    def test_run_daily_status_report_success(self):
        self.mock_load_results.return_value = [{"task": "foo", "status": "success"}]
        self.mock_iso_day.return_value = "2023-10-27"
        self.mock_report_lines.return_value = ["line 1", "line 2"]
        self.mock_append.return_value = ("appended body", "http://issue/1", None)
        self.mock_write.return_value = {"status": "success"}
        self.mock_overall_status.return_value = "success"

        config = {
            "reporting": {"daily_issue_prefix": "[test-prefix]"},
            "status_report": {"labels": ["l1", "l2"]},
        }
        result = run_daily_status_report(config)

        self.mock_load_results.assert_called_once()
        self.mock_append.assert_called_once_with(
            "line 1\nline 2",
            title="[test-prefix] - 2023-10-27",
            labels=["l1", "l2"],
            noun="daily issue",
        )
        self.mock_write.assert_called_once_with(
            "daily-status-report",
            ("success", "Daily automation completed with overall status success."),
            "appended body",
            {
                "issue_url": "http://issue/1",
                "task_results": [{"task": "foo", "status": "success"}],
            },
        )
        self.assertEqual(result, {"status": "success"})

    def test_run_daily_status_report_failure(self):
        self.mock_load_results.return_value = [{"task": "foo", "status": "success"}]
        self.mock_iso_day.return_value = "2023-10-27"
        self.mock_report_lines.return_value = ["line 1"]
        self.mock_append.return_value = ("appended body", None, "some error")
        self.mock_write.return_value = {"status": "failure"}
        self.mock_overall_status.return_value = "success"

        result = run_daily_status_report({})
        self.mock_write.assert_called_once_with(
            "daily-status-report",
            ("failure", "Daily automation completed with overall status success."),
            "appended body",
            {"issue_url": None, "task_results": [{"task": "foo", "status": "success"}]},
        )
        self.assertEqual(result, {"status": "failure"})
