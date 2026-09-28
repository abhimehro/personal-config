"""Lock merge CI to the full Cursor export-authority gate."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/code-quality.yml"
MAKEFILE = ROOT / "Makefile"
ARTIFACTS = ROOT / "tests/test_pr_lifecycle_artifacts.py"


class TestExportAuthorityMergeGate(unittest.TestCase):
    def test_code_quality_invokes_include_exports(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("--include-exports", text)
        self.assertIn("docs/cursor-automations/**", text)
        self.assertIn("tasks/pr-review-agent.config.yaml", text)

    def test_test_quick_runs_full_export_validator(self) -> None:
        text = MAKEFILE.read_text(encoding="utf-8")
        self.assertIn("--include-exports", text)

    def test_include_exports_patch_is_wrapped(self) -> None:
        for raw in ARTIFACTS.read_text(encoding="utf-8").splitlines():
            if "as gate" in raw:
                self.assertLessEqual(len(raw), 79, raw)

    def test_cli_include_exports_validates_example(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/validate_pr_lifecycle_artifacts.py",
                "tasks/pr-lifecycle-ledger.example.yaml",
                "--include-exports",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PR_LIFECYCLE_VALID", result.stdout)


if __name__ == "__main__":
    unittest.main()
