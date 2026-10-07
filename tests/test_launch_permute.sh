#!/bin/bash
# Test for media-streaming/scripts/launch-permute.sh syntax and security checks

set -euo pipefail

SCRIPT_PATH="media-streaming/scripts/launch-permute.sh"

echo "=== Testing $SCRIPT_PATH ==="

# 1. Syntax check
if bash -n "$SCRIPT_PATH"; then
    echo "PASS: $SCRIPT_PATH passes bash syntax check"
else
    echo "FAIL: $SCRIPT_PATH has bash syntax errors"
    exit 1
fi

# 2. Verify pgrep usage is safe from option injection (contains --) and does not use unsupported -q
if grep -q "pgrep -q" "$SCRIPT_PATH"; then
    echo "FAIL: $SCRIPT_PATH uses unsupported 'pgrep -q'"
    exit 1
else
    echo "PASS: $SCRIPT_PATH does not use 'pgrep -q'"
fi

if grep -q 'pgrep -f --' "$SCRIPT_PATH"; then
    echo "PASS: $SCRIPT_PATH uses safe 'pgrep -f --' delimiter"
else
    echo "FAIL: $SCRIPT_PATH does not use 'pgrep -f --'"
    exit 1
fi

echo "All tests passed for $SCRIPT_PATH!"
