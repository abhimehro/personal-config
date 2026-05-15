import sys
import types
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import subprocess

# Add scripts directory to path to import the module
scripts_dir = Path(__file__).parent.parent / ".github" / "scripts"
sys.path.append(str(scripts_dir))

# Stub the `yaml` module so this test can run with stdlib only (no pip deps),
# matching the repo convention documented in AGENTS.md / CONTRIBUTING.md.
# `repository_automation_common` imports `yaml` at module load, but the
# functions under test (`run_checked`, `run_process`) do not use YAML at all.
if "yaml" not in sys.modules:
    _yaml = types.ModuleType("yaml")
    _yaml.safe_load = lambda *_a, **_kw: {}
    _yaml.safe_dump = lambda *_a, **_kw: ""
    sys.modules["yaml"] = _yaml

import repository_automation_common
from repository_automation_common import run_checked

class TestRunChecked(unittest.TestCase):
    @patch("repository_automation_common.run_process")
    def test_run_checked_calls_run_process_with_check_true(self, mock_run_process):
        # Setup
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_run_process.return_value = mock_result
        command = ["echo", "hello"]

        # Execution
        result = run_checked(command)

        # Assertion
        mock_run_process.assert_called_once_with(command, check=True)
        self.assertEqual(result, mock_result)

    @patch("repository_automation_common.subprocess.run")
    def test_run_checked_integration_with_subprocess(self, mock_subprocess_run):
        # We can also mock subprocess.run to verify the entire chain
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_subprocess_run.return_value = mock_result
        command = ["ls", "-l"]

        # Capture expected env before execution to avoid spurious failures if
        # os.environ is mutated between execution and assertion.
        expected_env = repository_automation_common.command_env()

        # Execution
        result = run_checked(command)

        # Assertion
        mock_subprocess_run.assert_called_once_with(
            command,
            cwd=repository_automation_common.ROOT,
            check=True,
            capture_output=True,
            text=True,
            input=None,
            timeout=None,
            env=expected_env,
        )
        self.assertEqual(result, mock_result)

if __name__ == "__main__":
    unittest.main()
