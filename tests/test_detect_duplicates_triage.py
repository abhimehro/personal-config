import os
import subprocess  # nosec B404: test executes this repository's script with controlled argv.
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DETECT_DUPLICATES = REPO_ROOT / "detect_duplicates.py"


def _section(text: str, header: str, next_header: str | None = None) -> str:
    start = text.index(header) + len(header)
    end = text.index(next_header, start) if next_header else len(text)
    return text[start:end]


class TestDetectDuplicatesTriage(unittest.TestCase):
    def test_preserves_superseded_and_uses_exact_ready_membership(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tasks_dir = temp_path / "tasks"
            tasks_dir.mkdir()
            triage_file = tasks_dir / "pr-triage.md"
            triage_file.write_text(
                textwrap.dedent("""\
                    # PR Triage

                    ## SUPERSEDED
                    - abhimehro/example#123
                    ## STALE
                    ## CONFLICTING
                    ## DUPLICATE
                    - abhimehro/example#125
                    ## READY
                    - abhimehro/example#12
                    - abhimehro/example#123
                    - abhimehro/example#124
                    """),
                encoding="utf-8",
            )

            bin_dir = temp_path / "bin"
            bin_dir.mkdir()
            gh_bin = bin_dir / "gh"
            gh_bin.write_text(
                textwrap.dedent("""\
                    #!/usr/bin/env python3
                    import json
                    import sys

                    pr_id = sys.argv[sys.argv.index("view") + 1]
                    print(json.dumps({
                        "files": [{"path": f"file-{pr_id}.txt"}],
                        "number": int(pr_id),
                        "title": f"PR {pr_id}",
                    }))
                    """),
                encoding="utf-8",
            )
            gh_bin.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
            completed = (
                subprocess.run(  # nosec B603: test path and argv are controlled.
                    [sys.executable, str(DETECT_DUPLICATES)],
                    cwd=temp_path,
                    env=env,
                    capture_output=True,
                    text=True,
                )
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            updated_triage = triage_file.read_text(encoding="utf-8")
            superseded = _section(updated_triage, "## SUPERSEDED\n", "## STALE\n")
            duplicate = _section(updated_triage, "## DUPLICATE\n", "## READY\n")
            ready = _section(updated_triage, "## READY\n")

            self.assertIn("- abhimehro/example#123\n", superseded)
            self.assertEqual(1, superseded.count("- abhimehro/example#123\n"))
            self.assertIn("- abhimehro/example#125\n", duplicate)
            self.assertIn("- abhimehro/example#12\n", ready)
            self.assertIn("- abhimehro/example#124\n", ready)
            self.assertNotIn("- abhimehro/example#123\n", ready)
