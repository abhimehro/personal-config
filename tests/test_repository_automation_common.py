import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

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
            check=kwargs.get("check", False),
            capture_output=True,
            text=True,
            input=kwargs.get("input_text", None),
            timeout=kwargs.get("timeout", None),
            env=rac.command_env(),
        )

    @patch("subprocess.run")
    def test_run_process_scenarios(self, mock_run):
        # Basic scenario
        self._assert_mock_run(mock_run, ["echo", "hello"])

        mock_run.reset_mock()

        # Scenario with extra args
        self._assert_mock_run(
            mock_run, ["cat"], input_text="hello world", timeout=10, check=True
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


class TestActionRefPinning(unittest.TestCase):
    """Lesson 0z / supply-chain: never treat commit SHAs as version numbers."""

    CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"

    def test_is_commit_sha(self):
        self.assertTrue(rac.is_commit_sha(self.CHECKOUT_SHA))
        self.assertFalse(rac.is_commit_sha("v7.0.1"))
        self.assertFalse(rac.is_commit_sha("3d3c42e"))  # short SHA

    def test_numeric_version_ignores_commit_sha(self):
        # Regression: VERSION_PATTERN used to match hex digits inside SHAs
        # (e.g. leading "3"), which made SHA pins look older than tag v7.
        self.assertIsNone(rac.numeric_version(self.CHECKOUT_SHA))
        self.assertEqual(rac.numeric_version("v7.0.1"), (7, 0, 1))

    def test_target_ref_does_not_unpin_matching_sha(self):
        self.assertIsNone(
            rac.target_ref(self.CHECKOUT_SHA, "v7.0.1", version_hint="v7.0.1")
        )

    def test_target_ref_allows_sha_bump_when_hint_older(self):
        self.assertEqual(
            rac.target_ref(self.CHECKOUT_SHA, "v8.0.0", version_hint="v7.0.1"),
            "v8.0.0",
        )

    def test_target_ref_tag_to_newer_tag_name(self):
        # Caller must still resolve this tag name to a commit SHA before writing.
        self.assertEqual(rac.target_ref("v4", "v5.0.0"), "v5.0.0")


if __name__ == "__main__":
    unittest.main()
