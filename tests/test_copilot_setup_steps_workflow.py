#!/usr/bin/env python3
"""Static checks for copilot-setup-steps.yml CWE-94 hardening (ABHI-929)."""

import re
import sys
from pathlib import Path

WORKFLOW = Path(".github/workflows/copilot-setup-steps.yml")
STEP_MARKER = "- name: Development Partner Session"


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def extract_step_block(content: str) -> str:
    start = content.find(STEP_MARKER)
    if start == -1:
        raise ValueError(f"Step not found: {STEP_MARKER!r}")

    next_step = content.find("\n      - name:", start + len(STEP_MARKER))
    end = len(content) if next_step == -1 else next_step
    return content[start:end]


def extract_script_block(step_content: str) -> str:
    script_match = re.search(r"script:\s*\|\s*\n(.*)", step_content, re.DOTALL)
    if not script_match:
        raise ValueError("github-script script block not found")
    return script_match.group(1)


def main() -> int:
    if not WORKFLOW.is_file():
        print(f"✗ Missing workflow file: {WORKFLOW}")
        return 1

    content = read_workflow()
    step_content = extract_step_block(content)
    script_block = extract_script_block(step_content)

    print("=== TEST 1: workflow_dispatch request input ===")
    if "workflow_dispatch:" not in content:
        print("✗ workflow_dispatch trigger not found")
        return 1
    if "request:" not in content:
        print("✗ request input not defined")
        return 1
    print("✓ workflow_dispatch request input present")

    print("\n=== TEST 2: env binding for untrusted input ===")
    if "env:" not in step_content:
        print("✗ env block missing on Development Partner Session step")
        return 1
    if "REQUEST: ${{ github.event.inputs.request }}" not in step_content:
        print("✗ REQUEST not bound from github.event.inputs.request")
        return 1
    print("✓ REQUEST bound via env")

    print("\n=== TEST 3: script reads env, not interpolated expression ===")
    if "process.env.REQUEST" not in script_block:
        print("✗ script does not read process.env.REQUEST")
        return 1
    if re.search(
        r"const\s+request\s*=\s*['\"]\$\{\{\s*github\.event\.inputs\.request",
        script_block,
    ):
        print("✗ vulnerable direct interpolation in JS string literal")
        return 1
    if "${{" in script_block:
        print("✗ expression delimiter found inside github-script script block")
        return 1
    print("✓ script uses process.env.REQUEST without inline ${{ }}")

    print("\n=== TEST 4: security documentation ===")
    if "CWE-94" not in step_content:
        print("✗ CWE-94 security note missing from step")
        return 1
    print("✓ CWE-94 security note present")

    print("\n=== All Static Tests Passed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
