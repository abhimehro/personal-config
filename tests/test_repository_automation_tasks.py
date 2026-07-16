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
    run_safe_adjustment_commands,
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




from unittest.mock import patch

class TestRunSafeAdjustmentCommands(unittest.TestCase):
    def setUp(self):
        self.section = {
            "auto_apply_safe_changes": True,
            "safe_adjustment_commands": [{"name": "cmd", "run": "echo 1"}],
        }

    @patch("repository_automation_tasks.writes_allowed", return_value=False)
    def test_writes_not_allowed(self, mock_writes):
        res, url = run_safe_adjustment_commands({"auto_apply_safe_changes": True})
        self.assertEqual((res, url), ([], ""))

    @patch("repository_automation_tasks.writes_allowed", return_value=True)
    def test_auto_apply_disabled(self, mock_writes):
        res, url = run_safe_adjustment_commands({"auto_apply_safe_changes": False})
        self.assertEqual((res, url), ([], ""))

    @patch("repository_automation_tasks.writes_allowed", return_value=True)
    @patch("repository_automation_tasks.run_shell_command", return_value={"exit_code": 0})
    @patch("repository_automation_tasks.git_output", return_value="")
    def test_no_changes(self, mock_git, mock_shell, mock_writes):
        res, url = run_safe_adjustment_commands(self.section)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "cmd")
        self.assertEqual(url, "")

    @patch("repository_automation_tasks.writes_allowed", return_value=True)
    @patch("repository_automation_tasks.run_shell_command", return_value={"exit_code": 0})
    @patch("repository_automation_tasks.git_output", return_value=" M .github/workflows/main.yml\n")
    @patch("repository_automation_tasks._cached_matches_any", return_value=True)
    @patch("repository_automation_tasks.create_pr_for_current_changes", return_value="http://pr-url")
    def test_changes_applied(self, mock_pr, mock_matches, mock_git, mock_shell, mock_writes):
        res, url = run_safe_adjustment_commands(self.section)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "cmd")
        self.assertEqual(url, "http://pr-url")

if __name__ == "__main__":
    unittest.main()
