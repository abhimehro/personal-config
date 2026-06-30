#!/usr/bin/env python3
"""Test script for summary.yml workflow security validation."""

import unittest
from pathlib import Path


class TestSummaryWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        filepath = Path(".github/workflows/summary.yml")
        with open(filepath) as f:
            cls.content = f.read()

        # Extract the specific step block for reuse
        cls.step_start = cls.content.find("- name: Comment with AI summary")
        if cls.step_start != -1:
            next_step = cls.content.find("\n      - name:", cls.step_start + 1)
            step_end = cls.content.find("\n    steps:", cls.step_start + 1)
            if step_end == -1:
                step_end = len(cls.content)
            if next_step != -1 and next_step < step_end:
                step_end = next_step
            cls.step_content = cls.content[cls.step_start : step_end]
        else:
            cls.step_content = ""

        # Extract the specific job block for reuse
        cls.job_start = cls.content.find("summary:")
        if cls.job_start != -1:
            job_end = cls.content.find("\n  steps:", cls.job_start)
            cls.job_content = cls.content[cls.job_start : job_end]
        else:
            cls.job_content = ""

    def test_yaml_parseability(self):
        """Test 1: YAML Parseability (basic check)."""
        self.assertIn(
            "name: Summarize new issues", self.content, "Workflow name not found"
        )
        self.assertIn("jobs:", self.content, "jobs key not found")

    def test_step_exists(self):
        """Test 2: Expected step name and location."""
        self.assertNotEqual(self.step_start, -1, "Could not find step start")
        self.assertIn(
            "Comment with AI summary",
            self.content,
            "Step 'Comment with AI summary' not found",
        )

    def test_env_scope(self):
        """Test 3: Expected env scope."""
        self.assertIn("env:", self.step_content, "No env block in step")
        self.assertIn("RESPONSE:", self.step_content, "RESPONSE not in env")
        self.assertIn("GH_TOKEN:", self.step_content, "GH_TOKEN not in env")
        self.assertIn("ISSUE_NUMBER:", self.step_content, "ISSUE_NUMBER not in env")

    def test_secret_handling(self):
        """Test 4: Secret Handling."""
        self.assertIn(
            "secrets.GITHUB_TOKEN", self.step_content, "secrets.GITHUB_TOKEN not found"
        )

    def test_untrusted_output_binding(self):
        """Test 5: Untrusted Output Binding."""
        self.assertIn(
            "steps.inference.outputs.response",
            self.step_content,
            "steps.inference.outputs.response not found",
        )

    def test_shell_run_block_analysis(self):
        """Tests 6-8: Shell Run Block Analysis."""
        run_start = self.step_content.find("run: |")
        self.assertNotEqual(run_start, -1, "run block not found")

        run_block = self.step_content[run_start:]

        self.assertNotIn("${{", run_block, "Direct interpolation found in run block")
        self.assertIn("$RESPONSE", run_block, "$RESPONSE not used in run block")
        self.assertIn('"$RESPONSE"', run_block, "$RESPONSE not properly quoted")

    def test_token_permissions(self):
        """Test 9: Token Permissions."""
        self.assertNotEqual(self.job_start, -1, "summary job not found")
        self.assertIn("permissions:", self.job_content, "No permissions block in job")
        self.assertIn(
            "issues: write", self.job_content, "issues: write not found in permissions"
        )
        self.assertIn("contents: read", self.job_content, "contents: read not found")
        self.assertNotIn(
            "admin", self.job_content, "Admin permissions found (over-privileged)"
        )


if __name__ == "__main__":
    unittest.main()
