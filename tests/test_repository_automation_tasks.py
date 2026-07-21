import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Stub out the optional third-party `yaml` dependency so this test remains
# stdlib-only (per AGENTS.md / CONTRIBUTING.md: tests must not require pip
# installs). `repository_automation_common` imports `yaml` at module load
# time, but `configured_commands` itself does not use it.
sys.modules.setdefault("yaml", MagicMock())

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".github/scripts",
    )
)

from repository_automation_tasks import (  # noqa: E402
    apply_workflow_updates,
    configured_commands,
    execute_configured_commands,
    run_command_set,
    run_quality_assurance,
    run_safe_adjustment_commands,
    run_weekly_retrospective,
)


class TestRepositoryAutomationTasks(unittest.TestCase):
    def test_configured_commands_all_keys_present(self):
        section = {
            "setup_commands": [{"run": "setup1"}],
            "commands": [{"run": "cmd1"}, {"run": "cmd2"}],
            "security_commands": [{"run": "sec1"}],
        }
        expected = [
            ("setup", {"run": "setup1"}),
            ("command", {"run": "cmd1"}),
            ("command", {"run": "cmd2"}),
            ("security", {"run": "sec1"}),
        ]
        self.assertEqual(configured_commands(section), expected)

    def test_configured_commands_missing_keys(self):
        section = {"commands": [{"run": "cmd1"}]}
        expected = [("command", {"run": "cmd1"})]
        self.assertEqual(configured_commands(section), expected)

    def test_configured_commands_empty_section(self):
        self.assertEqual(configured_commands({}), [])

    def test_configured_commands_ignore_extra_keys(self):
        section = {"commands": [{"run": "cmd1"}], "other_commands": [{"run": "other"}]}
        expected = [("command", {"run": "cmd1"})]
        self.assertEqual(configured_commands(section), expected)


class TestApplyWorkflowUpdates(unittest.TestCase):
    """Regression tests for apply_workflow_updates (cascading str.replace fix)."""

    def _make_plan(self, text, replacements):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
        tmp.write(text)
        tmp.close()
        path = Path(tmp.name)
        return {"path": path, "text": text, "replacements": replacements}

    def test_no_cascade_when_old_is_substring_of_new(self):
        text = (
            "uses: actions/upload-artifact@v7\n"
            "uses: actions/upload-artifact@v7\n"
            "uses: actions/upload-artifact@v7\n"
        )
        replacements = [
            {
                "old": "uses: actions/upload-artifact@v7",
                "new": "uses: actions/upload-artifact@v7.0.1",
            },
            {
                "old": "uses: actions/upload-artifact@v7",
                "new": "uses: actions/upload-artifact@v7.0.1",
            },
            {
                "old": "uses: actions/upload-artifact@v7",
                "new": "uses: actions/upload-artifact@v7.0.1",
            },
        ]
        plan = self._make_plan(text, replacements)
        apply_workflow_updates([plan])
        result = plan["path"].read_text()
        plan["path"].unlink()
        self.assertNotIn("v7.0.1.0.1", result)
        self.assertEqual(result.count("actions/upload-artifact@v7.0.1"), 3)

    def test_distinct_replacements_still_applied(self):
        text = "uses: actions/checkout@v3\n" "uses: actions/upload-artifact@v4\n"
        replacements = [
            {"old": "uses: actions/checkout@v3", "new": "uses: actions/checkout@v4"},
            {
                "old": "uses: actions/upload-artifact@v4",
                "new": "uses: actions/upload-artifact@v5",
            },
        ]
        plan = self._make_plan(text, replacements)
        apply_workflow_updates([plan])
        result = plan["path"].read_text()
        plan["path"].unlink()
        self.assertIn("actions/checkout@v4", result)
        self.assertIn("actions/upload-artifact@v5", result)


class TestRunSafeAdjustmentCommands(unittest.TestCase):
    def setUp(self):
        self.section = {
            "auto_apply_safe_changes": True,
            "safe_adjustment_commands": [{"name": "cmd", "run": "echo 1"}],
        }

    @patch("repository_automation_tasks.writes_allowed", return_value=False)
    def test_writes_not_allowed(self, _mock_writes_allowed):
        result, url = run_safe_adjustment_commands({"auto_apply_safe_changes": True})
        self.assertEqual((result, url), ([], ""))

    @patch("repository_automation_tasks.writes_allowed", return_value=True)
    def test_auto_apply_disabled(self, _mock_writes_allowed):
        result, url = run_safe_adjustment_commands({"auto_apply_safe_changes": False})
        self.assertEqual((result, url), ([], ""))

    @patch("repository_automation_tasks.git_output", return_value="")
    @patch("repository_automation_tasks.run_shell_command", return_value={"exit_code": 0})
    @patch("repository_automation_tasks.writes_allowed", return_value=True)
    def test_no_changes(self, _mock_writes_allowed, _mock_run_shell_command, _mock_git_output):
        result, url = run_safe_adjustment_commands(self.section)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "cmd")
        self.assertEqual(url, "")

    def test_changes_applied(self):
        with patch.multiple(
            "repository_automation_tasks",
            writes_allowed=MagicMock(return_value=True),
            run_shell_command=MagicMock(return_value={"exit_code": 0}),
            git_output=MagicMock(return_value=" M .github/workflows/main.yml\n"),
            _cached_matches_any=MagicMock(return_value=True),
            create_pr_for_current_changes=MagicMock(return_value="http://pr-url"),
        ):
            result, url = run_safe_adjustment_commands(self.section)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["name"], "cmd")
            self.assertEqual(url, "http://pr-url")


