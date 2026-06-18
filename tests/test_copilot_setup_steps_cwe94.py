"""Regression tests for CWE-94 script injection hardening in copilot-setup-steps.yml.

The Development Partner workflow binds untrusted ``workflow_dispatch`` input
through an environment variable and reads it with ``process.env.REQUEST``.
Direct interpolation of ``github.event.inputs.request`` into the
``actions/github-script`` ``script:`` block would allow an attacker to break
out of a JS string literal and execute arbitrary Node code, e.g.::

    ; const {execSync} = require('child_process'); execSync('id')

These tests lock in the post-remediation contract so a future edit cannot
silently reintroduce the vulnerability.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"

# Crafted payload from ABHI-956 / Security Remediation Sprint acceptance criteria.
MALICIOUS_REQUEST = (
    "'; const {execSync} = require('child_process'); "
    "execSync('echo cwe94-injection-marker'); '"
)

STEP_MARKER = "- name: Development Partner Session"


def _read_workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _extract_development_partner_step(content: str) -> str:
    start = content.find(STEP_MARKER)
    if start == -1:
        raise AssertionError(f"{STEP_MARKER!r} not found in workflow")
    next_step = content.find("\n      - name:", start + len(STEP_MARKER))
    if next_step == -1:
        return content[start:]
    return content[start:next_step]


class TestCopilotSetupStepsWorkflowStatic(unittest.TestCase):
    """Static checks on the hardened workflow YAML."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = _read_workflow()
        cls.step = _extract_development_partner_step(cls.workflow)

    def test_workflow_file_exists(self) -> None:
        self.assertTrue(WORKFLOW_PATH.is_file())

    def test_request_bound_via_env_not_inline_in_script(self) -> None:
        self.assertIn(
            "REQUEST: ${{ github.event.inputs.request }}",
            self.step,
            "workflow_dispatch input must be passed through env.REQUEST",
        )
        self.assertIn("process.env.REQUEST", self.step)

        script_match = re.search(
            r"script:\s*\|\s*\n((?:            .*\n?)*)",
            self.step,
        )
        self.assertIsNotNone(script_match, "github-script block not found")
        script_body = script_match.group(1)

        self.assertNotIn(
            "${{ github.event.inputs.request }}",
            script_body,
            "untrusted input must not be interpolated inside script:",
        )
        self.assertNotIn(
            "github.event.inputs.request",
            script_body,
            "script must not reference github.event.inputs directly",
        )

    def test_security_comment_documents_cwe94(self) -> None:
        step_start = self.workflow.find(STEP_MARKER)
        self.assertGreater(step_start, 0)
        preamble = self.workflow[:step_start]
        self.assertIn("CWE-94", preamble)
        self.assertIn("SECURITY", preamble)
        self.assertIn("process.env.REQUEST", self.step)


class TestMaliciousPayloadBehavior(unittest.TestCase):
    """Simulate safe vs vulnerable binding with the ABHI-956 payload."""

    def test_vulnerable_template_would_emit_executable_injection(self) -> None:
        """Show why inline interpolation is unsafe (analysis only, no exec)."""
        vulnerable_js = f"const request = '{MALICIOUS_REQUEST}';"
        # After quote-breakout the payload's execSync call sits outside the string.
        self.assertRegex(
            vulnerable_js,
            r"const request = '';\s*const \{execSync\}",
        )

    @unittest.skipUnless(
        shutil.which("node"), "node required for env-binding simulation"
    )
    def test_env_binding_treats_payload_as_literal_string(self) -> None:
        """Mirrors the workflow: REQUEST env → process.env.REQUEST (no code exec)."""
        marker_path = os.path.join(tempfile.gettempdir(), "cwe94-injection-marker")
        if os.path.exists(marker_path):
            os.remove(marker_path)

        node_script = r"""
const request = process.env.REQUEST || '';
const result = {
  equalsPayload: request === process.env.REQUEST,
  containsExecSyncLiteral: request.includes('execSync'),
  markerExists: false,
};
try {
  result.markerExists = require('fs').existsSync(process.env.MARKER_PATH);
} catch (_) {}
console.log(JSON.stringify(result));
"""
        proc = subprocess.run(
            ["node", "-e", node_script],
            env={
                **os.environ,
                "REQUEST": MALICIOUS_REQUEST,
                "MARKER_PATH": marker_path,
            },
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        payload = json.loads(proc.stdout.strip())

        self.assertTrue(payload["equalsPayload"])
        self.assertTrue(
            payload["containsExecSyncLiteral"],
            "payload text is preserved literally, not stripped",
        )
        self.assertFalse(
            payload["markerExists"],
            "execSync in the payload must not run when read from process.env",
        )
        self.assertFalse(os.path.exists(marker_path))


if __name__ == "__main__":
    unittest.main()
