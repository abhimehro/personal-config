#!/usr/bin/env bash
#
# Unit tests for maintenance/lib/state.sh
# Mocks date and HOME to test state tracking, incremental checks, TTL, and flags.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/maintenance/lib/state.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-state')
trap 'rm -rf "$TEST_DIR"' EXIT

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

check_not() {
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

# ---- mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

# Mock date: returns a fixed epoch for date +%s, delegates everything else
# 2026-01-01 00:00:00 UTC = 1735689600
cat >"$MOCK_BIN/date" <<'MOCK'
#!/bin/bash
if [[ "${1:-}" == "+%s" ]]; then
	echo "1735689600"
else
	exec /bin/date "$@"
fi
MOCK
chmod +x "$MOCK_BIN/date"

# ---- state directory override ----
STATE_DIR="$TEST_DIR/state"
export PERSONAL_CONFIG_STATE_DIR="$STATE_DIR"

# ---- source the library ----
# Use PATH so state.sh picks up the mocked date for internal date +%s calls.
export PATH="$MOCK_BIN:$PATH"
# shellcheck disable=SC1090
source "$SOURCE"

echo "=== Testing maintenance/lib/state.sh ==="

# ---- Test 1: state_dir respects PERSONAL_CONFIG_STATE_DIR ----
if [[ $(state_dir) == "$STATE_DIR" ]]; then
	echo "PASS: state_dir uses PERSONAL_CONFIG_STATE_DIR"
	PASS=$((PASS + 1))
else
	echo "FAIL: state_dir returned '$(state_dir)', expected '$STATE_DIR'"
	FAIL=$((FAIL + 1))
fi

# ---- Test 2: state_ensure_dir creates the directory with safe permissions ----
state_ensure_dir
if [[ -d $STATE_DIR ]]; then
	echo "PASS: state_ensure_dir creates the state directory"
	PASS=$((PASS + 1))
else
	echo "FAIL: state directory not created"
	FAIL=$((FAIL + 1))
fi

# ---- Test 3: state_get_last_run returns 0 when missing ----
LAST_RUN_MISSING=$(state_get_last_run "missing_script")
if [[ $LAST_RUN_MISSING == "0" ]]; then
	echo "PASS: state_get_last_run returns 0 for missing marker"
	PASS=$((PASS + 1))
else
	echo "FAIL: expected 0 for missing marker, got '$LAST_RUN_MISSING'"
	FAIL=$((FAIL + 1))
fi

# ---- Test 4: state_set_last_run / state_get_last_run round-trip ----
state_set_last_run "test_script" "1735689600"
LAST_RUN=$(state_get_last_run "test_script")
if [[ $LAST_RUN == "1735689600" ]]; then
	echo "PASS: state_set/get_last_run round-trip"
	PASS=$((PASS + 1))
else
	echo "FAIL: expected 1735689600, got '$LAST_RUN'"
	FAIL=$((FAIL + 1))
fi

# ---- Test 5: state_set_last_run creates a sanitized file ----
if [[ -f "$STATE_DIR/test_script.last_run" ]]; then
	echo "PASS: sanitized last_run file created"
	PASS=$((PASS + 1))
else
	echo "FAIL: expected $STATE_DIR/test_script.last_run"
	FAIL=$((FAIL + 1))
fi

# ---- Test 6: DRY_RUN=1 does not write state ----
DRY_RUN=1 state_set_last_run "dryrun_test" "999" 2>"$TEST_DIR/dryrun.log" || true
if [[ ! -f "$STATE_DIR/dryrun_test.last_run" ]]; then
	echo "PASS: DRY_RUN=1 prevents state write"
	PASS=$((PASS + 1))
else
	echo "FAIL: state file written despite DRY_RUN=1"
	FAIL=$((FAIL + 1))
fi
check_grep "DRY_RUN prints skip message" "DRY RUN" "$TEST_DIR/dryrun.log"

# ---- Test 7: state_force_run_requested detects FORCE_RUN=1 ----
if FORCE_RUN=1 state_force_run_requested; then
	echo "PASS: state_force_run_requested detects FORCE_RUN=1"
	PASS=$((PASS + 1))
else
	echo "FAIL: state_force_run_requested missed FORCE_RUN=1"
	FAIL=$((FAIL + 1))
fi

# ---- Test 8: state_force_run_requested detects --force argument ----
if state_force_run_requested "--force"; then
	echo "PASS: state_force_run_requested detects --force"
	PASS=$((PASS + 1))
else
	echo "FAIL: state_force_run_requested missed --force"
	FAIL=$((FAIL + 1))
fi

# ---- Test 9: state_force_run_requested returns false by default ----
if ! state_force_run_requested; then
	echo "PASS: state_force_run_requested false by default"
	PASS=$((PASS + 1))
else
	echo "FAIL: state_force_run_requested should be false by default"
	FAIL=$((FAIL + 1))
fi

# ---- Test 10: is_modified_since_last_run returns 0 when state is missing ----
mkdir -p "$TEST_DIR/files"
touch "$TEST_DIR/files/a.txt"
if is_modified_since_last_run "$TEST_DIR/files" "new_script"; then
	echo "PASS: is_modified_since_last_run true when state missing"
	PASS=$((PASS + 1))
else
	echo "FAIL: is_modified_since_last_run should be true with missing state"
	FAIL=$((FAIL + 1))
fi

# ---- Test 11: is_modified_since_last_run returns 0 when path is newer ----
touch -d '2026-01-02 00:00:00' "$TEST_DIR/files/newer.txt"
state_set_last_run "mod_script" "1735689600"
if is_modified_since_last_run "$TEST_DIR/files" "mod_script"; then
	echo "PASS: is_modified_since_last_run detects newer file"
	PASS=$((PASS + 1))
else
	echo "FAIL: is_modified_since_last_run missed newer file"
	FAIL=$((FAIL + 1))
fi

# ---- Test 12: is_modified_since_last_run returns 1 when nothing changed ----
state_set_last_run "mod_script" "9999999999"
if ! is_modified_since_last_run "$TEST_DIR/files" "mod_script"; then
	echo "PASS: is_modified_since_last_run false when nothing changed"
	PASS=$((PASS + 1))
else
	echo "FAIL: is_modified_since_last_run should be false when nothing changed"
	FAIL=$((FAIL + 1))
fi

# ---- Test 13: is_modified_since_last_run returns 1 for non-existent path ----
if ! is_modified_since_last_run "$TEST_DIR/no_such_path" "mod_script"; then
	echo "PASS: is_modified_since_last_run false for non-existent path"
	PASS=$((PASS + 1))
else
	echo "FAIL: is_modified_since_last_run should be false for non-existent path"
	FAIL=$((FAIL + 1))
fi

# ---- Test 14: is_modified_since_last_run respects FORCE_RUN=1 ----
state_set_last_run "mod_script" "9999999999"
if FORCE_RUN=1 is_modified_since_last_run "$TEST_DIR/files" "mod_script"; then
	echo "PASS: is_modified_since_last_run honors FORCE_RUN=1"
	PASS=$((PASS + 1))
else
	echo "FAIL: is_modified_since_last_run should honor FORCE_RUN=1"
	FAIL=$((FAIL + 1))
fi

# ---- Test 15: state_ttl_expired returns true for missing/expired TTL ----
if state_ttl_expired "0" "3600"; then
	echo "PASS: state_ttl_expired true for missing timestamp"
	PASS=$((PASS + 1))
else
	echo "FAIL: state_ttl_expired should be true for missing timestamp"
	FAIL=$((FAIL + 1))
fi

# ---- Test 16: state_ttl_expired false when TTL not reached ----
# last_run == mocked now, elapsed 0 < 3600
if ! state_ttl_expired "1735689600" "3600"; then
	echo "PASS: state_ttl_expired false when TTL not reached"
	PASS=$((PASS + 1))
else
	echo "FAIL: state_ttl_expired should be false when TTL not reached"
	FAIL=$((FAIL + 1))
fi

# ---- Test 17: state_ttl_expired true when TTL exceeded ----
# 86400 seconds earlier than mocked now
if state_ttl_expired "$((1735689600 - 86400))" "3600"; then
	echo "PASS: state_ttl_expired true when TTL exceeded"
	PASS=$((PASS + 1))
else
	echo "FAIL: state_ttl_expired should be true when TTL exceeded"
	FAIL=$((FAIL + 1))
fi

# ---- Test 18: state_cache round-trip ----
state_set_cache "health_check_brew_doctor" "System ready to brew."
CACHED=$(state_get_cache "health_check_brew_doctor")
if [[ $CACHED == "System ready to brew." ]]; then
	echo "PASS: state_cache round-trip"
	PASS=$((PASS + 1))
else
	echo "FAIL: cache round-trip failed, got '$CACHED'"
	FAIL=$((FAIL + 1))
fi

# ---- Test 19: state_dir falls back to XDG_STATE_HOME ----
(
	unset PERSONAL_CONFIG_STATE_DIR
	export XDG_STATE_HOME="$TEST_DIR/xdg_state"
	EXPECTED="$TEST_DIR/xdg_state/personal-config"
	if [[ $(state_dir) == "$EXPECTED" ]]; then
		echo "PASS: state_dir falls back to XDG_STATE_HOME/personal-config"
		exit 0
	else
		echo "FAIL: state_dir returned '$(state_dir)', expected '$EXPECTED'"
		exit 1
	fi
)
result=$?
PASS=$((PASS + (result == 0 ? 1 : 0)))
FAIL=$((FAIL + (result == 0 ? 0 : 1)))

# ---- Test 20: state_dir falls back to ~/.local/state/personal-config ----
(
	unset PERSONAL_CONFIG_STATE_DIR XDG_STATE_HOME
	export HOME="$TEST_DIR/home"
	EXPECTED="$TEST_DIR/home/.local/state/personal-config"
	if [[ $(state_dir) == "$EXPECTED" ]]; then
		echo "PASS: state_dir falls back to HOME/.local/state/personal-config"
		exit 0
	else
		echo "FAIL: state_dir returned '$(state_dir)', expected '$EXPECTED'"
		exit 1
	fi
)
result=$?
PASS=$((PASS + (result == 0 ? 1 : 0)))
FAIL=$((FAIL + (result == 0 ? 0 : 1)))

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
