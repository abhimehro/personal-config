import unittest
import sys
import os
from unittest.mock import patch

import yaml

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".github", "scripts"))
from repository_automation_common import load_config


class TestLoadConfig(unittest.TestCase):
    @patch("repository_automation_common.CONFIG_PATH")
    def test_load_config_valid_with_automation(self, mock_path):
        mock_path.read_text.return_value = "automation:\n  key: value\n"
        self.assertEqual(load_config(), {"key": "value"})

    @patch("repository_automation_common.CONFIG_PATH")
    def test_load_config_valid_without_automation(self, mock_path):
        mock_path.read_text.return_value = "other:\n  key: value\n"
        self.assertEqual(load_config(), {})

    @patch("repository_automation_common.CONFIG_PATH")
    def test_load_config_empty(self, mock_path):
        mock_path.read_text.return_value = ""
        self.assertEqual(load_config(), {})

    @patch("repository_automation_common.CONFIG_PATH")
    def test_load_config_invalid_yaml(self, mock_path):
        mock_path.read_text.return_value = "invalid: yaml: :"
        with self.assertRaises(yaml.YAMLError):
            load_config()


if __name__ == "__main__":
    unittest.main()
