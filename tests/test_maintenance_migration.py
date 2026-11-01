"""Regression tests for maintenance containment and notification changes."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CleanupPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # Keep the script's optional config isolated from the developer's config.
        self.scripts = self.root / "maintenance/bin"
        self.scripts.mkdir(parents=True)
        (self.root / "maintenance/conf").mkdir()
        for name in ("quick_cleanup.sh", "system_cleanup.sh"):
            shutil.copy(ROOT / "maintenance/bin" / name, self.scripts / name)
        self.mock("find", '''case "$1" in
  "$HOME"/*) exec /usr/bin/find "$@" ;;
  *) exit "${MOCK_FIND_TEMP_EXIT:-0}" ;;
esac''')
        for name in ("brew", "npm", "pip3", "gem"):
            self.mock(name, 'exit "${MOCK_TOOL_EXIT:-0}"')
        self.mock("terminal-notifier", 'printf "%s\\n" "$*" >> "$NOTICE_LOG"')
        self.env = os.environ.copy()
        self.env.update(HOME=str(self.home), PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                        NOTICE_LOG=str(self.root / "notices"), AUTOMATED_RUN="1", FORCE_RUN="1",
                        ORPHAN_AGENT_APPS="1", TMPDIR=str(self.root))
        self.env.pop("BASH_ENV", None)

    def mock(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def run_cleanup(self, name: str, **env: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(["bash", str(self.scripts / name)], env={**self.env, **env},
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_old_downloads_are_preserved_in_both_cleanups(self) -> None:
        download = self.home / "Downloads/old.txt"
        download.parent.mkdir()
        download.write_text("personal data")
        os.utime(download, (1_000_000_000, 1_000_000_000))
        for script in ("quick_cleanup.sh", "system_cleanup.sh"):
            with self.subTest(script=script):
                self.run_cleanup(script)
                self.assertEqual(download.read_text(), "personal data")

    def test_quick_cleanup_keeps_fish_variables_and_agent_data(self) -> None:
        fish = self.home / ".config/fish/fish_variables"
        fish.parent.mkdir(parents=True)
        fish.write_text("SETUVAR _tide_prompt_999999:old\n")
        backup = fish.with_name("fish_variables.maintenance.bak")
        backup.write_text("prior backup\n")
        agent = self.home / ".windsurf-next/data"
        agent.parent.mkdir()
        agent.write_text("user data")
        self.run_cleanup("quick_cleanup.sh")
        self.assertEqual(fish.read_text(), "SETUVAR _tide_prompt_999999:old\n")
        self.assertEqual(backup.read_text(), "prior backup\n")
        self.assertEqual(agent.read_text(), "user data")

    def test_system_cleanup_notifies_on_failure_but_not_routine_automation(self) -> None:
        self.run_cleanup("system_cleanup.sh")
        notices = self.root / "notices"
        self.assertFalse(notices.exists())
        self.run_cleanup("system_cleanup.sh", MOCK_TOOL_EXIT="1")
        self.assertIn("Completed with warnings", notices.read_text())
        log = self.home / "Library/Logs/maintenance/system_cleanup.log"
        for message in ("Homebrew cleanup failed", "Homebrew autoremove failed", "npm cache verification failed", "pip cache purge", "gem cleanup failed"):
            with self.subTest(message=message):
                self.assertIn(message, log.read_text())

    def test_quick_cleanup_notifies_on_warnings_and_manual_success(self) -> None:
        notices = self.root / "notices"
        self.run_cleanup("quick_cleanup.sh")
        self.assertFalse(notices.exists())
        self.run_cleanup("quick_cleanup.sh", MOCK_FIND_TEMP_EXIT="1")
        self.assertIn("Completed with warnings", notices.read_text())
        notices.unlink()
        self.run_cleanup("quick_cleanup.sh", AUTOMATED_RUN="0")
        self.assertIn("Run completed", notices.read_text())


if __name__ == "__main__":
    unittest.main()
