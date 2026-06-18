import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import generate_report


class TestGenerateReport(unittest.TestCase):
    def test_process_draft_fixes(self):
        results = {
            "merged": [("repo1", "1", "title1")],
            "escalated": [
                ("repo2", "2", "title2", "reason1"),
                ("repo1", "3", "title3", "reason2"),
            ],
        }
        draft_fixes = ["repo1#3"]

        updated_results = generate_report.process_draft_fixes(results, draft_fixes)

        self.assertEqual(len(updated_results["merged"]), 2)
        self.assertEqual(updated_results["merged"][1], ("repo1", "3", "title3"))

        self.assertEqual(len(updated_results["escalated"]), 1)
        self.assertEqual(updated_results["escalated"][0][1], "2")

    def test_format_lists(self):
        merged_data = [("repo1", "123", "Fix issue")]
        closed_data = ["repo1#456"]
        escalated_data = ["repo2#789 (Merge Conflict)"]

        merged_str, closed_str, escalated_str = generate_report.format_lists(
            merged_data, closed_data, escalated_data
        )

        self.assertIn(
            "- [#123](https://github.com/repo1/pull/123) in `repo1`: Fix issue",
            merged_str,
        )
        self.assertIn("- [repo1#456](https://github.com/repo1/pull/456)", closed_str)
        self.assertIn(
            "- [repo2#789](https://github.com/repo2/pull/789) - (Merge Conflict)",
            escalated_str,
        )

    def test_generate_report_content(self):
        results = {"merged": [("repo", "1", "title")], "escalated": []}
        closed_data = ["repo#2"]
        escalated_data = ["repo#3 (Error)"]

        # Override the REPORT_TEMPLATE temporarily to avoid testing the full markdown content string
        generate_report.REPORT_TEMPLATE = "Merged: {merged_count}, Closed: {closed_count}, Escalated: {escalated_count}\n{merged_list}\n{closed_list}\n{escalated_list}"

        content = generate_report.generate_report_content(
            results, closed_data, escalated_data
        )

        self.assertIn("Merged: 1, Closed: 1, Escalated: 1", content)
        self.assertIn("[#1]", content)
        self.assertIn("[repo#2]", content)
        self.assertIn("[repo#3]", content)

    def test_format_lists_missing_fields(self):
        # Missing title in merged_data tuple triggers unpacking ValueError
        merged_data = [("repo1", "123")]
        with self.assertRaises(ValueError):
            generate_report.format_lists(merged_data, [], [])


if __name__ == "__main__":
    unittest.main()
