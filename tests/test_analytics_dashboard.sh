#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/analytics_dashboard.sh
#
# Uses mock HOME isolation and fixture JSONL metric files to run cleanly on
# Linux CI.  Verifies report creation, content validation, health scoring,
# graceful handling of empty/missing metrics, and HOME isolation.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/analytics_dashboard.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-analytics-dashboard')
# Save real HOME before any test overrides it
ORIG_HOME="$HOME"
MARKER="$TEST_DIR/start_marker"
touch "$MARKER"

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

# ---- helpers ----

# Create a mock HOME with the expected log directory structure
make_mock_home() {
	local home="$1"
	mkdir -p "$home/Library/Logs/maintenance/metrics"
	mkdir -p "$home/Library/Logs/maintenance/reports"
}

# Write fixture JSONL metrics for today so aggregate/health commands have data.
# Format mirrors what system_metrics.sh writes: one JSON object per line with
# "type" and "value" keys.
write_fixture_metrics() {
	local metrics_dir="$1"
	local today
	today=$(date +%Y%m%d)
	cat >"$metrics_dir/${today}.jsonl" <<'EOF'
{"type":"performance_score","value":85,"timestamp":"2026-03-07T10:00:00Z"}
{"type":"disk_usage_percent","value":30,"timestamp":"2026-03-07T10:00:00Z"}
{"type":"memory_free","value":4096,"timestamp":"2026-03-07T10:00:00Z"}
{"type":"health_warnings","value":0,"timestamp":"2026-03-07T10:00:00Z"}
{"type":"maintenance_agents_failed","value":0,"timestamp":"2026-03-07T10:00:00Z"}
EOF
}

echo "=== Testing maintenance/bin/analytics_dashboard.sh ==="

# ---- Test 1: summary command exits 0 on empty metrics dir (graceful degradation) ----
HOME1="$TEST_DIR/home1"
make_mock_home "$HOME1"

if HOME="$HOME1" bash "$SCRIPT" summary daily >"$TEST_DIR/t1.log" 2>&1; then
	echo "PASS: summary with empty metrics exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: summary with empty metrics exited non-zero"
	cat "$TEST_DIR/t1.log"
	FAIL=$((FAIL + 1))
fi

# ---- Test 2: summary report file created even with no metrics ----
SUMMARY_COUNT=$(find "$HOME1/Library/Logs/maintenance/reports" \
	-name "summary_daily_*.txt" 2>/dev/null | wc -l | tr -d ' ')
if [[ $SUMMARY_COUNT -gt 0 ]]; then
	echo "PASS: summary report file created"
	PASS=$((PASS + 1))
else
	echo "FAIL: summary report file not created"
	FAIL=$((FAIL + 1))
fi

# ---- Test 3: summary report contains expected header ----
SUMMARY_FILE1=$(find "$HOME1/Library/Logs/maintenance/reports" \
	-name "summary_daily_*.txt" 2>/dev/null | head -1)
check_grep "summary report has header" "SYSTEM MAINTENANCE SUMMARY REPORT" "$SUMMARY_FILE1"

# ---- Test 4: analytics.log created with [ANALYTICS] prefix entries ----
check "analytics.log created" \
	test -f "$HOME1/Library/Logs/maintenance/analytics.log"
check_grep "analytics.log uses [ANALYTICS] format" "\[ANALYTICS\]" \
	"$HOME1/Library/Logs/maintenance/analytics.log"

# ---- Test 5: dashboard command exits 0 on empty metrics dir ----
if HOME="$HOME1" bash "$SCRIPT" dashboard daily >"$TEST_DIR/t5.log" 2>&1; then
	echo "PASS: dashboard with empty metrics exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: dashboard with empty metrics exited non-zero"
	cat "$TEST_DIR/t5.log"
	FAIL=$((FAIL + 1))
fi

# ---- Test 6: HTML dashboard file created ----
DASH_COUNT=$(find "$HOME1/Library/Logs/maintenance/reports" \
	-name "dashboard_daily_*.html" 2>/dev/null | wc -l | tr -d ' ')
if [[ $DASH_COUNT -gt 0 ]]; then
	echo "PASS: HTML dashboard file created"
	PASS=$((PASS + 1))
else
	echo "FAIL: HTML dashboard file not created"
	FAIL=$((FAIL + 1))
fi

# ---- Test 7: HTML dashboard contains DOCTYPE and title ----
DASH_FILE=$(find "$HOME1/Library/Logs/maintenance/reports" \
	-name "dashboard_daily_*.html" 2>/dev/null | head -1)
