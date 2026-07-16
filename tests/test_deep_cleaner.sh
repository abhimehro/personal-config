#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/deep_cleaner.sh
# Mocks expensive / macOS-only commands and controls find to exercise the
# monthly gate, --force bypass, incremental section skipping, and DRY_RUN.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/deep_cleaner.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-deep-cleaner')
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0

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

check_not_grep() {
	local name="$1"
	local pattern="$2"
	local file="$3"
	if grep -q "$pattern" "$file" 2>/dev/null; then
		echo "FAIL: $name (pattern '$pattern' unexpectedly found in $file)"
		FAIL=$((FAIL + 1))
	else
		echo "PASS: $name"
		PASS=$((PASS + 1))
	fi
}

# ---- mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

cat >"$MOCK_BIN/find" <<'MOCK'
#!/bin/bash
# Return a fake changed file for -newermt probes when FORCE_CHANGED is set.
# For all other invocations, behave as if the directory is empty.
if [[ "$*" == *"-newermt"* ]]; then
	if [[ -f "${DEEP_FORCE_FIND_CHANGED:-}" ]]; then
		echo "/tmp/fake-changed"
	fi
	exit 0
fi
exit 0
MOCK
chmod +x "$MOCK_BIN/find"

cat >"$MOCK_BIN/du" <<'MOCK'
#!/bin/bash
# Return empty for -h, 0B for -sh
if [[ "$1" == "-sh" ]]; then
	echo "0B"
else
	echo ""
fi
MOCK
chmod +x "$MOCK_BIN/du"

# date mock: behave normally except when MOCK_DAY_OF_MONTH=first, then %-d returns 1
cat >"$MOCK_BIN/date" <<'MOCK'
#!/bin/bash
if [[ "${MOCK_DAY_OF_MONTH:-}" == "first" && "${1:-}" == "+%-d" ]]; then
	echo "1"
else
	exec /bin/date "$@"
fi
MOCK
chmod +x "$MOCK_BIN/date"

# ---- helpers ----
make_mock_home() {
	local home="$1"
	mkdir -p "$home/Library/Logs/maintenance"
}

get_report() {
	local home="$1"
	compgen -G "$home/Library/Logs/maintenance/deep_clean_report-*.txt" 2>/dev/null | head -n 1
}

seed_state() {
	local state_dir="$1"
	local ts="${2:-9999999999}"
	mkdir -p "$state_dir"
	for key in \
		deep_cleaner_large_files \
		deep_cleaner_app_remnants \
		deep_cleaner_system_caches \
		deep_cleaner_localizations \
		deep_cleaner_duplicates \
		deep_cleaner_mobile_backups \
		deep_cleaner_vms \
		deep_cleaner_browser_profiles \
		deep_cleaner_dev_caches \
		deep_cleaner_logs \
		deep_cleaner_mail_attachments; do
		printf '%s\n' "$ts" >"$state_dir/${key}.last_run"
		chmod 600 "$state_dir/${key}.last_run"
	done
}

echo "=== Testing maintenance/bin/deep_cleaner.sh ==="

# ---- Test 1: without --force, script exits 0 with monthly skip message ----
HOME1="$TEST_DIR/home1"
make_mock_home "$HOME1"
STATE_DIR1="$TEST_DIR/state1"

# Use the real date so today (not the 1st) is used.
if HOME="$HOME1" PERSONAL_CONFIG_STATE_DIR="$STATE_DIR1" PATH="$MOCK_BIN:$PATH" \
	bash "$SCRIPT" >"$TEST_DIR/t1.log" 2>&1; then
	echo "PASS: script exits 0 when skipping monthly run"
	PASS=$((PASS + 1))
else
	echo "FAIL: script did not exit 0 when skipping monthly run"
	cat "$TEST_DIR/t1.log"
	FAIL=$((FAIL + 1))
fi

check_grep "monthly skip message" "Monthly deep cleaning skipped" "$TEST_DIR/t1.log"

# ---- Test 2: --force bypasses the monthly gate and produces a report ----
HOME2="$TEST_DIR/home2"
make_mock_home "$HOME2"
STATE_DIR2="$TEST_DIR/state2"

if MOCK_DAY_OF_MONTH=first HOME="$HOME2" PERSONAL_CONFIG_STATE_DIR="$STATE_DIR2" PATH="$MOCK_BIN:$PATH" \
	bash "$SCRIPT" --force >"$TEST_DIR/t2.log" 2>&1; then
	echo "PASS: --force bypasses monthly gate and exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: --force run exited non-zero"
	cat "$TEST_DIR/t2.log"
	FAIL=$((FAIL + 1))
fi

check_grep "deep cleaner completed" "Deep cleaning analysis complete" "$TEST_DIR/t2.log"

if [[ -n $(get_report "$HOME2") ]]; then
	echo "PASS: deep clean report created"
	PASS=$((PASS + 1))
else
	echo "FAIL: deep clean report not created"
	FAIL=$((FAIL + 1))
fi

# ---- Test 3: fresh state + empty find causes all sections to skip ----
HOME3="$TEST_DIR/home3"
make_mock_home "$HOME3"
STATE_DIR3="$TEST_DIR/state3"
seed_state "$STATE_DIR3"

if MOCK_DAY_OF_MONTH=first HOME="$HOME3" PERSONAL_CONFIG_STATE_DIR="$STATE_DIR3" PATH="$MOCK_BIN:$PATH" \
	bash "$SCRIPT" >"$TEST_DIR/t3.log" 2>&1; then
	echo "PASS: sections skip run exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: sections skip run exited non-zero"
	cat "$TEST_DIR/t3.log"
	FAIL=$((FAIL + 1))
fi

REPORT3=$(get_report "$HOME3")
check_grep "large files section skipped" "LARGEST FILES AND DIRECTORIES" "$REPORT3"
check_grep "skip message present" "Skipped - no changes since last run" "$REPORT3"

# ---- Test 4: DRY_RUN=1 with --force does not write state ----
HOME4="$TEST_DIR/home4"
make_mock_home "$HOME4"
STATE_DIR4="$TEST_DIR/state4"
seed_state "$STATE_DIR4"

touch "$TEST_DIR/force_find_changed_t4"
MOCK_DAY_OF_MONTH=first DEEP_FORCE_FIND_CHANGED="$TEST_DIR/force_find_changed_t4" \
	DRY_RUN=1 HOME="$HOME4" PERSONAL_CONFIG_STATE_DIR="$STATE_DIR4" PATH="$MOCK_BIN:$PATH" \
	bash "$SCRIPT" --force >"$TEST_DIR/t4.log" 2>&1

if grep -q "9999999999" "$STATE_DIR4/deep_cleaner_large_files.last_run" 2>/dev/null; then
	echo "PASS: DRY_RUN=1 preserves existing state for large files"
	PASS=$((PASS + 1))
else
	echo "FAIL: DRY_RUN=1 overwrote existing state for large files"
	FAIL=$((FAIL + 1))
fi

check_grep "DRY_RUN logs state write" "\[DRY RUN\] Would write last_run" "$TEST_DIR/t4.log"

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
