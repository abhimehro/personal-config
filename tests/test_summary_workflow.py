#!/usr/bin/env python3
"""Static security checks for GitHub Actions untrusted-input handling.

Validates the CWE-94 mitigation pattern from ``summary.yml`` (lines 28-33):

1. Bind attacker-influenceable values in an ``env:`` block (not in ``run:`` / script).
2. Reference them only via quoted shell variables or ``process.env.*`` in JS.
3. Never interpolate ``${{ ... }}`` directly inside executable blocks.

Also verifies ``copilot-setup-steps.yml`` (#980) and all ``gemini-*.yml`` workflows
use the same binding model as the reference implementation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

_STEP_SPLIT = re.compile(r"^      - name:\s*(.+?)\s*$", re.MULTILINE)
def _extract_indented_block(step_content: str, block_kind: str) -> str:
    """Extract the body of a ``run:`` or ``script:`` folded scalar in a step."""
    header = re.search(rf"^(\s+){block_kind}:\s*(?:\|-|\|)\s*$", step_content, re.MULTILINE)
    if not header:
        raise AssertionError(f"{block_kind} block not found in step")

    body_indent = len(header.group(1)) + 2
    start = header.end()
    lines: list[str] = []
    for line in step_content[start:].splitlines(keepends=True):
        if line.strip() == "":
            lines.append(line)
            continue
        leading = len(line) - len(line.lstrip(" "))
        if leading < body_indent:
            break
        lines.append(line)
    return "".join(lines)


def read_workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def _normalize_step_name(name: str) -> str:
    return name.strip().strip('"').strip("'")


def iter_steps(content: str) -> list[tuple[str, str]]:
    """Yield (step_name, step_yaml_fragment) for each step under ``steps:``."""
    matches = list(_STEP_SPLIT.finditer(content))
    steps: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        steps.append((_normalize_step_name(match.group(1)), content[match.start() : end]))
    return steps


def extract_step(content: str, step_name: str) -> str:
    target = _normalize_step_name(step_name)
    for name, fragment in iter_steps(content):
        if name == target:
            return fragment
    raise AssertionError(f"step not found: {step_name!r}")


def extract_run_block(step_content: str) -> str:
    return _extract_indented_block(step_content, "run")


def extract_github_script_block(step_content: str) -> str:
    return _extract_indented_block(step_content, "script")


def assert_no_expression_delimiters_in_executable(executable: str, context: str) -> None:
    if "${{" in executable:
        raise AssertionError(f"${{ }} interpolation in executable block: {context}")


_UNTRUSTED_ENV_MARKERS = (
    "github.event",
    "inputs.",
    "outputs.",
    "needs.",
    "steps.",
)


def step_binds_untrusted_env(step: str) -> bool:
    """True when the step env block carries workflow/event-derived values."""
    env_start = step.find("env:")
    if env_start == -1:
        return False
    env_end = step.find("\n        uses:", env_start)
    if env_end == -1:
        env_end = step.find("\n        with:", env_start)
    if env_end == -1:
        env_end = len(step)
    env_block = step[env_start:env_end]
    return any(marker in env_block for marker in _UNTRUSTED_ENV_MARKERS)


def test_summary_yml_reference_pattern() -> None:
    """Reference implementation: summary.yml Comment with AI summary step."""
    content = read_workflow("summary.yml")
    step = extract_step(content, "Comment with AI summary")

    if "env:" not in step:
        raise AssertionError("env block missing")
    for key in ("RESPONSE", "GH_TOKEN", "ISSUE_NUMBER"):
        if f"{key}:" not in step:
            raise AssertionError(f"{key} missing from env")

    if "steps.inference.outputs.response" not in step:
        raise AssertionError("RESPONSE must bind steps.inference.outputs.response")

    if "secrets.GITHUB_TOKEN" not in step:
        raise AssertionError("GH_TOKEN must use secrets.GITHUB_TOKEN")

    run_block = extract_run_block(step)
    assert_no_expression_delimiters_in_executable(run_block, "summary.yml run block")

    if '"$RESPONSE"' not in run_block:
        raise AssertionError('run block must pass RESPONSE as a quoted shell arg')

    job_start = content.find("summary:")
    job_end = content.find("\n  steps:", job_start)
    job = content[job_start:job_end]
    if "permissions:" not in job or "issues: write" not in job:
        raise AssertionError("summary job must declare issues: write")
    if "admin" in job:
        raise AssertionError("summary job must not grant admin permissions")


def test_copilot_setup_steps_matches_summary_pattern() -> None:
    """copilot-setup-steps.yml (#980) must mirror summary.yml env binding for JS."""
    content = read_workflow("copilot-setup-steps.yml")
    step = extract_step(content, "Development Partner Session")

    if "uses: actions/github-script" not in step:
        raise AssertionError("Development Partner Session must use github-script")

    if "REQUEST:" not in step or "github.event.inputs.request" not in step:
        raise AssertionError("REQUEST must be bound from github.event.inputs.request in env")

    script = extract_github_script_block(step)
    assert_no_expression_delimiters_in_executable(script, "copilot-setup-steps script")

    if "process.env.REQUEST" not in script:
        raise AssertionError("script must read REQUEST via process.env.REQUEST")

    if re.search(r"['\"]?\$\{\{\s*github\.event\.inputs\.request", script):
        raise AssertionError("script must not interpolate workflow_dispatch input")

    if "SECURITY:" not in script and "CWE-94" not in script:
        raise AssertionError("security rationale comment expected in script")


def _iter_gemini_workflows() -> list[Path]:
    return sorted(WORKFLOWS.glob("gemini*.yml"))


def test_gemini_workflows_shell_run_blocks() -> None:
    """Gemini workflows: shell steps must not embed ${{ }} inside run bodies."""
    for path in _iter_gemini_workflows():
        content = path.read_text(encoding="utf-8")
        for step_name, step in iter_steps(content):
            if "run:" not in step:
                continue
            run_body = extract_run_block(step)
            assert_no_expression_delimiters_in_executable(
                run_body,
                f"{path.name} step {step_name!r}",
            )


def test_gemini_workflows_github_script_blocks() -> None:
    """Gemini github-script steps must use process.env, not inline ${{ }}."""
    for path in _iter_gemini_workflows():
        content = path.read_text(encoding="utf-8")
        for step_name, step in iter_steps(content):
            if "actions/github-script" not in step:
                continue
            script = extract_github_script_block(step)
            assert_no_expression_delimiters_in_executable(
                script,
                f"{path.name} github-script step {step_name!r}",
            )
            if step_binds_untrusted_env(step) and "process.env." not in script:
                raise AssertionError(
                    f"{path.name} step {step_name!r}: github-script must read env via process.env"
                )


def main() -> int:
    tests = [
        ("summary.yml reference pattern", test_summary_yml_reference_pattern),
        ("copilot-setup-steps.yml matches summary pattern", test_copilot_setup_steps_matches_summary_pattern),
        ("gemini shell run blocks", test_gemini_workflows_shell_run_blocks),
        ("gemini github-script blocks", test_gemini_workflows_github_script_blocks),
    ]

    failed = 0
    for label, fn in tests:
        print(f"=== {label} ===")
        try:
            fn()
            print("✓ passed\n")
        except AssertionError as exc:
            print(f"✗ {exc}\n")
            failed += 1

    if failed:
        print(f"=== {failed} check(s) failed ===")
        return 1

    print("=== All workflow untrusted-input checks passed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
