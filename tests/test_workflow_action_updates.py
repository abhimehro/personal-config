"""Contracts for the action revisions updated in PR #2272."""

import re
import runpy
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTICS = REPO_ROOT / ".github/workflows/agentics-maintenance.yml"
SECURITY = REPO_ROOT / ".github/workflows/security-scan.yml"
PIN_VALIDATOR = REPO_ROOT / ".github/scripts/validate_workflow_pins.py"


def _section(text: str, marker: str, next_marker: str) -> str:
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line == marker]
    if len(starts) != 1:
        raise AssertionError(f"Expected one {marker!r}, found {len(starts)}")
    start = starts[0]
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if re.fullmatch(next_marker, lines[i])
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def _step(workflow: str, job: str, name: str) -> str:
    job_text = _section(workflow, f"  {job}:", r"  [A-Za-z][\w-]*:")
    return _section(job_text, f"      - name: {name}", r"      - name: .+")


class TestWorkflowActionUpdates(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.agentics = AGENTICS.read_text(encoding="utf-8")
        cls.security = SECURITY.read_text(encoding="utf-8")

    def _pin(self, step: str, action: str) -> tuple[str, str]:
        uses_lines = re.findall(r"^        uses: (.+)$", step, flags=re.MULTILINE)
        self.assertEqual(len(uses_lines), 1, step)
        match = re.fullmatch(
            rf"{re.escape(action)}@([0-9a-f]{{40}}) # (v\d+\.\d+\.\d+)",
            uses_lines[0],
        )
        self.assertIsNotNone(match, uses_lines[0])
        return match.groups()

    def _assert_line(self, step: str, line: str) -> None:
        self.assertIn(line, step.splitlines())

    def test_gh_aw_setup_and_cli_share_one_pinned_release(self) -> None:
        setup_jobs = ("close-expired-entities", "run_operation")
        pins = []
        for job in setup_jobs:
            with self.subTest(job=job):
                step = _step(self.agentics, job, "Setup Scripts")
                pins.append(self._pin(step, "github/gh-aw/actions/setup"))
                self._assert_line(step, "          destination: /opt/gh-aw/actions")

        cli = _step(self.agentics, "run_operation", "Install gh-aw")
        pins.append(self._pin(cli, "github/gh-aw/actions/setup-cli"))
        self._assert_line(cli, "          version: v0.55.0")
        self.assertEqual(pins, [pins[0]] * 3)
        self.assertNotIn("85f884513884bf03676b7531a7c713e4e2725645", self.agentics)

    def test_trufflehog_event_range_keeps_implicit_commit_range(self) -> None:
        step = _step(
            self.security, "trufflehog-secrets", "TruffleHog OSS (event range)"
        )
        self._pin(step, "trufflesecurity/trufflehog")
        self._assert_line(
            step,
            "        if: github.event_name == 'push' || "
            "github.event_name == 'pull_request'",
        )
        self._assert_line(step, "          path: ./")
        self._assert_line(step, "          extra_args: --results=verified")
        self._assert_line(step, "          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}")
        self.assertNotRegex(step, r"(?m)^          (?:base|head):")

    def test_trufflehog_full_ref_uses_same_pin_and_explicit_range(self) -> None:
        event_step = _step(
            self.security, "trufflehog-secrets", "TruffleHog OSS (event range)"
        )
        full_step = _step(
            self.security, "trufflehog-secrets", "TruffleHog OSS (full ref)"
        )
        self.assertEqual(
            self._pin(full_step, "trufflesecurity/trufflehog"),
            self._pin(event_step, "trufflesecurity/trufflehog"),
        )
        self._assert_line(
            full_step,
            "        if: github.event_name == 'schedule' || "
            "github.event_name == 'workflow_dispatch'",
        )
        self._assert_line(full_step, "          path: ./")
        self._assert_line(full_step, '          base: ""')
        self._assert_line(full_step, "          head: ${{ github.ref_name }}")
        self._assert_line(full_step, "          extra_args: --results=verified")
        self._assert_line(
            full_step, "          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}"
        )
        self.assertNotIn("f714bf454f350590f4a24c3ddb1aef02c35bf5b6", self.security)

    def test_pin_validator_rejects_one_floating_ref_among_pinned_steps(self) -> None:
        """One bad update must fail even when the other action step stays pinned."""
        event_step = _step(
            self.security, "trufflehog-secrets", "TruffleHog OSS (event range)"
        )
        sha, _version = self._pin(event_step, "trufflesecurity/trufflehog")
        broken = self.security.replace(
            f"trufflesecurity/trufflehog@{sha}",
            "trufflesecurity/trufflehog@v3.97.8",
            1,
        )
        validate_file = runpy.run_path(str(PIN_VALIDATOR))["validate_file"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "security-scan.yml"
            path.write_text(broken, encoding="utf-8")
            violations = validate_file(path)

        self.assertEqual(len(violations), 1, violations)
        self.assertIn("trufflesecurity/trufflehog@v3.97.8", violations[0])


if __name__ == "__main__":
    unittest.main()
