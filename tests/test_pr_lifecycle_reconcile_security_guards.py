"""Unit tests for the path, diff, and title evidence used by reconcile."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_reconcile_guards as guards  # noqa: E402


def _diff(path: str, *lines: str) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n" + "\n".join(lines) + "\n"


class SecurityPathEvidenceTests(unittest.TestCase):
    def test_journal_exemption_is_limited_to_direct_markdown_children(self):
        cases = (
            (" .jules/sentinel.md ", True),
            ("nested/.JULES/SENTINEL.MD", True),
            (".jules/notes/sentinel.md", False),
            (".jules/security.py", False),
            ("not.jules/sentinel.md", False),
            (None, False),
        )
        for path, expected in cases:
            with self.subTest(path=path):
                self.assertEqual(guards.is_jules_journal_path(path), expected)

    def test_non_journal_paths_strip_and_filter_without_mutating_input(self):
        paths = [None, 7, "", "  ", " .jules/sentinel.md ", " src/report.py "]
        before = list(paths)
        self.assertEqual(guards.non_journal_paths(paths), ["src/report.py"])
        self.assertEqual(paths, before)

    def test_invalid_path_collections_supply_no_evidence(self):
        for paths in (None, "lib/security.py", {}, (".env",), 42):
            with self.subTest(paths=paths):
                self.assertEqual(guards.non_journal_paths(paths), [])
                self.assertEqual(guards.sticky_sensitive_classes(paths), [])
                self.assertFalse(guards.has_path_security_backing(paths))

    def test_each_sticky_taxonomy_class_has_path_backing(self):
        cases = (
            (".github/workflows/ci.yml", "workflows_and_permissions"),
            ("config/.env.local", "secrets"),
            ("src/oauth.py", "authentication_and_authorization"),
            ("Dockerfile", "deployment_and_infrastructure"),
            ("pnpm-lock.yaml", "lockfiles_and_major_dependencies"),
            (".trunk/trunk.yaml", "security_configuration"),
            ("db/migrations/001.sql", "database_migrations"),
            ("config/dns.toml", "network_and_browser_origins"),
            ("scripts/cleanup.sh", "shell_execution"),
            (".gitignore", "file_read_write_boundaries"),
            ("schemas/item.json", "public_api_contracts"),
            ("src/purge.py", "destructive_data_actions"),
        )
        for path, category in cases:
            with self.subTest(path=path):
                self.assertEqual(guards.sticky_sensitive_classes([path]), [category])
                self.assertTrue(guards.has_path_security_backing([path]))

    def test_sensitive_classes_are_sorted_unique_and_ignore_journals(self):
        self.assertEqual(
            guards.sticky_sensitive_classes(
                [".jules/credentials.md", "scripts/oauth.sh", "scripts/oauth.sh"]
            ),
            ["authentication_and_authorization", "shell_execution"],
        )

    def test_security_module_paths_exclude_test_locations(self):
        for path in (
            "lib/security.py",
            "src/safe_http.py",
            "Sources/TokenSanitizer.swift",
            "Sources/ApplicationSecurity.swift",
            "Sources/DomainMutationPolicy.swift",
            "Sources/ProcessLauncher.swift",
            "Sources/MCPTerminalRecord.swift",
        ):
            with self.subTest(path=path):
                self.assertTrue(guards.has_security_module_path([path]))
                self.assertTrue(guards.has_path_security_backing([path]))
        for path in (
            "tests/security.py",
            "src/test/security.py",
            "src/test_security.py",
            "Tests/ProcessLauncher.swift",
            "src/security_notes.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(guards.has_security_module_path([path]))


class SecurityDiffEvidenceTests(unittest.TestCase):
    def test_added_and_removed_production_security_operations_are_backing(self):
        operations = (
            "subprocess.run(command)",
            "resolved = os.path.realpath(target)",
            "authenticate(user)",
            "api_key = settings.key",
            "validate_url(target)",
            "sanitize_filename(name)",
        )
        for operation in operations:
            for prefix in ("+", "-"):
                with self.subTest(operation=operation, prefix=prefix):
                    self.assertTrue(
                        guards.has_diff_security_backing(
                            _diff("src/report.py", prefix + operation)
                        )
                    )

    def test_context_and_headers_do_not_count_as_changed_security_behavior(self):
        diff = _diff("src/safe_http.py", " validate_url(target)", "+log.info('ok')")
        self.assertFalse(guards.has_diff_security_backing(diff))
        for diff in (None, "", " \n", 42, [], {"diff": "+authenticate(user)"}):
            with self.subTest(diff=diff):
                self.assertFalse(guards.has_diff_security_backing(diff))

    def test_security_keywords_in_journals_and_tests_are_ignored(self):
        for path in (
            ".jules/sentinel.md",
            "nested/.JULES/security.MD",
            "tests/security.py",
            "src/test_auth.py",
            "src/test/security.py",
            "Sources/AuthenticationTests.swift",
        ):
            with self.subTest(path=path):
                self.assertFalse(
                    guards.has_diff_security_backing(_diff(path, "+authenticate(user)"))
                )

    def test_file_boundaries_restore_production_scanning_in_either_order(self):
        ignored = _diff("tests/test_report.py", "+authenticate(user)")
        benign = _diff("src/report.py", "+log.info('ok')")
        security = _diff("src/report.py", "+authenticate(user)")
        for diff, expected in (
            (ignored + benign, False),
            (benign + ignored, False),
            (ignored + security, True),
            (security + ignored, True),
        ):
            with self.subTest(diff=diff):
                self.assertEqual(guards.has_diff_security_backing(diff), expected)

    def test_deleted_tests_and_journals_do_not_supply_security_backing(self):
        for path in ("tests/test_report.py", ".jules/sentinel.md"):
            with self.subTest(path=path):
                diff = (
                    f"diff --git a/{path} b/{path}\n"
                    "deleted file mode 100644\n"
                    f"--- a/{path}\n+++ /dev/null\n"
                    "@@ -1 +0,0 @@\n-authenticate(user)\n"
                )
                self.assertFalse(guards.has_diff_security_backing(diff))

    def test_deleted_production_file_after_test_diff_still_supplies_backing(self):
        diff = _diff("tests/test_report.py", "+log.info('ok')") + (
            "diff --git a/src/report.py b/src/report.py\n"
            "deleted file mode 100644\n"
            "--- a/src/report.py\n+++ /dev/null\n"
            "@@ -1 +0,0 @@\n-authenticate(user)\n"
        )
        self.assertTrue(guards.has_diff_security_backing(diff))


class SecurityClassificationTests(unittest.TestCase):
    def test_title_branch_and_next_action_hints_require_backing(self):
        for field in ("title", "headRefName", "next_action"):
            for hint in ("Sentinel: cleanup", "fix SSRF", "CVE-2026-1234", "Hardening"):
                with self.subTest(field=field, hint=hint):
                    record = {field: hint, "changed_paths": ["src/report.py"]}
                    self.assertTrue(guards.has_title_security_hint(record))
                    self.assertEqual(guards.infer_pr_classification(record), "REFACTOR")
                    record["changed_paths"] = [".github/workflows/ci.yml"]
                    self.assertEqual(guards.infer_pr_classification(record), "SECURITY")

    def test_title_hints_use_word_boundaries(self):
        for title in ("sentinels cleanup", "insecurity report", "fix xssuffix"):
            with self.subTest(title=title):
                self.assertFalse(guards.has_title_security_hint({"title": title}))

    def test_nonsecurity_classification_uses_paths_and_bot_identity(self):
        cases = (
            ({"changed_paths": []}, "UNKNOWN"),
            ({"changed_paths": "src/report.py"}, "UNKNOWN"),
            ({"changed_paths": [".jules/sentinel.md"]}, "REFACTOR"),
            ({"changed_paths": ["src/report.py"]}, "REFACTOR"),
            ({"changed_paths": [".github/workflows/ci.YAML"]}, "CI_INFRA"),
            ({"changed_paths": ["package.json", "nested/uv.lock"]}, "DEPENDENCY"),
            ({"changed_paths": ["package.json", "src/report.py"]}, "REFACTOR"),
            (
                {"changed_paths": ["src/report.py"], "author": "Renovate[bot]"},
                "DEPENDENCY",
            ),
            (
                {
                    "changed_paths": ["src/report.py"],
                    "author": {"login": "dependabot[bot]"},
                },
                "DEPENDENCY",
            ),
        )
        for record, expected in cases:
            with self.subTest(record=record):
                self.assertEqual(guards.infer_pr_classification(record), expected)

    def test_security_evidence_needs_no_title_hint(self):
        for path in (
            ".env.local",
            "src/login.py",
            ".trunk/trunk.yaml",
            "config/dns.toml",
            "scripts/run.sh",
            ".gitignore",
            "src/purge.py",
            "lib/safe_http.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    guards.infer_pr_classification({"changed_paths": [path]}),
                    "SECURITY",
                )
        self.assertEqual(
            guards.infer_pr_classification(
                {"changed_paths": []},
                diff_text=_diff("src/report.py", "+authenticate(user)"),
            ),
            "SECURITY",
        )

    def test_infrastructure_paths_without_hint_do_not_automatically_mean_security(self):
        for path in ("Dockerfile", "db/migrations/001.sql", "schemas/item.json"):
            with self.subTest(path=path):
                self.assertTrue(guards.has_security_backing([path]))
                self.assertEqual(
                    guards.infer_pr_classification({"changed_paths": [path]}),
                    "REFACTOR",
                )

    def test_explicit_diff_overrides_record_diff_including_empty_string(self):
        record = {
            "changed_paths": ["src/report.py"],
            "diff_text": _diff("src/report.py", "+authenticate(user)"),
        }
        self.assertEqual(guards.infer_pr_classification(record), "SECURITY")
        self.assertEqual(
            guards.infer_pr_classification(record, diff_text=""), "REFACTOR"
        )
        record["diff_text"] = ""
        self.assertEqual(
            guards.infer_pr_classification(
                record, diff_text=_diff("src/report.py", "+authenticate(user)")
            ),
            "SECURITY",
        )


if __name__ == "__main__":
    unittest.main()
