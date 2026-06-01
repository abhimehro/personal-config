import unittest
import sys
import os

# Ensure the project root is in the path so we can import detect_duplicates
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detect_duplicates import _extract_duplicates_from_groups

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

if __name__ == '__main__':
    unittest.main()
