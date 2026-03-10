import codecs
import fnmatch
import subprocess
import tempfile
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

        if not stripped:
            continue

        if stripped.startswith("- "):
            excludes.append(stripped[2:].strip("'\""))
            continue

        # Stop when we hit the next top-level YAML key after exclude_paths.
        if indent <= exclude_indent:
            break

    return excludes


def codacy_path_matches(path, pattern):
    path_parts = PurePosixPath(path).parts
    pattern_parts = PurePosixPath(pattern).parts
    return _match_path_parts(path_parts, pattern_parts)


def _match_path_parts(path_parts, pattern_parts):
    if not pattern_parts:
        return not path_parts

    current_pattern = pattern_parts[0]
    remaining_patterns = pattern_parts[1:]

    if current_pattern == "**":
        return _match_path_parts(path_parts, remaining_patterns) or (
            bool(path_parts) and _match_path_parts(path_parts[1:], pattern_parts)
        )

    return (
        bool(path_parts)
        and fnmatch.fnmatchcase(path_parts[0], current_pattern)
        and _match_path_parts(path_parts[1:], remaining_patterns)
    )


def can_decode_as_utf8(file_path, chunk_size=8192):
    """Return True when a file decodes as UTF-8 using bounded memory.

    Parameters:
        file_path (Path): File to validate by decoding its bytes as UTF-8.
        chunk_size (int): Number of bytes to read per decode step.

    The test only needs to know whether Codacy might trip over non-UTF-8 content,
    so it validates incrementally in 8 KB chunks instead of loading large tracked
    binaries or exports fully into memory.
    """

    with file_path.open("rb") as handle:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
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
    def test_codacy_path_matches_respects_segment_boundaries(self):
        self.assertTrue(codacy_path_matches("configs/foo.bak", "configs/*.bak"))
        self.assertFalse(codacy_path_matches("configs/subdir/foo.bak", "configs/*.bak"))
        self.assertTrue(codacy_path_matches("configs/file1.bak", "configs/file?.bak"))
        self.assertFalse(codacy_path_matches("configs/file10.bak", "configs/file?.bak"))
        self.assertTrue(
            codacy_path_matches(
                "configs/.gemini/extensions/context7/docs/public/favicon.ico",
                "configs/.gemini/extensions/context7/docs/**",
            )
        )
        self.assertFalse(
            codacy_path_matches(
                "configs/.gemini/extensions/context7/other/favicon.ico",
                "configs/.gemini/extensions/context7/docs/**",
            )
        )

    def test_load_exclude_paths_only_reads_exclude_paths_block(self):
        config_text = """exclude_paths:
  - 'tests/**'
  - 'copilot-demo/**'
languages:
  - python
"""

        with patch.object(Path, "read_text", return_value=config_text):
            self.assertEqual(load_exclude_paths(), ["tests/**", "copilot-demo/**"])

    def test_load_exclude_paths_supports_same_indent_list_style(self):
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

            if not can_decode_as_utf8(file_path):
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

    def test_can_decode_as_utf8_handles_chunk_boundaries(self):
        with tempfile.NamedTemporaryFile(mode="wb") as handle:
            handle.write("🙂".encode("utf-8"))
            handle.flush()
            self.assertTrue(can_decode_as_utf8(Path(handle.name), chunk_size=1))

    def test_can_decode_as_utf8_handles_multiple_multibyte_boundaries(self):
        with tempfile.NamedTemporaryFile(mode="wb") as handle:
            handle.write("🙂é🙂".encode("utf-8"))
            handle.flush()
            self.assertTrue(can_decode_as_utf8(Path(handle.name), chunk_size=2))

    def test_can_decode_as_utf8_accepts_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="wb") as handle:
            self.assertTrue(can_decode_as_utf8(Path(handle.name)))

    def test_can_decode_as_utf8_rejects_invalid_bytes(self):
        with tempfile.NamedTemporaryFile(mode="wb") as handle:
            handle.write(b"valid-prefix\xffinvalid")
            handle.flush()
            self.assertFalse(can_decode_as_utf8(Path(handle.name), chunk_size=4))


if __name__ == "__main__":
    unittest.main()
