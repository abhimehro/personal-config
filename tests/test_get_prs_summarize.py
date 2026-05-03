import sys
import unittest
from pathlib import Path

# Add scripts directory to path to import the module
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.append(str(scripts_dir))

from get_prs_summarize import automation_hints

class TestAutomationHints(unittest.TestCase):
    def test_human_pr(self):
        pr = {
            "author": {"is_bot": False, "login": "alice"},
            "headRefName": "feature/new-button",
            "title": "Add new button",
            "body": "This adds a new button to the UI."
        }
        self.assertEqual(automation_hints(pr), "(none — treat as human unless reviews say otherwise)")

    def test_author_is_bot(self):
        pr = {"author": {"is_bot": True, "login": "bot-account"}}
        self.assertEqual(automation_hints(pr), "author_is_bot")

    def test_bot_login_suffix(self):
        pr = {"author": {"is_bot": False, "login": "dependabot[bot]"}}
        self.assertEqual(automation_hints(pr), "bot_login")

    def test_branch_signals(self):
        cases = [
            ("jules/update", "branch:jules"),
            ("sentinel/fix", "branch:sentinel"),
            ("bolt/perf", "branch:bolt"),
            ("palette/ui", "branch:palette"),
            ("automation-task", "branch:automation-"),
            ("daily-qa-run", "branch:daily-qa"),
            # Note: "chore/jules" matches "jules" first in the current implementation,
            # so it results in "branch:jules".
            ("chore/jules-update", "branch:jules"),
            ("cursor-agent/test", "branch:cursor-agent"),
            ("renovate/upgrade", "branch:renovate"),
            ("dependabot/npm", "branch:dependabot"),
            ("copilot-fix", "branch:copilot"),
        ]
        for branch, expected in cases:
            with self.subTest(branch=branch):
                pr = {"headRefName": branch}
                self.assertEqual(automation_hints(pr), expected)

    def test_title_kw(self):
        cases = [
            ("Update by jules", "title:jules"),
            ("Sentinel: security fix", "title:sentinel"),
            ("Bump version dependabot", "title:dependabot"),
            ("Renovate config", "title:renovate"),
            ("autofix something", "title:autofix"),
            ("Bolt: speed up", "title:bolt"),
            ("Palette: colors", "title:palette"),
            ("Automation script", "title:automation"),
        ]
        for title, expected in cases:
            with self.subTest(title=title):
                pr = {"title": title}
                self.assertEqual(automation_hints(pr), expected)

    def test_body_markers(self):
        cases = [
            ("See jules.google.com for more", "body:automation_marker"),
            ("This was created automatically by jules", "body:automation_marker"),
            ("The pull request was automatically generated", "body:automation_marker"),
            ("Signed-off-by: dependabot", "body:automation_marker"),
        ]
        for body, expected in cases:
            with self.subTest(body=body):
                pr = {"body": body}
                self.assertEqual(automation_hints(pr), expected)

    def test_multiple_hints_sorted(self):
        # The hints should be semicolon separated and sorted alphabetically.
        pr = {
            "author": {"is_bot": True, "login": "mybot[bot]"},
            "headRefName": "bolt/feature",
            "title": "Bolt: fast",
            "body": "created automatically by jules"
        }
        hints = automation_hints(pr)
        expected_hints = [
            "author_is_bot",
            "body:automation_marker",
            "bot_login",
            "branch:bolt",
            "title:bolt"
        ]
        self.assertEqual(hints, "; ".join(expected_hints))

    def test_none_input_values(self):
        # PR dictionary might have missing fields or None values
        pr = {
            "author": None,
            "headRefName": None,
            "title": None,
            "body": None
        }
        self.assertEqual(automation_hints(pr), "(none — treat as human unless reviews say otherwise)")

if __name__ == "__main__":
    unittest.main()
