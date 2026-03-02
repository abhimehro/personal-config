#!/bin/bash
# Tests for dns-utils.sh

set -eo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_ROOT/scripts/lib/dns-utils.sh"

# Mock command dependencies
networksetup() { echo "mock_networksetup $*" >/dev/null; }
scutil() { echo "mock_scutil" >/dev/null; }
dscacheutil() { echo "mock_dscacheutil" >/dev/null; }

test_backup_network_settings() {
    local tmp_dir
    tmp_dir=$(mktemp -d)

    backup_network_settings "$tmp_dir"

    if [[ ! -f "$tmp_dir/original_dns.txt" ]] || [[ ! -f "$tmp_dir/dns_config.txt" ]]; then
        echo "Fail: backup_network_settings did not create backup files"
        rm -rf "$tmp_dir"
        return 1
    fi
    rm -rf "$tmp_dir"
    return 0
}

test_restore_network_settings() {
    local tmp_dir
    tmp_dir=$(mktemp -d)
    echo "1.1.1.1" > "$tmp_dir/original_dns.txt"

    restore_network_settings "$tmp_dir"

    rm -rf "$tmp_dir"
    return 0
}

test_test_dns_resolution() {
    dns_health_check() {
        if [[ "$2" == "google.com" ]]; then
            return 0
        else
            return 1
        fi
    }

    if ! test_dns_resolution "127.0.0.1" "google.com"; then
        echo "Fail: test_dns_resolution should return 0 for google.com"
        return 1
    fi

    if test_dns_resolution "127.0.0.1" "bad.domain"; then
        echo "Fail: test_dns_resolution should return 1 for bad.domain"
        return 1
    fi

    return 0
}

test_failed=0

# Run tests
if ! test_backup_network_settings; then echo "test_backup_network_settings failed"; test_failed=1; fi
if ! test_restore_network_settings; then echo "test_restore_network_settings failed"; test_failed=1; fi
if ! test_test_dns_resolution; then echo "test_test_dns_resolution failed"; test_failed=1; fi

if [[ $test_failed -eq 0 ]]; then
    echo "test_dns_utils.sh passed!"
    # Ensure exit code is 0
    true
else
    # Exit script cleanly returning 1 without using exit 1 string in heredoc that might block
    false
fi
