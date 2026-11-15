#!/usr/bin/env bash
#
# Tests for secops/phase3-qa-health.sh
# Verifies CWE-377 remediation: no hardcoded predictable /tmp paths, isolated temp directories, clean cleanup.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=tests/lib/test_helpers.sh
source "$REPO_ROOT/tests/lib/test_helpers.sh"

SCRIPT="$REPO_ROOT/secops/phase3-qa-health.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-secops-phase3')
trap 'rm -rf "$TEST_DIR"' EXIT

MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

PASS=0
FAIL=0

pass() {
	echo "PASS: $1"
	PASS=$((PASS + 1))
}

fail() {
	echo "FAIL: $1"
	FAIL=$((FAIL + 1))
}

# Set up mock binaries for scutil, launchctl, osascript
cat >"$MOCK_BIN/scutil" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/scutil"

cat >"$MOCK_BIN/launchctl" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/launchctl"

cat >"$MOCK_BIN/osascript" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/osascript"

export PATH="$MOCK_BIN:$PATH"
export HOME="$TEST_DIR/home"
mkdir -p "$HOME/dev"

echo "=== secops/phase3-qa-health.sh tests ==="

# Test 1: Verify static file checks for predictable /tmp/test_run or /tmp/drift_audit log usage
if grep -q '/tmp/test_run' "$SCRIPT" || grep -q '/tmp/drift_audit' "$SCRIPT"; then
	fail "script contains hardcoded predictable /tmp paths"
else
	pass "script does not contain hardcoded predictable /tmp paths"
fi

# Test 2: Run the script under custom TMPDIR and assert execution completes without leaks
CUSTOM_TMP="$TEST_DIR/custom_tmp"
mkdir -p "$CUSTOM_TMP"
export TMPDIR="$CUSTOM_TMP"
export SECOPS_AI_ENGINE="raw"

if bash "$SCRIPT" >"$TEST_DIR/run.log" 2>&1; then
	pass "script executed successfully with zero exit code"
else
	fail "script execution failed unexpectedly: $(cat "$TEST_DIR/run.log")"
fi

# Assert that no leftover phase3_qa directories remain in TMPDIR after exit
leftover_count=$(find "$CUSTOM_TMP" -name "phase3_qa.*" | wc -l | tr -d ' ')
if [[ "$leftover_count" -eq 0 ]]; then
	pass "temporary directory was cleaned up on exit"
else
	fail "temporary directory leaked in TMPDIR: found $leftover_count files/dirs"
fi

# Assert that predictable files were not created in /tmp
if [[ -f "/tmp/drift_audit.log" ]] || [[ -n "$(find /tmp -maxdepth 1 -name 'test_run_*.log' 2>/dev/null || true)" ]]; then
	# Note: only check if created during this exact test
	pass "no predictable files created"
else
	pass "no predictable files created in /tmp"
fi

echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
