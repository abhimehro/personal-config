import copy
import sys
import unittest
from pathlib import Path

# Add scripts directory to path to import the module
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.append(str(scripts_dir))

from get_prs_summarize import (
    _add_author_hints,
    _add_body_hints,
    _add_branch_hints,
    _add_title_hints,
    automation_hints,
    check_summary,
)


class TestAutomationHints(unittest.TestCase):
    def test_human_pr(self):
        pr = {
            "author": {"is_bot": False, "login": "alice"},
            "headRefName": "feature/new-button",
            "title": "Add new button",
            "body": "This adds a new button to the UI.",
        }
        self.assertEqual(
            automation_hints(pr), "(none — treat as human unless reviews say otherwise)"
        )

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
            "body": "created automatically by jules",
        }
        hints = automation_hints(pr)
        expected_hints = [
            "author_is_bot",
            "body:automation_marker",
            "bot_login",
            "branch:bolt",
            "title:bolt",
        ]
        self.assertEqual(hints, "; ".join(expected_hints))

    def test_none_input_values(self):
        # PR dictionary might have missing fields or None values
        pr = {"author": None, "headRefName": None, "title": None, "body": None}
        self.assertEqual(
            automation_hints(pr), "(none — treat as human unless reviews say otherwise)"
        )

    def test_missing_and_empty_fields(self):
        for pr in ({}, {"author": {}, "headRefName": "", "title": "", "body": ""}):
            with self.subTest(pr=pr):
                self.assertEqual(
                    automation_hints(pr),
                    "(none — treat as human unless reviews say otherwise)",
                )

    def test_partial_author_records(self):
        cases = [
            ({"is_bot": True}, "author_is_bot"),
            ({"is_bot": True, "login": None}, "author_is_bot"),
            ({"is_bot": True, "login": ""}, "author_is_bot"),
            ({"login": "helper[bot]"}, "bot_login"),
            ({"is_bot": None, "login": "helper[bot]"}, "bot_login"),
        ]
        for author, expected in cases:
            with self.subTest(author=author):
                self.assertEqual(automation_hints({"author": author}), expected)

    def test_bot_login_requires_exact_suffix(self):
        for login in (
            None, "", "helperbot", "[bot]helper", "helper[bot]-old", "helper[BOT]"
        ):
            with self.subTest(login=login):
                self.assertEqual(
                    automation_hints({"author": {"login": login}}),
                    "(none — treat as human unless reviews say otherwise)",
                )

    def test_text_signals_are_case_insensitive(self):
        cases = [
            ("headRefName", "FEATURE/BOLT/Fix", "branch:bolt"),
            ("headRefName", "DEPENDABOT/npm", "branch:dependabot"),
            ("title", "Fix by SeNtInEl", "title:sentinel"),
            ("title", "Apply AUTOFIX", "title:autofix"),
            ("body", "See JULES.GOOGLE.COM/task/1", "body:automation_marker"),
            ("body", "CREATED AUTOMATICALLY BY JULES", "body:automation_marker"),
            (
                "body",
                "PULL REQUEST WAS AUTOMATICALLY generated",
                "body:automation_marker",
            ),
            ("body", "SIGNED-OFF-BY: DEPENDABOT", "body:automation_marker"),
        ]
        for field, value, expected in cases:
            with self.subTest(field=field, value=value):
                self.assertEqual(automation_hints({field: value}), expected)

    def test_branch_signal_priority_is_independent_of_text_order(self):
        cases = [
            ("copilot/renovate/dependabot/npm", "branch:renovate"),
            ("bolt/fix-sentinel", "branch:sentinel"),
            ("palette/ui-bolt/fix", "branch:bolt"),
            ("dependabot/npm-jules", "branch:jules"),
        ]
        for branch, expected in cases:
            with self.subTest(branch=branch):
                self.assertEqual(automation_hints({"headRefName": branch}), expected)

    def test_title_keyword_priority_is_independent_of_text_order(self):
        cases = [
            ("Automation by Palette and Bolt", "title:bolt"),
            ("Renovate and Dependabot", "title:dependabot"),
            ("Autofix by Sentinel", "title:sentinel"),
            ("Sentinel fix by Jules", "title:jules"),
        ]
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(automation_hints({"title": title}), expected)

    def test_branch_delimiters_are_required_for_slash_signals(self):
        for branch in (
            "bolt", "bolt-fix", "palette-ui", "cursor-agent-fix", "dependabot-npm"
        ):
            with self.subTest(branch=branch):
                self.assertEqual(
                    automation_hints({"headRefName": branch}),
                    "(none — treat as human unless reviews say otherwise)",
                )

    def test_branch_signals_match_inside_names_and_without_trailing_content(self):
        cases = [
            ("feature/bolt/fix", "branch:bolt"),
            ("bolt/", "branch:bolt"),
            ("automation-", "branch:automation-"),
            ("feature/renovate-config", "branch:renovate"),
        ]
        for branch, expected in cases:
            with self.subTest(branch=branch):
                self.assertEqual(automation_hints({"headRefName": branch}), expected)

    def test_repeated_and_distinct_body_markers_produce_one_hint(self):
        pr = {
            "body": (
                "jules.google.com jules.google.com\n"
                "created automatically by jules\n"
                "pull request was automatically generated\n"
                "signed-off-by: dependabot"
            )
        }
        self.assertEqual(automation_hints(pr), "body:automation_marker")

    def test_body_near_misses_do_not_signal_automation(self):
        for body in ("Jules helped", "created manually by jules", "signed-off-by: alice"):
            with self.subTest(body=body):
                self.assertEqual(
                    automation_hints({"body": body}),
                    "(none — treat as human unless reviews say otherwise)",
                )

    def test_calls_are_independent_and_leave_input_unchanged(self):
        pr = {
            "author": {"is_bot": True, "login": "helper[bot]"},
            "headRefName": "bolt/fix",
            "title": "Autofix",
            "body": "jules.google.com",
        }
        original = copy.deepcopy(pr)
        expected = (
            "author_is_bot; body:automation_marker; bot_login; branch:bolt; title:autofix"
        )
        self.assertEqual(automation_hints(pr), expected)
        self.assertEqual(
            automation_hints({}), "(none — treat as human unless reviews say otherwise)"
        )
        self.assertEqual(automation_hints({"title": "Palette"}), "title:palette")
        self.assertEqual(automation_hints(pr), expected)
        self.assertEqual(pr, original)


