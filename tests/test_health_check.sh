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
cat >"$MOCK_BIN/ping" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/ping"

# Mock uptime: macOS-style "load averages:" so awk parsing succeeds
cat >"$MOCK_BIN/uptime" <<'MOCK'
#!/bin/bash
echo " 10:00AM  up 1 day,  2:30, 3 users, load averages: 0.50 0.60 0.70"
MOCK
chmod +x "$MOCK_BIN/uptime"

# Mock launchctl: returns a single healthy agent (no non-zero exit codes)
cat >"$MOCK_BIN/launchctl" <<'MOCK'
#!/bin/bash
echo "0       -       com.example.agent"
MOCK
chmod +x "$MOCK_BIN/launchctl"

# Mock sysctl: return 4 CPUs regardless of argument
cat >"$MOCK_BIN/sysctl" <<'MOCK'
#!/bin/bash
echo "4"
MOCK
chmod +x "$MOCK_BIN/sysctl"

# Mock log: return empty/0 to avoid scanning system logs during tests
cat >"$MOCK_BIN/log" <<'MOCK'
#!/bin/bash
if [[ -n ${MOCK_CALL_LOG:-} ]]; then
	echo "log $*" >> "$MOCK_CALL_LOG"
fi
if [[ "$*" == *"show"* ]]; then
	echo "0"
fi
exit 0
MOCK
chmod +x "$MOCK_BIN/log"

# Mock brew: return successful doctor output instantly to avoid running actual brew doctor
cat >"$MOCK_BIN/brew" <<'MOCK'
#!/bin/bash
if [[ -n ${MOCK_CALL_LOG:-} ]]; then
	echo "brew $*" >> "$MOCK_CALL_LOG"
fi
if [[ "$*" == *"doctor"* ]]; then
	echo "Your system is ready to brew."
fi
exit 0
MOCK
chmod +x "$MOCK_BIN/brew"
cat >"$MOCK_BIN/pgrep" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/pgrep"

# ---- helper: create an isolated home with required log dirs ----
make_mock_home() {
	local home="$1"
	mkdir -p "$home/Library/Logs/maintenance"
	mkdir -p "$home/Library/Logs/DiagnosticReports"
}

