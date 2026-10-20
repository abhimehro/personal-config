"""Unit tests for diff signals and Dependabot workflow boundaries."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_guardrails as guardrails  # noqa: E402


def _diff(path: str, lines: str) -> str:
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@\n{lines}\n"


class ResolvedBumpTests(unittest.TestCase):
    def test_versions_and_grouped_bumps(self) -> None:
        cases = (
            ("Bump lib from 1.2.3 to 1.2.4", "patch"),
            ("Bump lib FROM v1.2.3 TO v1.3.0", "minor"),
            ("from 0.1.9 to 0.2.0", "minor"),
            ("from 1.2.3 to 2.0.0", None),
            ("from 2.0.0 to 1.9.9", None),
            ("from 1.3.0 to 1.2.9", None),
            ("from 1.2.4 to 1.2.3", None),
            ("from 1.2.3 to 1.2.3", None),
            ("from 1.2 to 1.3", None),
            ("Update dependencies", None),
            ("from 1.2.3 to 1.2.4; from 2.1.0 to 2.2.0", "minor"),
            ("from 1.2.3 to 1.2.4; from 2.1.0 to 3.0.0", None),
            ("from 1.2.3 to 1.2.4; from 2.1.0 to 2.1.0", None),
        )
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(expected, guardrails.resolved_bump(title, None))

    def test_diff_can_supply_bump_but_must_agree_with_title(self) -> None:
        patch = "from 1.2.3 to 1.2.4"
        minor = "from 1.2.3 to 1.3.0"
        major = "from 1.2.3 to 2.0.0"
        for title, diff, expected in (
            (None, patch, "patch"),
            (patch, patch, "patch"),
            (patch, "+uses: actions/checkout@" + "a" * 40, "patch"),
            (patch, minor, None),
            (minor, patch, None),
            (patch, major, None),
            (None, None, None),
        ):
            with self.subTest(title=title, diff=diff):
                self.assertEqual(expected, guardrails.resolved_bump(title, diff))


class WorkflowDiffTests(unittest.TestCase):
    def test_permission_additions_removals_and_context_blocks(self) -> None:
        cases = (
            ("+permissions: read-all", True),
            ("-permissions: {}", True),
            (" permissions:\n-  contents: read\n+  contents: write", True),
            ("+      id-token: write", True),
            ("-      security-events: write", True),
            (" permissions:\n+  future-scope: write", True),
            (" permissions:\n   contents: read\n jobs:\n+  build:", False),
            (" permissions:\n   contents: read\n@@\n+  build:", False),
            ("+name: CI\n+on: push", False),
            (" permissions:\n   contents: read", False),
        )
        for lines, expected in cases:
            with self.subTest(lines=lines):
                self.assertEqual(
                    expected,
                    guardrails.permissions_block_changed(
                        _diff(".github/workflows/ci.yml", lines)
                    ),
                )

    def test_permissions_context_does_not_leak_to_next_file(self) -> None:
        diff = _diff(".github/workflows/first.yml", " permissions:\n   contents: read")
        diff += _diff(".github/workflows/second.yml", "+  name: Build")
        self.assertFalse(guardrails.permissions_block_changed(diff))

    def test_added_actions_require_full_pins_or_local_paths(self) -> None:
        sha = "0123456789abcdef" * 2 + "01234567"
        for ref, expected in (
            (f"actions/checkout@{sha}", True),
            (f"'actions/checkout@{sha}'", True),
            (f'"actions/checkout@{sha}" # v4.1.2', True),
            ("./.github/actions/setup", True),
            ("actions/checkout@v4", False),
            ("actions/checkout@main", False),
            ("actions/checkout", False),
            ("actions/checkout@" + "a" * 39, False),
            ("actions/checkout@" + "a" * 41, False),
            ("actions/checkout@" + "z" * 40, False),
        ):
            with self.subTest(ref=ref):
                self.assertEqual(
                    expected,
                    guardrails.added_actions_pinned(
                        _diff(".github/workflows/ci.yml", f"+  - uses: {ref}")
                    ),
                )

    def test_removed_and_context_action_refs_do_not_count_as_additions(self) -> None:
        diff = _diff(
            ".github/workflows/ci.yml",
            "-  - uses: actions/checkout@v3\n"
            "   - uses: actions/cache@v4\n"
            "+  - uses: actions/checkout@" + "a" * 40,
        )
        self.assertTrue(guardrails.added_actions_pinned(diff))
        self.assertFalse(
            guardrails.added_actions_pinned(diff + "\n+  - uses: actions/setup-node@v4")
        )


class DiffSecuritySignalsTests(unittest.TestCase):
    def test_added_and_removed_security_behavior(self) -> None:
        cases = (
            ("subprocess.run(command)", "shell_execution"),
            (
                "hmac.compare_digest(actual, expected)",
                "authentication_and_authorization",
            ),
            ("html.escape(value)", "security_configuration"),
            ("os.path.commonpath(paths)", "file_read_write_boundaries"),
            ('os.environ["API_KEY"]', "secrets"),
            ('allow_origins = ["https://example.test"]', "network_and_browser_origins"),
        )
        for line, expected in cases:
            for marker in ("+", "-"):
                with self.subTest(line=line, marker=marker):
                    self.assertEqual(
                        {expected},
                        guardrails.diff_security_signals(
                            _diff("src/main.py", marker + line)
                        ),
                    )

    def test_docs_tests_and_comments_do_not_trigger_signals(self) -> None:
        for path in (
            ".jules/nested/journal.MD",
            "docs/guide.rst",
            "README.markdown",
            "tests/test_process.py",
            "pkg/specs/process.ts",
            "pkg/process_test.go",
            "pkg/test_process.py",
            "Tests/ProcessTests.swift",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    set(),
                    guardrails.diff_security_signals(_diff(path, "+eval(input)")),
                )
        for path, comment in (
            ("src/main.py", "+  # eval(input)"),
            ("src/main.ts", "+  // eval(input)"),
            ("src/main.swift", "+  // eval(input)"),
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    set(), guardrails.diff_security_signals(_diff(path, comment))
                )

    def test_context_is_ignored_and_file_exclusions_do_not_leak(self) -> None:
        diff = _diff("tests/test_process.py", "+eval(input)")
        diff += _diff("src/main.py", " eval(input)\n+print('ready')")
        self.assertEqual(set(), guardrails.diff_security_signals(diff))
        diff += _diff(
            "src/service.py", "+eval(input)\n+html.escape(value)\n+eval(other)"
        )
        self.assertEqual(
            {"shell_execution", "security_configuration"},
            guardrails.diff_security_signals(diff),
        )


if __name__ == "__main__":
    unittest.main()
