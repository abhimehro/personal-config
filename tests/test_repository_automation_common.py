import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

scripts_dir = Path(__file__).parent.parent / ".github" / "scripts"
sys.path.append(str(scripts_dir))

if "yaml" not in sys.modules:
    _yaml = types.ModuleType("yaml")
    _yaml.safe_load = lambda *_a, **_kw: {}
    _yaml.safe_dump = lambda *_a, **_kw: ""
    sys.modules["yaml"] = _yaml

import repository_automation_common  # noqa: E402
from repository_automation_common import load_config, run_checked  # noqa: E402


class TestLoadConfig(unittest.TestCase):
    @patch("repository_automation_common.yaml.safe_load")
    @patch("repository_automation_common.CONFIG_PATH")
    def test_load_config_valid_with_automation(self, mock_path, mock_safe_load):
        mock_path.read_text.return_value = "automation:\n  key: value\n"
        mock_safe_load.return_value = {"automation": {"key": "value"}}
        self.assertEqual(load_config(), {"key": "value"})

    @patch("repository_automation_common.yaml.safe_load")
    @patch("repository_automation_common.CONFIG_PATH")
    def test_load_config_valid_without_automation(self, mock_path, mock_safe_load):
        mock_path.read_text.return_value = "other:\n  key: value\n"
        mock_safe_load.return_value = {"other": {"key": "value"}}
        self.assertEqual(load_config(), {})

    @patch("repository_automation_common.yaml.safe_load")
    @patch("repository_automation_common.CONFIG_PATH")
    def test_load_config_empty(self, mock_path, mock_safe_load):
        mock_path.read_text.return_value = ""
        mock_safe_load.return_value = None
        self.assertEqual(load_config(), {})

    @patch("repository_automation_common.yaml.safe_load")
    @patch("repository_automation_common.CONFIG_PATH")
    def test_load_config_invalid_yaml(self, mock_path, mock_safe_load):
        mock_path.read_text.return_value = "invalid: yaml: :"
        mock_safe_load.side_effect = ValueError("bad yaml")
        with self.assertRaises(ValueError):
            load_config()


class TestRunChecked(unittest.TestCase):
    @patch("repository_automation_common.run_process")
    def test_run_checked_calls_run_process_with_check_true(self, mock_run_process):
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_run_process.return_value = mock_result
        command = ["echo", "hello"]

        result = run_checked(command)

        mock_run_process.assert_called_once_with(command, check=True)
        self.assertEqual(result, mock_result)

    @patch("repository_automation_common.subprocess.run")
    def test_run_checked_integration_with_subprocess(self, mock_subprocess_run):
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_subprocess_run.return_value = mock_result
        command = ["ls", "-l"]

        expected_env = repository_automation_common.command_env()

        result = run_checked(command)

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
