#!/bin/bash
#
# Unit tests for scripts/lib/file-common.sh
# Covers: assert_not_symlink, assert_none_are_symlinks, secure_mkdir,
#         atomic_write, source guard
# No network calls; all assertions use the local filesystem only.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-lib-file-common')
trap 'rm -rf "$TEST_DIR"' EXIT

# Source the library under test
# shellcheck source=scripts/lib/file-common.sh
source "$REPO_ROOT/scripts/lib/file-common.sh"

PASS=0
FAIL=0

check() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

check_false() {
    local name="$1"; shift
    if ! "$@" >/dev/null 2>&1; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

check_output() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (expected='$expected', got='$actual')"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Testing scripts/lib/file-common.sh ==="

# Shared fixtures
REAL_FILE="$TEST_DIR/real.txt"
LINK_FILE="$TEST_DIR/link.txt"
touch "$REAL_FILE"
ln -s "$REAL_FILE" "$LINK_FILE"

# --- assert_not_symlink ---
echo ""
echo "-- assert_not_symlink --"

check       "assert_not_symlink: returns 0 for regular file"       assert_not_symlink "$REAL_FILE"
check_false "assert_not_symlink: returns 1 for symlink"            assert_not_symlink "$LINK_FILE"
# Non-existent path is not a symlink, so should return 0.
check       "assert_not_symlink: returns 0 for non-existent path"  assert_not_symlink "$TEST_DIR/no_such_file"

# --- assert_none_are_symlinks ---
echo ""
echo "-- assert_none_are_symlinks --"

REAL_2="$TEST_DIR/real2.txt"
touch "$REAL_2"

check       "assert_none_are_symlinks: returns 0 when no symlinks present" \
    assert_none_are_symlinks "$REAL_FILE" "$REAL_2"
check_false "assert_none_are_symlinks: returns 1 when one path is a symlink" \
    assert_none_are_symlinks "$REAL_FILE" "$LINK_FILE"

# --- secure_mkdir ---
echo ""
echo "-- secure_mkdir --"

NEW_DIR="$TEST_DIR/newdir"
check "secure_mkdir creates the directory"            secure_mkdir "$NEW_DIR" 700
check "secure_mkdir is idempotent (second call ok)"   secure_mkdir "$NEW_DIR" 700

# Refuses to operate on an existing symlink.
REAL_TARGET_DIR="$TEST_DIR/realdir"
LINK_DIR="$TEST_DIR/linkdir"
mkdir "$REAL_TARGET_DIR"
ln -s "$REAL_TARGET_DIR" "$LINK_DIR"
check_false "secure_mkdir rejects an existing symlink"          secure_mkdir "$LINK_DIR"

# Refuses to overwrite an existing non-directory file.
NONDIR="$TEST_DIR/nondir"
touch "$NONDIR"
check_false "secure_mkdir rejects an existing non-directory file" secure_mkdir "$NONDIR"

# --- atomic_write ---
echo ""
echo "-- atomic_write --"

DEST="$TEST_DIR/output.txt"
atomic_write "$DEST" "hello world"
check "atomic_write creates the destination file"   test -f "$DEST"
check_output "atomic_write writes correct content"  "hello world" "$(cat "$DEST")"

# Overwrite of an existing regular file must succeed.
atomic_write "$DEST" "updated content"
check_output "atomic_write overwrites existing file" "updated content" "$(cat "$DEST")"

# Refuses to write when destination is a symlink.
LINK_TARGET="$TEST_DIR/link_target.txt"
LINK_DEST="$TEST_DIR/link_dest.txt"
touch "$LINK_TARGET"
ln -s "$LINK_TARGET" "$LINK_DEST"
ATOMIC_RC=0
(atomic_write "$LINK_DEST" "should not write" >/dev/null 2>&1) || ATOMIC_RC=$?
check "atomic_write rejects a symlink destination" test "$ATOMIC_RC" -ne 0
# The symlink target must remain untouched.
check "atomic_write does not modify the symlink target" test ! -s "$LINK_TARGET"

# --- Source guard ---
echo ""
echo "-- source guard --"
# shellcheck source=scripts/lib/file-common.sh
source "$REPO_ROOT/scripts/lib/file-common.sh"
check "source guard variable is set to 'true'" test "$_FILE_COMMON_SH_" = "true"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
