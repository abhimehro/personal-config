#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/system_metrics.sh
# Mocks uptime, sysctl, vm_stat, df, dd, ping, ps, launchctl so the tests
# run cleanly on Linux CI without any macOS-specific tools.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/system_metrics.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-system-metrics')
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

# Mock uptime: macOS-style "load averages:" so the awk field-split succeeds
cat > "$MOCK_BIN/uptime" << 'MOCK'
#!/bin/bash
echo " 10:00AM  up 1 day,  2:30, 3 users, load averages: 0.50 0.60 0.70"
MOCK
chmod +x "$MOCK_BIN/uptime"

# Mock sysctl: return 4 CPUs regardless of argument
cat > "$MOCK_BIN/sysctl" << 'MOCK'
#!/bin/bash
echo "4"
MOCK
chmod +x "$MOCK_BIN/sysctl"

# Mock vm_stat: deterministic page-level memory statistics
cat > "$MOCK_BIN/vm_stat" << 'MOCK'
#!/bin/bash
echo "Mach Virtual Memory Statistics: (page size of 4096 bytes)"
echo "Pages free:                               12345."
echo "Pages active:                             67890."
echo "Pages inactive:                           11111."
echo "Pages speculative:                         2222."
echo "Pages throttled:                              0."
echo "Pages wired down:                         33333."
echo "Pages purgeable:                           4444."
echo "Pages stored in compressor:                5555."
MOCK
chmod +x "$MOCK_BIN/vm_stat"

# Mock df: 70 % disk usage, matching column positions the script expects
#   $3 = Used, $4 = Avail, $5 = Capacity (percent)
cat > "$MOCK_BIN/df" << 'MOCK'
#!/bin/bash
echo "Filesystem       Size   Used  Avail Capacity  Mounted on"
echo "/dev/disk1s1    500G   350G   150G      70%   /"
MOCK
chmod +x "$MOCK_BIN/df"

# Mock dd: succeed immediately without performing any actual I/O
cat > "$MOCK_BIN/dd" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/dd"

# Mock ping: returns a successful reply so the latency branch runs
cat > "$MOCK_BIN/ping" << 'MOCK'
#!/bin/bash
echo "PING 8.8.8.8: 56 data bytes"
echo "64 bytes from 8.8.8.8: icmp_seq=0 ttl=56 time=10.5 ms"
MOCK
chmod +x "$MOCK_BIN/ping"

# Mock ps: small deterministic process table (CPU/MEM below threshold)
cat > "$MOCK_BIN/ps" << 'MOCK'
#!/bin/bash
echo "USER   PID  %CPU %MEM    VSZ   RSS STAT STARTED      TIME COMMAND"
echo "root     1   0.0  0.1   1234   567 S    Mon01    0:00.00 launchd"
echo "root     2   0.5  0.2   2468  1024 S    Mon01    0:00.01 kernel_task"
echo "user   100   1.0  0.3   3456  2048 S    Mon01    0:00.02 bash"
MOCK
chmod +x "$MOCK_BIN/ps"

# Mock launchctl: one healthy maintenance agent (keeps the grep | wc -l pipeline happy)
cat > "$MOCK_BIN/launchctl" << 'MOCK'
#!/bin/bash
echo "0       -       com.abhimehrotra.maintenance.metrics"
MOCK
chmod +x "$MOCK_BIN/launchctl"

# ---- helper: create an isolated home with required log directories ----
make_mock_home() {
    local home="$1"
    mkdir -p "$home/Library/Logs/maintenance/metrics"
}

echo "=== Testing maintenance/bin/system_metrics.sh ==="

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

# ---- Test 2: system_metrics.log is created ----
check "system_metrics.log created" \
    test -f "$HOME1/Library/Logs/maintenance/system_metrics.log"

# ---- Test 3: metrics JSONL file is created in metrics/ subdirectory ----
if [[ -n "$(find "$HOME1/Library/Logs/maintenance/metrics" \
        -name "*.jsonl" -print -quit 2>/dev/null)" ]]; then
    echo "PASS: metrics JSONL file created"
    PASS=$((PASS + 1))
else
    echo "FAIL: metrics JSONL file not created"
    FAIL=$((FAIL + 1))
fi

# ---- Test 4: log contains [METRIC] formatted entries ----
check_grep "[METRIC] entries present in log" "\[METRIC\]" \
    "$HOME1/Library/Logs/maintenance/system_metrics.log"

# ---- Test 5: JSONL file contains the expected timestamp field ----
JSONL_FILE=$(find "$HOME1/Library/Logs/maintenance/metrics" \
    -name "*.jsonl" | head -1)
check_grep "JSONL contains timestamp field" '"timestamp"' "$JSONL_FILE"

# ---- Test 6: daily summary file is created ----
if [[ -n "$(find "$HOME1/Library/Logs/maintenance/metrics" \
        -name "daily_summary_*.txt" -print -quit 2>/dev/null)" ]]; then
    echo "PASS: daily summary file created"
    PASS=$((PASS + 1))
else
    echo "FAIL: daily summary file not created"
    FAIL=$((FAIL + 1))
fi

# ---- Test 7: memory metrics logged when vm_stat is available ----
check_grep "memory_free metric logged" "memory_free" \
    "$HOME1/Library/Logs/maintenance/system_metrics.log"

# ---- Test 8: disk usage percent metric logged ----
check_grep "disk_usage_percent metric logged" "disk_usage_percent" \
    "$HOME1/Library/Logs/maintenance/system_metrics.log"

# ---- Test 9: graceful degradation when vm_stat is absent ----
# Build a second mock bin that intentionally omits vm_stat
MOCK_BIN2="$TEST_DIR/mock_bin2"
mkdir -p "$MOCK_BIN2"
for f in uptime sysctl df dd ping ps launchctl; do
    cp "$MOCK_BIN/$f" "$MOCK_BIN2/$f"
done

HOME2="$TEST_DIR/home2"
make_mock_home "$HOME2"

if PATH="$MOCK_BIN2:$PATH" HOME="$HOME2" \
        bash "$SCRIPT" > "$TEST_DIR/t9.log" 2>&1; then
    echo "PASS: exits 0 without vm_stat (graceful degradation)"
    PASS=$((PASS + 1))
else
    echo "FAIL: exited non-zero without vm_stat"
    cat "$TEST_DIR/t9.log"
    FAIL=$((FAIL + 1))
fi

# ---- Test 10: writes are isolated to the mock HOME ----
# Verify that log files landed inside HOME1 (not the runner's real home).
if [[ -n "$(find "$HOME1/Library/Logs/maintenance" -type f -print -quit 2>/dev/null)" ]]; then
    echo "PASS: metrics written to isolated mock HOME"
    PASS=$((PASS + 1))
else
    echo "FAIL: no metric files found in mock HOME"
    FAIL=$((FAIL + 1))
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
