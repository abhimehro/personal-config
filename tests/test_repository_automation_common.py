import os
import sys
import types
import unittest
from unittest.mock import patch, MagicMock

# Ensure the scripts directory is in the path
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".github",
        "scripts",
    ),
)

# Stub yaml since we don't need it for truncate and it might not be installed
if "yaml" not in sys.modules:
    _yaml = types.ModuleType("yaml")
    sys.modules["yaml"] = _yaml

import repository_automation_common as rac


class TestTruncate(unittest.TestCase):
    def test_truncate_under_limit(self):
        self.assertEqual(rac.truncate("hello", limit=50), "hello")

    def test_truncate_exact_limit(self):
        text = "a" * 50
        self.assertEqual(rac.truncate(text, limit=50), text)

    def test_truncate_over_limit(self):
        text = "a" * 51
        expected = "a" * 34 + "\n... [truncated]"
        result = rac.truncate(text, limit=50)
        self.assertEqual(result, expected)
        # Truncated output must never exceed the requested limit.
        self.assertLessEqual(len(result), 50)

    def test_truncate_empty_text(self):
        self.assertEqual(rac.truncate("", limit=50), "")

    def test_truncate_small_limit(self):
        # When limit is smaller than the suffix, the function must still
        # respect the limit rather than growing the output via negative slicing.
        text = "abcdefghijklmnop"
        result = rac.truncate(text, limit=10)
        self.assertEqual(result, "abcdefghij")
        self.assertLessEqual(len(result), 10)

    def test_truncate_default_limit(self):
        text = "a" * 4001
        expected = "a" * 3984 + "\n... [truncated]"
        result = rac.truncate(text)
        self.assertEqual(result, expected)
        self.assertLessEqual(len(result), 4000)






class TestRunProcess(unittest.TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def _assert_mock_run(self, mock_run, cmd, **kwargs):
        mock_completed = MagicMock()
        mock_run.return_value = mock_completed

        result = rac.run_process(cmd, **kwargs)

        self.assertEqual(result, mock_completed)
        mock_run.assert_called_once_with(
            cmd,
            cwd=rac.ROOT,
            check=kwargs.get('check', False),
            capture_output=True,
            text=True,
            input=kwargs.get('input_text', None),
            timeout=kwargs.get('timeout', None),
            env=rac.command_env(),
        )

    @patch("subprocess.run")
    def test_run_process_scenarios(self, mock_run):
        # Basic scenario
        self._assert_mock_run(mock_run, ["echo", "hello"])

        mock_run.reset_mock()

        # Scenario with extra args
        self._assert_mock_run(
            mock_run,
            ["cat"],
            input_text="hello world",
            timeout=10,
            check=True
        )

    def test_run_process_real(self):
        # Do a real call just to ensure it doesn't crash on a trivial command
        # if the environment is somewhat sane.
        if sys.platform != "win32":
            result = rac.run_process(["echo", "real"])
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "real")


class TestRunShellCommand(unittest.TestCase):
    @patch("repository_automation_common.run_process")
    def test_run_shell_command_basic(self, mock_run_process):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "output\n"
        mock_proc.stderr = "error\n"
        mock_run_process.return_value = mock_proc

        result = rac.run_shell_command("echo hello")

        mock_run_process.assert_called_once_with(
            [rac.BASH_BIN, "-lc", "echo hello"], timeout=1800
        )

        self.assertEqual(result["command"], "echo hello")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], "output\n")
        self.assertEqual(result["stderr"], "error\n")

    @patch("repository_automation_common.run_process")
    def test_run_shell_command_timeout(self, mock_run_process):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "output\n"
        mock_proc.stderr = ""
        mock_run_process.return_value = mock_proc

        result = rac.run_shell_command("sleep 10", timeout=5)

        mock_run_process.assert_called_once_with(
            [rac.BASH_BIN, "-lc", "sleep 10"], timeout=5
        )
        self.assertEqual(result["exit_code"], 0)

    @patch("repository_automation_common.run_process")
    def test_run_shell_command_truncation(self, mock_run_process):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        long_output = "a" * 5000
        mock_proc.stdout = long_output
        mock_proc.stderr = long_output
        mock_run_process.return_value = mock_proc

        result = rac.run_shell_command("echo long")

        self.assertLess(len(result["stdout"]), len(long_output))
        self.assertLess(len(result["stderr"]), len(long_output))
        self.assertTrue(result["stdout"].endswith("... [truncated]"))
        self.assertTrue(result["stderr"].endswith("... [truncated]"))

if __name__ == "__main__":
    unittest.main()
