import unittest
from unittest.mock import patch
import sys
import os

# Ensure the .github/scripts directory is in the path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".github/scripts"))

import repository_automation_common

class TestRepositoryAutomationCommon(unittest.TestCase):
    @patch("repository_automation_common.gh_json")
    def test_mcp_json(self, mock_gh_json):
        mock_gh_json.return_value = {"success": True}

        args = ["pr", "view", "123", "--json", "title"]
        default_val = {"error": "fallback"}

        result = repository_automation_common.mcp_json(args, default=default_val)

        mock_gh_json.assert_called_once_with(args, default_val)
        self.assertEqual(result, {"success": True})

    @patch("repository_automation_common.gh_json")
    def test_mcp_json_no_default(self, mock_gh_json):
        mock_gh_json.return_value = {"success": True}

        args = ["pr", "view", "123", "--json", "title"]

        result = repository_automation_common.mcp_json(args)

        mock_gh_json.assert_called_once_with(args, None)
        self.assertEqual(result, {"success": True})

    @patch("repository_automation_common.gh_text")
    def test_mcp_text(self, mock_gh_text):
        mock_gh_text.return_value = "PR title"

        args = ["pr", "view", "123", "--json", "title", "-t", "{{.title}}"]
        default_val = "fallback_title"

        result = repository_automation_common.mcp_text(args, default=default_val)

        mock_gh_text.assert_called_once_with(args, default_val)
        self.assertEqual(result, "PR title")

    @patch("repository_automation_common.gh_text")
    def test_mcp_text_no_default(self, mock_gh_text):
        mock_gh_text.return_value = "PR title"

        args = ["pr", "view", "123", "--json", "title", "-t", "{{.title}}"]

        result = repository_automation_common.mcp_text(args)

        mock_gh_text.assert_called_once_with(args, "")
        self.assertEqual(result, "PR title")

if __name__ == "__main__":
    unittest.main()
