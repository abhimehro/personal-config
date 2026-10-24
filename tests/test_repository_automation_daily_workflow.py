"""Regression contracts for daily QA dependencies and contributor commands."""

import re
import shlex
import subprocess  # nosec B404
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github/workflows/repository-automation-daily.yml"


class TestDailyQualityAssuranceDependencies(unittest.TestCase):
    def setUp(self):
        self.workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.job = self.workflow["jobs"]["quality_assurance"]
        self.steps = self.job["steps"]
        self.install = self.step("Install automation runner dependencies")

    def step(self, name):
        matches = [step for step in self.steps if step.get("name") == name]
        self.assertEqual(len(matches), 1, f"Expected exactly one {name!r} step")
        return matches[0]

    def run_install(self, exit_code=0):
        # Intercept Python so the real workflow shell command can be exercised
        # without downloading packages or modifying the test environment.
        mock_python = (
            "python() { printf '%s\\n' \"$@\"; " f"return {exit_code}; }}\n"
        )
        return subprocess.run(  # nosec B603 B607
            [
                "bash",
                "--noprofile",
                "--norc",
                "-eo",
                "pipefail",
                "-c",
                mock_python + self.install["run"],
            ],
            cwd=REPO_ROOT,
            env={"PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )

    def test_qa_installs_from_repository_requirements(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["-m", "pip", "install", "--upgrade", "pip", "-r", "requirements.txt"],
        )

    def test_qa_requirements_supply_pinned_smoke_and_full_suite_dependencies(self):
        args = shlex.split(self.install["run"])
        self.assertIn("-r", args, "PyYAML alone cannot run the QA smoke tests")
        manifest = REPO_ROOT / args[args.index("-r") + 1]
        requirements = {
            line.split("==", 1)[0].lower(): line
            for raw in manifest.read_text(encoding="utf-8").splitlines()
            if (line := raw.split("#", 1)[0].strip())
        }
        for package in ("pyyaml", "jsonschema", "requests"):
            with self.subTest(package=package):
                self.assertIn(package, requirements)
                self.assertRegex(
                    requirements[package], rf"(?i)^{package}==\d+\.\d+\.\d+$"
                )

    def test_dependencies_install_after_checkout_and_python_before_qa(self):
        install_index = self.steps.index(self.install)
        for name in ("Checkout repository", "Set up Python"):
            with self.subTest(step=name):
                self.assertLess(self.steps.index(self.step(name)), install_index)
        self.assertLess(
            install_index,
            self.steps.index(self.step("Execute quality assurance task")),
        )
        # A relative requirements path must resolve against the repository root.
        for owner in (self.workflow, self.job):
            defaults = owner.get("defaults", {}).get("run", {})
            self.assertIn(defaults.get("working-directory", "."), (".", "./"))
        self.assertIn(self.install.get("working-directory", "."), (".", "./"))

    def test_dependency_install_is_required_on_every_qa_run(self):
        self.assertNotIn("if", self.install)
        self.assertFalse(self.install.get("continue-on-error", False))

    def test_pip_failure_is_not_silently_ignored(self):
        result = self.run_install(exit_code=23)
        self.assertEqual(result.returncode, 23, result.stderr)


class TestContributingLintCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        cls.lint_section = contributing.split("## Running the Linter\n", 1)[1].split(
            "\n## ", 1
        )[0]
        cls.makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    def test_documented_lint_command_matches_non_mutating_make_recipe(self):
        documented = re.search(
            r"^make lint\s+#\s*(?:equivalent to:\s*)?(trunk[^\n]+)",
            self.lint_section,
            re.MULTILINE,
        )
        self.assertIsNotNone(documented)
        recipe = re.search(r"^lint:[^\n]*\n\t([^\n]+)", self.makefile, re.MULTILINE)
        self.assertIsNotNone(recipe)
        self.assertEqual(shlex.split(documented[1]), shlex.split(recipe[1]))
        self.assertIn("--no-fix", shlex.split(documented[1]))

    def test_lint_guidance_includes_fix_and_standalone_correctness_targets(self):
        targets = re.findall(r"^make (lint[\w-]*)\b", self.lint_section, re.MULTILINE)
        self.assertCountEqual(targets, ["lint", "lint-fix", "lint-errors"])
        for target in targets:
            with self.subTest(target=target):
                self.assertRegex(self.makefile, rf"(?m)^{re.escape(target)}:")
        documented = re.search(
            r"^make lint-fix\s+#\s*(?:equivalent to:\s*)?(trunk[^\n]+)",
            self.lint_section,
            re.MULTILINE,
        )
        self.assertIsNotNone(documented)
        recipe = re.search(
            r"^lint-fix:[^\n]*\n\t([^\n]+)", self.makefile, re.MULTILINE
        )
        self.assertIsNotNone(recipe)
        self.assertEqual(shlex.split(documented[1]), shlex.split(recipe[1]))

    def test_per_file_ci_reproduction_also_disables_fixes(self):
        commands = re.findall(r"`(trunk check[^`]*<file>[^`]*)`", self.lint_section)
        self.assertEqual(len(commands), 1)
        self.assertIn("--no-fix", shlex.split(commands[0]))


if __name__ == "__main__":
    unittest.main()