# ---- helper: write a df mock returning a specific percentage ----
write_df_mock() {
	local pct="$1"
	cat >"$MOCK_BIN/df" <<MOCK
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
	bash "$SCRIPT" >"$TEST_DIR/t1.log" 2>&1; then
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
if [[ $REPORT_COUNT -gt 0 ]]; then
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

if PATH="$MOCK_BIN:$PATH" HOME="$HOME2" AUTOMATED_RUN=1 DISK_WARN_PCT=80 \
	bash "$SCRIPT" >"$TEST_DIR/t2.log" 2>&1; then
	echo "PASS: high disk usage run exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: high disk usage run exited non-zero"
	cat "$TEST_DIR/t2.log"
	FAIL=$((FAIL + 1))
fi

check_grep "high disk usage warning logged" "High disk usage" \
	"$HOME2/Library/Logs/maintenance/health_check.log"

# ---- Test 6: critical disk usage warning logged ----
HOME3="$TEST_DIR/home3"
make_mock_home "$HOME3"
write_df_mock 92

if PATH="$MOCK_BIN:$PATH" HOME="$HOME3" AUTOMATED_RUN=1 DISK_CRIT_PCT=90 \
	bash "$SCRIPT" >"$TEST_DIR/t3.log" 2>&1; then
	echo "PASS: critical disk usage run exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: critical disk usage run exited non-zero"
	cat "$TEST_DIR/t3.log"
	FAIL=$((FAIL + 1))
fi

check_grep "critical disk usage warning logged" "Critical disk usage" \
	"$HOME3/Library/Logs/maintenance/health_check.log"

# ---- Test 7: invalid DISK_CRIT_PCT in config triggers fallback warning ----
# Copy script into a temp dir with a custom conf so we control what's sourced
HOME4="$TEST_DIR/home4"
make_mock_home "$HOME4"
write_df_mock 50
mkdir -p "$TEST_DIR/maint7/bin" "$TEST_DIR/maint7/conf" "$TEST_DIR/maint7/lib"
cp "$SCRIPT" "$TEST_DIR/maint7/bin/health_check.sh"
cp "$REPO_ROOT/maintenance/lib/state.sh" "$TEST_DIR/maint7/lib/state.sh"
echo "DISK_CRIT_PCT=not_a_number" >"$TEST_DIR/maint7/conf/config.env"

if PATH="$MOCK_BIN:$PATH" HOME="$HOME4" AUTOMATED_RUN=1 \
	bash "$TEST_DIR/maint7/bin/health_check.sh" >"$TEST_DIR/t7.log" 2>&1; then
	echo "PASS: script completes (exits 0) after DISK_CRIT_PCT fallback"
	PASS=$((PASS + 1))
else
	echo "FAIL: script failed after DISK_CRIT_PCT fallback"
	cat "$TEST_DIR/t7.log"
	FAIL=$((FAIL + 1))
fi

check_grep "invalid DISK_CRIT_PCT fallback warning" "Invalid DISK_CRIT_PCT" \
	"$HOME4/Library/Logs/maintenance/health_check.log"

REPORT7=$(find "$HOME4/Library/Logs/maintenance" -name "health_report-*.txt" 2>/dev/null | wc -l | tr -d ' ')
if [[ $REPORT7 -gt 0 ]]; then
	echo "PASS: report written after DISK_CRIT_PCT fallback"
	PASS=$((PASS + 1))
else
	echo "FAIL: report not written after DISK_CRIT_PCT fallback"
	FAIL=$((FAIL + 1))
fi

# ---- Test 8: invalid HEALTH_LOG_LOOKBACK_HOURS in config triggers fallback ----
HOME5="$TEST_DIR/home5"
make_mock_home "$HOME5"
write_df_mock 50
mkdir -p "$TEST_DIR/maint8/bin" "$TEST_DIR/maint8/conf" "$TEST_DIR/maint8/lib"
cp "$SCRIPT" "$TEST_DIR/maint8/bin/health_check.sh"
cp "$REPO_ROOT/maintenance/lib/state.sh" "$TEST_DIR/maint8/lib/state.sh"
echo "HEALTH_LOG_LOOKBACK_HOURS=invalid" >"$TEST_DIR/maint8/conf/config.env"

if PATH="$MOCK_BIN:$PATH" HOME="$HOME5" AUTOMATED_RUN=1 \
	bash "$TEST_DIR/maint8/bin/health_check.sh" >"$TEST_DIR/t8.log" 2>&1; then
	echo "PASS: script completes (exits 0) after HEALTH_LOG_LOOKBACK_HOURS fallback"
	PASS=$((PASS + 1))
else
	echo "FAIL: script failed after HEALTH_LOG_LOOKBACK_HOURS fallback"
	cat "$TEST_DIR/t8.log"
	FAIL=$((FAIL + 1))
fi

check_grep "invalid HEALTH_LOG_LOOKBACK_HOURS fallback warning" \
	"Invalid HEALTH_LOG_LOOKBACK_HOURS" \
	"$HOME5/Library/Logs/maintenance/health_check.log"

REPORT8=$(find "$HOME5/Library/Logs/maintenance" -name "health_report-*.txt" 2>/dev/null | wc -l | tr -d ' ')
if [[ $REPORT8 -gt 0 ]]; then
	echo "PASS: report written after HEALTH_LOG_LOOKBACK_HOURS fallback"
	PASS=$((PASS + 1))
else
	echo "FAIL: report not written after HEALTH_LOG_LOOKBACK_HOURS fallback"
	FAIL=$((FAIL + 1))
fi

# ---- helper: copy and patch health_check.sh for TTL tests ----
# The script hardcodes /Library/Logs/DiagnosticReports; we replace it with the
# isolated mock-home directory so Linux CI can exercise the panic log branch.
copy_patched_script() {
	local dest="$1"
	local panic_dir="$2"
	mkdir -p "$dest/bin" "$dest/lib" "$dest/conf"
	cp "$SCRIPT" "$dest/bin/health_check.sh"
	cp "$REPO_ROOT/maintenance/lib/state.sh" "$dest/lib/state.sh"
	sed -i "s#/Library/Logs/DiagnosticReports#$panic_dir#g" "$dest/bin/health_check.sh"
}

# ---- helper: seed state files for TTL tests ----
seed_health_state() {
	local state_dir="$1"
	local ts="${2:-9999999999}"
	local cached_brew="${3:-Your system is ready to brew.}"
	local cached_log="${4:-0}"
	mkdir -p "$state_dir"
	for key in health_check_brew_doctor health_check_log_show_panic; do
		printf '%s\n' "$ts" >"$state_dir/${key}.last_run"
		chmod 600 "$state_dir/${key}.last_run"
	done
	printf '%s\n' "$cached_brew" >"$state_dir/health_check_brew_doctor.cache"
	chmod 600 "$state_dir/health_check_brew_doctor.cache"
	printf '%s\n' "$cached_log" >"$state_dir/health_check_log_show_panic.cache"
	chmod 600 "$state_dir/health_check_log_show_panic.cache"
}

# ---- Test 9: TTL not expired uses cached brew doctor and log show results ----
HOME6="$TEST_DIR/home6"
make_mock_home "$HOME6"
write_df_mock 70
STATE_DIR6="$TEST_DIR/state6"
seed_health_state "$STATE_DIR6" 9999999999
copy_patched_script "$TEST_DIR/maint6" "$HOME6/Library/Logs/DiagnosticReports"
MOCK_CALL_LOG="$TEST_DIR/mock_calls_9.log"
export MOCK_CALL_LOG
: >"$MOCK_CALL_LOG"

if PATH="$MOCK_BIN:$PATH" HOME="$HOME6" AUTOMATED_RUN=1 PERSONAL_CONFIG_STATE_DIR="$STATE_DIR6" \
	bash "$TEST_DIR/maint6/bin/health_check.sh" >"$TEST_DIR/t9.log" 2>&1; then
	echo "PASS: TTL not expired run exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: TTL not expired run exited non-zero"
	cat "$TEST_DIR/t9.log"
	FAIL=$((FAIL + 1))
fi

if [[ -s $MOCK_CALL_LOG ]] && grep -qE 'brew doctor|log show' "$MOCK_CALL_LOG"; then
	echo "FAIL: brew doctor or log show called when TTL not expired"
	FAIL=$((FAIL + 1))
else
	echo "PASS: brew doctor and log show not called when TTL not expired"
	PASS=$((PASS + 1))
fi

check_grep "cached brew doctor result used" "brew doctor: System ready to brew" "$HOME6/Library/Logs/maintenance/health_check.log"

# ---- Test 10: TTL expired re-runs brew doctor and log show ----
HOME7="$TEST_DIR/home7"
make_mock_home "$HOME7"
write_df_mock 70
STATE_DIR7="$TEST_DIR/state7"
seed_health_state "$STATE_DIR7" 0
copy_patched_script "$TEST_DIR/maint7" "$HOME7/Library/Logs/DiagnosticReports"
MOCK_CALL_LOG="$TEST_DIR/mock_calls_10.log"
export MOCK_CALL_LOG
: >"$MOCK_CALL_LOG"

if PATH="$MOCK_BIN:$PATH" HOME="$HOME7" AUTOMATED_RUN=1 PERSONAL_CONFIG_STATE_DIR="$STATE_DIR7" \
	bash "$TEST_DIR/maint7/bin/health_check.sh" >"$TEST_DIR/t10.log" 2>&1; then
	echo "PASS: TTL expired run exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: TTL expired run exited non-zero"
	cat "$TEST_DIR/t10.log"
	FAIL=$((FAIL + 1))
fi

check_grep "TTL expired triggers brew doctor" "brew doctor" "$MOCK_CALL_LOG"
check_grep "TTL expired triggers log show" "log show" "$MOCK_CALL_LOG"

# ---- Test 11: --force bypasses TTL and re-runs expensive checks ----
HOME8="$TEST_DIR/home8"
make_mock_home "$HOME8"
write_df_mock 70
STATE_DIR8="$TEST_DIR/state8"
seed_health_state "$STATE_DIR8" 9999999999
copy_patched_script "$TEST_DIR/maint8" "$HOME8/Library/Logs/DiagnosticReports"
MOCK_CALL_LOG="$TEST_DIR/mock_calls_11.log"
export MOCK_CALL_LOG
: >"$MOCK_CALL_LOG"

if PATH="$MOCK_BIN:$PATH" HOME="$HOME8" AUTOMATED_RUN=1 PERSONAL_CONFIG_STATE_DIR="$STATE_DIR8" \
	bash "$TEST_DIR/maint8/bin/health_check.sh" --force >"$TEST_DIR/t11.log" 2>&1; then
	echo "PASS: --force run exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: --force run exited non-zero"
	cat "$TEST_DIR/t11.log"
	FAIL=$((FAIL + 1))
fi

check_grep "--force triggers brew doctor" "brew doctor" "$MOCK_CALL_LOG"
check_grep "--force triggers log show" "log show" "$MOCK_CALL_LOG"

# ---- Test 12: DRY_RUN=1 does not update state ----
HOME9="$TEST_DIR/home9"
make_mock_home "$HOME9"
write_df_mock 70
STATE_DIR9="$TEST_DIR/state9"
seed_health_state "$STATE_DIR9" 0
copy_patched_script "$TEST_DIR/maint9" "$HOME9/Library/Logs/DiagnosticReports"
MOCK_CALL_LOG="$TEST_DIR/mock_calls_12.log"
export MOCK_CALL_LOG
: >"$MOCK_CALL_LOG"

DRY_RUN=1 PATH="$MOCK_BIN:$PATH" HOME="$HOME9" AUTOMATED_RUN=1 PERSONAL_CONFIG_STATE_DIR="$STATE_DIR9" \
	bash "$TEST_DIR/maint9/bin/health_check.sh" >"$TEST_DIR/t12.log" 2>&1

if grep -qx "0" "$STATE_DIR9/health_check_brew_doctor.last_run" 2>/dev/null; then
	echo "PASS: DRY_RUN=1 preserves existing brew doctor state"
	PASS=$((PASS + 1))
else
	echo "FAIL: DRY_RUN=1 overwrote brew doctor state"
	FAIL=$((FAIL + 1))
fi

check_grep "DRY_RUN logs intended state write" "\[DRY RUN\] Would write last_run" "$TEST_DIR/t12.log"

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
