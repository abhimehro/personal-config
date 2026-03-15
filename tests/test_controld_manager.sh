#!/bin/bash
# Tests for controld-manager.sh orchestration

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Use a test directory for controld config and logs
export CONTROLD_DIR="$REPO_ROOT/tests/fixtures/controld"
export LOG_FILE="$(mktemp)"
mkdir -p "$CONTROLD_DIR"

# Source the manager via the BASH_SOURCE guard (avoids running main "$@")
# shellcheck source=controld-system/scripts/controld-manager
source "$REPO_ROOT/controld-system/scripts/controld-manager"

test_failed=0

# ── Mock all functions that require root / macOS system access ───────────────
check_root() { return 0; }
setup_directories() { echo "mock_setup_directories"; return 0; }
backup_network_settings() { echo "mock_backup_network_settings"; }
restore_network_settings() { echo "mock_restore_network_settings"; }
generate_profile_config() { echo "mock_generate_profile_config"; return 0; }
restart_with_config() { echo "mock_restart_with_config"; return 0; }
test_profile_connection() {
    if [[ "$1" == "bad_profile" ]]; then return 1; fi
    return 0
}
safe_stop() { echo "mock_safe_stop"; return 0; }
emergency_recovery() { echo "mock_emergency_recovery"; return 0; }
show_status() { echo "mock_show_status"; return 0; }
pgrep() { return 1; }

# Global flag used by test_switch_profile_restores_on_failure
TEST_RESTORE_CALLED=""

# === $MOCK_BIN subprocess smoke tests ========================================
# Invoke controld-manager as a subprocess with PATH-injected fakes so no real
# system calls reach launchctl, scutil, dig, etc.
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-controld-manager')
# shellcheck disable=SC2064  # we want the current $TEST_DIR value captured in the trap
trap "rm -rf '$TEST_DIR'" EXIT
MOCK_BIN="$TEST_DIR/mock_bin"
CONTROLD_MGR="$REPO_ROOT/controld-system/scripts/controld-manager"
mkdir -p "$MOCK_BIN"

# Mock pgrep: report ctrld as not running (avoids macOS-only paths in show_status)
cat > "$MOCK_BIN/pgrep" << 'MOCK'
#!/bin/sh
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"

