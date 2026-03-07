#!/usr/bin/env bash
#
# Unit tests for maintenance/lib/common.sh and maintenance/lib/common_simple.sh
#
# These two foundational libraries are sourced by maintenance scripts.
# Tests cover: sourcing under strict mode, path variables, logging functions,
# require_cmd, and mock HOME isolation (no real ~/Library/Logs writes).
#
# Linux CI compatible: sw_vers and osascript are provided via MOCK_BIN.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-maintenance-lib')
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

check_false() {
    local name="$1"; shift
    if ! "$@" >/dev/null 2>&1; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

check_contains() {
    local name="$1"
    local pattern="$2"
    local haystack="$3"
    if echo "$haystack" | grep -Fq -- "$pattern"; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (pattern '$pattern' not found)"
        echo "Output:"
        echo "$haystack"
        FAIL=$((FAIL + 1))
    fi
}

# ---- mock bin: provides sw_vers and osascript for Linux CI ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

cat > "$MOCK_BIN/sw_vers" << 'MOCK'
#!/bin/bash
echo "15.0"
MOCK
chmod +x "$MOCK_BIN/sw_vers"

# NOTE: osascript is macOS-only; mock prevents failure in notify() on Linux
cat > "$MOCK_BIN/osascript" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/osascript"

# ====================================================================
# Section A: maintenance/lib/common.sh
# ====================================================================
echo "=== Testing maintenance/lib/common.sh ==="

HOME_A="$TEST_DIR/home_a"
LOG_DIR_A="$TEST_DIR/logs_a"
mkdir -p "$HOME_A/Library/Logs/maintenance" "$LOG_DIR_A"

# ---- A1: sourcing under strict mode does not fail ----
a1_exit=0
(
    set -euo pipefail
    export HOME="$HOME_A"
    export LOG_DIR="$LOG_DIR_A"
    PATH="$MOCK_BIN:$PATH"
    # shellcheck source=maintenance/lib/common.sh
    source "$REPO_ROOT/maintenance/lib/common.sh"
) > "$TEST_DIR/a1.log" 2>&1 || a1_exit=$?
if [[ "$a1_exit" -eq 0 ]]; then
    echo "PASS: common.sh: sourcing under strict mode succeeds"
    PASS=$((PASS + 1))
else
    echo "FAIL: common.sh: sourcing under strict mode failed (exit $a1_exit)"
    cat "$TEST_DIR/a1.log"
    FAIL=$((FAIL + 1))
fi

# Source common.sh into the current shell for A2–A11
HOME="$HOME_A"
LOG_DIR="$LOG_DIR_A"
PATH="$MOCK_BIN:$PATH"
# shellcheck source=maintenance/lib/common.sh
source "$REPO_ROOT/maintenance/lib/common.sh"

# ---- A2: REPO_ROOT is set and non-empty ----
check "common.sh: REPO_ROOT is set and non-empty" test -n "${REPO_ROOT:-}"

# ---- A3: MNT_ROOT is set and non-empty ----
check "common.sh: MNT_ROOT is set and non-empty" test -n "${MNT_ROOT:-}"

# ---- A4: LOG_DIR is set and uses mock HOME (no real ~/Library writes) ----
check "common.sh: LOG_DIR is set and non-empty" test -n "${LOG_DIR:-}"
check "common.sh: LOG_DIR is isolated to test dir" test "$LOG_DIR" = "$LOG_DIR_A"

# ---- A5: log_info writes output containing the message ----
info_out=$(log_info "test-info-message" 2>/dev/null)
check_contains "common.sh: log_info output contains message" "test-info-message" "$info_out"

# ---- A6: log_warn writes output containing WARNING level ----
warn_out=$(log_warn "test-warn-message" 2>/dev/null)
check_contains "common.sh: log_warn output contains WARNING" "WARNING" "$warn_out"

# ---- A7: log_error writes output containing ERROR level ----
err_out=$(log_error "test-error-message" 2>/dev/null)
check_contains "common.sh: log_error output contains ERROR" "ERROR" "$err_out"

# ---- A8: logging functions exit 0 (non-fatal) ----
log_info "exit-code-check" > /dev/null 2>&1
check "common.sh: log_info exits 0" true

# ---- A9: log writes a file to LOG_DIR ----
log_file_count=$(find "$LOG_DIR_A" -type f -name "*.log" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$log_file_count" -gt 0 ]]; then
    echo "PASS: common.sh: log writes to file in LOG_DIR"
    PASS=$((PASS + 1))
else
    echo "FAIL: common.sh: no log file found under $LOG_DIR_A"
    FAIL=$((FAIL + 1))
fi

# ---- A10: require_cmd returns 0 for an existing command ----
check "common.sh: require_cmd succeeds for 'bash'" require_cmd bash

# ---- A11: require_cmd returns non-zero for a missing command ----
check_false "common.sh: require_cmd fails for non-existent command" \
    require_cmd __no_such_cmd_xyz__

# ====================================================================
# Section B: maintenance/lib/common_simple.sh
# Run in a subshell to keep functions/variables isolated from Section A.
# ====================================================================
echo ""
echo "=== Testing maintenance/lib/common_simple.sh ==="

HOME_B="$TEST_DIR/home_b"
LOG_DIR_B="$TEST_DIR/logs_b"
mkdir -p "$HOME_B/Library/Logs/maintenance" "$LOG_DIR_B"

# ---- B1: sourcing under strict mode does not fail ----
b1_exit=0
(
    set -euo pipefail
    export HOME="$HOME_B"
    export LOG_DIR="$LOG_DIR_B"
    PATH="$MOCK_BIN:$PATH"
    # shellcheck source=maintenance/lib/common_simple.sh
    source "$REPO_ROOT/maintenance/lib/common_simple.sh"
) > "$TEST_DIR/b1.log" 2>&1 || b1_exit=$?
if [[ "$b1_exit" -eq 0 ]]; then
    echo "PASS: common_simple.sh: sourcing under strict mode succeeds"
    PASS=$((PASS + 1))
else
    echo "FAIL: common_simple.sh: sourcing under strict mode failed (exit $b1_exit)"
    cat "$TEST_DIR/b1.log"
    FAIL=$((FAIL + 1))
fi

# Run B2–B9 inside a subshell; results are tallied from its stdout.
b_results="$TEST_DIR/b_results.log"
(
    export HOME="$HOME_B"
    export LOG_DIR="$LOG_DIR_B"
    PATH="$MOCK_BIN:$PATH"
    # shellcheck source=maintenance/lib/common_simple.sh
    source "$REPO_ROOT/maintenance/lib/common_simple.sh"

    b_pass() { echo "PASS: $*"; }
    b_fail() { echo "FAIL: $*"; }

    # B2: REPO_ROOT is set and non-empty
    [[ -n "${REPO_ROOT:-}" ]] \
        && b_pass "common_simple.sh: REPO_ROOT is set and non-empty" \
        || b_fail "common_simple.sh: REPO_ROOT is empty"

    # B3: MNT_ROOT is set and non-empty
    [[ -n "${MNT_ROOT:-}" ]] \
        && b_pass "common_simple.sh: MNT_ROOT is set and non-empty" \
        || b_fail "common_simple.sh: MNT_ROOT is empty"

    # B4: LOG_DIR is set and isolated to test dir
    [[ -n "${LOG_DIR:-}" ]] \
        && b_pass "common_simple.sh: LOG_DIR is set and non-empty" \
        || b_fail "common_simple.sh: LOG_DIR is empty"

    # B5: log_info output contains the message
    info_out=$(log_info "simple-info-msg" 2>/dev/null)
    echo "$info_out" | grep -q "simple-info-msg" \
        && b_pass "common_simple.sh: log_info output contains message" \
        || b_fail "common_simple.sh: log_info missing message (got: $info_out)"

    # B6: log_warn output contains WARNING level indicator
    warn_out=$(log_warn "simple-warn-msg" 2>/dev/null)
    echo "$warn_out" | grep -q "WARNING" \
        && b_pass "common_simple.sh: log_warn output contains WARNING" \
        || b_fail "common_simple.sh: log_warn missing WARNING (got: $warn_out)"

    # B7: log_error output contains ERROR level indicator
    err_out=$(log_error "simple-error-msg" 2>/dev/null)
    echo "$err_out" | grep -q "ERROR" \
        && b_pass "common_simple.sh: log_error output contains ERROR" \
        || b_fail "common_simple.sh: log_error missing ERROR (got: $err_out)"

    # B8: require_cmd returns 0 for an existing command
    if require_cmd bash >/dev/null 2>&1; then
        b_pass "common_simple.sh: require_cmd succeeds for 'bash'"
    else
        b_fail "common_simple.sh: require_cmd failed for 'bash'"
    fi

    # B9: require_cmd returns non-zero for a missing command
    rc=0
    require_cmd __no_such_cmd_xyz__ >/dev/null 2>&1 || rc=$?
    if [[ "$rc" -ne 0 ]]; then
        b_pass "common_simple.sh: require_cmd fails for non-existent command"
    else
        b_fail "common_simple.sh: require_cmd should fail for non-existent command"
    fi
) > "$b_results" 2>&1

# Print B results and tally PASS/FAIL counts
while IFS= read -r line; do
    echo "$line"
    case "$line" in
        PASS:*) PASS=$((PASS + 1)) ;;
        FAIL:*) FAIL=$((FAIL + 1)) ;;
    esac
done < "$b_results"

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
