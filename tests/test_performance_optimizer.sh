#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/performance_optimizer.sh
# Mocks macOS-only commands and controls find to exercise incremental
# state-tracking, force/dry-run semantics, and skip behavior.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/performance_optimizer.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-performance-optimizer')
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

# ---- mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

cat >"$MOCK_BIN/sysctl" <<'MOCK'
#!/bin/bash
if [[ "$1" == "-n" && "$2" == "hw.ncpu" ]]; then
	echo "4"
elif [[ "$1" == "-n" && "$2" == "hw.memsize" ]]; then
	echo "17179869184"
fi
MOCK
chmod +x "$MOCK_BIN/sysctl"

cat >"$MOCK_BIN/vm_stat" <<'MOCK'
#!/bin/bash
echo "Mach Virtual Memory Statistics: (pages active, etc)"
echo "Pages free: 100000."
echo "Pages inactive: 50000."
echo "Pages speculative: 10000."
echo "page size of 4096 bytes"
MOCK
chmod +x "$MOCK_BIN/vm_stat"

cat >"$MOCK_BIN/uptime" <<'MOCK'
#!/bin/bash
echo " 10:00AM  up 1 day,  2 users,  load averages: 0.50 0.60 0.70"
MOCK
chmod +x "$MOCK_BIN/uptime"

cat >"$MOCK_BIN/df" <<'MOCK'
#!/bin/bash
echo "Filesystem    512-blocks      Used  Available Capacity Mounted on"
echo "/dev/disk1s1  100000000  90000000  10000000     90% /"
MOCK
chmod +x "$MOCK_BIN/df"

cat >"$MOCK_BIN/du" <<'MOCK'
#!/bin/bash
# Return 0 MB for -sm, 0B for -sh
if [[ "$1" == "-sm" ]]; then
	echo "0"
else
	echo "0B"
fi
MOCK
chmod +x "$MOCK_BIN/du"

cat >"$MOCK_BIN/mdutil" <<'MOCK'
#!/bin/bash
if [[ "$1" == "-s" ]]; then
	echo "Indexing disabled."
fi
exit 0
MOCK
chmod +x "$MOCK_BIN/mdutil"

cat >"$MOCK_BIN/ping" <<'MOCK'
#!/bin/bash
echo "rtt min/avg/max/mdev = 20.123/25.456/30.789/4.123 ms"
exit 0
MOCK
chmod +x "$MOCK_BIN/ping"

cat >"$MOCK_BIN/ps" <<'MOCK'
#!/bin/bash
# Return no processes for any query pattern used by the script.
exit 0
MOCK
chmod +x "$MOCK_BIN/ps"

cat >"$MOCK_BIN/launchctl" <<'MOCK'
#!/bin/bash
if [[ "$1" == "list" ]]; then
	exit 0
fi
exit 0
MOCK
chmod +x "$MOCK_BIN/launchctl"

cat >"$MOCK_BIN/renice" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/renice"

cat >"$MOCK_BIN/dscacheutil" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/dscacheutil"

cat >"$MOCK_BIN/killall" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/killall"

cat >"$MOCK_BIN/sudo" <<'MOCK'
#!/bin/bash
exec "$@"
MOCK
chmod +x "$MOCK_BIN/sudo"

# find mock: -newermt probes return a hit only when FORCE_FIND_CHANGED is set.
# All other invocations (including delete scans) are no-ops.
cat >"$MOCK_BIN/find" <<'MOCK'
#!/bin/bash
if [[ "$*" == *"-newermt"* ]]; then
	if [[ -f "${PERF_FORCE_FIND_CHANGED:-}" ]]; then
		echo "/tmp/fake-changed"
	fi
	exit 0
fi
exit 0
MOCK
chmod +x "$MOCK_BIN/find"

# ---- helpers ----
make_mock_home() {
	local home="$1"
	mkdir -p "$home/Library/Logs/maintenance"
}

copy_script_tree() {
	local dest="$1"
	mkdir -p "$dest/bin" "$dest/lib" "$dest/config"
	cp "$SCRIPT" "$dest/bin/performance_optimizer.sh"
	cp "$REPO_ROOT/maintenance/lib/state.sh" "$dest/lib/state.sh"
}

seed_state() {
	local state_dir="$1"
	local key="$2"
	local ts="${3:-9999999999}"
	mkdir -p "$state_dir"
	printf '%s\n' "$ts" >"$state_dir/${key}.last_run"
	chmod 600 "$state_dir/${key}.last_run"
}

echo "=== Testing maintenance/bin/performance_optimizer.sh ==="

# ---- Test 1: disk action skips cache cleanup when nothing changed ----
HOME1="$TEST_DIR/home1"
make_mock_home "$HOME1"
copy_script_tree "$TEST_DIR/maint1"
STATE_DIR1="$TEST_DIR/state1"
seed_state "$STATE_DIR1" performance_optimizer_cache

if PATH="$MOCK_BIN:$PATH" HOME="$HOME1" PERSONAL_CONFIG_STATE_DIR="$STATE_DIR1" \
	bash "$TEST_DIR/maint1/bin/performance_optimizer.sh" disk >"$TEST_DIR/t1.log" 2>&1; then
	echo "PASS: disk action exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: disk action exited non-zero"
	cat "$TEST_DIR/t1.log"
	FAIL=$((FAIL + 1))
