#!/usr/bin/env python3
"""Test script for summary.yml workflow security validation."""

import sys
from pathlib import Path


def read_file(path):
    with open(path) as f:
        return f.read()


def main():
    filepath = Path(".github/workflows/summary.yml")
    content = read_file(filepath)

    # Test 1: YAML Parseability (basic check)
    print("=== TEST 1: YAML Parseability ===")
    if "name: Summarize new issues" not in content:
        print("✗ Workflow name not found")
        return 1
    if "jobs:" not in content:
        print("✗ jobs key not found")
        return 1
    print("✓ Basic YAML structure valid")

    # Test 2: Expected step name and location
    print("\n=== TEST 2: Step Exists ===")
    if "Comment with AI summary" not in content:
        print("✗ Step 'Comment with AI summary' not found")
        return 1
    print("✓ Step 'Comment with AI summary' exists")

    # Extract the step block (between "Comment with AI summary" and next "- name:" or end)
    step_start = content.find("- name: Comment with AI summary")
    if step_start == -1:
        print("✗ Could not find step start")
        return 1

    # Find the next step or end of steps
    next_step = content.find("\n      - name:", step_start + 1)
    step_end = content.find("\n    steps:", step_start + 1)
    if step_end == -1:
        step_end = len(content)
    if next_step != -1 and next_step < step_end:
        step_end = next_step

    step_content = content[step_start:step_end]
    print(f"  Step content preview: {repr(step_content[:200])}")

    # Test 3: Expected env scope
    print("\n=== TEST 3: Env Scope ===")
    if "env:" not in step_content:
        print("✗ No env block in step")
        return 1
    if "RESPONSE:" not in step_content:
        print("✗ RESPONSE not in env")
        return 1
    if "GH_TOKEN:" not in step_content:
        print("✗ GH_TOKEN not in env")
        return 1
    if "ISSUE_NUMBER:" not in step_content:
        print("✗ ISSUE_NUMBER not in env")
        return 1
    print("✓ RESPONSE, GH_TOKEN, ISSUE_NUMBER all in env")

    # Test 4: Secret handling
    print("\n=== TEST 4: Secret Handling ===")
    if "secrets.GITHUB_TOKEN" not in step_content:
        print("✗ secrets.GITHUB_TOKEN not found")
        return 1
    print("✓ GH_TOKEN uses secrets.GITHUB_TOKEN")

    # Test 5: RESPONSE binding
    print("\n=== TEST 5: Untrusted Output Binding ===")
    if "steps.inference.outputs.response" not in step_content:
        print("✗ steps.inference.outputs.response not found")
        return 1
    print("✓ RESPONSE bound to ${{ steps.inference.outputs.response }}")

    # Test 6-8: Shell run block analysis
    print("\n=== TESTS 6-8: Shell Run Block Analysis ===")

    # Find run block
    run_start = step_content.find("run: |")
    if run_start == -1:
        print("✗ run block not found")
        return 1

    run_block = step_content[run_start:]
    # Get the actual command
    lines = run_block.split("\n")
    command_lines = []
    for line in lines[1:]:  # Skip "run: |" line
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if stripped.startswith("gh"):
            command_lines.append(stripped)

    command = " ".join(command_lines)
    print(f"  Command: {command}")

    # Check for direct interpolation in run block
    if "${{" in run_block:
        print("✗ Direct interpolation found in run block")
        return 1
    print("✓ No direct ${{ }} interpolation in run block")

    if "$RESPONSE" not in run_block:
        print("✗ $RESPONSE not used in run block")
        return 1
    print("✓ $RESPONSE is used in run block")

    if '"$RESPONSE"' not in run_block:
        print("✗ $RESPONSE not properly quoted")
        return 1
    print("✓ $RESPONSE is properly quoted")

    # Test 9: Token permissions (check at job level)
    print("\n=== TEST 9: Token Permissions ===")
    job_start = content.find("summary:")
    job_end = content.find("\n  steps:", job_start)
    job_content = content[job_start:job_end]

    if "permissions:" not in job_content:
        print("✗ No permissions block in job")
        return 1

    if "issues: write" not in job_content:
        print("✗ issues: write not found in permissions")
        return 1
    print("✓ issues permission is write")

    # Check for minimal permissions
    if "contents: read" not in job_content:
        print("✗ contents: read not found")
        return 1

    # Make sure no admin permissions
    if "admin" in job_content:
        print("✗ Admin permissions found (over-privileged)")
        return 1

    print("✓ Least-privilege permissions granted")

    print("\n=== All Static Tests Passed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
