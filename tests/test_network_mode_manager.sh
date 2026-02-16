#!/bin/bash
#
# Unit tests for network-mode-manager.sh
# Tests modes, profiles, and basic logic using mocks

set -euo pipefail

# Setup
TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

# Mock dependencies
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
export PATH="$MOCK_BIN:$PATH"

# Create mocks
cat > "$MOCK_BIN/ctrld" << 'EOF'
#!/bin/bash
echo "MOCK CTRLD CALLED: $@"
EOF
chmod +x "$MOCK_BIN/ctrld"

cat > "$MOCK_BIN/networksetup" << 'EOF'
#!/bin/bash
echo "MOCK NETWORKSETUP CALLED: $@"
EOF
chmod +x "$MOCK_BIN/networksetup"

cat > "$MOCK_BIN/scutil" << 'EOF'
#!/bin/bash
if [[ "$*" == "--dns" ]]; then
    echo "nameserver[0] : 127.0.0.1"
fi
EOF
chmod +x "$MOCK_BIN/scutil"

# Mock IPv6 Manager
MOCK_IPV6="$TEST_DIR/ipv6-manager.sh"
echo '#!/bin/bash' > "$MOCK_IPV6"
echo 'echo "MOCK IPV6 CALLED: $@"' >> "$MOCK_IPV6"
chmod +x "$MOCK_IPV6"

# Mock controld-manager
MOCK_CD_MGR="$TEST_DIR/controld-manager"
cat > "$MOCK_CD_MGR" << 'EOF'
#!/bin/bash
echo "MOCK CONTROLD-MANAGER CALLED: $@"
EOF
chmod +x "$MOCK_CD_MGR"

# Path to the real script
REAL_MANAGER="./scripts/network-mode-manager.sh"

# Create a test version of the manager that points to mocks
TEST_MANAGER="$TEST_DIR/network-mode-manager.sh"
cp "$REAL_MANAGER" "$TEST_MANAGER"

# Copy library
mkdir -p "$TEST_DIR/lib"
cp scripts/lib/network-core.sh "$TEST_DIR/lib/"

# Inject mocks into the test manager
sed -i '' "s|IPV6_MANAGER=".*"|IPV6_MANAGER="$MOCK_IPV6"|" "$TEST_MANAGER"
sed -i '' "s|local controld_manager=".*"|local controld_manager="$MOCK_CD_MGR"|" "$TEST_MANAGER"

# Helper to run test
run_test() {
    local name="$1"
    shift
    echo "Running test: $name..."
    if bash "$TEST_MANAGER" "$@" > "$TEST_DIR/out.log" 2>&1; then
        echo "PASS: $name"
    else
        echo "FAIL: $name"
        cat "$TEST_DIR/out.log"
        return 1
    fi
}

# Test Cases
EXIT_CODE=0

run_test "Status Command" status || EXIT_CODE=1
run_test "Control D Browsing" controld browsing || EXIT_CODE=1
run_test "Control D Privacy" controld privacy || EXIT_CODE=1
run_test "Windscribe Standalone" windscribe || EXIT_CODE=1
run_test "Windscribe + Privacy" windscribe privacy || EXIT_CODE=1

# Test invalid profile
echo "Running test: Invalid Profile..."
if bash "$TEST_MANAGER" controld invalid_profile >/dev/null 2>&1; then
    echo "FAIL: Accepted invalid profile"
    EXIT_CODE=1
else
    echo "PASS: Rejected invalid profile"
fi

exit $EXIT_CODE
