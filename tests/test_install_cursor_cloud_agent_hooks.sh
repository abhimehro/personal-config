#!/usr/bin/env bash
# Tests for scripts/install_cursor_cloud_agent_hooks.sh (Cursor Cloud hook sync).
set -euo pipefail

echo "=========================================="
echo "Testing install_cursor_cloud_agent_hooks.sh"
echo "=========================================="

TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'cursor-hooks-test')"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/install_cursor_cloud_agent_hooks.sh"
PRE_SRC="${REPO_ROOT}/scripts/cursor_cloud_agent_pre_commit.sh"
CM_SRC="${REPO_ROOT}/scripts/cursor_cloud_agent_commit_msg.sh"

cleanup() {
	rm -rf "$TEST_DIR"
}
trap cleanup EXIT

fail() {
	echo "❌ FAIL: $*" >&2
	exit 1
}

echo ""
echo "Test 1: Script exists and is executable"
echo "---"
[[ -x $SCRIPT ]] || fail "script missing or not executable"
echo "✅ PASS"

echo ""
echo "Test 2: Skip when hook dir has no hook files"
echo "---"
empty_dir="${TEST_DIR}/empty"
mkdir -p "$empty_dir"
out="$(CURSOR_AGENT_HOOKS_DIR="$empty_dir" bash "$SCRIPT" 2>&1)" || fail "should exit 0 when skipping"
echo "$out" | grep -q 'need both' || fail "expected skip message, got: $out"
[[ ! -f ${empty_dir}/pre-commit.cursor ]] || fail "should not create pre-commit"
echo "✅ PASS"

echo ""
echo "Test 3: Refuse when a hook path is a symlink"
echo "---"
bad_dir="${TEST_DIR}/bad-symlink"
mkdir -p "$bad_dir"
: >"${bad_dir}/commit-msg.cursor"
ln -sf /tmp/cursor-hook-target-should-not-be-written "${bad_dir}/pre-commit.cursor"
if CURSOR_AGENT_HOOKS_DIR="$bad_dir" bash "$SCRIPT" 2>/dev/null; then
	fail "expected non-zero exit when pre-commit.cursor is symlink"
fi
echo "✅ PASS"

echo ""
echo "Test 4: Install overwrites both hooks when both are regular files"
echo "---"
good_dir="${TEST_DIR}/good"
mkdir -p "$good_dir"
: >"${good_dir}/pre-commit.cursor"
: >"${good_dir}/commit-msg.cursor"
CURSOR_AGENT_HOOKS_DIR="$good_dir" bash "$SCRIPT" || fail "install should succeed"
cmp -s "$PRE_SRC" "${good_dir}/pre-commit.cursor" || fail "pre-commit content mismatch"
cmp -s "$CM_SRC" "${good_dir}/commit-msg.cursor" || fail "commit-msg content mismatch"
[[ -x ${good_dir}/pre-commit.cursor ]] || fail "pre-commit should be executable"
[[ -x ${good_dir}/commit-msg.cursor ]] || fail "commit-msg should be executable"
echo "✅ PASS"

echo ""
echo "All install_cursor_cloud_agent_hooks tests passed."