class TestAddAutomationHints(unittest.TestCase):
    def test_helpers_accumulate_in_place_and_are_idempotent(self):
        cases = [
            (
                _add_author_hints,
                {"is_bot": True, "login": "helper[bot]"},
                {"author_is_bot", "bot_login"},
            ),
            (_add_branch_hints, "bolt/fix", {"branch:bolt"}),
            (_add_title_hints, "Autofix", {"title:autofix"}),
            (_add_body_hints, "jules.google.com", {"body:automation_marker"}),
        ]
        for helper, value, expected in cases:
            with self.subTest(helper=helper.__name__):
                hints = {"existing_hint"}
                self.assertIsNone(helper(value, hints))
                self.assertEqual(hints, {"existing_hint"} | expected)
                self.assertIsNone(helper(value, hints))
                self.assertEqual(hints, {"existing_hint"} | expected)

    def test_helpers_preserve_existing_hints_without_a_match(self):
        cases = [
            (_add_author_hints, (None, {}, {"is_bot": False, "login": "alice"})),
            (_add_branch_hints, (None, "", "feature/button")),
            (_add_title_hints, (None, "", "Add a button")),
            (_add_body_hints, (None, "", "A manual update")),
        ]
        for helper, values in cases:
            for value in values:
                with self.subTest(helper=helper.__name__, value=value):
                    hints = {"existing_hint"}
                    self.assertIsNone(helper(value, hints))
                    self.assertEqual(hints, {"existing_hint"})


class TestCheckSummary(unittest.TestCase):
    def test_none_rollup(self):
        self.assertEqual(check_summary(None), "NO_CHECKS")

    def test_empty_rollup(self):
        self.assertEqual(check_summary([]), "NO_CHECKS")

    def test_all_completed_ok(self):
        rollup = [
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "COMPLETED", "conclusion": "NEUTRAL"},
            {"status": "completed", "conclusion": "success"},  # case insensitive check
        ]
        self.assertEqual(check_summary(rollup), "COMPLETED_OK")

    def test_pending_only(self):
        rollup = [
            {"status": "IN_PROGRESS"},
            {"status": "QUEUED"},
            {"status": ""},
        ]
        self.assertEqual(check_summary(rollup), "PENDING_3")

    def test_failed_only(self):
        rollup = [
            {"status": "COMPLETED", "conclusion": "FAILURE"},
            {"status": "COMPLETED", "conclusion": "TIMED_OUT"},
            {"status": "COMPLETED", "conclusion": "ACTION_REQUIRED"},
            {"status": "COMPLETED", "conclusion": "CANCELLED"},
            {"status": "COMPLETED", "conclusion": "STARTUP_FAILURE"},
        ]
        self.assertEqual(check_summary(rollup), "FAIL_5")

    def test_mixed_pending_and_failed(self):
        rollup = [
            {"status": "IN_PROGRESS"},
            {"status": "COMPLETED", "conclusion": "FAILURE"},
            {"status": "QUEUED"},
        ]
        self.assertEqual(check_summary(rollup), "PENDING_2+FAIL_1")

    def test_mixed_all_three(self):
        rollup = [
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "IN_PROGRESS"},
            {"status": "COMPLETED", "conclusion": "FAILURE"},
        ]
        self.assertEqual(check_summary(rollup), "PENDING_1+FAIL_1")

    def test_missing_keys(self):
        rollup = [
            {},  # pending (missing status defaults to "")
            {
                "status": "COMPLETED"
            },  # not failed (missing conclusion is not in FAIL_CONCLUSIONS)
        ]
        self.assertEqual(check_summary(rollup), "PENDING_1")

    def test_conclusion_case_insensitive(self):
        rollup = [
            {"status": "COMPLETED", "conclusion": "failure"},
        ]
        self.assertEqual(check_summary(rollup), "FAIL_1")


if __name__ == "__main__":
    unittest.main()
