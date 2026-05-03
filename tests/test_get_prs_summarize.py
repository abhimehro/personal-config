#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

# Add scripts directory to path to import the module
REPO_ROOT = Path(__file__).parent.parent
sys.path.append(str(REPO_ROOT / "scripts"))

from get_prs_summarize import check_summary

class TestCheckSummary(unittest.TestCase):
    def test_none_rollup(self):
        self.assertEqual(check_summary(None), "NO_CHECKS")

    def test_empty_rollup(self):
        self.assertEqual(check_summary([]), "NO_CHECKS")

    def test_all_completed_ok(self):
        rollup = [
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "COMPLETED", "conclusion": "NEUTRAL"},
            {"status": "completed", "conclusion": "success"}, # case insensitive check
        ]
        self.assertEqual(check_summary(rollup), "COMPLETED_OK")

    def test_pending_only(self):
        rollup = [
            {"status": "IN_PROGRESS"},
            {"status": "QUEUED"},
            {"status": ""},
        ]
        self.assertEqual(check_summary(rollup), "PENDING_3")

    def test_failed_only(self):
        rollup = [
            {"status": "COMPLETED", "conclusion": "FAILURE"},
            {"status": "COMPLETED", "conclusion": "TIMED_OUT"},
            {"status": "COMPLETED", "conclusion": "ACTION_REQUIRED"},
            {"status": "COMPLETED", "conclusion": "CANCELLED"},
            {"status": "COMPLETED", "conclusion": "STARTUP_FAILURE"},
        ]
        self.assertEqual(check_summary(rollup), "FAIL_5")

    def test_mixed_pending_and_failed(self):
        rollup = [
            {"status": "IN_PROGRESS"},
            {"status": "COMPLETED", "conclusion": "FAILURE"},
            {"status": "QUEUED"},
        ]
        self.assertEqual(check_summary(rollup), "PENDING_2+FAIL_1")

    def test_mixed_all_three(self):
        rollup = [
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "IN_PROGRESS"},
            {"status": "COMPLETED", "conclusion": "FAILURE"},
        ]
        self.assertEqual(check_summary(rollup), "PENDING_1+FAIL_1")

    def test_missing_keys(self):
        # missing status defaults to "", which is not COMPLETED -> pending
        # missing conclusion defaults to "", which is not in FAIL_CONCLUSIONS
        rollup = [
            {}, # pending
            {"status": "COMPLETED"}, # not failed, OK
        ]
        self.assertEqual(check_summary(rollup), "PENDING_1")

    def test_conclusion_case_insensitive(self):
        rollup = [
            {"status": "COMPLETED", "conclusion": "failure"},
        ]
        self.assertEqual(check_summary(rollup), "FAIL_1")

if __name__ == "__main__":
    unittest.main()
