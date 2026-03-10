import codecs
import re
import subprocess
import unittest
from pathlib import Path, PurePosixPath
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
CODACY_CONFIG = REPO_ROOT / ".codacy.yml"


def load_exclude_paths():
    excludes = []
    in_exclude_paths = False
    exclude_indent = None

    for line in CODACY_CONFIG.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if not in_exclude_paths:
            if stripped == "exclude_paths:":
                in_exclude_paths = True
                exclude_indent = indent
            continue

        if indent <= exclude_indent and stripped and not stripped.startswith("- "):
            break

        if indent > exclude_indent and line.lstrip().startswith("- "):
            excludes.append(line.lstrip()[2:].strip("'\""))

    return excludes


def codacy_path_matches(path, pattern):
    path = PurePosixPath(path).as_posix()
    pattern = PurePosixPath(pattern).as_posix()

    regex_parts = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                regex_parts.append(".*")
                i += 2
                continue
            regex_parts.append("[^/]*")
        elif char == "?":
            regex_parts.append("[^/]")
        else:
            regex_parts.append(re.escape(char))
        i += 1

    return re.fullmatch("".join(regex_parts), path) is not None


def is_utf8_encoded(file_path, chunk_size=8192):
    decoder = codecs.getincrementaldecoder("utf-8")()

    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            try:
                decoder.decode(chunk)
            except UnicodeDecodeError:
                return False

    try:
        decoder.decode(b"", final=True)
    except UnicodeDecodeError:
        return False

    return True


class TestCodacyConfig(unittest.TestCase):
    def test_load_exclude_paths_only_reads_exclude_paths_block(self):
        config_text = """exclude_paths:
  - 'tests/**'
  - 'copilot-demo/**'
languages:
  - python
"""

        with patch.object(Path, "read_text", return_value=config_text):
            self.assertEqual(load_exclude_paths(), ["tests/**", "copilot-demo/**"])

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
                any(codacy_path_matches(path, pattern) for pattern in exclude_paths),
                f"{path} is not covered by .codacy.yml exclude_paths",
            )

        self.assertFalse(
            codacy_path_matches("configs/subdir/something.bak", "configs/*.bak"),
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

            if not is_utf8_encoded(file_path):
                tracked_non_utf8_files.append(relative_path)

        self.assertGreater(len(tracked_non_utf8_files), 0)

        uncovered_files = [
            relative_path
            for relative_path in tracked_non_utf8_files
            if not any(
                codacy_path_matches(relative_path, pattern) for pattern in exclude_paths
            )
        ]
        self.assertEqual(
            uncovered_files,
            [],
            f"Tracked non-UTF8 files must be excluded from Codacy: {uncovered_files}",
        )


if __name__ == "__main__":
    unittest.main()
