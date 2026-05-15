import unittest
import sys
import os

# Ensure the project root is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scratch_inventory import get_category

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
        self.assertEqual(get_category("Implement dark mode", "feature/dark-mode"), "FEATURE")
        self.assertEqual(get_category("", ""), "FEATURE")

if __name__ == '__main__':
    unittest.main()
