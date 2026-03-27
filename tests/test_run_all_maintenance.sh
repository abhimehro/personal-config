#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/run_all_maintenance.sh
# Mocks: health_check.sh, quick_cleanup.sh, and all weekly-mode sub-scripts
#
# Pattern: script-copy + mock-sibling (see docs/TESTING.md for patterns)
# The orchestrator resolves sub-scripts relative to its own SCRIPT_DIR, so
# we copy it into a temp directory alongside mock siblings.  LOG_DIR is then
# automatically "$TEST_DIR/bin/../tmp" — no sed-patching required.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/run_all_maintenance.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-run-all-maint')
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0

check_grep() {
	local name="$1" pattern="$2" file="$3"
	if grep -q "$pattern" "$file" 2>/dev/null; then
		echo "PASS: $name"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $name (pattern '$pattern' not found in $file)"
		FAIL=$((FAIL + 1))
	fi
}

# ---- setup: place the orchestrator in a mock SCRIPT_DIR ----
# SCRIPT_DIR inside the copy = "$TEST_DIR/bin"
# LOG_DIR inside the copy   = "$TEST_DIR/bin/../tmp" = "$TEST_DIR/tmp"
MOCK_DIR="$TEST_DIR/bin"
LOG_TMP="$TEST_DIR/tmp"
mkdir -p "$MOCK_DIR"
cp "$SCRIPT" "$MOCK_DIR/run_all_maintenance.sh"

CALL_LOG="$TEST_DIR/calls.log"

# Helper: create a mock sub-script that records its invocation and exits 0
make_mock_ok() {
	local name="$1"
	cat >"$MOCK_DIR/$name" <<MOCK
#!/usr/bin/env bash
echo "$name called" >> "$CALL_LOG"
exit 0
MOCK
	chmod +x "$MOCK_DIR/$name"
}

# Helper: create a mock sub-script that records its invocation and exits 1
make_mock_fail() {
	local name="$1"
	cat >"$MOCK_DIR/$name" <<MOCK
#!/usr/bin/env bash
echo "$name called (fail)" >> "$CALL_LOG"
exit 1
MOCK
	chmod +x "$MOCK_DIR/$name"
}

# Install success mocks for every sub-script the orchestrator may invoke
for s in health_check.sh quick_cleanup.sh brew_maintenance.sh \
	node_maintenance.sh google_drive_monitor.sh service_optimizer.sh \
	performance_optimizer.sh system_cleanup.sh editor_cleanup.sh \
	deep_cleaner.sh smart_scheduler.sh generate_error_summary.sh; do
	make_mock_ok "$s"
done

echo "=== Testing maintenance/bin/run_all_maintenance.sh ==="

# ---- Test 1: help flag exits 0 ----
if bash "$MOCK_DIR/run_all_maintenance.sh" help >"$TEST_DIR/t1.log" 2>&1; then
	echo "PASS: help exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: help exited non-zero"
	cat "$TEST_DIR/t1.log"
	FAIL=$((FAIL + 1))
fi

# ---- Test 2: unknown mode exits non-zero ----
t2_exit=0
bash "$MOCK_DIR/run_all_maintenance.sh" bogus-mode >"$TEST_DIR/t2.log" 2>&1 || t2_exit=$?
if [[ $t2_exit -ne 0 ]]; then
	echo "PASS: unknown mode exits non-zero"
	PASS=$((PASS + 1))
else
	echo "FAIL: unknown mode should exit non-zero"
	FAIL=$((FAIL + 1))
fi

# ---- Test 3: health mode dispatches to health_check.sh ----
>"$CALL_LOG"
if bash "$MOCK_DIR/run_all_maintenance.sh" health >"$TEST_DIR/t3.log" 2>&1; then
	echo "PASS: health mode exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: health mode exited non-zero"
	cat "$TEST_DIR/t3.log"
	FAIL=$((FAIL + 1))
fi
check_grep "health mode calls health_check.sh" "health_check.sh called" "$CALL_LOG"

# ---- Test 4: quick mode dispatches to quick_cleanup.sh ----
>"$CALL_LOG"
if bash "$MOCK_DIR/run_all_maintenance.sh" quick >"$TEST_DIR/t4.log" 2>&1; then
	echo "PASS: quick mode exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: quick mode exited non-zero"
	cat "$TEST_DIR/t4.log"
	FAIL=$((FAIL + 1))
fi
check_grep "quick mode calls quick_cleanup.sh" "quick_cleanup.sh called" "$CALL_LOG"