# Smoke: 'status' exits 0 and emits the Service Status header
test_smoke_status() {
    local output rc
    if output=$(PATH="$MOCK_BIN:$PATH" bash "$CONTROLD_MGR" status 2>&1); then
        rc=0
    else
        rc=$?
    fi
    if [[ "$rc" -ne 0 ]]; then
        echo "Fail: 'status' should exit 0, got $rc. Output:"
        echo "$output"
        return 1
    fi
    if ! echo "$output" | grep -q "Service Status"; then
        echo "Fail: 'status' should output 'Service Status'. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# Smoke: unknown/help command shows usage text
test_smoke_help() {
    local output rc
    # controld-manager's '*' case prints usage and is expected to return 0.
    # Run under 'if' so non-zero exit doesn't trigger 'set -e', and capture rc explicitly.
    if output=$(PATH="$MOCK_BIN:$PATH" bash "$CONTROLD_MGR" --help 2>&1); then
        rc=0
    else
        rc=$?
    fi
    if [[ "$rc" -ne 0 ]]; then
        echo "Fail: '--help' should exit with status 0, got $rc. Output:"
        echo "$output"
        return 1
    fi
    if ! echo "$output" | grep -qiE "usage|commands"; then
        echo "Fail: '--help' should display usage/commands. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# Smoke: root-required commands (stop) exit non-zero and mention 'root'
# when invoked as a non-root user.  Skipped automatically if running as root.
test_smoke_stop_requires_root() {
    if [[ "${EUID:-$(id -u 2>/dev/null || echo 0)}" -eq 0 ]]; then
        echo "SKIP: test_smoke_stop_requires_root (running as root)"
        return 0  # skip: already root — meaningful only in non-root environments
    fi
    local output rc
    if output=$(PATH="$MOCK_BIN:$PATH" bash "$CONTROLD_MGR" stop 2>&1); then
        rc=0
    else
        rc=$?
    fi
    if [[ "$rc" -eq 0 ]]; then
        echo "Fail: 'stop' (as non-root) should exit non-zero. Exit: $rc. Output:"
        echo "$output"
        return 1
    fi
    if ! echo "$output" | grep -qi "root"; then
        echo "Fail: 'stop' (as non-root) should mention root requirement. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# ── Test: valid profile switch (doh3) ────────────────────────────────────────
test_switch_profile_valid() {
    export CTR_PROFILE_PRIVACY_ID="test1234"

    local output
    output=$(switch_profile "privacy" "doh3" 2>&1)

    if ! echo "$output" | grep -q "Successfully switched to privacy profile"; then
        echo "Fail: switch_profile failed to output success message. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# ── Test: invalid profile name rejected ─────────────────────────────────────
test_switch_profile_invalid() {
    local output
    output=$(switch_profile "bad_profile" "doh3" 2>&1)

    if ! echo "$output" | grep -q "Unknown profile"; then
        echo "Fail: switch_profile should fail for unknown profile. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# ── Test: doh protocol accepted (not just doh3) ──────────────────────────────
test_switch_profile_doh_protocol() {
    export CTR_PROFILE_GAMING_ID="gametest123"

    local output
    output=$(switch_profile "gaming" "doh" 2>&1)

    if ! echo "$output" | grep -q "Successfully switched to gaming profile"; then
        echo "Fail: switch_profile with doh protocol failed. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# ── Test: invalid protocol rejected ──────────────────────────────────────────
test_switch_profile_invalid_protocol() {
    export CTR_PROFILE_GAMING_ID="gametest123"

    local output
    output=$(switch_profile "gaming" "invalid_proto" 2>&1)
    local status=$?

    if [ "$status" -eq 0 ]; then
        echo "Fail: switch_profile should return non-zero for invalid protocol. Exit status: $status"
        echo "Output:"
        echo "$output"
        return 1
    fi
    if ! echo "$output" | grep -q "Invalid profile ID or protocol"; then
        echo "Fail: switch_profile should reject invalid protocol. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# ── Test: main status + stop commands ────────────────────────────────────────
test_main_commands() {
    local output

    output=$(main "status" 2>&1)
    if ! echo "$output" | grep -q "mock_show_status"; then
        echo "Fail: main 'status' didn't call show_status. Output:"
        echo "$output"
        return 1
    fi

    output=$(main "stop" 2>&1)
    if ! echo "$output" | grep -q "mock_safe_stop"; then
        echo "Fail: main 'stop' didn't call safe_stop. Output:"
        echo "$output"
        return 1
    fi

    return 0
}

# ── Test: main switch without profile name shows usage ───────────────────────
test_switch_missing_profile() {
    local output rc

    # NOTE: main "switch" intentionally returns non-zero when profile is missing.
    # Run it in an if-condition so set -e does not terminate the script on failure.
    if output=$(main "switch" 2>&1); then
        rc=0
    else
        rc=$?
    fi

    if [[ "$rc" -eq 0 ]]; then
        echo "Fail: 'main switch' (no profile arg) should return non-zero exit code."
        echo "Output:"
        echo "$output"
        return 1
    fi
    if ! echo "$output" | grep -qiE "usage|available profiles"; then
        echo "Fail: 'main switch' (no profile arg) should show usage. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# ── Test: main init calls setup_directories and backup_network_settings ───────
test_init_command() {
    local output
    output=$(main "init" 2>&1)

    if ! echo "$output" | grep -q "mock_setup_directories"; then
        echo "Fail: main 'init' didn't call setup_directories. Output:"
        echo "$output"
        return 1
    fi
    if ! echo "$output" | grep -q "mock_backup_network_settings"; then
        echo "Fail: main 'init' didn't call backup_network_settings. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# ── Test: main emergency calls emergency_recovery ─────────────────────────────
test_emergency_command() {
    local output
    output=$(main "emergency" 2>&1)

    if ! echo "$output" | grep -q "mock_emergency_recovery"; then
        echo "Fail: main 'emergency' didn't call emergency_recovery. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# ── Test: main test runs DNS health check ────────────────────────────────────
test_test_command() {
    local output
    output=$(main "test" 2>&1)

    if ! echo "$output" | grep -q "DNS"; then
        echo "Fail: main 'test' should output DNS status. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# ── Test: unknown command shows usage ────────────────────────────────────────
test_unknown_command() {
    local output
    output=$(main "unknown_cmd" 2>&1)

    if ! echo "$output" | grep -qiE "usage|commands"; then
        echo "Fail: unknown command should display usage. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

# ── Test: DNS backup/restore — restore called on connection failure ───────────
# Validates that switch_profile calls restore_network_settings when
# test_profile_connection signals a failure (simulating the DNS restore path).
test_switch_profile_restores_on_failure() {
    TEST_RESTORE_CALLED=""

    # Override mocks for this test only
    restore_network_settings() { TEST_RESTORE_CALLED="yes"; }
    test_profile_connection() { return 1; }

    export CTR_PROFILE_BROWSING_ID="browstest123"
    # Run in main shell (not a subshell) so TEST_RESTORE_CALLED update is visible.
    # switch_profile is expected to return 1 here (connection failure triggers restore).
    local rc=0
    switch_profile "browsing" "doh3" >/dev/null 2>&1 || rc=$?

    # Restore shared mocks for any future tests
    restore_network_settings() { echo "mock_restore_network_settings"; }
    test_profile_connection() {
        if [[ "$1" == "bad_profile" ]]; then return 1; fi
        return 0
    }

    if [[ "$TEST_RESTORE_CALLED" != "yes" ]]; then
        echo "Fail: restore_network_settings was not called on connection failure (switch_profile rc=$rc)"
        return 1
    fi
    return 0
}

# ── Run all tests ─────────────────────────────────────────────────────────────
if ! test_switch_profile_valid;                then echo "test_switch_profile_valid failed";                test_failed=1; fi
if ! test_switch_profile_invalid;              then echo "test_switch_profile_invalid failed";              test_failed=1; fi
if ! test_switch_profile_doh_protocol;         then echo "test_switch_profile_doh_protocol failed";         test_failed=1; fi
if ! test_switch_profile_invalid_protocol;     then echo "test_switch_profile_invalid_protocol failed";     test_failed=1; fi
if ! test_main_commands;                       then echo "test_main_commands failed";                       test_failed=1; fi
if ! test_switch_missing_profile;              then echo "test_switch_missing_profile failed";              test_failed=1; fi
if ! test_init_command;                        then echo "test_init_command failed";                        test_failed=1; fi
if ! test_emergency_command;                   then echo "test_emergency_command failed";                   test_failed=1; fi
if ! test_test_command;                        then echo "test_test_command failed";                        test_failed=1; fi
if ! test_unknown_command;                     then echo "test_unknown_command failed";                     test_failed=1; fi
if ! test_switch_profile_restores_on_failure;  then echo "test_switch_profile_restores_on_failure failed";  test_failed=1; fi
# $MOCK_BIN subprocess smoke tests
if ! test_smoke_status;                        then echo "test_smoke_status failed";                        test_failed=1; fi
if ! test_smoke_help;                          then echo "test_smoke_help failed";                          test_failed=1; fi
if ! test_smoke_stop_requires_root;            then echo "test_smoke_stop_requires_root failed";            test_failed=1; fi

if [[ $test_failed -eq 0 ]]; then
    echo "test_controld_manager.sh passed!"
    true
else
    false
fi