fi

check_grep "disk action skips cache cleanup when nothing changed" \
	"Cache directories unchanged; skipping disk cache cleanup" "$TEST_DIR/t1.log"

# ---- Test 2: DRY_RUN=1 prevents state writes and deletions on changed inputs ----
HOME2="$TEST_DIR/home2"
make_mock_home "$HOME2"
copy_script_tree "$TEST_DIR/maint2"
STATE_DIR2="$TEST_DIR/state2"
seed_state "$STATE_DIR2" performance_optimizer_cache

touch "$TEST_DIR/force_find_changed_t2"
PERF_FORCE_FIND_CHANGED="$TEST_DIR/force_find_changed_t2" \
	PATH="$MOCK_BIN:$PATH" HOME="$HOME2" PERSONAL_CONFIG_STATE_DIR="$STATE_DIR2" DRY_RUN=1 \
	bash "$TEST_DIR/maint2/bin/performance_optimizer.sh" disk >"$TEST_DIR/t2.log" 2>&1

if [[ ! -f "$STATE_DIR2/performance_optimizer_cache.last_run" ]] ||
	grep -q "9999999999" "$STATE_DIR2/performance_optimizer_cache.last_run" 2>/dev/null; then
	echo "PASS: DRY_RUN=1 prevents state write for disk cache"
	PASS=$((PASS + 1))
else
	echo "FAIL: state file overwritten despite DRY_RUN=1"
	FAIL=$((FAIL + 1))
fi

check_grep "DRY_RUN logs intended cache cleanup" \
	"\[DRY RUN\] Would clean files" "$TEST_DIR/t2.log"

# ---- Test 3: --force bypasses the unchanged cache skip ----
HOME3="$TEST_DIR/home3"
make_mock_home "$HOME3"
copy_script_tree "$TEST_DIR/maint3"
STATE_DIR3="$TEST_DIR/state3"
seed_state "$STATE_DIR3" performance_optimizer_cache

DRY_RUN=1 PATH="$MOCK_BIN:$PATH" HOME="$HOME3" PERSONAL_CONFIG_STATE_DIR="$STATE_DIR3" \
	bash "$TEST_DIR/maint3/bin/performance_optimizer.sh" disk --force >"$TEST_DIR/t3.log" 2>&1

check_grep "--force bypasses cache skip" "High disk usage detected" "$TEST_DIR/t3.log"
if grep -q "Cache directories unchanged" "$TEST_DIR/t3.log"; then
	echo "FAIL: --force did not bypass cache skip"
	FAIL=$((FAIL + 1))
else
	echo "PASS: --force bypasses cache skip (no unchanged message)"
	PASS=$((PASS + 1))
fi

# ---- Test 4: apps action skips temp cleanup when nothing changed ----
HOME4="$TEST_DIR/home4"
make_mock_home "$HOME4"
copy_script_tree "$TEST_DIR/maint4"
STATE_DIR4="$TEST_DIR/state4"
seed_state "$STATE_DIR4" performance_optimizer_temp

if PATH="$MOCK_BIN:$PATH" HOME="$HOME4" PERSONAL_CONFIG_STATE_DIR="$STATE_DIR4" \
	bash "$TEST_DIR/maint4/bin/performance_optimizer.sh" apps >"$TEST_DIR/t4.log" 2>&1; then
	echo "PASS: apps action exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: apps action exited non-zero"
	cat "$TEST_DIR/t4.log"
	FAIL=$((FAIL + 1))
fi

check_grep "apps action skips temp cleanup when nothing changed" \
	"Temp directories unchanged; skipping temp file cleanup" "$TEST_DIR/t4.log"

# ---- Test 5: changed inputs cause temp cleanup path to run (DRY_RUN) ----
HOME5="$TEST_DIR/home5"
make_mock_home "$HOME5"
copy_script_tree "$TEST_DIR/maint5"
STATE_DIR5="$TEST_DIR/state5"
seed_state "$STATE_DIR5" performance_optimizer_temp

touch "$TEST_DIR/force_find_changed_t5"
PERF_FORCE_FIND_CHANGED="$TEST_DIR/force_find_changed_t5" \
	PATH="$MOCK_BIN:$PATH" HOME="$HOME5" PERSONAL_CONFIG_STATE_DIR="$STATE_DIR5" DRY_RUN=1 \
	bash "$TEST_DIR/maint5/bin/performance_optimizer.sh" apps >"$TEST_DIR/t5.log" 2>&1

check_grep "changed inputs trigger temp cleanup path" \
	"\[DRY RUN\] Would clean files" "$TEST_DIR/t5.log"

# ---- Test 6: full optimize exits 0 under mocks without deleting anything ----
HOME6="$TEST_DIR/home6"
make_mock_home "$HOME6"
copy_script_tree "$TEST_DIR/maint6"

if DRY_RUN=1 PATH="$MOCK_BIN:$PATH" HOME="$HOME6" \
	bash "$TEST_DIR/maint6/bin/performance_optimizer.sh" optimize >"$TEST_DIR/t6.log" 2>&1; then
	echo "PASS: optimize action exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: optimize action exited non-zero"
	cat "$TEST_DIR/t6.log"
	FAIL=$((FAIL + 1))
fi

check_grep "optimize completes" "Performance optimization completed" "$TEST_DIR/t6.log"

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
