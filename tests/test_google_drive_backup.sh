#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/google_drive_backup.sh
# Mocks rsync and date; verifies dry-run behavior, fail-secure exclusion
# fallback, Monday skip, and argument handling.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/google_drive_backup.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-gdrive-backup')
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
        echo "FAIL: $name (pattern '$pattern' not found)"
        FAIL=$((FAIL + 1))
    fi
}

# ---- mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

# Mock rsync: accept any args, succeed silently
cat > "$MOCK_BIN/rsync" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/rsync"

# Mock date for day-of-week tests: returns Monday (1) for +%u
cat > "$MOCK_BIN/date_monday" << 'MOCK'
#!/bin/bash
if [[ "$*" == "+%u" ]]; then
    echo "1"
else
    exec /bin/date "$@"
fi
MOCK
chmod +x "$MOCK_BIN/date_monday"

# ---- shared mock home ----
MOCK_HOME="$TEST_DIR/home"
mkdir -p "$MOCK_HOME"

# ---- Test 1: --help exits 0 ----
check_exit "--help exits 0" 0 \
    bash "$SCRIPT" --help

# ---- Test 2: unknown argument exits 2 ----
check_exit "unknown arg exits 2" 2 \
    bash "$SCRIPT" --bogus-flag

# ---- Test 3: --dry-run --light exits 0 (no backup paths needed) ----
if PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" FORCE_RUN=1 \
        bash "$SCRIPT" --dry-run --light \
        > "$TEST_DIR/t3.log" 2>&1; then
    echo "PASS: --dry-run --light exits 0"
    PASS=$((PASS + 1))
else
    echo "FAIL: --dry-run --light exited non-zero"
    cat "$TEST_DIR/t3.log"
    FAIL=$((FAIL + 1))
fi

# ---- Test 4: missing excludes file triggers fail-secure fallback ----
# Pass a non-existent excludes file; script should warn and apply defaults
t4_exit=0
PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" FORCE_RUN=1 \
    bash "$SCRIPT" --dry-run --light \
    --excludes "$TEST_DIR/no_such_excludes.txt" \
    > "$TEST_DIR/t4.log" 2>&1 || t4_exit=$?
if [[ "$t4_exit" -eq 0 ]]; then
    echo "PASS: missing excludes exits 0"
    PASS=$((PASS + 1))
else
    echo "FAIL: missing excludes exited $t4_exit (expected 0)"
    cat "$TEST_DIR/t4.log"
    FAIL=$((FAIL + 1))
fi

check_output "missing excludes triggers fallback warning" \
    "DEFAULT SECURITY EXCLUSIONS" "$TEST_DIR/t4.log"

# ---- Test 5: Monday light-mode skip (no FORCE_RUN) ----
# Mock date to return Monday; light mode should skip and exit 0
cp "$MOCK_BIN/date_monday" "$MOCK_BIN/date"
if PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" \
        bash "$SCRIPT" --dry-run --light \
        > "$TEST_DIR/t5.log" 2>&1; then
    echo "PASS: Monday skip exits 0"
    PASS=$((PASS + 1))
else
    echo "FAIL: Monday skip exited non-zero"
    cat "$TEST_DIR/t5.log"
    FAIL=$((FAIL + 1))
fi

check_output "Monday skip prints skipping message" \
    "Skipping Light Backup on Monday" "$TEST_DIR/t5.log"
rm -f "$MOCK_BIN/date"

# ---- Test 6: FORCE_RUN=1 bypasses Monday skip ----
cp "$MOCK_BIN/date_monday" "$MOCK_BIN/date"
PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" FORCE_RUN=1 \
    bash "$SCRIPT" --dry-run --light \
    > "$TEST_DIR/t6.log" 2>&1 || true

# When FORCE_RUN=1, the script should NOT print the skipping message
if ! grep -q "Skipping Light Backup on Monday" "$TEST_DIR/t6.log" 2>/dev/null; then
    echo "PASS: FORCE_RUN=1 bypasses Monday skip"
    PASS=$((PASS + 1))
else
    echo "FAIL: FORCE_RUN=1 did not bypass Monday skip"
    FAIL=$((FAIL + 1))
fi
rm -f "$MOCK_BIN/date"

# ---- Test 7: --dry-run --full exits 0 ----
if PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" \
        bash "$SCRIPT" --dry-run --full \
        > "$TEST_DIR/t7.log" 2>&1; then
    echo "PASS: --dry-run --full exits 0"
    PASS=$((PASS + 1))
else
    echo "FAIL: --dry-run --full exited non-zero"
    cat "$TEST_DIR/t7.log"
    FAIL=$((FAIL + 1))
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
