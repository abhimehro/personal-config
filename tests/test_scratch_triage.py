"""Unit tests for scratch_triage.run_cmd (salvages #992)."""

import subprocess
import sys
import unittest
from unittest.mock import patch

# Repo root on path so scratch_triage imports without package layout.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

import scratch_triage  # noqa: E402


class TestRunCmd(unittest.TestCase):
    @patch("scratch_triage.subprocess.run")
    def test_run_cmd_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout='{"ok": true}', stderr=""
        )
        ok, out, err = scratch_triage.run_cmd(["gh", "version"])
        self.assertTrue(ok)
        self.assertEqual(out, '{"ok": true}')
        self.assertEqual(err, "")
        mock_run.assert_called_once_with(
            ["gh", "version"], capture_output=True, text=True
        )

    @patch("scratch_triage.subprocess.run")
    def test_run_cmd_failure(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["gh"], returncode=1, stdout="", stderr="not found"
        )
        ok, out, err = scratch_triage.run_cmd(["gh", "missing"])
        self.assertFalse(ok)
        self.assertEqual(out, "")
        self.assertEqual(err, "not found")



class TestFindMatchingPRs(unittest.TestCase):
    def setUp(self):
        self.prs = [
            {"repo": "repo1", "title": "Fix bug 1", "number": 1},
            {"repo": "repo1", "title": "Update README", "number": 2},
            {"repo": "repo2", "title": "Fix bug 2", "number": 3},
            {"repo": "repo1", "title_lower": "some pre-lowered title", "title": "SOME PRE-LOWERED TITLE", "number": 4},
        ]

    def test_match_single_keyword(self):
        matches = scratch_triage._find_matching_prs(self.prs, "repo1", ["bug"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["number"], 1)

    def test_match_multiple_keywords(self):
        matches = scratch_triage._find_matching_prs(self.prs, "repo1", ["fix", "bug"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["number"], 1)

    def test_wrong_repo(self):
        matches = scratch_triage._find_matching_prs(self.prs, "repo1", ["bug 2"])
        self.assertEqual(len(matches), 0)

    def test_title_lower_fallback(self):
        matches = scratch_triage._find_matching_prs(self.prs, "repo1", ["pre-lowered"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["number"], 4)

    def test_empty_keywords(self):
        matches = scratch_triage._find_matching_prs(self.prs, "repo1", [])
        self.assertEqual(len(matches), 3)

if __name__ == "__main__":
    unittest.main()
