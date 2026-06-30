"""Regression tests for CWE-94 in copilot-setup-steps.yml (ABHI-943).

workflow_dispatch inputs must not be interpolated into github-script ``script:``
blocks as JavaScript string literals. Binding via step ``env:`` and reading
``process.env`` prevents script injection from breaking out of quotes.

Merged fix: PR #980 (commit 4972970). Related: email-security-pipeline#881.
"""


import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github/workflows/copilot-setup-steps.yml"

STEP_MARKER = "- name: Development Partner Session"
VULNERABLE_PATTERN = re.compile(
    r"const\s+request\s*=\s*['\"]\$\{\{\s*github\.event\.inputs\.request\s*\}\}['\"]"
)
INPUT_EXPR = "${{ github.event.inputs.request }}"


class TestCopilotSetupStepsWorkflowSecurity(unittest.TestCase):
    """Static guards for github-script input handling."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_file_exists(self) -> None:
        self.assertTrue(WORKFLOW.is_file())

    def test_development_partner_step_present(self) -> None:
        self.assertIn(STEP_MARKER, self.content)

    def _step_block(self) -> str:
        start = self.content.index(STEP_MARKER)
        next_step = self.content.find("\n      - name:", start + 1)
        end = next_step if next_step != -1 else len(self.content)
        return self.content[start:end]

    def test_request_bound_via_env_not_script_literal(self) -> None:
        block = self._step_block()
        self.assertIn("uses: actions/github-script@", block)
        self.assertIn("env:", block)
        self.assertIn("REQUEST:", block)
        self.assertIn(INPUT_EXPR, block)
        self.assertRegex(block, r"const\s+request\s*=\s*process\.env\.REQUEST")
        self.assertIsNone(
            VULNERABLE_PATTERN.search(block),
            "workflow_dispatch request must not be interpolated into a JS string literal",
        )

    def test_no_input_expression_inside_script_block(self) -> None:
        block = self._step_block()
        script_start = block.index("script: |")
        script_body = block[script_start:]
        self.assertNotIn(
            INPUT_EXPR,
            script_body,
            "github.event.inputs.request must not appear inside script: (env binding only)",
        )

    def test_malicious_payload_would_not_match_safe_pattern(self) -> None:
        """Document attacker payload that the fix neutralizes."""
        payload = "'; require('child_process').execSync('id'); //"
        safe_usage = f"const request = process.env.REQUEST || '';\n// {payload}"
        self.assertIn("process.env.REQUEST", safe_usage)
        self.assertNotRegex(safe_usage, VULNERABLE_PATTERN)


if __name__ == "__main__":
    unittest.main()
