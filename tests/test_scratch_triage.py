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


class TestContainsAllKeywords(unittest.TestCase):
    def test_contains_all_present(self):
        title = "bolt optimization: fix dataframe iteration performance"
        kws = ("bolt", "iteration", "performance")
        self.assertTrue(scratch_triage._contains_all_keywords(title, kws))

    def test_missing_one_keyword(self):
        title = "bolt optimization: fix dataframe performance"
        kws = ("bolt", "iteration", "performance")
        self.assertFalse(scratch_triage._contains_all_keywords(title, kws))

    def test_empty_keywords_list(self):
        title = "bolt optimization: fix dataframe iteration performance"
        kws = ()
        self.assertTrue(scratch_triage._contains_all_keywords(title, kws))

    def test_empty_title(self):
        title = ""
        kws = ("bolt", "iteration")
        self.assertFalse(scratch_triage._contains_all_keywords(title, kws))

    def test_partial_match(self):
        title = "bolt optimization: iterate data"
        kws = ("iteration",)
        self.assertFalse(scratch_triage._contains_all_keywords(title, kws))


if __name__ == "__main__":
    unittest.main()
