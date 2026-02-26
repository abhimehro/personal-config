#!/bin/bash
#
# Security Test for network-mode-manager.sh
# Verifies that the script fails securely when /usr/local/bin/controld-manager is missing.

set -u

# Setup
TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

# Mock dependencies
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
export PATH="$MOCK_BIN:$PATH"

# Create minimal mocks to pass prereqs
touch "$MOCK_BIN/ctrld" && chmod +x "$MOCK_BIN/ctrld"
touch "$MOCK_BIN/networksetup" && chmod +x "$MOCK_BIN/networksetup"
touch "$MOCK_BIN/scutil" && chmod +x "$MOCK_BIN/scutil"

# Mock IPv6 Manager
MOCK_IPV6="$TEST_DIR/ipv6-manager.sh"
echo '#!/bin/bash' > "$MOCK_IPV6"
chmod +x "$MOCK_IPV6"

# Path to the real script
REAL_MANAGER="./scripts/network-mode-manager.sh"

# Create a test version of the manager
TEST_MANAGER="$TEST_DIR/network-mode-manager.sh"
cp "$REAL_MANAGER" "$TEST_MANAGER"

# Copy library
mkdir -p "$TEST_DIR/lib"
cp scripts/lib/network-core.sh "$TEST_DIR/lib/"

# Inject mock IPv6 manager location (same as original test)
if [[ "$(uname -s)" == "Darwin" ]]; then
    sed -i '' "s|IPV6_MANAGER=\".*\"|IPV6_MANAGER=\"$MOCK_IPV6\"|" "$TEST_MANAGER"
else
    sed -i "s|IPV6_MANAGER=\".*\"|IPV6_MANAGER=\"$MOCK_IPV6\"|" "$TEST_MANAGER"
fi

# DO NOT inject a mock location for controld-manager.
# This ensures the script looks for /usr/local/bin/controld-manager.
# We assume /usr/local/bin/controld-manager does NOT exist in this environment.
# If it does, this test might fail (false negative), but that's unlikely here.

echo "Running security test: ensuring failure when system binary is missing..."

# Run the script. It should fail.
output=$("$TEST_MANAGER" controld browsing 2>&1)
exit_code=$?

echo "Exit code: $exit_code"
echo "Output: $output"

if [[ $exit_code -ne 0 ]]; then
    if echo "$output" | grep -q "controld-manager script not found in /usr/local/bin"; then
        echo "PASS: Script failed securely with correct error message."
        exit 0
    else
        echo "FAIL: Script failed but with unexpected error message."
        exit 1
    fi
else
    echo "FAIL: Script succeeded but should have failed."
    exit 1
fi
