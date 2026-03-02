#!/bin/bash
# Tests for controld-manager.sh orchestration

set -eo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# We don't execute controld-manager directly because it calls 'check_root' and 'main "$@"'
# automatically when not sourced, but we modified it to use the guard.
source "$REPO_ROOT/controld-system/scripts/controld-manager"

test_failed=0

# Mock command dependencies and commands that require root/system access
check_root() { return 0; }
setup_directories() { echo "mock_setup_directories"; return 0; }
backup_network_settings() { echo "mock_backup_network_settings"; }
restore_network_settings() { echo "mock_restore_network_settings"; }
generate_profile_config() { echo "mock_generate_profile_config"; return 0; }
restart_with_config() { echo "mock_restart_with_config"; return 0; }
test_profile_connection() {
    if [[ "$1" == "bad_profile" ]]; then return 1; fi
    return 0;
}
safe_stop() { echo "mock_safe_stop"; return 0; }
emergency_recovery() { echo "mock_emergency_recovery"; return 0; }
show_status() { echo "mock_show_status"; return 0; }
pgrep() { return 1; }

test_switch_profile_valid() {
    export CTR_PROFILE_PRIVACY_ID="test1234"

    # Run switch profile
    local output
    output=$(switch_profile "privacy" "doh3" 2>&1)

    if ! echo "$output" | grep -q "Successfully switched to privacy profile"; then
        echo "Fail: switch_profile failed to output success message. Output:"
        echo "$output"
        return 1
    fi
    return 0
}

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

if ! test_switch_profile_valid; then echo "test_switch_profile_valid failed"; test_failed=1; fi
if ! test_switch_profile_invalid; then echo "test_switch_profile_invalid failed"; test_failed=1; fi
if ! test_main_commands; then echo "test_main_commands failed"; test_failed=1; fi

if [[ $test_failed -eq 0 ]]; then
    echo "test_controld_manager.sh passed!"
    true
else
    false
fi
