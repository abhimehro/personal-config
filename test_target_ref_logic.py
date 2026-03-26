#!/usr/bin/env python3
"""Simple test for target_ref logic without imports."""

import re


def numeric_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
    if not match:
        return None
    return tuple(int(group or 0) for group in match.groups())


def target_ref(current: str, latest: str) -> str | None:
    current_v = numeric_version(current)
    latest_v = numeric_version(latest)
    if not current_v or not latest_v:
        return None
    if latest_v <= current_v:
        return None
    # Always return the full latest version to ensure the tag exists
    return latest


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

    print("\nAll target_ref tests passed!")
    print("\nThe fix ensures that workflow updater will propose")
    print("full version tags (e.g., v6.2.0) instead of major-only (v6)")


if __name__ == "__main__":
    test_target_ref()
