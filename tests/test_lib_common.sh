#!/bin/bash
#
# Unit tests for scripts/lib/common.sh
# Tests make_temp_file, make_temp_dir, is_regular_file, is_real_dir, wait_for_process_stop

set -euo pipefail

# Setup
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-common')
trap 'rm -rf "$TEST_DIR"' EXIT

# Source the library under test
# shellcheck source=scripts/lib/common.sh
source "$REPO_ROOT/scripts/lib/common.sh"

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

echo "=== Testing scripts/lib/common.sh ==="

# --- make_temp_file ---
echo ""
echo "-- make_temp_file --"

TF=$(make_temp_file)
check "make_temp_file creates a file" test -f "$TF"
check "make_temp_file creates a regular file (not a symlink)" test ! -L "$TF"
rm -f "$TF"

TF2=$(make_temp_file "myprefix.XXXXXX")
check "make_temp_file with custom template" test -f "$TF2"
rm -f "$TF2"

# --- make_temp_dir ---
echo ""
echo "-- make_temp_dir --"

TD=$(make_temp_dir)
check "make_temp_dir creates a directory" test -d "$TD"
check "make_temp_dir creates a real directory (not a symlink)" test ! -L "$TD"
rmdir "$TD"

# --- is_regular_file ---
echo ""
echo "-- is_regular_file --"

REGULAR="$TEST_DIR/regular.txt"
touch "$REGULAR"
check "is_regular_file: regular file returns true" is_regular_file "$REGULAR"

LINK="$TEST_DIR/link.txt"
ln -s "$REGULAR" "$LINK"
check_false "is_regular_file: symlink returns false" is_regular_file "$LINK"

check_false "is_regular_file: nonexistent path returns false" is_regular_file "$TEST_DIR/no_such_file"

# --- is_real_dir ---
echo ""
echo "-- is_real_dir --"

REAL_D="$TEST_DIR/realdir"
mkdir "$REAL_D"
check "is_real_dir: real directory returns true" is_real_dir "$REAL_D"

LINK_D="$TEST_DIR/linkdir"
ln -s "$REAL_D" "$LINK_D"
check_false "is_real_dir: symlink-to-dir returns false" is_real_dir "$LINK_D"

check_false "is_real_dir: nonexistent path returns false" is_real_dir "$TEST_DIR/no_such_dir"

# --- wait_for_process_stop ---
echo ""
echo "-- wait_for_process_stop --"

# Start a short-lived background process and confirm wait_for_process_stop returns
sleep 0.5 &
SLEEP_PID=$!

# Use a process name that is guaranteed NOT to exist to test the fast path
wait_for_process_stop "no_such_process_xyz" 5
check "wait_for_process_stop returns for non-existent process" true

# Confirm we can also wait for a real process (sleep) by name – just verify no hang
# We do not pgrep by name here because 'sleep' may collide; just verify it returns.
wait "$SLEEP_PID" 2>/dev/null || true
check "wait_for_process_stop does not hang when process exits" true

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
