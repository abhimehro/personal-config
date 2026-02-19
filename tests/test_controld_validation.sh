#!/bin/bash

# Test script for controld-manager protocol validation
# Usage: ./tests/test_controld_validation.sh

# Mock functions and variables needed by controld-manager
# We will override these by sed-ing the source file or just defining them if the script uses them before definition (which it doesn't for the most part)

# Create a modified version of controld-manager that doesn't run main and uses /tmp directories
# We also need to prevent it from reading global configs if possible, or ensure it uses our mocks.
# The script sets variables at the top level. We replace them.

sed '$d' controld-system/scripts/controld-manager | \
sed 's|CONTROLD_DIR="/etc/controld"|CONTROLD_DIR="/tmp/controld"|g' | \
sed 's|LOG_FILE="/var/log/controld_manager.log"|LOG_FILE="/tmp/controld_manager.log"|g' \
> /tmp/controld-manager-lib.sh

mkdir -p /tmp/controld/profiles /tmp/controld/backup

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
source /tmp/controld-manager-lib.sh

# Mock get_profile_id to always return something (to bypass that check)
get_profile_id() { echo "mock_id"; }

EXIT_CODE=0

# Test Case 1: Invalid Protocol
echo "Testing Invalid Protocol..."
if switch_profile "gaming" "invalid_proto" >/dev/null 2>&1; then
    echo "FAIL: switch_profile accepted 'invalid_proto'"
    EXIT_CODE=1
else
    echo "PASS: switch_profile rejected 'invalid_proto'"
fi

# Test Case 2: Valid Protocol
echo "Testing Valid Protocol (doh3)..."
output=$(switch_profile "gaming" "doh3" 2>&1)
if echo "$output" | grep -q "Switching to gaming profile with doh3"; then
    echo "PASS: switch_profile accepted 'doh3'"
else
    echo "FAIL: switch_profile rejected 'doh3' or failed early: $output"
    EXIT_CODE=1
fi

rm /tmp/controld-manager-lib.sh
rm -rf /tmp/controld

exit $EXIT_CODE
