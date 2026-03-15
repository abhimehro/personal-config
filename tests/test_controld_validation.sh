#!/bin/bash

# Test script for controld-manager protocol validation
# Usage: ./tests/test_controld_validation.sh

export CONTROLD_DIR
CONTROLD_DIR="$(mktemp -d)"
export LOG_FILE
LOG_FILE="$(mktemp)"

LIB_FILE="$(mktemp)"
cp controld-system/scripts/controld-manager "$LIB_FILE"

mkdir -p "$CONTROLD_DIR/profiles" "$CONTROLD_DIR/backup"

# Mock external commands
ctrld() { echo "ctrld called with $*"; }
networksetup() { echo "networksetup called with $*"; }
scutil() { echo "scutil called with $*"; }
dscacheutil() { echo "dscacheutil called with $*"; }
killall() { echo "killall called with $*"; }
pkill() { echo "pkill called with $*"; }
dig() { echo "dig called with $*"; }
sudo() { "$@"; } # Mock sudo by just running the command

# Source the library
source "$LIB_FILE"

# Mock get_profile_id to always return something (to bypass that check)
get_profile_id() { echo "mock_id"; }

test_failed=0

# Test Case 1: Invalid Protocol
echo "Testing Invalid Protocol..."
if switch_profile "gaming" "invalid_proto" >/dev/null 2>&1; then
    echo "FAIL: switch_profile accepted 'invalid_proto'"
    test_failed=1
else
    echo "PASS: switch_profile rejected 'invalid_proto'"
fi

# Test Case 2: Valid Protocol
echo "Testing Valid Protocol (doh3)..."
setup_directories() { return 0; }
generate_profile_config() { return 0; }
restart_with_config() { return 0; }
restart_with_native_profile() { return 0; }
test_profile_connection() { return 0; }
pgrep() { return 1; }

# Mock get_profile_protocol and other stuff just in case they fail in this test context
get_profile_protocol() { echo "doh3"; }
validate_profile_id() { return 0; }
validate_protocol() { return 0; }
redact_profile_id() { echo "mock_id"; }

output=$(switch_profile "gaming" "doh3" 2>&1)
if echo "$output" | grep -q "Successfully switched to gaming profile"; then
    echo "PASS: switch_profile accepted 'doh3'"
else
    echo "FAIL: switch_profile rejected 'doh3' or failed early: $output"
    test_failed=1
fi

rm -f "$LIB_FILE" "${LIB_FILE}.bak" "$LOG_FILE"
rm -rf "$CONTROLD_DIR"

if [[ $test_failed -eq 0 ]]; then
    true
else
    false
fi
