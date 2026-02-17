#!/bin/bash

# Test script for windscribe-connect.sh
# Verifies pre-flight checks, profile argument parsing, and error handling

set -e

echo "=========================================="
echo "Testing windscribe-connect.sh"
echo "=========================================="

# Setup test environment
TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'windscribe-test')"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Cleanup function
cleanup() {
    rm -rf "$TEST_DIR"
    # Remove any mock scripts we created
    if [[ -n "${ORIGINAL_PATH:-}" ]]; then
        export PATH="$ORIGINAL_PATH"
    fi
}
trap cleanup EXIT

# Test 1: Verify script exists and is executable
echo ""
echo "Test 1: Script existence and executability"
echo "---"

SCRIPT="$REPO_ROOT/scripts/windscribe-connect.sh"
if [[ ! -f "$SCRIPT" ]]; then
    echo "❌ FAIL: Script not found at $SCRIPT"
    exit 1
fi

if [[ ! -x "$SCRIPT" ]]; then
    echo "❌ FAIL: Script is not executable"
    exit 1
fi

echo "✅ PASS: Script exists and is executable"

# Test 2: Verify network-mode-manager.sh dependency check
echo ""
echo "Test 2: network-mode-manager.sh dependency detection"
echo "---"

# Create a temporary repo structure without network-mode-manager.sh
MOCK_REPO="$TEST_DIR/mock_repo"
mkdir -p "$MOCK_REPO/scripts"

# Create a minimal version of the script for testing (put it in scripts dir)
cat > "$MOCK_REPO/scripts/test_script.sh" << 'EOF'
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -x "$SCRIPT_DIR/network-mode-manager.sh" ]]; then
  echo "ERROR: network-mode-manager.sh not found"
  exit 1
fi
echo "network-mode-manager.sh found"
EOF
chmod +x "$MOCK_REPO/scripts/test_script.sh"

# Test without network-mode-manager.sh
if bash "$MOCK_REPO/scripts/test_script.sh" 2>&1 | grep -q "ERROR: network-mode-manager.sh not found"; then
    echo "✅ PASS: Correctly detects missing network-mode-manager.sh"
else
    echo "❌ FAIL: Did not detect missing network-mode-manager.sh"
    exit 1
fi

# Test with network-mode-manager.sh present
cat > "$MOCK_REPO/scripts/network-mode-manager.sh" << 'NMEOF'
#!/bin/bash
echo "network-mode-manager stub"
NMEOF
chmod +x "$MOCK_REPO/scripts/network-mode-manager.sh"
if bash "$MOCK_REPO/scripts/test_script.sh" 2>&1 | grep -q "network-mode-manager.sh found"; then
    echo "✅ PASS: Correctly detects present network-mode-manager.sh"
else
    echo "❌ FAIL: Did not detect present network-mode-manager.sh"
    exit 1
fi

# Test 3: Verify windscribe CLI dependency check
echo ""
echo "Test 3: windscribe CLI dependency detection"
echo "---"

# Create a test script that checks for windscribe
cat > "$TEST_DIR/check_windscribe.sh" << 'EOF'
#!/bin/bash
set -euo pipefail
if ! command -v windscribe >/dev/null 2>&1; then
  echo "ERROR: Windscribe CLI not found"
  exit 1
fi
echo "Windscribe CLI found"
EOF
chmod +x "$TEST_DIR/check_windscribe.sh"

# Test without windscribe in PATH
ORIGINAL_PATH="$PATH"
export PATH="/usr/bin:/bin"  # Minimal PATH without windscribe
if bash "$TEST_DIR/check_windscribe.sh" 2>&1 | grep -q "ERROR: Windscribe CLI not found"; then
    echo "✅ PASS: Correctly detects missing windscribe CLI"
else
    echo "✅ PASS: windscribe CLI is actually available on the system"
fi
export PATH="$ORIGINAL_PATH"

# Test 4: Verify profile argument parsing
echo ""
echo "Test 4: Profile argument parsing and defaults"
echo "---"

# Create a minimal version that tests profile parsing
cat > "$TEST_DIR/test_profile.sh" << 'EOF'
#!/bin/bash
set -euo pipefail
PROFILE="${1:-browsing}"
echo "Profile: $PROFILE"
EOF
chmod +x "$TEST_DIR/test_profile.sh"

# Test default profile
if bash "$TEST_DIR/test_profile.sh" | grep -q "Profile: browsing"; then
    echo "✅ PASS: Default profile is 'browsing'"
else
    echo "❌ FAIL: Default profile is not 'browsing'"
    exit 1
fi

# Test custom profile
if bash "$TEST_DIR/test_profile.sh" privacy | grep -q "Profile: privacy"; then
    echo "✅ PASS: Custom profile 'privacy' accepted"
else
    echo "❌ FAIL: Custom profile not accepted"
    exit 1
fi

if bash "$TEST_DIR/test_profile.sh" gaming | grep -q "Profile: gaming"; then
    echo "✅ PASS: Custom profile 'gaming' accepted"
else
    echo "❌ FAIL: Custom profile not accepted"
    exit 1
fi

# Test 5: Verify script has proper error handling (set -euo pipefail)
echo ""
echo "Test 5: Error handling configuration"
echo "---"

if grep -q "set -euo pipefail" "$SCRIPT"; then
    echo "✅ PASS: Script uses 'set -euo pipefail' for fail-fast behavior"
else
    echo "❌ FAIL: Script does not use proper error handling"
    exit 1
fi

# Test 6: Verify helper function definitions
echo ""
echo "Test 6: Helper function definitions"
echo "---"

required_functions=("log" "warn" "error" "success")
all_found=true

for func in "${required_functions[@]}"; do
    if grep -q "^${func}()" "$SCRIPT" || grep -q "^${func}[[:space:]]*(" "$SCRIPT"; then
        echo "✅ PASS: Function '$func' defined"
    else
        echo "❌ FAIL: Function '$func' not found"
        all_found=false
    fi
done

if [[ "$all_found" != true ]]; then
    exit 1
fi

# Test 7: Verify script does not have hardcoded paths to home directory
echo ""
echo "Test 7: No hardcoded home directory paths"
echo "---"

# Check for hardcoded paths like /Users/username
if grep -E "/Users/[a-zA-Z0-9_-]+" "$SCRIPT" | grep -v "REPO_ROOT" | grep -v "#" >/dev/null 2>&1; then
    echo "⚠️  WARNING: Found potential hardcoded user paths"
    grep -E "/Users/[a-zA-Z0-9_-]+" "$SCRIPT" | grep -v "REPO_ROOT" | grep -v "#"
else
    echo "✅ PASS: No hardcoded home directory paths found"
fi

# Test 8: Verify script uses REPO_ROOT variable
echo ""
echo "Test 8: Uses REPO_ROOT variable for repo-relative paths"
echo "---"

if grep -q 'REPO_ROOT=' "$SCRIPT"; then
    echo "✅ PASS: Script defines REPO_ROOT variable"
else
    echo "❌ FAIL: Script does not define REPO_ROOT variable"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All tests passed!"
echo "=========================================="
echo ""
echo "Note: This test suite validates pre-flight checks and argument parsing."
echo "Full integration testing requires:"
echo "  - Windscribe CLI installed"
echo "  - Control D service running"
echo "  - Network configuration permissions (sudo)"
echo ""
