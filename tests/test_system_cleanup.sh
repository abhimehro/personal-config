#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/system_cleanup.sh
# Mocks brew and date; verifies cleanup logic, log creation, Monday skip,
# and cache pruning without touching real system directories.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/system_cleanup.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-system-cleanup')
trap 'rm -rf "$TEST_DIR"' EXIT

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

# Mock brew: succeed without doing anything
cat > "$MOCK_BIN/brew" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/brew"

# Mock find: wrap the real binary so permission errors in /tmp don't abort
# the script under set -eo pipefail (a Linux CI compatibility shim)
cat > "$MOCK_BIN/find" << 'MOCK'
#!/bin/bash
/usr/bin/find "$@" 2>/dev/null || true
MOCK
chmod +x "$MOCK_BIN/find"

# Mock date_monday: returns 1 (+%u = Monday), delegates other formats to real date
cat > "$MOCK_BIN/date_monday" << 'MOCK'
#!/bin/bash
if [[ "$*" == "+%u" ]]; then
    echo "1"
else
    exec /bin/date "$@"
fi
MOCK
chmod +x "$MOCK_BIN/date_monday"

# Mock date_tuesday: returns 2 (+%u = Tuesday), delegates other formats
cat > "$MOCK_BIN/date_tuesday" << 'MOCK'
#!/bin/bash
if [[ "$*" == "+%u" ]]; then
    echo "2"
else
    exec /bin/date "$@"
fi
MOCK
chmod +x "$MOCK_BIN/date_tuesday"

# ---- helper: create isolated home with required dirs ----
make_mock_home() {
    local home="$1"
    mkdir -p "$home/Library/Logs/maintenance"
    mkdir -p "$home/Library/Caches"
    mkdir -p "$home/Library/Logs"
    mkdir -p "$home/Downloads"
}

echo "=== Testing maintenance/bin/system_cleanup.sh ==="

# ---- Test 1: happy path exits 0 ----
HOME1="$TEST_DIR/home1"
make_mock_home "$HOME1"

if PATH="$MOCK_BIN:$PATH" HOME="$HOME1" \
        bash "$SCRIPT" > "$TEST_DIR/t1.log" 2>&1; then
    echo "PASS: happy path exits 0"
    PASS=$((PASS + 1))
else
    echo "FAIL: happy path exited non-zero"
    cat "$TEST_DIR/t1.log"
    FAIL=$((FAIL + 1))
fi

# ---- Test 2: system_cleanup.log is created ----
check "system_cleanup.log created" \
    test -f "$HOME1/Library/Logs/maintenance/system_cleanup.log"

# ---- Test 3: disk usage logged before and after cleanup ----
check_grep "disk usage before cleanup logged" "before cleanup" \
    "$HOME1/Library/Logs/maintenance/system_cleanup.log"

check_grep "disk usage after cleanup logged" "after cleanup" \
    "$HOME1/Library/Logs/maintenance/system_cleanup.log"

# ---- Test 4: Monday AUTOMATED_RUN skip exits 0 early ----
HOME2="$TEST_DIR/home2"
make_mock_home "$HOME2"
cp "$MOCK_BIN/date_monday" "$MOCK_BIN/date"

if PATH="$MOCK_BIN:$PATH" HOME="$HOME2" AUTOMATED_RUN=1 \
        bash "$SCRIPT" > "$TEST_DIR/t4.log" 2>&1; then
    echo "PASS: Monday AUTOMATED_RUN skip exits 0"
    PASS=$((PASS + 1))
else
    echo "FAIL: Monday AUTOMATED_RUN skip exited non-zero"
    cat "$TEST_DIR/t4.log"
    FAIL=$((FAIL + 1))
fi

if grep -q "Skipping execution on Monday" "$TEST_DIR/t4.log" 2>/dev/null; then
    echo "PASS: Monday skip prints skipping message"
    PASS=$((PASS + 1))
else
    echo "FAIL: Monday skip message not printed"
    FAIL=$((FAIL + 1))
fi
rm -f "$MOCK_BIN/date"

# ---- Test 5: non-Monday AUTOMATED_RUN does not skip ----
HOME3="$TEST_DIR/home3"
make_mock_home "$HOME3"
cp "$MOCK_BIN/date_tuesday" "$MOCK_BIN/date"

if PATH="$MOCK_BIN:$PATH" HOME="$HOME3" AUTOMATED_RUN=1 \
        bash "$SCRIPT" > "$TEST_DIR/t5.log" 2>&1; then
    echo "PASS: Tuesday AUTOMATED_RUN runs normally (exits 0)"
    PASS=$((PASS + 1))
else
    echo "FAIL: Tuesday AUTOMATED_RUN exited non-zero"
    cat "$TEST_DIR/t5.log"
    FAIL=$((FAIL + 1))
fi

if ! grep -q "Skipping execution on Monday" "$TEST_DIR/t5.log" 2>/dev/null; then
    echo "PASS: non-Monday run does not skip"
    PASS=$((PASS + 1))
else
    echo "FAIL: non-Monday run printed Monday skip message"
    FAIL=$((FAIL + 1))
fi
rm -f "$MOCK_BIN/date"

# ---- Test 6: cache pruning removes old files ----
HOME4="$TEST_DIR/home4"
make_mock_home "$HOME4"
mkdir -p "$HOME4/Library/Caches/test-mycache"
OLD_FILE="$HOME4/Library/Caches/test-mycache/oldfile.txt"
touch "$OLD_FILE"
# Set mtime well beyond the 30-day threshold (2020-01-01)
touch -t 202001010000 "$OLD_FILE"

if PATH="$MOCK_BIN:$PATH" HOME="$HOME4" CLEANUP_CACHE_DAYS=30 \
    bash "$SCRIPT" > "$TEST_DIR/t6.log" 2>&1; then
    echo "PASS: cache pruning run exited 0"
    PASS=$((PASS + 1))
else
    echo "FAIL: cache pruning run exited non-zero"
    cat "$TEST_DIR/t6.log"
    FAIL=$((FAIL + 1))
fi

if [[ ! -f "$OLD_FILE" ]]; then
    echo "PASS: old cache file pruned"
    PASS=$((PASS + 1))
else
    echo "FAIL: old cache file not pruned"
    FAIL=$((FAIL + 1))
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
