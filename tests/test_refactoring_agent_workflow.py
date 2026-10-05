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
        approved_refactor_action = {
            "uses": "codescene-oss/pr-refactoring-agent@65c5742190fa836cdb3ee55e96afef4a0d4c95c6",
            "version": "v1.1.1",
        }

        for attempt_id in ("refactor-attempt-1", "refactor-attempt-2"):
            with self.subTest(attempt_id=attempt_id):
                self.assertEqual(
                    steps_by_id[attempt_id]["uses"], approved_refactor_action["uses"]
                )
                self.assertEqual(
                    steps_by_id[attempt_id]["with"]["version"],
                    approved_refactor_action["version"],
                )

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

    def test_upgraded_refactor_retry_preserves_request_and_provider_inputs(self) -> None:
        steps = load_workflow()["jobs"]["refactor"]["steps"]
        attempts = [
            step
            for step in steps
            if step.get("uses", "").startswith("codescene-oss/pr-refactoring-agent@")
        ]
        self.assertEqual(
            [step["id"] for step in attempts],
            ["refactor-attempt-1", "refactor-attempt-2"],
        )
        first, retry = attempts
        self.assertEqual(retry["with"], first["with"])
        self.assertEqual(retry["env"], first["env"])
        self.assertEqual(
            first["with"]["pr_number"], "${{ github.event.issue.number }}"
        )
        self.assertEqual(
            first["with"]["command"], "${{ steps.prepare-command.outputs.command }}"
        )
        self.assertEqual(first["with"]["model"], "${{ steps.providers.outputs.model }}")
        self.assertEqual(
            first["with"]["opencode_auth_json"], "${{ steps.opencode-auth.outputs.json }}"
        )
        # The action release and the requested tool version are independent.
        self.assertEqual(first["with"]["version"], "v1.1.1")
        self.assertEqual(
            first["with"]["google_api_key"],
            "${{ steps.providers.outputs.enable_google == 'true' "
            "&& secrets.GOOGLE_API_KEY || '' }}",
        )
        for key in ("GOOGLE_GENERATIVE_AI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
            with self.subTest(key=key):
                self.assertEqual(first["env"][key], first["with"]["google_api_key"])
        self.assertEqual(
            first["env"]["MISTRAL_API_KEY"],
            "${{ steps.providers.outputs.enable_mistral == 'true' "
            "&& secrets.MISTRAL_API_KEY || '' }}",
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
