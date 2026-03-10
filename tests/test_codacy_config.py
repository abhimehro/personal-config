import fnmatch
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CODACY_CONFIG = REPO_ROOT / ".codacy.yml"


def load_exclude_paths():
    excludes = []
    for line in CODACY_CONFIG.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            excludes.append(stripped[2:].strip("'\""))
    return excludes


class TestCodacyConfig(unittest.TestCase):
    def test_excludes_cover_known_codacy_problem_paths(self):
        exclude_paths = load_exclude_paths()
        required_patterns = {
            "copilot-demo/**",
            "configs/.config/mole/bin/**",
            "configs/.gemini/extensions/context7/docs/**",
            "configs/*.bak",
            "configs/*.rayconfig",
        }
        self.assertTrue(
            required_patterns.issubset(set(exclude_paths)),
            f"Missing expected Codacy exclude patterns: {required_patterns - set(exclude_paths)}",
        )

        problematic_paths = [
            "copilot-demo/weather-assistant.ts",
            "configs/.config/mole/bin/analyze-go",
            "configs/.config/mole/bin/status-go",
            "configs/.gemini/extensions/context7/docs/public/favicon.ico",
            "configs/.gemini/extensions/context7/docs/images/dashboard/manage-cards.png",
            "configs/.zshrc.bak",
            "configs/Raycast_2026-01-26.rayconfig",
        ]

        for path in problematic_paths:
            self.assertTrue(
                any(fnmatch.fnmatch(path, pattern) for pattern in exclude_paths),
                f"{path} is not covered by .codacy.yml exclude_paths",
            )

    def test_tracked_non_utf8_files_are_excluded_from_codacy(self):
        exclude_paths = load_exclude_paths()
        tracked_files = subprocess.check_output(
            ["git", "ls-files", "-z"],
            cwd=REPO_ROOT,
        ).decode("utf-8").split("\0")

        tracked_non_utf8_files = []
        for relative_path in tracked_files:
            if not relative_path:
                continue

            file_path = REPO_ROOT / relative_path
            if not file_path.is_file():
                continue

            try:
                file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                tracked_non_utf8_files.append(relative_path)

        self.assertGreater(len(tracked_non_utf8_files), 0)

        uncovered_files = [
            relative_path
            for relative_path in tracked_non_utf8_files
            if not any(fnmatch.fnmatch(relative_path, pattern) for pattern in exclude_paths)
        ]
        self.assertEqual(
            uncovered_files,
            [],
            f"Tracked non-UTF8 files must be excluded from Codacy: {uncovered_files}",
        )


if __name__ == "__main__":
    unittest.main()
