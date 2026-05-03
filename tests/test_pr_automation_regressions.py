import os
import runpy
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDetectDuplicatesTriageRewrite(unittest.TestCase):
    def test_preserves_existing_superseded_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tasks_dir = os.path.join(tmpdir, "tasks")
            os.makedirs(tasks_dir)
            triage_path = os.path.join(tasks_dir, "pr-triage.md")
            with open(triage_path, "w", encoding="utf-8") as fh:
                fh.write(
                    "# PR Triage\n\n"
                    "## SUPERSEDED\n"
                    "- abhimehro/personal-config#744\n"
                    "## STALE\n"
                    "## CONFLICTING\n"
                    "## DUPLICATE\n"
                    "## READY\n"
                )

            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                runpy.run_path(
                    os.path.join(REPO_ROOT, "detect_duplicates.py"),
                    run_name="__main__",
                )
            finally:
                os.chdir(old_cwd)

            with open(triage_path, "r", encoding="utf-8") as fh:
                contents = fh.read()
            superseded_section = contents.split("## SUPERSEDED\n", 1)[1].split(
                "## STALE\n", 1
            )[0]
            self.assertIn(
                "- abhimehro/personal-config#744\n",
                superseded_section,
            )


if __name__ == "__main__":
    unittest.main()