class TestRunQualityAssurance(unittest.TestCase):
    @patch("repository_automation_tasks.run_command_set")
    @patch("repository_automation_tasks.write_result")
    def test_run_quality_assurance_cases(self, mock_write_result, mock_run_command_set):
        cases = [
            (
                "with_config",
                {"quality_assurance": {"commands": [{"run": "echo test"}]}},
                {"commands": [{"run": "echo test"}]},
                [{"cmd": "echo test", "exit": 0}],
            ),
            (
                "default_config",
                {},
                {},
                [],
            ),
        ]

        for name, config, expected_arg, command_results in cases:
            with self.subTest(name=name):
                mock_run_command_set.reset_mock()
                mock_write_result.reset_mock()

                mock_run_command_set.return_value = (
                    "success",
                    "1 passed",
                    {"body": "test output", "command_results": command_results},
                )
                mock_write_result.return_value = {"status": "success"}

                result = run_quality_assurance(config)

                mock_run_command_set.assert_called_once_with(
                    "quality-assurance",
                    expected_arg,
                )
                mock_write_result.assert_called_once_with(
                    "quality-assurance",
                    ("success", "1 passed"),
                    "test output",
                    {"command_results": command_results},
                )
                self.assertEqual(result, {"status": "success"})


class TestExecuteConfiguredCommands(unittest.TestCase):
    @patch("repository_automation_tasks.run_shell_command")
    def test_execute_configured_commands_success(self, mock_run_shell_command):
        mock_run_shell_command.side_effect = lambda cmd, timeout: {
            "exit_code": 0,
            "stdout": f"ran {cmd}",
            "stderr": "",
        }

        section = {
            "setup_commands": [{"name": "Setup A", "run": "setup_a"}],
            "commands": [
                {
                    "name": "Cmd B",
                    "run": "cmd_b",
                    "timeout_seconds": 60,
                    "optional": True,
                }
            ],
        }

        setup_entries, command_entries = execute_configured_commands(section)

        self.assertEqual(len(setup_entries), 1)
        self.assertEqual(setup_entries[0]["name"], "Setup A")
        self.assertEqual(setup_entries[0]["exit_code"], 0)
        self.assertEqual(setup_entries[0]["stdout"], "ran setup_a")
        self.assertEqual(setup_entries[0]["optional"], False)

        self.assertEqual(len(command_entries), 1)
        self.assertEqual(command_entries[0]["name"], "Cmd B")
        self.assertEqual(command_entries[0]["exit_code"], 0)
        self.assertEqual(command_entries[0]["stdout"], "ran cmd_b")
        self.assertEqual(command_entries[0]["optional"], True)

        mock_run_shell_command.assert_any_call("setup_a", 1800)
        mock_run_shell_command.assert_any_call("cmd_b", 60)

    def test_execute_configured_commands_empty(self):
        setup_entries, command_entries = execute_configured_commands({})
        self.assertEqual(setup_entries, [])
        self.assertEqual(command_entries, [])


class TestRunCommandSet(unittest.TestCase):
    def _run_with_mock(self, mock_return):
        with unittest.mock.patch("repository_automation_tasks.execute_configured_commands") as mock_execute:
            mock_execute.return_value = mock_return
            return run_command_set("my-task", {})

    def test_run_command_set_success(self):
        status, summary, data = self._run_with_mock((
            [{"name": "setup1", "exit_code": 0}],
            [{"name": "cmd1", "exit_code": 0}],
        ))
        self.assertEqual(status, "success")
        self.assertEqual(summary, "my-task executed 1 setup commands and 1 validation commands.")
        self.assertIn("## Setup commands", data["body"])
        self.assertNotIn("## Human review required", data["body"])
        self.assertNotIn("## Optional command warnings", data["body"])

    def test_run_command_set_warning(self):
        status, summary, data = self._run_with_mock((
            [],
            [{"name": "cmd1", "exit_code": 1, "optional": True}],
        ))
        self.assertEqual(status, "warning")
        self.assertNotIn("## Human review required", data["body"])
        self.assertIn("## Optional command warnings", data["body"])
        self.assertIn("`cmd1` failed but is configured as optional.", data["body"])

    def test_run_command_set_failure(self):
        status, summary, data = self._run_with_mock((
            [{"name": "setup1", "exit_code": 1}],
            [{"name": "cmd1", "exit_code": 1, "optional": True}],
        ))
        self.assertEqual(status, "failure")
        self.assertIn("## Human review required", data["body"])
        self.assertIn("`setup1` failed and is not marked optional.", data["body"])
        self.assertNotIn("## Optional command warnings", data["body"])


