import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.github/scripts'))

from repository_automation_tasks import configured_commands

class TestRepositoryAutomationTasks(unittest.TestCase):
    def test_configured_commands_all_keys_present(self):
        section = {
            "setup_commands": [{"run": "setup1"}],
            "commands": [{"run": "cmd1"}, {"run": "cmd2"}],
            "security_commands": [{"run": "sec1"}]
        }
        expected = [
            ("setup", {"run": "setup1"}),
            ("command", {"run": "cmd1"}),
            ("command", {"run": "cmd2"}),
            ("security", {"run": "sec1"})
        ]
        self.assertEqual(configured_commands(section), expected)

    def test_configured_commands_missing_keys(self):
        section = {
            "commands": [{"run": "cmd1"}]
        }
        expected = [
            ("command", {"run": "cmd1"})
        ]
        self.assertEqual(configured_commands(section), expected)

    def test_configured_commands_empty_section(self):
        self.assertEqual(configured_commands({}), [])

    def test_configured_commands_ignore_extra_keys(self):
        section = {
            "commands": [{"run": "cmd1"}],
            "other_commands": [{"run": "other"}]
        }
        expected = [
            ("command", {"run": "cmd1"})
        ]
        self.assertEqual(configured_commands(section), expected)

if __name__ == '__main__':
    unittest.main()
