#!/usr/bin/env python3
"""Static security checks for .github/workflows/copilot-setup-steps.yml (CWE-94).

Validates that workflow_dispatch input is bound via env and read from
process.env in github-script, not interpolated into the script body.

Related: ABHI-929, ABHI-963, ABHI-955, ABHI-956 (malicious payload cases).
"""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOW = Path(".github/workflows/copilot-setup-steps.yml")

# Example payloads that must not break out of a JS string literal if misconfigured.
MALICIOUS_PAYLOADS = [
    '"; require("child_process").execSync("id"); //',
    "'\nprocess.exit(1)\n//",
    "${{ github.run_id }}",
]


def read_workflow() -> str:
    if not WORKFLOW.is_file():
        raise FileNotFoundError(f"Missing workflow file: {WORKFLOW}")
    return WORKFLOW.read_text(encoding="utf-8")


def extract_development_partner_step(content: str) -> str:
    marker = "- name: Development Partner Session"
    start = content.find(marker)
    if start == -1:
        raise AssertionError("Development Partner Session step not found")
    next_step = content.find("\n      - name:", start + 1)
    end = next_step if next_step != -1 else len(content)
    return content[start:end]


def test_yaml_structure(content: str) -> None:
    assert "workflow_dispatch:" in content
    assert "request:" in content
    assert "copilot-setup-steps:" in content


def test_env_binding(step: str) -> None:
    assert "env:" in step
    assert "REQUEST: ${{ github.event.inputs.request }}" in step


def test_no_direct_input_interpolation_in_script(step: str) -> None:
    script_start = step.find("script: |")
    assert script_start != -1, "github-script block not found"
    script_body = step[script_start:]
    js_lines = [
        line
        for line in script_body.splitlines()
        if line.strip() and not line.strip().startswith("//")
    ]
    js_text = "\n".join(js_lines)
    assert "github.event.inputs.request" not in js_text, (
        "Direct interpolation of workflow_dispatch input in script body "
        "(CWE-94). Use process.env.REQUEST instead."
    )
    # Only forbid ${{ inside executable JS lines (not YAML env above script block)
    assert "${{" not in js_text, "Direct ${{ }} interpolation in script body"
    assert "process.env.REQUEST" in script_body


def test_malicious_payload_would_not_embed(step: str) -> None:
    """If request were inlined in JS quotes, these payloads could break out."""
    script_start = step.find("script: |")
    script_body = step[script_start:] if script_start != -1 else ""
    for payload in MALICIOUS_PAYLOADS:
        simulated_vulnerable = f"const request = '{payload}';"
        # Vulnerable pattern: attacker-controlled chars inside single-quoted JS literal
        if (
            simulated_vulnerable.count("'") >= 2
            and "process.env" not in simulated_vulnerable
        ):
            pass  # documents why env binding matters
        assert (
            payload not in script_body
        ), "Payload must not appear literally in workflow"


def main() -> int:
    print(f"=== CWE-94 static analysis: {WORKFLOW} ===\n")
    content = read_workflow()
    test_yaml_structure(content)
    print("✓ workflow_dispatch and job structure present")

    step = extract_development_partner_step(content)
    test_env_binding(step)
    print("✓ REQUEST bound via env from github.event.inputs.request")

    test_no_direct_input_interpolation_in_script(step)
    print("✓ script uses process.env.REQUEST (no direct input interpolation)")

    test_malicious_payload_would_not_embed(step)
    print("✓ malicious payload patterns absent from script (env-binding model)")

    print("\n=== All copilot-setup-steps security checks passed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
