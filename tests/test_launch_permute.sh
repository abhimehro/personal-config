#!/bin/bash
# Test for media-streaming/scripts/launch-permute.sh security fix (CWE-88)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TARGET_SCRIPT="$REPO_ROOT/media-streaming/scripts/launch-permute.sh"

echo "Running tests for launch-permute.sh security fix..."

# 1. Verify syntax with bash -n
bash -n "$TARGET_SCRIPT"
echo "PASS: Syntax check passed."

# 2. Check that pgrep is called with -- delimiter and redirected output
if grep -q 'pgrep -- "Permute 4" >/dev/null 2>&1' "$TARGET_SCRIPT"; then
    echo "PASS: Security fix (pgrep -- with redirection) verified in source code."
else
    echo "FAIL: Expected pgrep -- \"Permute 4\" >/dev/null 2>&1 in source code."
    exit 1
fi

# 3. Check no non-portable pgrep -q flag remains
if grep -E 'pgrep\s+-q' "$TARGET_SCRIPT"; then
    echo "FAIL: Non-portable pgrep -q flag found in source code."
    exit 1
fi

echo "All launch-permute.sh tests passed successfully!"