check_grep "dashboard is valid HTML (DOCTYPE)" "<!DOCTYPE html>" "$DASH_FILE"
check_grep "dashboard has expected title" "System Maintenance Dashboard" "$DASH_FILE"

# ---- Test 8: health command exits 0 and outputs a numeric score ----
HOME2="$TEST_DIR/home2"
make_mock_home "$HOME2"

# log_info() uses tee -a which writes to stdout; the health score is a plain
# number on its own line.  A trailing log_info call follows main, so we filter
# for the first purely-numeric line rather than relying on tail -1.
HEALTH_OUTPUT=$(HOME="$HOME2" bash "$SCRIPT" health 2>/dev/null |
	grep -E '^[0-9]+$' | head -1)
if [[ $HEALTH_OUTPUT =~ ^[0-9]+$ ]]; then
	echo "PASS: health command returns numeric value ($HEALTH_OUTPUT)"
	PASS=$((PASS + 1))
else
	echo "FAIL: health command returned non-numeric output: '$HEALTH_OUTPUT'"
	FAIL=$((FAIL + 1))
fi

# ---- Test 9: health command returns positive score when fixture metrics are present ----
HOME3="$TEST_DIR/home3"
make_mock_home "$HOME3"
write_fixture_metrics "$HOME3/Library/Logs/maintenance/metrics"

HEALTH_SCORE=$(HOME="$HOME3" bash "$SCRIPT" health 2>/dev/null |
	grep -E '^[0-9]+$' | head -1)
if [[ $HEALTH_SCORE =~ ^[0-9]+$ ]] && [[ $HEALTH_SCORE -gt 0 ]]; then
	echo "PASS: health returns positive score with fixture metrics ($HEALTH_SCORE)"
	PASS=$((PASS + 1))
else
	echo "FAIL: expected positive health score with fixture metrics; got: '$HEALTH_SCORE'"
	FAIL=$((FAIL + 1))
fi

# ---- Test 10: summary report with fixture metrics contains health and schedule info ----
HOME4="$TEST_DIR/home4"
make_mock_home "$HOME4"
write_fixture_metrics "$HOME4/Library/Logs/maintenance/metrics"

if HOME="$HOME4" bash "$SCRIPT" summary weekly >"$TEST_DIR/t10.log" 2>&1; then
	echo "PASS: summary with fixture metrics exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: summary with fixture metrics exited non-zero"
	cat "$TEST_DIR/t10.log"
	FAIL=$((FAIL + 1))
fi

SUMMARY4=$(find "$HOME4/Library/Logs/maintenance/reports" \
	-name "summary_weekly_*.txt" 2>/dev/null | head -1)
check_grep "summary contains OVERALL HEALTH" "OVERALL HEALTH" "$SUMMARY4"
check_grep "summary contains schedule status section" "MAINTENANCE SCHEDULE STATUS" "$SUMMARY4"

# ---- Test 11: insights command exits 0 with empty metrics ----
HOME5="$TEST_DIR/home5"
make_mock_home "$HOME5"

if HOME="$HOME5" bash "$SCRIPT" insights >"$TEST_DIR/t11.log" 2>&1; then
	echo "PASS: insights with empty metrics exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: insights with empty metrics exited non-zero"
	cat "$TEST_DIR/t11.log"
	FAIL=$((FAIL + 1))
fi

# ---- Test 12: insights file created in reports directory ----
INSIGHTS_COUNT=$(find "$HOME5/Library/Logs/maintenance/reports" \
	-name "insights_*.txt" 2>/dev/null | wc -l | tr -d ' ')
if [[ $INSIGHTS_COUNT -gt 0 ]]; then
	echo "PASS: insights file created"
	PASS=$((PASS + 1))
else
	echo "FAIL: insights file not created"
	FAIL=$((FAIL + 1))
fi

# ---- Test 13: trends command exits 0 with empty metrics ----
if HOME="$HOME5" bash "$SCRIPT" trends performance_score 7 \
	>"$TEST_DIR/t13.log" 2>&1; then
	echo "PASS: trends with empty metrics exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: trends with empty metrics exited non-zero"
	cat "$TEST_DIR/t13.log"
	FAIL=$((FAIL + 1))
fi

# ---- Test 14: no writes to real HOME during test run ----
# Every test invocation above used a dedicated $TEST_DIR/homeN as HOME, so the
# real analytics.log must not be newer than our start marker.
REAL_ANALYTICS_LOG="${ORIG_HOME}/Library/Logs/maintenance/analytics.log"
if [[ ! -f $REAL_ANALYTICS_LOG ]] || [[ $REAL_ANALYTICS_LOG -ot $MARKER ]]; then
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
