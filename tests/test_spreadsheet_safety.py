"""Regression tests for spreadsheet formula injection defenses (CWE-1236)."""

import unittest

from spreadsheet_safety import escape_spreadsheet_formula


class TestSpreadsheetSafety(unittest.TestCase):
    def test_escapes_formula_prefixes(self) -> None:
        cases = (
            ("=1+1", "'=1+1"),
            ("+cmd", "'+cmd"),
            ("-2+3", "'-2+3"),
            ("@SUM(A1)", "'@SUM(A1)"),
            ("\tcmd", "'\tcmd"),
            ("\rcmd", "'\rcmd"),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(escape_spreadsheet_formula(raw), expected)

    def test_leaves_safe_values_unchanged(self) -> None:
        self.assertEqual(escape_spreadsheet_formula("normal title"), "normal title")
        self.assertEqual(escape_spreadsheet_formula(""), "")
        self.assertEqual(escape_spreadsheet_formula("feature/foo"), "feature/foo")

    def test_malicious_pr_title_vector(self) -> None:
        malicious = '=HYPERLINK("http://evil.example","click")'
        escaped = escape_spreadsheet_formula(malicious)
        self.assertTrue(escaped.startswith("'"))
        self.assertIn("HYPERLINK", escaped)


if __name__ == "__main__":
    unittest.main()