# ---- Test 5: weekly mode dispatches to expected scripts ----
>"$CALL_LOG"
if bash "$MOCK_DIR/run_all_maintenance.sh" weekly >"$TEST_DIR/t5.log" 2>&1; then
	echo "PASS: weekly mode exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: weekly mode exited non-zero"
	cat "$TEST_DIR/t5.log"
	FAIL=$((FAIL + 1))
fi
check_grep "weekly calls health_check.sh" "health_check.sh called" "$CALL_LOG"
check_grep "weekly calls quick_cleanup.sh" "quick_cleanup.sh called" "$CALL_LOG"
check_grep "weekly calls performance_optimizer" "performance_optimizer.sh called" "$CALL_LOG"

# ---- Test 6: default (no-args) mode runs weekly tasks ----
>"$CALL_LOG"
if bash "$MOCK_DIR/run_all_maintenance.sh" >"$TEST_DIR/t6.log" 2>&1; then
	echo "PASS: default (no-args) mode exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: default (no-args) mode exited non-zero"
	cat "$TEST_DIR/t6.log"
	FAIL=$((FAIL + 1))
fi
check_grep "no-args calls health_check.sh" "health_check.sh called" "$CALL_LOG"
check_grep "no-args calls quick_cleanup.sh" "quick_cleanup.sh called" "$CALL_LOG"
check_grep "no-args calls performance_optimizer" "performance_optimizer.sh called" "$CALL_LOG"

# ---- Test 7: error propagation — orchestrator exits non-zero when sub-script fails ----
make_mock_fail "health_check.sh"
>"$CALL_LOG"
t7_exit=0
bash "$MOCK_DIR/run_all_maintenance.sh" health >"$TEST_DIR/t7.log" 2>&1 || t7_exit=$?
if [[ $t7_exit -ne 0 ]]; then
	echo "PASS: sub-script failure propagated to orchestrator"
	PASS=$((PASS + 1))
else
	echo "FAIL: orchestrator did not propagate sub-script failure"
	FAIL=$((FAIL + 1))
fi
make_mock_ok "health_check.sh"

# ---- Test 8: master log file is created in LOG_DIR ----
# Remove any master logs left by earlier tests so this assertion is unambiguous.
rm -f "$LOG_TMP"/maintenance_master_*.log 2>/dev/null || true
>"$CALL_LOG"
bash "$MOCK_DIR/run_all_maintenance.sh" health >"$TEST_DIR/t8.log" 2>&1
log_count=$(find "$LOG_TMP" -name "maintenance_master_*.log" -type f 2>/dev/null | wc -l | tr -d ' ')
if [[ $log_count -gt 0 ]]; then
	echo "PASS: master log file created in LOG_DIR"
	PASS=$((PASS + 1))
else
	echo "FAIL: master log file not found under $LOG_TMP"
	FAIL=$((FAIL + 1))
fi

# ---- Test 8: concurrent locking prevents second instance ----
# Pre-create a fresh lock so the orchestrator sees a recent (non-stale) lock
mkdir -p "$LOG_TMP/run_all_maintenance.lock"
>"$CALL_LOG"
t8_out=$(bash "$MOCK_DIR/run_all_maintenance.sh" health 2>&1 || true)
rmdir "$LOG_TMP/run_all_maintenance.lock" 2>/dev/null || true
if echo "$t8_out" | grep -q "already running"; then
	echo "PASS: concurrent lock blocks second instance"
	PASS=$((PASS + 1))
else
	echo "FAIL: expected 'already running' message; got: $t8_out"
	FAIL=$((FAIL + 1))
fi
if ! grep -q "health_check.sh called" "$CALL_LOG" 2>/dev/null; then
	echo "PASS: no sub-scripts called while locked"
	PASS=$((PASS + 1))
else
	echo "FAIL: sub-scripts were invoked despite active lock"
	FAIL=$((FAIL + 1))
fi

# ---- Test 9: idempotency — two sequential runs both dispatch successfully ----
>"$CALL_LOG"
bash "$MOCK_DIR/run_all_maintenance.sh" health >"$TEST_DIR/t9a.log" 2>&1
bash "$MOCK_DIR/run_all_maintenance.sh" health >"$TEST_DIR/t9b.log" 2>&1
call_count=$(grep -c "health_check.sh called" "$CALL_LOG" 2>/dev/null || true)
if [[ $call_count -eq 2 ]]; then
	echo "PASS: idempotency — two sequential runs both dispatched"
	PASS=$((PASS + 1))
else
	echo "FAIL: expected 2 health_check.sh dispatches, got $call_count"
	FAIL=$((FAIL + 1))
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
