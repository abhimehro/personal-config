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


class TestGroupPRs(unittest.TestCase):
    def test_group_prs_basic(self):
        all_prs = [
            {
                "repo": "personal-config",
                "number": 101,
                "title": "fix eval CWE-78 issue",
                "title_lower": "fix eval cwe-78 issue",
            },
            {
                "repo": "personal-config",
                "number": 100,
                "title": "address cwe-78 with eval",
                "title_lower": "address cwe-78 with eval",
            },
            {
                "repo": "personal-config",
                "number": 102,
                "title": "unrelated",
                "title_lower": "unrelated",
            },
            {
                "repo": "other-repo",
                "number": 103,
                "title": "fix eval cwe-78 issue",
                "title_lower": "fix eval cwe-78 issue",
            },
        ]

        triage_md = ["# Initial Header\n"]
        scratch_triage.group_prs(all_prs, triage_md)

        self.assertEqual(all_prs[0].get("status_action"), "KEEP")
        self.assertEqual(all_prs[1].get("status_action"), "CLOSE")
        self.assertIsNone(all_prs[2].get("status_action"))
        self.assertIsNone(all_prs[3].get("status_action"))

        self.assertEqual(len(triage_md), 2)
        self.assertIn(
            "personal-config **#101** | **#100** | Same CWE-78 eval injection theme; keep newest",
            triage_md[1],
        )

    def test_group_prs_multiple_groups(self):
        all_prs = [
            {
                "repo": "personal-config",
                "number": 201,
                "title": "Palette prompt updates",
                "title_lower": "palette prompt updates",
            },
            {
                "repo": "personal-config",
                "number": 200,
                "title": "Old palette prompt",
                "title_lower": "old palette prompt",
            },
            {
                "repo": "email-security-pipeline",
                "number": 301,
                "title": "empty state layout",
                "title_lower": "empty state layout",
            },
            {
                "repo": "email-security-pipeline",
                "number": 300,
                "title": "empty state visual",
                "title_lower": "empty state visual",
            },
        ]

        triage_md = []
        scratch_triage.group_prs(all_prs, triage_md)

        self.assertEqual(all_prs[0].get("status_action"), "KEEP")
        self.assertEqual(all_prs[1].get("status_action"), "CLOSE")
        self.assertEqual(all_prs[2].get("status_action"), "KEEP")
        self.assertEqual(all_prs[3].get("status_action"), "CLOSE")

        self.assertEqual(len(triage_md), 2)
