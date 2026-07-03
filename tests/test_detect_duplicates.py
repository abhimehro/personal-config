import os
import sys
import unittest
from unittest.mock import patch

# Ensure the project root is in the path so we can import detect_duplicates
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from detect_duplicates import (
    _extract_duplicates_from_groups,
    _generate_duplicate_section,
    _generate_ready_section,
    _generate_superseded_section,
    _group_prs_by_files,
    get_duplicates,
)


class TestDetectDuplicates(unittest.TestCase):
    def test_extract_duplicates_from_groups_multiple_prs(self):
        """Test with multiple PRs touching the same files, should return duplicates (older PRs)."""
        file_groups = {
            ("repoA", ("file1.py", "file2.py")): [
                {"number": 123},
                {"number": 456},
                {"number": 789},
            ]
        }
        duplicates = _extract_duplicates_from_groups(file_groups)
        # Should sort desc (789, 456, 123) and keep the first one, return rest
        self.assertEqual(duplicates, ["repoA#456", "repoA#123"])

    def test_extract_duplicates_from_groups_single_pr(self):
        """Test with a single PR in a group, should return empty list."""
        file_groups = {
            ("repoA", ("file1.py", "file2.py")): [
                {"number": 123},
            ]
        }
        duplicates = _extract_duplicates_from_groups(file_groups)
        self.assertEqual(duplicates, [])

    def test_extract_duplicates_from_groups_empty_input(self):
        """Test with empty file_groups, should return empty list."""
        file_groups = {}
        duplicates = _extract_duplicates_from_groups(file_groups)
        self.assertEqual(duplicates, [])

    def test_extract_duplicates_from_groups_mixed(self):
        """Test with a mix of groups with single and multiple PRs."""
        file_groups = {
            ("repoA", ("file1.py", "file2.py")): [
                {"number": 123},
                {"number": 456},
                {"number": 789},
            ],
            ("repoB", ("file3.py",)): [
                {"number": 101},
            ],
            ("repoC", ("file4.py",)): [
                {"number": 202},
                {"number": 303},
            ],
        }
        duplicates = _extract_duplicates_from_groups(file_groups)
        self.assertEqual(duplicates, ["repoA#456", "repoA#123", "repoC#202"])

    def test_generate_superseded_section(self):
        """Test _generate_superseded_section with matching PRs."""
        ready_prs = ["repoA#123", "repoB#456", "repoC#789"]
        superseded_text = "- repoA#123\nsome other text\nrepoB#456"
        out = _generate_superseded_section(ready_prs, superseded_text)
        self.assertEqual(out, ["## SUPERSEDED", "- repoA#123", "- repoB#456"])

    def test_generate_superseded_section_with_prefix(self):
        """Test _generate_superseded_section where ready PRs already have a dash prefix."""
        ready_prs = ["- repoA#123", "repoB#456"]
        superseded_text = "- repoA#123\nrepoB#456"
        out = _generate_superseded_section(ready_prs, superseded_text)
        self.assertEqual(out, ["## SUPERSEDED", "- repoA#123", "- repoB#456"])

    def test_generate_superseded_section_empty(self):
        """Test _generate_superseded_section with no matches."""
        ready_prs = ["repoA#123"]
        superseded_text = "nothing here"
        out = _generate_superseded_section(ready_prs, superseded_text)
        self.assertEqual(out, ["## SUPERSEDED"])

    def test_generate_superseded_section_empty_input(self):
        """Test _generate_superseded_section with empty inputs."""
        self.assertEqual(_generate_superseded_section([], "text"), ["## SUPERSEDED"])
        self.assertEqual(
            _generate_superseded_section(["repoA#123"], ""), ["## SUPERSEDED"]
        )

    def test_generate_duplicate_section(self):
        """Test _generate_duplicate_section with duplicates."""
        duplicates = ["repoA#123", "repoB#456"]
        out = _generate_duplicate_section(duplicates)
        self.assertEqual(out, ["## DUPLICATE", "- repoA#123", "- repoB#456"])

    def test_generate_duplicate_section_empty(self):
        """Test _generate_duplicate_section with empty duplicates."""
        self.assertEqual(_generate_duplicate_section([]), ["## DUPLICATE"])

    def test_generate_ready_section(self):
        """Test _generate_ready_section filters out duplicates."""
        ready_only = ["repoA#123", "repoB#456", "repoC#789"]
        duplicates = ["repoB#456"]
        out = _generate_ready_section(ready_only, duplicates)
        self.assertEqual(out, ["## READY", "- repoA#123", "- repoC#789"])

    def test_generate_ready_section_empty_ready(self):
        """Test _generate_ready_section with empty ready_only."""
        self.assertEqual(_generate_ready_section([], ["repoA#123"]), ["## READY"])

    def test_generate_ready_section_empty_duplicates(self):
        """Test _generate_ready_section with empty duplicates."""
        ready_only = ["repoA#123"]
        self.assertEqual(
            _generate_ready_section(ready_only, []), ["## READY", "- repoA#123"]
        )

    @patch("detect_duplicates.run_gh")
    def test_group_prs_by_files_happy_path(self, mock_run_gh):
        """Test successful grouping of PRs based on fetched info."""
        # Mock responses from gh api graphql
        mock_run_gh.return_value = {
            "data": {
                "pr0": {
                    "pullRequest": {
                        "number": 1,
                        "title": "PR 1",
                        "files": {
                            "nodes": [{"path": "file1.py"}, {"path": "file2.py"}]
                        },
                    }
                },
                "pr1": {
                    "pullRequest": {
                        "number": 2,
                        "title": "PR 2",
                        "files": {
                            "nodes": [{"path": "file2.py"}, {"path": "file1.py"}]
                        },
                    }
                },
                "pr2": {
                    "pullRequest": {
                        "number": 3,
                        "title": "PR 3",
                        "files": {"nodes": [{"path": "file3.py"}]},
                    }
                },
            }
        }

        ready_only = ["repoA/projectA#1", "repoA/projectA#2", "repoB/projectB#3"]
        file_groups = _group_prs_by_files(ready_only)

        # files should be sorted tuples
        keyA = ("repoA/projectA", ("file1.py", "file2.py"))
        keyB = ("repoB/projectB", ("file3.py",))

        self.assertIn(keyA, file_groups)
        self.assertEqual(len(file_groups[keyA]), 2)
        self.assertEqual({pr["number"] for pr in file_groups[keyA]}, {1, 2})

        self.assertIn(keyB, file_groups)
        self.assertEqual(len(file_groups[keyB]), 1)
        self.assertEqual(file_groups[keyB][0]["number"], 3)

    @patch("detect_duplicates.run_gh")
    def test_group_prs_by_files_empty_input(self, mock_run_gh):
        """Test with empty input list."""
        result = _group_prs_by_files([])
        self.assertEqual(len(result), 0)
        mock_run_gh.assert_not_called()

    @patch("detect_duplicates.run_gh")
    def test_group_prs_by_files_api_failure(self, mock_run_gh):
        """Test when graphql query returns None (e.g., API error)."""
        mock_run_gh.return_value = None
        result = _group_prs_by_files(["repoA/projectA#123"])
        self.assertEqual(len(result), 0)

    @patch("detect_duplicates.run_gh")
    def test_group_prs_by_files_empty_files(self, mock_run_gh):
        """Test when PR has no files."""
        mock_run_gh.return_value = {
            "data": {
                "pr0": {
                    "pullRequest": {
                        "number": 1,
                        "title": "PR 1",
                        "files": {"nodes": []},
                    }
                }
            }
        }
        result = _group_prs_by_files(["repoA/projectA#1"])
        self.assertEqual(len(result), 1)

        key = ("repoA/projectA", ())
        self.assertIn(key, result)
        self.assertEqual(len(result[key]), 1)
        self.assertEqual(result[key][0]["number"], 1)


    @patch("detect_duplicates._extract_duplicates_from_groups")
    @patch("detect_duplicates._group_prs_by_files")
    def test_get_duplicates(self, mock_group, mock_extract):
        mock_group.return_value = {"group1": ["pr1"]}
        mock_extract.return_value = ["dup1", "dup2"]
        ready_only = ["pr1", "pr2"]
        result = get_duplicates(ready_only)
        mock_group.assert_called_once_with(ready_only)
        mock_extract.assert_called_once_with({"group1": ["pr1"]})
        self.assertEqual(result, ["dup1", "dup2"])


if __name__ == "__main__":
    unittest.main()
