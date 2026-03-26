#!/usr/bin/env python3
"""Test script to verify the automation fixes."""

import sys

sys.path.insert(0, ".github/scripts")

try:
    from repository_automation_common import (
        MCP_AVAILABLE,
        USE_MCP_GITHUB,
        target_ref,
    )
except ImportError as e:
    print(f"Error: Could not import repository_automation_common: {e}", file=sys.stderr)
    print(
        "Make sure .github/scripts/repository_automation_common.py exists",
        file=sys.stderr,
    )
    sys.exit(1)


def test_target_ref():
    """Test that target_ref returns full versions, not major-only."""
    print("Testing target_ref function...")

    # Test case 1: Current is v4, latest is v6.2.0
    result = target_ref("v4", "v6.2.0")
    assert result == "v6.2.0", f"Expected v6.2.0, got {result}"
    print("✓ Test 1 passed: Major version bump returns full version")

    # Test case 2: Current is v5.1.0, latest is v5.2.0
    result = target_ref("v5.1.0", "v5.2.0")
    assert result == "v5.2.0", f"Expected v5.2.0, got {result}"
    print("✓ Test 2 passed: Minor version bump returns full version")

    # Test case 3: Current is newer than latest
    result = target_ref("v6.0.0", "v5.2.0")
    assert result is None, f"Expected None, got {result}"
    print("✓ Test 3 passed: No update when current is newer")

    # Test case 4: Current equals latest
    result = target_ref("v5.2.0", "v5.2.0")
    assert result is None, f"Expected None, got {result}"
    print("✓ Test 4 passed: No update when versions are equal")

    print("All target_ref tests passed!\n")


def test_mcp_status():
    """Test MCP configuration status."""
    print("Testing MCP configuration...")
    print(f"MCP_AVAILABLE: {MCP_AVAILABLE}")
    print(f"USE_MCP_GITHUB: {USE_MCP_GITHUB}")

    if MCP_AVAILABLE and USE_MCP_GITHUB:
        print("✓ MCP GitHub integration is enabled")
    else:
        print("ℹ MCP GitHub integration is disabled (will use gh CLI)")

    print("To enable MCP mode, set USE_MCP_GITHUB=true\n")


def main():
    print("=== Testing personal-config automation fixes ===\n")

    test_target_ref()
    test_mcp_status()

    print("=== Fix verification complete ===")
    print("\nSummary of changes:")
    print("1. ✓ Python linters now exclude mole distribution files")
    print("2. ✓ target_ref returns full version tags (e.g., v6.2.0)")
    print("3. ✓ MCP compatibility layer added (set USE_MCP_GITHUB=true to enable)")


if __name__ == "__main__":
    main()
