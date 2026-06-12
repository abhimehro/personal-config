import os
import sys
import unittest

# Ensure the project root is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from unittest.mock import MagicMock, patch

from scratch_inventory import _fetch_repo_prs, generate_markdown, get_category


class TestScratchInventory(unittest.TestCase):
    def test_get_category_security(self):
        # Happy path - standard security keywords
        self.assertEqual(get_category("Fix sentinel issue", "main"), "SECURITY")
        self.assertEqual(get_category("Update security protocol", "main"), "SECURITY")
        self.assertEqual(get_category("Prevent sql injection", "patch"), "SECURITY")
        self.assertEqual(get_category("Fix CWE-79", "main"), "SECURITY")
        self.assertEqual(get_category("Mitigate SSRF", "main"), "SECURITY")
        self.assertEqual(get_category("Upgrade TLS version", "main"), "SECURITY")

        # Edge cases - case insensitivity
        self.assertEqual(get_category("SENTINEL updates", "main"), "SECURITY")

        # Edge cases - branch name matches
        self.assertEqual(get_category("Update", "fix-tls-bug"), "SECURITY")

    def test_get_category_performance(self):
        self.assertEqual(get_category("Bolt optimization", "main"), "PERFORMANCE")
        self.assertEqual(get_category("Improve perf", "main"), "PERFORMANCE")
        self.assertEqual(get_category("Optimize loop", "main"), "PERFORMANCE")

    def test_get_category_ui(self):
        self.assertEqual(get_category("Update palette", "main"), "UI")
        self.assertEqual(get_category("Improve UX", "main"), "UI")
        self.assertEqual(get_category("Fix UI bug", "main"), "UI")

    def test_get_category_ci_infra(self):
        self.assertEqual(get_category("Fix QA tests", "main"), "CI/INFRA")
        self.assertEqual(get_category("Add unit test", "main"), "CI/INFRA")
        self.assertEqual(get_category("Update CI pipeline", "main"), "CI/INFRA")
        self.assertEqual(get_category("Fix infra issues", "main"), "CI/INFRA")
        self.assertEqual(get_category("Update github action", "main"), "CI/INFRA")

    def test_get_category_refactor(self):
        self.assertEqual(get_category("Refactor code", "main"), "REFACTOR")
        self.assertEqual(get_category("Update import paths", "main"), "REFACTOR")
        self.assertEqual(get_category("Clean up old files", "main"), "REFACTOR")

    def test_get_category_feature(self):
        self.assertEqual(get_category("Add new widget", "main"), "FEATURE")
        self.assertEqual(
            get_category("Implement dark mode", "feature/dark-mode"), "FEATURE"
        )
        self.assertEqual(get_category("", ""), "FEATURE")

    def test_generate_markdown_escapes_formula_injection(self):
        prs = [
            {
                "repo": "personal-config",
                "number": 1,
                "author": {"login": "+evil"},
                "headRefName": "=branch",
                "title": '=HYPERLINK("http://evil")',
                "mergeStateStatus": "CLEAN",
                "createdAt": "2026-05-24T00:00:00Z",
            }
        ]
        md = "\n".join(generate_markdown(prs))
        self.assertIn("'+evil", md)
        self.assertIn("'=branch", md)
        self.assertIn("'=HYPERLINK", md)

    @patch("scratch_inventory.subprocess.run")
    def test_fetch_repo_prs_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [
                {
                    "number": 1,
                    "title": "Test PR",
                    "author": {"login": "testuser"},
                    "headRefName": "main",
                    "mergeStateStatus": "CLEAN",
                    "state": "OPEN",
                    "createdAt": "2023-01-01T00:00:00Z",
                }
            ]
        )
        mock_run.return_value = mock_result

        repo = "abhimehro/test-repo"
        prs = _fetch_repo_prs(repo)

        self.assertEqual(len(prs), 1)
        self.assertEqual(prs[0]["repo"], "test-repo")
        self.assertEqual(prs[0]["number"], 1)

        # Verify subprocess.run was called correctly
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertIn("gh", args[0])
        self.assertIn(repo, args[0])
        self.assertEqual(kwargs.get("capture_output"), True)
        self.assertEqual(kwargs.get("text"), True)

    @patch("scratch_inventory.subprocess.run")
    def test_fetch_repo_prs_failure(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Error"
        mock_result.stderr = "Command failed"
        mock_run.return_value = mock_result

        repo = "abhimehro/test-repo"
        prs = _fetch_repo_prs(repo)

        self.assertEqual(prs, [])
        mock_run.assert_called_once()


if __name__ == "__main__":

    unittest.main()
