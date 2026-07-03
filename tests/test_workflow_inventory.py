#!/usr/bin/env python3
"""Keep the workflow inventory docs aligned with .github/workflows/."""

import re
import unittest
from pathlib import Path


README = Path(".github/workflows/README.md")
WORKFLOW_DIR = Path(".github/workflows")
REMOVED_WORKFLOWS = {"shellcheck.yml", "test-refactoring-agent.yml"}


class TestWorkflowInventory(unittest.TestCase):
    def test_readme_lists_exact_workflow_files(self) -> None:
        readme = README.read_text()
        section_match = re.search(
            r"## Current workflow inventory\n(?P<section>.*?)(?:\n## |\Z)",
            readme,
            re.S,
        )
        self.assertIsNotNone(section_match, "Workflow inventory section not found")

        documented = set(re.findall(r"`([A-Za-z0-9._-]+\.yml)`", section_match.group("section")))
        actual = {path.name for path in WORKFLOW_DIR.glob("*.yml")}

        self.assertEqual(documented, actual)

    def test_removed_workflows_stay_gone(self) -> None:
        actual = {path.name for path in WORKFLOW_DIR.glob("*.yml")}
        self.assertTrue(REMOVED_WORKFLOWS.isdisjoint(actual))


if __name__ == "__main__":
    unittest.main()
