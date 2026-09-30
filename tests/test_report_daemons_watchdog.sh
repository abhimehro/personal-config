#!/usr/bin/env bash
#
# Unit tests for scripts/report-daemons-watchdog.sh
# Tests option injection protection (CWE-88) for pgrep calls.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/report-daemons-watchdog.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-report-daemons-watchdog')
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0

MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"
PGREP_LOG="$TEST_DIR/pgrep.log"

cat >"$MOCK_BIN/pgrep" <<MOCK
#!/bin/bash
echo "\$*" >> "$TEST_DIR/pgrep.log"
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"

cat >"$MOCK_BIN/ps" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/ps"

TEST_SCRIPT="$TEST_DIR/report-daemons-watchdog.sh"
cp "$SCRIPT" "$TEST_SCRIPT"
sed -i 's|export PATH=.*|export PATH="'"$MOCK_BIN"':$PATH"|g' "$TEST_SCRIPT"

RUN_OUTPUT="$TEST_DIR/run.out"
RUN_EXIT=0
bash "$TEST_SCRIPT" >"$RUN_OUTPUT" 2>&1 || RUN_EXIT=$?

if [[ $RUN_EXIT -eq 0 ]]; then
	echo "PASS: script executed successfully with mock pgrep"
	PASS=$((PASS + 1))
else
	echo "FAIL: script exited with code $RUN_EXIT"
	cat "$RUN_OUTPUT"
	FAIL=$((FAIL + 1))
fi

if grep -q "\-x -- ReportCrash" "$PGREP_LOG"; then
	echo "PASS: pgrep received '--' option separator before process name argument"
	PASS=$((PASS + 1))
else
	echo "FAIL: pgrep did not receive '--' option separator"
	cat "$PGREP_LOG" 2>/dev/null || true
	FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
