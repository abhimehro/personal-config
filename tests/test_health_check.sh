#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/health_check.sh
# Mocks df, ping, uptime, sysctl, launchctl to run cleanly on Linux CI

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/health_check.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-health-check')
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

# ---- shared mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

# Mock ping: always succeeds (avoids network dependency in CI)
cat > "$MOCK_BIN/ping" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/ping"

# Mock uptime: macOS-style "load averages:" so awk parsing succeeds
cat > "$MOCK_BIN/uptime" << 'MOCK'
#!/bin/bash
echo " 10:00AM  up 1 day,  2:30, 3 users, load averages: 0.50 0.60 0.70"
MOCK
chmod +x "$MOCK_BIN/uptime"

# Mock launchctl: returns a single healthy agent (no non-zero exit codes)
cat > "$MOCK_BIN/launchctl" << 'MOCK'
#!/bin/bash
echo "0       -       com.example.agent"
MOCK
chmod +x "$MOCK_BIN/launchctl"

# Mock sysctl: return 4 CPUs regardless of argument
cat > "$MOCK_BIN/sysctl" << 'MOCK'
#!/bin/bash
echo "4"
MOCK
chmod +x "$MOCK_BIN/sysctl"

# ---- helper: create an isolated home with required log dirs ----
make_mock_home() {
    local home="$1"
    mkdir -p "$home/Library/Logs/maintenance"
    mkdir -p "$home/Library/Logs/DiagnosticReports"
}

# ---- helper: write a df mock returning a specific percentage ----
write_df_mock() {
    local pct="$1"
    cat > "$MOCK_BIN/df" << MOCK
#!/bin/bash
echo "Filesystem    512-blocks      Used  Available Capacity Mounted on"
echo "/dev/disk1s1  100000000  ${pct}000000  $((100 - pct))000000     ${pct}% /"
MOCK
    chmod +x "$MOCK_BIN/df"
}

echo "=== Testing maintenance/bin/health_check.sh ==="

# ---- Test 1: happy path exits 0 ----
HOME1="$TEST_DIR/home1"
make_mock_home "$HOME1"
write_df_mock 70

if PATH="$MOCK_BIN:$PATH" HOME="$HOME1" AUTOMATED_RUN=1 \
        bash "$SCRIPT" > "$TEST_DIR/t1.log" 2>&1; then
    echo "PASS: happy path exits 0"
    PASS=$((PASS + 1))
else
    echo "FAIL: happy path exited non-zero"
    cat "$TEST_DIR/t1.log"
    FAIL=$((FAIL + 1))
fi

# ---- Test 2: health report file is created ----
REPORT_COUNT=$(find "$HOME1/Library/Logs/maintenance" \
    -name "health_report-*.txt" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$REPORT_COUNT" -gt 0 ]]; then
    echo "PASS: health report file created"
    PASS=$((PASS + 1))
else
    echo "FAIL: health report file not created"
    FAIL=$((FAIL + 1))
fi

# ---- Test 3: health_check.log is created ----
check "health_check.log created" \
    test -f "$HOME1/Library/Logs/maintenance/health_check.log"

# ---- Test 4: disk percentage appears in log ----
check_grep "disk usage logged" "Disk usage for /" \
    "$HOME1/Library/Logs/maintenance/health_check.log"

# ---- Test 5: high disk usage warning logged ----
HOME2="$TEST_DIR/home2"
make_mock_home "$HOME2"
write_df_mock 85

PATH="$MOCK_BIN:$PATH" HOME="$HOME2" AUTOMATED_RUN=1 DISK_WARN_PCT=80 \
    bash "$SCRIPT" > "$TEST_DIR/t2.log" 2>&1 || true

check_grep "high disk usage warning logged" "High disk usage" \
    "$HOME2/Library/Logs/maintenance/health_check.log"

# ---- Test 6: critical disk usage warning logged ----
HOME3="$TEST_DIR/home3"
make_mock_home "$HOME3"
write_df_mock 92

PATH="$MOCK_BIN:$PATH" HOME="$HOME3" AUTOMATED_RUN=1 DISK_CRIT_PCT=90 \
    bash "$SCRIPT" > "$TEST_DIR/t3.log" 2>&1 || true

check_grep "critical disk usage warning logged" "Critical disk usage" \
    "$HOME3/Library/Logs/maintenance/health_check.log"

# ---- Test 7: invalid DISK_CRIT_PCT in config triggers fallback warning ----
# Copy script into a temp dir with a custom conf so we control what's sourced
HOME4="$TEST_DIR/home4"
make_mock_home "$HOME4"
write_df_mock 50
mkdir -p "$TEST_DIR/maint7/bin" "$TEST_DIR/maint7/conf"
cp "$SCRIPT" "$TEST_DIR/maint7/bin/health_check.sh"
echo "DISK_CRIT_PCT=not_a_number" > "$TEST_DIR/maint7/conf/config.env"

PATH="$MOCK_BIN:$PATH" HOME="$HOME4" AUTOMATED_RUN=1 \
    bash "$TEST_DIR/maint7/bin/health_check.sh" > "$TEST_DIR/t7.log" 2>&1 || true

check_grep "invalid DISK_CRIT_PCT fallback warning" "Invalid DISK_CRIT_PCT" \
    "$HOME4/Library/Logs/maintenance/health_check.log"

# ---- Test 8: invalid HEALTH_LOG_LOOKBACK_HOURS in config triggers fallback ----
HOME5="$TEST_DIR/home5"
make_mock_home "$HOME5"
write_df_mock 50
mkdir -p "$TEST_DIR/maint8/bin" "$TEST_DIR/maint8/conf"
cp "$SCRIPT" "$TEST_DIR/maint8/bin/health_check.sh"
echo "HEALTH_LOG_LOOKBACK_HOURS=invalid" > "$TEST_DIR/maint8/conf/config.env"

PATH="$MOCK_BIN:$PATH" HOME="$HOME5" AUTOMATED_RUN=1 \
    bash "$TEST_DIR/maint8/bin/health_check.sh" > "$TEST_DIR/t8.log" 2>&1 || true

check_grep "invalid HEALTH_LOG_LOOKBACK_HOURS fallback warning" \
    "Invalid HEALTH_LOG_LOOKBACK_HOURS" \
    "$HOME5/Library/Logs/maintenance/health_check.log"

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
