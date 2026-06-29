"""Unit tests for scratch_triage (salvages #992)."""

import subprocess
import sys
import unittest
from unittest.mock import patch

# Repo root on path so scratch_triage imports without package layout.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

import scratch_triage  # noqa: E402


class TestProcessPrGroup(unittest.TestCase):
    def test_process_pr_group_multiple_matches(self):
        matches = [
            {"number": 100, "title": "fix: A"},
            {"number": 105, "title": "fix: B"},
            {"number": 102, "title": "fix: C"},
        ]
        groups = []
        scratch_triage._process_pr_group(matches, "my-repo", "my-rationale", groups)

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group["repo"], "my-repo")
        self.assertEqual(group["rationale"], "my-rationale")
        self.assertEqual(group["keep"]["number"], 105)
        self.assertEqual(group["keep"].get("status_action"), "KEEP")

        self.assertEqual(len(group["dups"]), 2)
        dup_nums = [d["number"] for d in group["dups"]]
        self.assertEqual(dup_nums, [102, 100])
        for d in group["dups"]:
            self.assertEqual(d.get("status_action"), "CLOSE")

    def test_process_pr_group_single_match(self):
        matches = [{"number": 100, "title": "fix: A"}]
        groups = []
        scratch_triage._process_pr_group(matches, "my-repo", "my-rationale", groups)
        self.assertEqual(len(groups), 0)
        self.assertNotIn("status_action", matches[0])

    def test_process_pr_group_no_matches(self):
        matches = []
        groups = []
        scratch_triage._process_pr_group(matches, "my-repo", "my-rationale", groups)
        self.assertEqual(len(groups), 0)


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


if __name__ == "__main__":
    unittest.main()
