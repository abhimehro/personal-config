"""Unit tests for scripts/run_pr_triage_queue.py (imported via importlib)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "run_pr_triage_queue",
    _ROOT / "scripts" / "run_pr_triage_queue.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Could not load scripts/run_pr_triage_queue.py for tests")
_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_mod)


class TestRunPrTriageQueue(unittest.TestCase):
    def test_slice_stops_at_next_top_level_heading(self) -> None:
        md = """# Title
## Planned mutations (test)

```bash
gh pr merge 2 --repo abhimehro/ok --squash
```

## Phase 2 later

```bash
gh pr merge 99 --repo abhimehro/wrong --squash
```
"""
        cmds = _mod.extract_gh_commands(md)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0][3], "2")

    def test_extract_merge_and_close(self) -> None:
        md = """## Planned mutations

```bash
# merges
gh pr merge 1 --repo abhimehro/foo-bar --squash

# closes
gh pr close 9 --repo abhimehro/foo-bar --comment 'Duplicate of #1'
```
"""
        cmds = _mod.extract_gh_commands(md)
        self.assertEqual(
            cmds[0],
            ["gh", "pr", "merge", "1", "--repo", "abhimehro/foo-bar", "--squash"],
        )
        self.assertEqual(
            cmds[1],
            [
                "gh",
                "pr",
                "close",
                "9",
                "--repo",
                "abhimehro/foo-bar",
                "--comment",
                "Duplicate of #1",
            ],
        )

    def test_reject_shell_metacharacters(self) -> None:
        with self.assertRaises(ValueError):
            _mod.line_to_argv("gh pr merge 1 --repo abhimehro/x --squash; true")

    def test_missing_heading_errors(self) -> None:
        with self.assertRaises(ValueError):
            _mod.extract_gh_commands("# no planned mutations\n")

    def test_disallowed_subcommand(self) -> None:
        md = """## Planned mutations
```bash
gh api repos/foo --method GET
```
"""
        with self.assertRaises(ValueError):
            _mod.extract_gh_commands(md)


if __name__ == "__main__":
    unittest.main()
