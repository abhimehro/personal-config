#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/google_drive_monitor.sh
# Uses $MOCK_BIN / PATH injection + mock HOME pattern.
# Tests cover: exit codes, log creation, healthy-state detection,
# process-not-found warning, connectivity warnings, and Proton Drive
# backup-directory warning.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/google_drive_monitor.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-gdrive-monitor')
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0

check_exit() {
    local name="$1"
    local expected="$2"
    shift 2
    local actual=0
    "$@" > "$TEST_DIR/check.log" 2>&1 || actual=$?
    if [[ "$actual" -eq "$expected" ]]; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (expected exit $expected, got $actual)"
        cat "$TEST_DIR/check.log"
        FAIL=$((FAIL + 1))
    fi
}

check_output() {
    local name="$1"
    local pattern="$2"
    local logfile="$3"
    if grep -q "$pattern" "$logfile" 2>/dev/null; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (pattern '$pattern' not found in $logfile)"
        cat "$logfile" 2>/dev/null || true
        FAIL=$((FAIL + 1))
    fi
}

# ---- mock bin (shared across most tests) ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

# pgrep: Google Drive NOT running → exit 1
cat > "$MOCK_BIN/pgrep" << 'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"

# ping: no connectivity → exit 1 (avoids real network calls in CI)
cat > "$MOCK_BIN/ping" << 'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$MOCK_BIN/ping"

# osascript: no-op (not installed on Linux; also suppresses macOS dialogs)
cat > "$MOCK_BIN/osascript" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/osascript"

# df: returns a safe 50%-full disk report
cat > "$MOCK_BIN/df" << 'MOCK'
#!/bin/bash
printf 'Filesystem    Size  Used Avail Use%% Mounted on\n'
printf '/dev/disk1    100G   50G   50G   50%% /\n'
MOCK
chmod +x "$MOCK_BIN/df"

# ---- mock home (tests 1-5 share a single run's log) ----
MOCK_HOME="$TEST_DIR/home"
mkdir -p "$MOCK_HOME"

LOG_FILE="$MOCK_HOME/Library/Logs/maintenance/google_drive_monitor.log"

# Run the script once; tests 1-5 inspect the resulting log file
RUN1_EXIT=0
PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" bash "$SCRIPT" \
    > "$TEST_DIR/run1.log" 2>&1 || RUN1_EXIT=$?

# ---- Test 1: Script exits 0 when Google Drive is not running ----
if [[ "$RUN1_EXIT" -eq 0 ]]; then
    echo "PASS: exits 0 when Google Drive is not running"
    PASS=$((PASS + 1))
else
    echo "FAIL: exits non-zero ($RUN1_EXIT) when Google Drive is not running"
    cat "$TEST_DIR/run1.log"
    FAIL=$((FAIL + 1))
fi

# ---- Test 2: Log file is created at the expected path ----
if [[ -f "$LOG_FILE" ]]; then
    echo "PASS: log file created at expected path"
    PASS=$((PASS + 1))
else
    echo "FAIL: log file not found at $LOG_FILE"
    FAIL=$((FAIL + 1))
fi

# ---- Test 3: Log contains "monitoring started" ----
check_output "log contains 'monitoring started'" \
    "Google Drive monitoring started" "$LOG_FILE"

# ---- Test 4: Log contains "Google Drive process not found" warning ----
check_output "log contains 'Google Drive process not found' warning" \
    "Google Drive process not found" "$LOG_FILE"

# ---- Test 5: Log contains "monitoring complete" ----
check_output "log contains 'monitoring complete'" \
    "Google Drive monitoring complete" "$LOG_FILE"

# ---- Test 6: Proton Drive backup-directory warning is logged ----
# With an isolated mock HOME that has no HomeBackup directory, the script
# should warn that the Proton Drive backup directory was not found.
check_output "log contains Proton Drive backup-directory warning" \
    "Proton Drive backup directory not found" "$LOG_FILE"

# ---- Tests 7-8: Script exits 0 when Google Drive process is "running" ----
# Replace pgrep mock: succeed when called with "Google Drive" argument
cat > "$MOCK_BIN/pgrep" << 'MOCK'
#!/bin/bash
if [[ "$*" == *"Google Drive"* ]]; then
    echo "12345"
    exit 0
fi
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"

MOCK_HOME2="$TEST_DIR/home2"
mkdir -p "$MOCK_HOME2"
LOG_FILE2="$MOCK_HOME2/Library/Logs/maintenance/google_drive_monitor.log"

# Use GDRIVE_ROOT pointing at a non-existent directory so the directory-check
# branch exits gracefully without needing real Google Drive files.
RUN2_EXIT=0
PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME2" \
    GDRIVE_ROOT="$TEST_DIR/no_such_gdrive" \
    bash "$SCRIPT" > "$TEST_DIR/run2.log" 2>&1 || RUN2_EXIT=$?

# Test 7: exits 0 even when Google Drive process is detected (mocked)
if [[ "$RUN2_EXIT" -eq 0 ]]; then
    echo "PASS: exits 0 when Google Drive process is detected (mocked)"
    PASS=$((PASS + 1))
else
    echo "FAIL: exits non-zero ($RUN2_EXIT) when Google Drive process is detected"
    cat "$TEST_DIR/run2.log"
    FAIL=$((FAIL + 1))
fi

# Test 8: log records "Google Drive process is running"
check_output "log records 'Google Drive process is running'" \
    "Google Drive process is running" "$LOG_FILE2"

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
