"""Verify PR automation shell scripts avoid sourcing external env files."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_AUTOMATION_SCRIPTS = (
    ROOT / "close_prs.sh",
    ROOT / "close_more.sh",
)


class TestPrAutomationScripts(unittest.TestCase):
    def test_legacy_scripts_do_not_source_external_env_files(self) -> None:
        for script in LEGACY_AUTOMATION_SCRIPTS:
            with self.subTest(script=script.name):
                content = script.read_text(encoding="utf-8")
                self.assertNotRegex(content, r"(?m)^\s*source\s+.*GH_TOKEN\.env")
                self.assertNotRegex(content, r"(?m)^\s*\.\s+.*GH_TOKEN\.env")
                self.assertIn("ensure_gh_token.sh", content)

    def test_fix_drafts_uses_python_loader(self) -> None:
        content = (ROOT / "fix_drafts.sh").read_text(encoding="utf-8")
        self.assertNotRegex(content, r"(?m)^\s*source\s+")
        self.assertNotRegex(content, r"(?m)^\s*\.\s+")
        self.assertNotIn("ensure_gh_token.sh", content)
        self.assertIn("gh_token_env", content)


if __name__ == "__main__":
    unittest.main()
