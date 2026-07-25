"""Verify PR automation shell scripts avoid sourcing token helpers and actually run."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTOMATION_SCRIPTS = (
    ROOT / "close_prs.sh",
    ROOT / "close_more.sh",
    ROOT / "fix_drafts.sh",
    ROOT / "scripts" / "verify_gh_auth.sh",
)


class TestPrAutomationScripts(unittest.TestCase):
    def test_scripts_do_not_source_external_env_files(self) -> None:
        for script in AUTOMATION_SCRIPTS:
            with self.subTest(script=script.name):
                content = script.read_text(encoding="utf-8")
                self.assertNotRegex(content, r"(?m)^\s*source\s+.*GH_TOKEN\.env")
                self.assertNotRegex(content, r"(?m)^\s*\.\s+.*GH_TOKEN\.env")
                self.assertIn("ensure_gh_token.sh", content)

    def test_scripts_do_not_source_any_shell_helper(self) -> None:
        for script in AUTOMATION_SCRIPTS:
            with self.subTest(script=script.name):
                content = script.read_text(encoding="utf-8")
                self.assertNotRegex(content, r"(?m)^\s*source\s")
                self.assertNotRegex(content, r"(?m)^\s*\.\s+\S")

    def test_close_prs_requires_confirmation(self) -> None:
        result = subprocess.run(
            ["bash", str(ROOT / "close_prs.sh")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("--yes", result.stderr)

    def test_close_prs_reaches_pr_close_logic(self) -> None:
        """Stub gh on PATH and prove close_prs.sh runs all twelve closures."""
        tmp = tempfile.mkdtemp()
        try:
            log = Path(tmp) / "gh_calls.log"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            (bin_dir / "gh").write_text(
                "#!/usr/bin/env bash\n"
                f'GH_STUB_LOG="{log}"\n'
                'printf "%s " "gh" >> "$GH_STUB_LOG"\n'
                'for arg in "$@"; do\n'
                '  printf "%s " "$arg" >> "$GH_STUB_LOG"\n'
                "done\n"
                'printf "\\n" >> "$GH_STUB_LOG"\n',
                encoding="utf-8",
            )
            (bin_dir / "gh").chmod(0o755)

            env = os.environ.copy()
            # Prevent Devin /etc/bash_env functions (e.g. `gh`) from shadowing our stub.
            env.pop("BASH_ENV", None)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            env["GH_TOKEN"] = "test-token"

            result = subprocess.run(
                ["bash", str(ROOT / "close_prs.sh"), "--yes"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                env=env,
            )

            if result.returncode != 0 or not log.exists():
                raise AssertionError(
                    f"rc={result.returncode} PATH={env['PATH']!r} "
                    f"BASH_ENV={env.get('BASH_ENV')!r} "
                    f"log_exists={log.exists()}"
                )
            calls = log.read_text(encoding="utf-8")
            self.assertEqual(calls.count("pr close "), 12)
            self.assertIn("pr close 739 --repo abhimehro/personal-config", calls)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
