"""Value allowlist regressions for PR #2076.

Run: python3 -m unittest tests.test_gitleaks_dummy_allowlist -v
Requires Python 3.11+; scanner checks additionally require Gitleaks on PATH
(verified with 8.30.1). All credential-shaped inputs are synthetic.
"""

import itertools
import json
import re
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / ".github" / "gitleaks.toml"


class TestDummyAllowlist(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with CONFIG_PATH.open("rb") as config_file:
            config = tomllib.load(config_file)
        cls.patterns = [re.compile(value) for value in config["allowlist"]["regexes"]]
        rule = next(
            rule
            for rule in config["rules"]
            if rule["id"] == "personal-config-generic-secret"
        )
        cls.secret_rule = re.compile(rule["regex"])

    def assert_allowlisted(self, value, expected=True):
        self.assertEqual(
            any(pattern.search(value) for pattern in self.patterns), expected, value
        )

    def test_original_false_positive_and_documented_dummies(self):
        for value in (
            "sk-very-secret-key-12345",
            "my-dummy-secret-99",
            "placeholder-secret",
            "key-12345",
        ):
            with self.subTest(value=value):
                self.assert_allowlisted(value)

    def test_very_secret_key_separator_case_and_numeric_suffix_variants(self):
        for separators in itertools.product(("", "-", "_"), repeat=3):
            for suffix in ("", "0", "12345"):
                value = (
                    f"very{separators[0]}secret{separators[1]}key"
                    f"{separators[2]}{suffix}"
                )
                for candidate in (value, value.upper()):
                    with self.subTest(value=candidate):
                        self.assert_allowlisted(candidate)

    def test_dummy_families_separator_case_and_alphanumeric_suffix_variants(self):
        for family, before, after, suffix in itertools.product(
            ("dummy", "placeholder", "fake", "sample"),
            ("", "-", "_"),
            ("", "-", "_"),
            ("", "0", "a9z"),
        ):
            value = f"{family}{before}secret{after}{suffix}"
            for candidate in (value, value.upper()):
                with self.subTest(value=candidate):
                    self.assert_allowlisted(candidate)

    def test_self_describing_values_can_be_embedded_in_a_longer_token(self):
        for value in ("prefix-very_secret_key_42-suffix", "my-FAKE_SECRET_a9-suffix"):
            with self.subTest(value=value):
                self.assert_allowlisted(value)

    def test_captured_tail_is_exact_and_case_sensitive(self):
        for value in (
            "key-1234",
            "key-123456",
            "prefix-key-12345",
            "key-12345-suffix",
            "key-12345.",
            "KEY-12345",
            "key_12345",
            " key-12345",
            "key-12345 ",
        ):
            with self.subTest(value=value):
                self.assert_allowlisted(value, expected=False)

    def test_near_misses_and_unmarked_values_are_not_allowlisted(self):
        for value in (
            "",
            "dummy",
            "secret",
            "very-secret",
            "very--secret-key",
            "very_secret__key",
            "dummy--secret",
            "placeholder__secret",
            "fake.secret",
            "sample secret",
            "production-secret-a9z",
            "m7Q2v9N4z6R8p3W5",
        ):
            with self.subTest(value=value):
                self.assert_allowlisted(value, expected=False)

    def test_original_assignment_allowlists_the_captured_secret(self):
        line = 'config.deepfake_api_key = "sk-very-secret-key-12345"'
        match = self.secret_rule.search(line)
        self.assertIsNotNone(match)
        self.assertEqual(match.group("secret"), "key-12345")
        self.assert_allowlisted(match.group("secret"))


@unittest.skipUnless(shutil.which("gitleaks"), "Gitleaks required for scanner checks")
class TestDummyAllowlistScanner(unittest.TestCase):
    def scan(self, content, expected_exit):
        # stdin bypasses the pre-existing path exclusions for tests/mock/sample.
        # An isolated cwd also prevents a local .gitleaksignore masking findings.
        with tempfile.TemporaryDirectory(prefix="gitleaks-allowlist-") as directory:
            report = Path(directory) / "report.json"
            result = subprocess.run(
                [
                    shutil.which("gitleaks"),
                    "stdin",
                    "--config",
                    str(CONFIG_PATH),
                    "--no-banner",
                    "--log-level",
                    "error",
                    "--exit-code",
                    "23",
                    "--report-format",
                    "json",
                    "--report-path",
                    str(report),
                ],
                input=content,
                text=True,
                capture_output=True,
                cwd=directory,
                timeout=15,
                check=False,
            )
            self.assertEqual(result.returncode, expected_exit, result.stderr)
            return json.loads(report.read_text(encoding="utf-8"))

    def test_documented_dummies_produce_no_findings(self):
        findings = self.scan(
            'config.deepfake_api_key = "sk-very-secret-key-12345"\n'
            'api_key = "my-dummy-secret-99"\n'
            'api_key = "placeholder-secret"\n'
            'password = "key-12345"\n',
            expected_exit=0,
        )
        self.assertEqual(findings, [])

    def test_mixed_input_keeps_canary_and_near_miss_findings(self):
        # Construct a PAT-shaped canary without committing a complete token.
        canary = "ghp_" + "aB3dE6gH9jK2mN5pQ8sT1vW4yZ7cF0iL3oR6"
        near_misses = ("key-123456", "prefix-key-12345", "key-12345-suffix")
        content = (
            'config.deepfake_api_key = "sk-very-secret-key-12345"\n'
            f'github_token = "{canary}" # placeholder-secret;\n'
            + "".join(f'password = "{value}"\n' for value in near_misses)
        )
        findings = self.scan(content, expected_exit=23)
        for rule_id in ("personal-config-github-token", "github-pat"):
            with self.subTest(rule=rule_id):
                self.assertTrue(
                    any(
                        item["RuleID"] == rule_id and item["Secret"] == canary
                        for item in findings
                    )
                )
        captured = {
            item["Secret"]
            for item in findings
            if item["RuleID"] == "personal-config-generic-secret"
        }
        self.assertEqual(captured, set(near_misses))


if __name__ == "__main__":
    unittest.main()
