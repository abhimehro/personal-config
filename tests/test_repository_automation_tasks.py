import os
import sys
import unittest
from unittest.mock import MagicMock

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
    run_command_set,
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
        import tempfile
        from pathlib import Path

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



class TestRunCommandSet(unittest.TestCase):
    @unittest.mock.patch("repository_automation_tasks.execute_configured_commands")
    def test_run_command_set_success(self, mock_execute):
        mock_execute.return_value = (
            [{"name": "setup1", "exit_code": 0}],
            [{"name": "cmd1", "exit_code": 0}],
        )
        status, summary, data = run_command_set("my-task", {})
        self.assertEqual(status, "success")
        self.assertEqual(summary, "my-task executed 1 setup commands and 1 validation commands.")
        self.assertIn("## Setup commands", data["body"])
        self.assertNotIn("## Human review required", data["body"])
        self.assertNotIn("## Optional command warnings", data["body"])

    @unittest.mock.patch("repository_automation_tasks.execute_configured_commands")
    def test_run_command_set_warning(self, mock_execute):
        mock_execute.return_value = (
            [],
            [{"name": "cmd1", "exit_code": 1, "optional": True}],
        )
        status, summary, data = run_command_set("my-task", {})
        self.assertEqual(status, "warning")
        self.assertNotIn("## Human review required", data["body"])
        self.assertIn("## Optional command warnings", data["body"])
        self.assertIn("`cmd1` failed but is configured as optional.", data["body"])

    @unittest.mock.patch("repository_automation_tasks.execute_configured_commands")
    def test_run_command_set_failure(self, mock_execute):
        mock_execute.return_value = (
            [{"name": "setup1", "exit_code": 1}],
            [{"name": "cmd1", "exit_code": 1, "optional": True}],
        )
        status, summary, data = run_command_set("my-task", {})
        self.assertEqual(status, "failure")
        self.assertIn("## Human review required", data["body"])
        self.assertIn("`setup1` failed and is not marked optional.", data["body"])
        self.assertNotIn("## Optional command warnings", data["body"])

if __name__ == "__main__":
    unittest.main()
