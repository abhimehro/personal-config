import os
import shutil
import subprocess  # nosec B404
import unittest
from pathlib import Path

import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "refactoring-agent.yml"
)


def load_workflow():
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


class TestRefactoringAgentWorkflow(unittest.TestCase):
    def test_refactoring_agent_enforces_concurrency_per_pr(self):
        workflow = load_workflow()

        self.assertEqual(
            workflow["concurrency"],
            {
                "group": "refactoring-agent-${{ github.event.issue.number }}",
                "cancel-in-progress": True,
            },
        )

    def test_refactoring_agent_retries_failed_push_once(self):
        steps = load_workflow()["jobs"]["refactor"]["steps"]
        steps_by_id = {step["id"]: step for step in steps if "id" in step}
        steps_by_name = {step["name"]: step for step in steps if "name" in step}

        self.assertTrue(steps_by_id["refactor-attempt-1"]["continue-on-error"] is True)
        self.assertTrue(
            steps_by_name["Wait before retrying failed refactor"]["if"]
            == "steps.refactor-attempt-1.outcome == 'failure'"
        )
        self.assertTrue(
            steps_by_name["Wait before retrying failed refactor"]["env"]
            == {"REFACTOR_RETRY_DELAY_SECONDS": 15}
        )
        self.assertTrue(
            steps_by_name["Wait before retrying failed refactor"]["run"]
            == 'sleep "${REFACTOR_RETRY_DELAY_SECONDS}"'
        )
        self.assertTrue(
            steps_by_id["refactor-attempt-2"]["if"]
            == "steps.refactor-attempt-1.outcome == 'failure'"
        )
        self.assertTrue(steps_by_id["refactor-attempt-2"]["continue-on-error"] is True)
        self.assertTrue(
            steps_by_name["Fail if both refactor attempts fail"]["if"]
            == "always() && steps.refactor-attempt-1.outcome == 'failure' && steps.refactor-attempt-2.outcome == 'failure'"
        )

    def test_prepare_command_extracts_first_cs_agent_line_from_multiline_comment(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_path_str:
            tmp_path = Path(tmp_path_str)
            steps = load_workflow()["jobs"]["refactor"]["steps"]
            prepare_command_step = next(
                step for step in steps if step.get("id") == "prepare-command"
            )
            github_output = tmp_path / "github-output.txt"
            home_dir = tmp_path / "home"
            home_dir.mkdir()

            bash = shutil.which("bash")
            if bash is None:
                self.fail("bash not found in PATH; cannot run workflow shell test")

            result = subprocess.run(  # nosec B603
                [bash, "-e", "-c", prepare_command_step["run"]],
                check=False,
                capture_output=True,
                text=True,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": str(home_dir),
                    "LANG": "C.UTF-8",
                    "RAW_COMMENT": (
                        "> /cs-agent fix-code-health-degradations\n\n"
                        "Acknowledged. I already updated the PR.\n\n"
                        "/cs-agent second-command-should-be-ignored"
                    ),
                    "GITHUB_OUTPUT": str(github_output),
                },
            )

            self.assertEqual(result.returncode, 0, result.stderr)  # nosec B101
            self.assertIn(
                "Final command: /cs-agent skill:fix-code-health-degradations",
                result.stdout,
            )  # nosec B101
            self.assertNotIn(
                "second-command-should-be-ignored", result.stdout
            )  # nosec B101
            self.assertEqual(
                github_output.read_text(encoding="utf-8"),
                (  # nosec B101
                    "command<<EOF\n"
                    "/cs-agent skill:fix-code-health-degradations\n"
                    "EOF\n"
                ),
            )

    def test_prepare_command_fails_when_no_cs_agent_line_present(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_path_str:
            tmp_path = Path(tmp_path_str)
            steps = load_workflow()["jobs"]["refactor"]["steps"]
            prepare_command_step = next(
                step for step in steps if step.get("id") == "prepare-command"
            )
            home_dir = tmp_path / "home"
            home_dir.mkdir()
            github_output = tmp_path / "github-output.txt"

            bash = shutil.which("bash")
            if bash is None:
                self.fail("bash not found in PATH; cannot run workflow shell test")

            result = subprocess.run(  # nosec B603
                [bash, "-e", "-c", prepare_command_step["run"]],
                check=False,
                capture_output=True,
                text=True,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": str(home_dir),
                    "LANG": "C.UTF-8",
                    "RAW_COMMENT": "This comment has no slash-command at all.",
                    "GITHUB_OUTPUT": str(github_output),
                },
            )

            self.assertNotEqual(result.returncode, 0)  # nosec B101
            self.assertIn("::error::", result.stdout)  # nosec B101
