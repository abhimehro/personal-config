import unittest
import sys
import os
from unittest.mock import patch

# Ensure the project root is in the path so we can import detect_duplicates
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detect_duplicates import _extract_duplicates_from_groups, _group_prs_by_files

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


    @patch('detect_duplicates.fetch_pr_info')
    def test_group_prs_by_files_happy_path(self, mock_fetch):
        """Test successful grouping of PRs based on fetched info."""
        # Mock returns (repo, info_dict)
        mock_fetch.side_effect = [
            ("repoA", {"number": 1, "files": [{"path": "file1.py"}, {"path": "file2.py"}]}),
            ("repoA", {"number": 2, "files": [{"path": "file2.py"}, {"path": "file1.py"}]}), # Same files, different order
            ("repoB", {"number": 3, "files": [{"path": "file3.py"}]}),
        ]

        ready_only = ["repoA#1", "repoA#2", "repoB#3"]
        file_groups = _group_prs_by_files(ready_only)

        # files should be sorted tuples
        keyA = ("repoA", ("file1.py", "file2.py"))
        keyB = ("repoB", ("file3.py",))

        self.assertIn(keyA, file_groups)
        self.assertEqual(len(file_groups[keyA]), 2)
        self.assertEqual({pr["number"] for pr in file_groups[keyA]}, {1, 2})

        self.assertIn(keyB, file_groups)
        self.assertEqual(len(file_groups[keyB]), 1)
        self.assertEqual(file_groups[keyB][0]["number"], 3)

    @patch('detect_duplicates.fetch_pr_info')
    def test_group_prs_by_files_empty_input(self, mock_fetch):
        """Test with empty input list."""
        file_groups = _group_prs_by_files([])
        self.assertEqual(dict(file_groups), {})
        mock_fetch.assert_not_called()

    @patch('detect_duplicates.fetch_pr_info')
    def test_group_prs_by_files_api_failure(self, mock_fetch):
        """Test when fetch_pr_info returns None (e.g., API error)."""
        mock_fetch.return_value = None

        ready_only = ["repoA#1"]
        file_groups = _group_prs_by_files(ready_only)

        self.assertEqual(dict(file_groups), {})
        mock_fetch.assert_called_once_with("repoA#1")

    @patch('detect_duplicates.fetch_pr_info')
    def test_group_prs_by_files_empty_files(self, mock_fetch):
        """Test when PR has no files."""
        mock_fetch.return_value = ("repoA", {"number": 1, "files": []})

        ready_only = ["repoA#1"]
        file_groups = _group_prs_by_files(ready_only)

        key = ("repoA", ())
        self.assertIn(key, file_groups)
        self.assertEqual(len(file_groups[key]), 1)
        self.assertEqual(file_groups[key][0]["number"], 1)

if __name__ == '__main__':
    unittest.main()
