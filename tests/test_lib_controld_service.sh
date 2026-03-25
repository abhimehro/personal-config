#!/bin/bash
#
# Unit tests for scripts/lib/controld-service.sh
# Covers: setup_directories (happy path + symlink rejection), safe_stop,
#         show_status (service stopped), source guard
# Mocks: ctrld, pgrep, pkill, networksetup

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-lib-controld-service')
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
trap 'rm -rf "$TEST_DIR"' EXIT

# --- Mocks ---
# ctrld mock: records every invocation so we can assert it was called correctly.
CTRLD_LOG="$TEST_DIR/ctrld.log"
cat >"$MOCK_BIN/ctrld" <<MOCK
#!/bin/bash
echo "ctrld \$*" >> "$CTRLD_LOG"
exit 0
MOCK
chmod +x "$MOCK_BIN/ctrld"

# pgrep mock: ctrld is NOT running in this test environment.
cat >"$MOCK_BIN/pgrep" <<'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"

# pkill mock: always succeeds (nothing to kill).
cat >"$MOCK_BIN/pkill" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/pkill"

# networksetup mock: returns a plausible DNS value.
cat >"$MOCK_BIN/networksetup" <<'MOCK'
#!/bin/bash
echo "1.1.1.1"
MOCK
chmod +x "$MOCK_BIN/networksetup"

export PATH="$MOCK_BIN:$PATH"

# Source the library under test
# shellcheck source=scripts/lib/controld-service.sh
source "$REPO_ROOT/scripts/lib/controld-service.sh"

PASS=0
FAIL=0

check() {
	local name="$1"
	shift
	if "$@" >/dev/null 2>&1; then
		echo "PASS: $name"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $name"
		FAIL=$((FAIL + 1))
	fi
}

check_false() {
	local name="$1"
	shift
	if ! "$@" >/dev/null 2>&1; then
		echo "PASS: $name"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $name"
		FAIL=$((FAIL + 1))
	fi
}

check_grep() {
	local name="$1"
	local pattern="$2"
	local file="$3"
	if grep -q "$pattern" "$file" 2>/dev/null; then
		echo "PASS: $name"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $name (pattern '$pattern' not found in $file)"
		FAIL=$((FAIL + 1))
	fi
}

echo "=== Testing scripts/lib/controld-service.sh ==="

# --- setup_directories: happy path ---
echo ""
echo "-- setup_directories (happy path) --"

SETUP_BASE="$TEST_DIR/setup_test"
C_DIR="$SETUP_BASE/controld"
P_DIR="$SETUP_BASE/profiles"
B_DIR="$SETUP_BASE/backup"
LOG_F="$SETUP_BASE/controld.log"
mkdir -p "$SETUP_BASE"

setup_directories "$C_DIR" "$P_DIR" "$B_DIR" "$LOG_F"

check "setup_directories creates controld_dir" test -d "$C_DIR"
check "setup_directories creates profiles_dir" test -d "$P_DIR"
check "setup_directories creates backup_dir" test -d "$B_DIR"
check "setup_directories creates log file" test -f "$LOG_F"
check "log file is a regular file (not symlink)" test ! -L "$LOG_F"

# --- setup_directories: symlink rejection ---
echo ""
echo "-- setup_directories (symlink rejection) --"

SYMLINK_TARGET="$TEST_DIR/target.log"
SYMLINK_LOG="$TEST_DIR/fake.log"
touch "$SYMLINK_TARGET"
ln -s "$SYMLINK_TARGET" "$SYMLINK_LOG"

SETUP_RC=0
setup_directories "$TEST_DIR/c2" "$TEST_DIR/p2" "$TEST_DIR/b2" "$SYMLINK_LOG" \
	>/dev/null 2>&1 || SETUP_RC=$?
check "setup_directories rejects symlink log file" test "$SETUP_RC" -ne 0

# --- safe_stop ---
echo ""
echo "-- safe_stop --"

SAFESTOP_RC=0
safe_stop "$TEST_DIR" >/dev/null 2>&1 || SAFESTOP_RC=$?
check "safe_stop exits 0 when service is not running" test "$SAFESTOP_RC" -eq 0
check_grep "safe_stop invoked ctrld stop" "ctrld stop" "$CTRLD_LOG"

# --- show_status (service stopped) ---
echo ""
echo "-- show_status (stopped) --"

show_status "$TEST_DIR" >"$TEST_DIR/status.out" 2>&1 || true
check "show_status produces output" test -s "$TEST_DIR/status.out"
check_grep "show_status reports Stopped state" "Stopped" "$TEST_DIR/status.out"
check_grep "show_status prints protocol list" "doh3" "$TEST_DIR/status.out"

# --- Source guard ---
echo ""
echo "-- source guard --"
# shellcheck source=scripts/lib/controld-service.sh
source "$REPO_ROOT/scripts/lib/controld-service.sh"
check "source guard variable is set to 'true'" test "$_CONTROLD_SERVICE_SH_" = "true"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
	exit 1
fi
