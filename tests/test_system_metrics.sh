#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/system_metrics.sh
# Mocks vm_stat, df, uptime, sysctl, launchctl, ps, ping, brew to run cleanly
# on Linux CI.  Verifies metrics file creation, log format, graceful
# degradation when a system command is absent, and HOME isolation.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/system_metrics.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-system-metrics')
# Save real HOME before any test overrides it
ORIG_HOME="$HOME"
MARKER="$TEST_DIR/start_marker"
touch "$MARKER"

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

# Mock uptime: macOS-style "load averages:" so awk parsing in the script succeeds
cat > "$MOCK_BIN/uptime" << 'MOCK'
#!/bin/bash
echo " 10:00AM  up 3 days,  2:30, 3 users, load averages: 0.50 0.60 0.70"
MOCK
chmod +x "$MOCK_BIN/uptime"

# Mock sysctl: return 4 CPUs regardless of argument
cat > "$MOCK_BIN/sysctl" << 'MOCK'
#!/bin/bash
echo "4"
MOCK
chmod +x "$MOCK_BIN/sysctl"

# Mock vm_stat: deterministic memory page output matching macOS format.
# Field positions match the awk selectors in system_metrics.sh:
#   /Pages free:/            -> $3 (value)
#   /Pages active:/          -> $3
#   /Pages inactive:/        -> $3
#   /Pages wired down:/      -> $4
#   /Pages stored in compressor:/ -> $5
#   /page size of/           -> $8 (page size in bytes)
cat > "$MOCK_BIN/vm_stat" << 'MOCK'
#!/bin/bash
echo "Mach Virtual Memory Statistics: (page size of 4096 bytes)"
echo "Pages free:                               12345."
echo "Pages active:                             67890."
echo "Pages inactive:                           10000."
echo "Pages speculative:                            0."
echo "Pages throttled:                              0."
echo "Pages wired down:                         20000."
echo "Pages stored in compressor:               5000."
MOCK
chmod +x "$MOCK_BIN/vm_stat"

# Mock df: return a consistent disk usage line (30% used, 350G available).
# $3=Used, $4=Avail, $5=Use% — matches NR==2 selectors in system_metrics.sh.
cat > "$MOCK_BIN/df" << 'MOCK'
#!/bin/bash
echo "Filesystem      Size  Used Avail Use% Mounted on"
echo "/dev/sda1       500G  150G  350G  30% /"
MOCK
chmod +x "$MOCK_BIN/df"

# Mock launchctl: one healthy maintenance agent (PID 0 in $1, status '-' in $2)
cat > "$MOCK_BIN/launchctl" << 'MOCK'
#!/bin/bash
echo "0       -       com.abhimehrotra.maintenance.test"
MOCK
chmod +x "$MOCK_BIN/launchctl"

# Mock ps: return a header plus two low-resource processes so that the awk
# high-CPU / high-MEM counters produce deterministic (zero) values.
cat > "$MOCK_BIN/ps" << 'MOCK'
#!/bin/bash
echo "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND"
echo "user      1234  0.0  0.1 100000  1234 ?        S    10:00   0:00 /usr/bin/proc1"
echo "user      5678  2.0  1.0 200000  2000 ?        S    10:00   0:00 /usr/bin/proc2"
MOCK
chmod +x "$MOCK_BIN/ps"

# Mock ping: succeed and emit a line containing "time=" so the awk/cut chain
# can extract a numeric latency value.
# Field layout: $7 = "time=10.123" -> cut -d'=' -f2 = "10.123"
cat > "$MOCK_BIN/ping" << 'MOCK'
#!/bin/bash
echo "PING 8.8.8.8: 56 data bytes"
echo "64 bytes from 8.8.8.8: icmp_seq=0 ttl=115 time=10.123 ms"
MOCK
chmod +x "$MOCK_BIN/ping"

# Mock brew: deterministic counts so the test is hermetic even when Homebrew
# is installed on the host.  system_metrics.sh only calls brew when it is
# present on PATH, so without this mock a real brew invocation could make the
# test slow or produce non-deterministic output.
cat > "$MOCK_BIN/brew" << 'MOCK'
#!/bin/bash
case "$1" in
    list)     printf "pkg1\npkg2\npkg3\n" ;;
    outdated) printf "old-pkg\n" ;;
    *)        exit 0 ;;
esac
MOCK
chmod +x "$MOCK_BIN/brew"

# ---- helper: create an isolated home with the expected log directories ----
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

# ---- Test 2: metrics JSONL file is created in the metrics directory ----
JSONL_COUNT=$(find "$HOME1/Library/Logs/maintenance/metrics" \
    -name "*.jsonl" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$JSONL_COUNT" -gt 0 ]]; then
    echo "PASS: metrics JSONL file created"
    PASS=$((PASS + 1))
else
    echo "FAIL: metrics JSONL file not created"
    FAIL=$((FAIL + 1))
fi

# ---- Test 3: system_metrics.log is created ----
check "system_metrics.log created" \
    test -f "$HOME1/Library/Logs/maintenance/system_metrics.log"

# ---- Test 4: log entries use the [METRIC] format ----
check_grep "log entries use [METRIC] format" "\[METRIC\]" \
    "$HOME1/Library/Logs/maintenance/system_metrics.log"

# ---- Test 5: daily summary file is created ----
SUMMARY_COUNT=$(find "$HOME1/Library/Logs/maintenance/metrics" \
    -name "daily_summary_*.txt" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$SUMMARY_COUNT" -gt 0 ]]; then
    echo "PASS: daily summary file created"
    PASS=$((PASS + 1))
else
    echo "FAIL: daily summary file not created"
    FAIL=$((FAIL + 1))
fi

# ---- Test 6: graceful degradation — exits 0 when vm_stat is absent ----
# The script guards the vm_stat block with `if command -v vm_stat >/dev/null 2>&1`
# so removing it from PATH must not abort the script under set -euo pipefail.
HOME2="$TEST_DIR/home2"
make_mock_home "$HOME2"

# Build a second mock_bin without vm_stat
MOCK_BIN2="$TEST_DIR/mock_bin2"
cp -r "$MOCK_BIN" "$MOCK_BIN2"
rm -f "$MOCK_BIN2/vm_stat"

if PATH="$MOCK_BIN2:$PATH" HOME="$HOME2" \
        bash "$SCRIPT" > "$TEST_DIR/t6.log" 2>&1; then
    echo "PASS: graceful degradation exits 0 without vm_stat"
    PASS=$((PASS + 1))
else
    echo "FAIL: script aborted when vm_stat is absent"
    cat "$TEST_DIR/t6.log"
    FAIL=$((FAIL + 1))
fi

# ---- Test 7: system_metrics.log still created when vm_stat is absent ----
check "system_metrics.log created without vm_stat" \
    test -f "$HOME2/Library/Logs/maintenance/system_metrics.log"

# ---- Test 8: no writes to real HOME during test run ----
# All test invocations above used a dedicated $TEST_DIR/homeN as HOME, so the
# real home must not have a system_metrics.log that is newer than our start marker.
REAL_METRICS_LOG="${ORIG_HOME}/Library/Logs/maintenance/system_metrics.log"
if [[ ! -f "$REAL_METRICS_LOG" ]] || [[ "$REAL_METRICS_LOG" -ot "$MARKER" ]]; then
    echo "PASS: no writes to real HOME during test"
    PASS=$((PASS + 1))
else
    echo "FAIL: script wrote to real HOME (${ORIG_HOME}/Library/Logs/maintenance)"
    FAIL=$((FAIL + 1))
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
