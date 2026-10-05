"""Offline integration contracts for the action upgrades in PR #2423.

The action implementations live upstream. These tests protect their local
invocation contracts; they do not execute third-party actions or require tokens.
"""

import unittest
from pathlib import Path
from typing import Any

import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def load_job(workflow: str, job: str) -> dict[str, Any]:
    return yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))[
        "jobs"
    ][job]


class TestConsolidatedWorkflowUpdates(unittest.TestCase):
    def action_steps(
        self, workflow: str, job: str, action: str, count: int = 1
    ) -> list[dict[str, Any]]:
        steps = [
            step
            for step in load_job(workflow, job)["steps"]
            if step.get("uses", "").split("@", 1)[0] == action
        ]
        self.assertEqual(len(steps), count, (workflow, job, action))
        return steps

    def test_upgraded_actions_use_approved_full_commit_pins(self) -> None:
        # Include repeated invocations so an upgrade cannot leave a retry or a
        # scan mode running an older action. Version inputs are separate from pins.
        cases = (
            (
                "jules-pr-review.yml",
                "review",
                "thalesraymond/jules-pr-reviewer",
                "04cb0a36e5d1a5939147845003fb99746833f7b0",
                1,
            ),
            (
                "pr-recap.yml",
                "sync",
                "actions/checkout",
                "3d3c42e5aac5ba805825da76410c181273ba90b1",
                1,
            ),
            (
                "pr-recap.yml",
                "sync",
                "actions/setup-python",
                "5fda3b95a4ea91299a34e894583c3862153e4b97",
                1,
            ),
            (
                "release-drafter.yml",
                "update_release_draft",
                "release-drafter/release-drafter",
                "72967cdc98ddd3160f1fc3dff619de365e137dd0",
                1,
            ),
            (
                "security-scan.yml",
                "trufflehog-secrets",
                "trufflesecurity/trufflehog",
                "4dd8831c5f12599465d4d45c3c447b4018a34c85",
                2,
            ),
            *(
                (
                    "security-scan.yml",
                    "codeql-analysis",
                    f"github/codeql-action/{phase}",
                    "2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2",
                    1,
                )
                for phase in ("init", "autobuild", "analyze")
            ),
            (
                "security-scan.yml",
                "sbom-generation",
                "anchore/sbom-action",
                "66cbf4bc1f1c0d2edc94016e65bc221b6bb0ad6c",
                1,
            ),
        )
        for workflow, job, action, sha, count in cases:
            with self.subTest(workflow=workflow, job=job, action=action):
                for step in self.action_steps(workflow, job, action, count):
                    self.assertEqual(step["uses"], f"{action}@{sha}")

    def test_jules_upgrade_preserves_review_safety_inputs(self) -> None:
        step = self.action_steps(
            "jules-pr-review.yml", "review", "thalesraymond/jules-pr-reviewer"
        )[0]
        inputs = step["with"]
        for name in ("skip_drafts", "skip_forks", "dedupe"):
            with self.subTest(input=name):
                self.assertIs(inputs[name], True)
        self.assertIs(inputs["enable_approve"], False)
        self.assertEqual(inputs["fail_on"], "never")
        self.assertEqual(inputs["block_on"], "high")
        self.assertEqual(inputs["min_severity_to_report"], "warning")
        self.assertEqual(inputs["jules_api_key"], "${{ secrets.JULES_API_KEY }}")
        self.assertEqual(inputs["github_token"], "${{ secrets.GITHUB_TOKEN }}")
        self.assertLess(
            inputs["timeout_minutes"],
            load_job("jules-pr-review.yml", "review")["timeout-minutes"],
        )

    def test_recap_setup_precedes_sync_and_retains_history_and_python_version(self) -> None:
        job = load_job("pr-recap.yml", "sync")
        checkout = self.action_steps("pr-recap.yml", "sync", "actions/checkout")[0]
        python = self.action_steps("pr-recap.yml", "sync", "actions/setup-python")[0]
        sync_steps = [step for step in job["steps"] if "run" in step]
        self.assertEqual(len(sync_steps), 1)
        self.assertLess(job["steps"].index(checkout), job["steps"].index(python))
        self.assertLess(job["steps"].index(python), job["steps"].index(sync_steps[0]))
        self.assertEqual(checkout["with"]["fetch-depth"], 10)
        self.assertEqual(python["with"]["python-version"], "3.12")
        for step in (checkout, python):
            with self.subTest(action=step["uses"]):
                self.assertNotIn("if", step)
                self.assertFalse(step.get("continue-on-error", False))

    def test_release_drafter_handles_pull_request_and_push_commit_sources(self) -> None:
        step = self.action_steps(
            "release-drafter.yml",
            "update_release_draft",
            "release-drafter/release-drafter",
        )[0]
        # Push events have no pull_request object; retain the github.sha fallback.
        self.assertEqual(
            step["with"]["commitish"],
            "${{ github.event.pull_request.head.sha || github.sha }}",
        )
        self.assertEqual(step["env"]["GITHUB_TOKEN"], "${{ secrets.GITHUB_TOKEN }}")
        self.assertNotIn("if", step)

    def test_codeql_upgrade_preserves_phase_order_and_language_partitioning(self) -> None:
        job = load_job("security-scan.yml", "codeql-analysis")
        phases = [
            self.action_steps(
                "security-scan.yml", "codeql-analysis", f"github/codeql-action/{phase}"
            )[0]
            for phase in ("init", "autobuild", "analyze")
        ]
        positions = [job["steps"].index(step) for step in phases]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(job["strategy"]["matrix"]["language"], ["javascript", "python"])
        self.assertIs(job["strategy"]["fail-fast"], False)
        self.assertEqual(phases[0]["with"]["languages"], "${{ matrix.language }}")
        self.assertEqual(
            phases[2]["with"]["category"], "/language:${{ matrix.language }}"
        )
        self.assertIs(phases[2]["continue-on-error"], True)
        for step in phases[:2]:
            with self.subTest(action=step["uses"]):
                self.assertFalse(step.get("continue-on-error", False))
        for step in phases:
            with self.subTest(action=step["uses"]):
                self.assertNotIn("if", step)

    def test_sbom_output_matches_uploaded_artifact(self) -> None:
        job = load_job("security-scan.yml", "sbom-generation")
        generate = self.action_steps(
            "security-scan.yml", "sbom-generation", "anchore/sbom-action"
        )[0]
        upload = self.action_steps(
            "security-scan.yml", "sbom-generation", "actions/upload-artifact"
        )[0]
        self.assertEqual(generate["with"]["image"], ".")
        self.assertEqual(generate["with"]["format"], "spdx-json")
        self.assertEqual(generate["with"]["output-file"], "sbom.spdx.json")
        self.assertEqual(upload["with"]["path"], generate["with"]["output-file"])
        self.assertLess(job["steps"].index(generate), job["steps"].index(upload))


if __name__ == "__main__":
    unittest.main()
