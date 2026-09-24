import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent.parent / "adguard" / "scripts"
GENERATORS = (
    "consolidate_adblock_lists.py",
    "create_consolidated_lists.py",
    "extract_domains.py",
)
OUTPUT_FILES = (
    "Consolidated-Denylist.txt",
    "Consolidated-Allowlist.txt",
    "Consolidated-Denylist.json",
    "Consolidated-Allowlist.json",
)


def run_generator(script, source, output):
    env = os.environ.copy()
    env["ADGUARD_LISTS_DIR"] = str(source)
    args = [sys.executable, str(SCRIPTS / script)]
    if script == "consolidate_adblock_lists.py":
        args += ["--input-dir", str(source), "--output-dir", str(output)]
    else:
        output = source
    result = subprocess.run(args, env=env, capture_output=True, text=True)
    return result, output


class TestAdGuardPkValidation(unittest.TestCase):
    def test_invalid_pk_rejects_source_before_writing_files(self):
        cases = (
            ("CD-Microsoft-Tracker.json", 0, "tracker.example\n@@||tracker.example^"),
            ("CD-Microsoft-Tracker.json", 0, "@@||tracker.example^"),
            ("CD-Microsoft-Tracker.json", 0, "tracker.example\r!comment"),
            ("CD-Control-D-Bypass.json", 1, "allowed.example\n||blocked.example^"),
            ("CD-Control-D-Bypass.json", 1, "*.*"),
            ("CD-Control-D-Bypass.json", 1, "api*.example*"),
            ("CD-Control-D-Bypass.json", 1, 42),
        )
        for script in GENERATORS:
            for filename, action, pk in cases:
                with self.subTest(script=script, filename=filename, pk=pk):
                    with tempfile.TemporaryDirectory() as root:
                        source = Path(root) / "source"
                        output = Path(root) / "output"
                        source.mkdir()
                        output.mkdir()
                        (source / filename).write_text(
                            json.dumps({"rules": [{"PK": pk, "action": {"do": action}}]}),
                            encoding="utf-8",
                        )
                        result, actual_output = run_generator(script, source, output)
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        self.assertIn("Invalid PK", result.stderr)
                        for name in OUTPUT_FILES:
                            self.assertFalse((actual_output / name).exists(), name)

    def test_valid_domains_and_allowlist_wildcards_remain_supported(self):
        for script in GENERATORS:
            with self.subTest(script=script):
                with tempfile.TemporaryDirectory() as root:
                    source = Path(root) / "source"
                    output = Path(root) / "output"
                    source.mkdir()
                    output.mkdir()
                    fixtures = {
                        "CD-Microsoft-Tracker.json": [
                            {"PK": "tracker.example", "action": {"do": 0}}
                        ],
                        "CD-Control-D-Bypass.json": [
                            {"PK": "api*.example.com", "action": {"do": 1}}
                        ],
                        "CD-Most-Abused-TLDs.json": [
                            {"PK": "*.example", "action": {"do": 1}}
                        ],
                    }
                    for filename, rules in fixtures.items():
                        (source / filename).write_text(
                            json.dumps({"rules": rules}), encoding="utf-8"
                        )
                    result, actual_output = run_generator(script, source, output)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn(
                        "tracker.example",
                        (actual_output / "Consolidated-Denylist.txt").read_text(
                            encoding="utf-8"
                        ).splitlines(),
                    )
                    allowlist_lines = (
                        (actual_output / "Consolidated-Allowlist.txt")
                        .read_text(encoding="utf-8")
                        .splitlines()
                    )
                    self.assertIn("@@api*.example.com", allowlist_lines)
                    self.assertIn("@@*.example", allowlist_lines)


if __name__ == "__main__":
    unittest.main()
