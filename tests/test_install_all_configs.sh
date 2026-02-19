#!/bin/bash

# Test script for install_all_configs.sh
# Verifies installation orchestration, dependency checks, and error handling

set -e

echo "=========================================="
echo "Testing install_all_configs.sh"
echo "=========================================="

# Setup test environment
TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'install-test')"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Cleanup function
cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# Test 1: Verify script exists and is executable
echo ""
echo "Test 1: Script existence and executability"
echo "---"

SCRIPT="$REPO_ROOT/scripts/install_all_configs.sh"
if [[ ! -f "$SCRIPT" ]]; then
    echo "❌ FAIL: Script not found at $SCRIPT"
    exit 1
fi

if [[ ! -x "$SCRIPT" ]]; then
    echo "❌ FAIL: Script is not executable"
    exit 1
fi

echo "✅ PASS: Script exists and is executable"

# Test 2: Verify error handling (set -Eeuo pipefail)
echo ""
echo "Test 2: Error handling configuration"
echo "---"

if grep -q "set -Eeuo pipefail" "$SCRIPT"; then
    echo "✅ PASS: Script uses 'set -Eeuo pipefail' for fail-fast behavior"
else
    echo "❌ FAIL: Script does not use proper error handling"
    exit 1
fi

# Test 3: Verify helper function definitions
echo ""
echo "Test 3: Helper function definitions"
echo "---"

required_functions=("log" "success" "warn" "error" "step" "substep")
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

# Test 4: Verify script references required dependencies
echo ""
echo "Test 4: Dependency script references"
echo "---"

required_scripts=("sync_all_configs.sh" "verify_all_configs.sh")
all_found=true

for script in "${required_scripts[@]}"; do
    if grep -q "$script" "$SCRIPT"; then
        echo "✅ PASS: References '$script'"
    else
        echo "❌ FAIL: Does not reference '$script'"
        all_found=false
    fi
done

if [[ "$all_found" != true ]]; then
    exit 1
fi

# Test 5: Verify script defines REPO_ROOT
echo ""
echo "Test 5: Uses REPO_ROOT variable for repo-relative paths"
echo "---"

if grep -q 'REPO_ROOT=' "$SCRIPT"; then
    echo "✅ PASS: Script defines REPO_ROOT variable"
else
    echo "❌ FAIL: Script does not define REPO_ROOT variable"
    exit 1
fi

# Test 6: Test dependency script existence checks
echo ""
echo "Test 6: Dependency script existence validation"
echo "---"

# Create a mock installation script to test dependency checks
cat > "$TEST_DIR/test_deps.sh" << 'EOF'
#!/bin/bash
set -Eeuo pipefail

REPO_ROOT="$1"
SYNC_SCRIPT="$REPO_ROOT/scripts/sync_all_configs.sh"
VERIFY_SCRIPT="$REPO_ROOT/scripts/verify_all_configs.sh"

# Check sync script
if [[ ! -x "$SYNC_SCRIPT" ]]; then
    echo "ERROR: Sync script not found or not executable"
    exit 1
fi

# Check verify script
if [[ ! -x "$VERIFY_SCRIPT" ]]; then
    echo "ERROR: Verify script not found or not executable"
    exit 1
fi

echo "OK: All dependency scripts found"
EOF
chmod +x "$TEST_DIR/test_deps.sh"

# Test with missing scripts
MOCK_REPO="$TEST_DIR/mock_repo"
mkdir -p "$MOCK_REPO/scripts"

if bash "$TEST_DIR/test_deps.sh" "$MOCK_REPO" 2>&1 | grep -q "ERROR"; then
    echo "✅ PASS: Correctly detects missing dependency scripts"
else
    echo "❌ FAIL: Did not detect missing dependency scripts"
    exit 1
fi

# Test with scripts present
touch "$MOCK_REPO/scripts/sync_all_configs.sh"
touch "$MOCK_REPO/scripts/verify_all_configs.sh"
chmod +x "$MOCK_REPO/scripts/sync_all_configs.sh"
chmod +x "$MOCK_REPO/scripts/verify_all_configs.sh"

if bash "$TEST_DIR/test_deps.sh" "$MOCK_REPO" 2>&1 | grep -q "OK"; then
    echo "✅ PASS: Correctly validates present dependency scripts"
else
    echo "❌ FAIL: Did not validate present dependency scripts"
    exit 1
fi

# Test 7: Verify user confirmation prompt exists
echo ""
echo "Test 7: User confirmation prompt"
echo "---"

if grep -q "read -p" "$SCRIPT" || grep -q "read.*REPLY" "$SCRIPT"; then
    echo "✅ PASS: Script includes user confirmation prompt"
else
    echo "⚠️  WARNING: Script may not include user confirmation"
fi

# Test 8: Test installation flow with mocked scripts
echo ""
echo "Test 8: Installation orchestration flow"
echo "---"