class TestRunWeeklyRetrospective(unittest.TestCase):
    def setUp(self):
        self.mock_recent_daily_runs = patch("repository_automation_tasks.recent_daily_runs").start()
        self.mock_weekly_markers = patch("repository_automation_tasks.weekly_markers").start()
        self.mock_ensure_gh_token = patch("repository_automation_tasks.ensure_gh_token").start()
        self.mock_run_safe_adjustment_commands = patch(
            "repository_automation_tasks.run_safe_adjustment_commands"
        ).start()
        self.mock_weekly_report_lines = patch(
            "repository_automation_tasks.weekly_report_lines"
        ).start()
        self.mock_append_publication_result = patch(
            "repository_automation_tasks.append_publication_result"
        ).start()
        self.mock_write_result = patch("repository_automation_tasks.write_result").start()
        self.addCleanup(patch.stopall)

    def test_run_weekly_retrospective_success(self):
        self.mock_recent_daily_runs.return_value = ["run1", "run2"]
        self.mock_weekly_markers.return_value = ["marker1"]
        self.mock_ensure_gh_token.return_value = True
        self.mock_run_safe_adjustment_commands.return_value = (
            [{"name": "safe_cmd", "exit_code": 0}],
            "http://safe_pr",
        )
        self.mock_weekly_report_lines.return_value = ("success", ["line1", "line2"])
        self.mock_append_publication_result.return_value = (
            "appended_body",
            "http://issue",
            False,
        )
        self.mock_write_result.return_value = {"status": "success"}

        config = {
            "weekly_retrospective": {"labels": ["weekly"]},
            "reporting": {"daily_issue_prefix": "[test] Daily", "weekly_issue_prefix": "[test] Weekly"}
        }

        result = run_weekly_retrospective(config)

        self.mock_recent_daily_runs.assert_called_once()
        self.mock_weekly_markers.assert_called_once_with("[test] Daily")
        self.mock_ensure_gh_token.assert_called_once()
        self.mock_run_safe_adjustment_commands.assert_called_once_with({"labels": ["weekly"]})
        self.mock_weekly_report_lines.assert_called_once_with(
            config,
            ["run1", "run2"],
            ["marker1"],
            [{"name": "safe_cmd", "exit_code": 0}],
            "http://safe_pr",
        )
        self.mock_write_result.assert_called_once()

        self.assertEqual(result, {"status": "success"})

    def test_run_weekly_retrospective_no_gh_token(self):
        self.mock_recent_daily_runs.return_value = ["run1", "run2"]
        self.mock_weekly_markers.return_value = ["marker1"]
        self.mock_ensure_gh_token.return_value = False
        self.mock_weekly_report_lines.return_value = ("success", ["line1", "line2"])
        self.mock_append_publication_result.return_value = (
            "appended_body",
            "http://issue",
            False,
        )
        self.mock_write_result.return_value = {"status": "success"}

        config = {}
        result = run_weekly_retrospective(config)

        self.mock_run_safe_adjustment_commands.assert_not_called()
        self.mock_weekly_report_lines.assert_called_once_with(
            config, ["run1", "run2"], ["marker1"], [], ""
        )
        self.assertEqual(result, {"status": "success"})

    def test_run_weekly_retrospective_publication_error(self):
        self.mock_recent_daily_runs.return_value = ["run1", "run2"]
        self.mock_weekly_markers.return_value = ["marker1"]
        self.mock_ensure_gh_token.return_value = True
        self.mock_run_safe_adjustment_commands.return_value = ([], "")
        self.mock_weekly_report_lines.return_value = ("success", ["line1", "line2"])
        # error returned by append_publication_result is True
        self.mock_append_publication_result.return_value = (
            "appended_body",
            "http://issue",
            True,
        )
        self.mock_write_result.return_value = {"status": "failure"}

        config = {}
        result = run_weekly_retrospective(config)

        # check that write_result is called with status "failure" because error=True
        self.mock_write_result.assert_called_once_with(
            "weekly-retrospective",
            ("failure", "Reviewed 2 daily workflow runs from the last 7 days."),
            "appended_body",
            {"runs": ["run1", "run2"], "issue_url": "http://issue", "safe_pr_url": ""}
        )
        self.assertEqual(result, {"status": "failure"})


if __name__ == "__main__":
    unittest.main()
