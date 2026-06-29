import importlib.util
import sys
import unittest
from pathlib import Path

# Load the script dynamically because it has hyphens in its name
project_root = Path(__file__).resolve().parent.parent
script_path = project_root / "adguard" / "scripts" / "test-adguard-import.py"

spec = importlib.util.spec_from_file_location("adguard_script_test", script_path)
test_adguard_import = importlib.util.module_from_spec(spec)
sys.modules["adguard_script_test"] = test_adguard_import
spec.loader.exec_module(test_adguard_import)


class TestValidateLine(unittest.TestCase):

    def test_empty_line(self):
        is_valid, msg = test_adguard_import.validate_line("", 1, "denylist")
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

        is_valid, msg = test_adguard_import.validate_line("   \n", 2, "allowlist")
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

    def test_comment_line(self):
        is_valid, msg = test_adguard_import.validate_line("# This is a comment", 1, "denylist")
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

        is_valid, msg = test_adguard_import.validate_line("  # Indented comment", 2, "allowlist")
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

    def test_denylist_valid(self):
        is_valid, msg = test_adguard_import.validate_line("example.com", 1, "denylist")
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

    def test_denylist_invalid(self):
        is_valid, msg = test_adguard_import.validate_line("example", 1, "denylist")
        self.assertFalse(is_valid)
        self.assertEqual(msg, "Line 1: Invalid domain format - 'example'")

        is_valid, msg = test_adguard_import.validate_line("@@example.com", 2, "denylist")
        self.assertFalse(is_valid)
        self.assertEqual(msg, "Line 2: Invalid domain format - '@@example.com'")

    def test_allowlist_valid(self):
        is_valid, msg = test_adguard_import.validate_line("@@example.com", 1, "allowlist")
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

    def test_allowlist_invalid(self):
        is_valid, msg = test_adguard_import.validate_line("example.com", 1, "allowlist")
        self.assertFalse(is_valid)
        self.assertEqual(msg, "Line 1: Invalid allowlist format - 'example.com'")

        is_valid, msg = test_adguard_import.validate_line("@@example", 2, "allowlist")
        self.assertFalse(is_valid)
        self.assertEqual(msg, "Line 2: Invalid allowlist format - '@@example'")

    def test_unknown_format(self):
        is_valid, msg = test_adguard_import.validate_line("example.com", 1, "unknown_type")
        self.assertFalse(is_valid)
        self.assertEqual(msg, "Line 1: Unknown format - 'example.com'")


class TestCountLineTypes(unittest.TestCase):

    def _assert_stats_and_issues(self, stats, issues, expected_issues):
        self.assertEqual(stats["total"], 6)
        self.assertEqual(stats["comments"], 1)
        self.assertEqual(stats["empty"], 1)
        self.assertEqual(stats["valid"], 2)
        self.assertEqual(stats["invalid"], 2)

        self.assertEqual(len(issues), len(expected_issues))
        for i, expected_issue in enumerate(expected_issues):
            self.assertEqual(issues[i], expected_issue)

    def test_denylist_counts(self):
        lines = [
            "# Header comment",
            "",
            "example.com",
            "test.com",
            "invalid_domain",
            "@@not-allowed.com"
        ]
        stats, issues = test_adguard_import.count_line_types(lines, "denylist")

        expected_issues = [
            "Line 5: Invalid domain format - 'invalid_domain'",
            "Line 6: Invalid domain format - '@@not-allowed.com'"
        ]
        self._assert_stats_and_issues(stats, issues, expected_issues)

    def test_allowlist_counts(self):
        lines = [
            "# Allowlist header",
            "   \n",
            "@@example.com",
            "@@test.com",
            "example.com",
            "@@invalid"
        ]
        stats, issues = test_adguard_import.count_line_types(lines, "allowlist")

        expected_issues = [
            "Line 5: Invalid allowlist format - 'example.com'",
            "Line 6: Invalid allowlist format - '@@invalid'"
        ]
        self._assert_stats_and_issues(stats, issues, expected_issues)

    def test_empty_list(self):
        lines = []
        stats, issues = test_adguard_import.count_line_types(lines, "denylist")

        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["comments"], 0)
        self.assertEqual(stats["empty"], 0)
        self.assertEqual(stats["valid"], 0)
        self.assertEqual(stats["invalid"], 0)
        self.assertEqual(len(issues), 0)


if __name__ == "__main__":
    unittest.main()