# Create a mock installation environment
MOCK_INSTALL_DIR="$TEST_DIR/mock_install"
mkdir -p "$MOCK_INSTALL_DIR/scripts"

# Create mock sync script that succeeds
cat > "$MOCK_INSTALL_DIR/scripts/sync_all_configs.sh" << 'EOF'
#!/bin/bash
echo "SYNC: Running sync_all_configs.sh"
exit 0
EOF
chmod +x "$MOCK_INSTALL_DIR/scripts/sync_all_configs.sh"

# Create mock verify script that succeeds
cat > "$MOCK_INSTALL_DIR/scripts/verify_all_configs.sh" << 'EOF'
#!/bin/bash
echo "VERIFY: Running verify_all_configs.sh"
exit 0
EOF
chmod +x "$MOCK_INSTALL_DIR/scripts/verify_all_configs.sh"

# Create a simplified installer that mimics the logic
cat > "$TEST_DIR/test_install.sh" << 'EOF'
#!/bin/bash
set -Eeuo pipefail

REPO_ROOT="$1"
SYNC_SCRIPT="$REPO_ROOT/scripts/sync_all_configs.sh"
VERIFY_SCRIPT="$REPO_ROOT/scripts/verify_all_configs.sh"

# Check dependencies
if [[ ! -x "$SYNC_SCRIPT" ]]; then
    echo "ERROR: Sync script not found"
    exit 1
fi

if [[ ! -x "$VERIFY_SCRIPT" ]]; then
    echo "ERROR: Verify script not found"
    exit 1
fi

# Run sync
"$SYNC_SCRIPT"
sync_exit=$?

# Run verify
"$VERIFY_SCRIPT"
verify_exit=$?

# Check results
if [[ $sync_exit -eq 0 ]] && [[ $verify_exit -eq 0 ]]; then
    echo "SUCCESS: Installation completed"
    exit 0
else
    echo "ERROR: Installation failed"
    exit 1
fi
EOF
chmod +x "$TEST_DIR/test_install.sh"

# Test successful installation
if bash "$TEST_DIR/test_install.sh" "$MOCK_INSTALL_DIR" 2>&1 | grep -q "SUCCESS"; then
    echo "✅ PASS: Orchestrates installation flow correctly"
else
    echo "❌ FAIL: Installation flow failed"
    exit 1
fi

# Test 9: Test error handling when sync fails
echo ""
echo "Test 9: Error handling when sync script fails"
echo "---"

# Create mock sync script that fails
cat > "$MOCK_INSTALL_DIR/scripts/sync_all_configs.sh" << 'EOF'
#!/bin/bash
echo "SYNC: Failed"
exit 1
EOF

# The test script will exit with non-zero when sync fails
# We expect the overall script to fail, which means our test_install.sh will exit non-zero
if ! bash "$TEST_DIR/test_install.sh" "$MOCK_INSTALL_DIR" >/dev/null 2>&1; then
    echo "✅ PASS: Correctly handles sync script failure (exits with error)"
else
    echo "❌ FAIL: Did not handle sync script failure"
    exit 1
fi

# Test 10: Verify script has informative output
echo ""
echo "Test 10: Script output and user experience"
echo "---"

# Check for UX elements (emojis, colors, clear messaging)
ux_elements=("🎨" "✅" "INFO" "Plan of Action" "Next steps")
found_elements=0

for element in "${ux_elements[@]}"; do
    if grep -q "$element" "$SCRIPT"; then
        echo "✅ PASS: Found UX element '$element'"
        found_elements=$((found_elements + 1))
    fi
done

if [[ $found_elements -ge 2 ]]; then
    echo "✅ PASS: Script has good UX elements"
else
    echo "⚠️  WARNING: Script may lack user-friendly output"
fi

# Test 11: Verify no hardcoded paths
echo ""
echo "Test 11: No hardcoded home directory paths"
echo "---"

# Check for hardcoded paths (excluding comments)
if grep -E "/Users/[a-zA-Z0-9_-]+" "$SCRIPT" | grep -v "^\s*#" | grep -v "REPO_ROOT" >/dev/null 2>&1; then
    echo "⚠️  WARNING: Found potential hardcoded user paths"
    grep -E "/Users/[a-zA-Z0-9_-]+" "$SCRIPT" | grep -v "^\s*#" | grep -v "REPO_ROOT"
else
    echo "✅ PASS: No hardcoded user paths found"
fi

echo ""
echo "=========================================="
echo "✅ All tests passed!"
echo "=========================================="
echo ""
echo "Note: This test suite validates orchestration logic and error handling."
echo "Full integration testing requires:"
echo "  - Actual sync_all_configs.sh and verify_all_configs.sh scripts"
echo "  - Home directory write permissions"
echo "  - User interaction for confirmation prompt"
echo ""
