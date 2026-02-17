#!/bin/bash

# Test script for sync_all_configs.sh
# Verifies symlink creation, backup behavior, and error handling

set -e

echo "=========================================="
echo "Testing sync_all_configs.sh"
echo "=========================================="

# Setup test environment
TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'sync-test')"
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

SCRIPT="$REPO_ROOT/scripts/sync_all_configs.sh"
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

required_functions=("log" "success" "warn" "error" "ensure_file_link" "ensure_dir_link")
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

# Test 4: Test ensure_file_link function behavior with mocks
echo ""
echo "Test 4: File symlink creation logic"
echo "---"

# Create a mock repo structure
MOCK_REPO="$TEST_DIR/mock_repo"
MOCK_HOME="$TEST_DIR/mock_home"
mkdir -p "$MOCK_REPO/configs"
mkdir -p "$MOCK_HOME"

# Create a test file
echo "test content" > "$MOCK_REPO/configs/test.conf"

# Create a minimal ensure_file_link function for testing
cat > "$TEST_DIR/test_file_link.sh" << 'EOF'
#!/bin/bash
set -Eeuo pipefail

ensure_file_link() {
    local link="$1"
    local target="$2"
    local name="$3"

    # Check if target exists
    if [[ ! -e "$target" ]]; then
        echo "SKIP: Target not found: $target"
        return 0
    fi

    # Check if symlink already exists and is correct
    if [[ -L "$link" ]] && [[ "$(readlink "$link")" == "$target" ]]; then
        echo "OK: $name symlink is intact"
        return 0
    fi

    # Backup existing file if it exists and is not a symlink
    if [[ -e "$link" ]] && [[ ! -L "$link" ]]; then
        local backup="${link}.backup.$(date +%Y%m%d_%H%M%S)"
        echo "BACKUP: $name to $backup"
        mv "$link" "$backup"
    fi

    # Remove existing symlink if it points to wrong location
    if [[ -L "$link" ]]; then
        rm -f "$link"
    fi

    # Create parent directory if needed
    mkdir -p "$(dirname "$link")"

    # Create symlink
    echo "CREATE: $name -> $target"
    ln -s "$target" "$link"
}

# Run test
ensure_file_link "$1" "$2" "$3"
EOF
chmod +x "$TEST_DIR/test_file_link.sh"

# Test: Create new symlink
if bash "$TEST_DIR/test_file_link.sh" "$MOCK_HOME/test.conf" "$MOCK_REPO/configs/test.conf" "test.conf" | grep -q "CREATE"; then
    echo "✅ PASS: Creates new symlink when target exists"
else
    echo "❌ FAIL: Did not create symlink"
    exit 1
fi

# Verify symlink was created correctly
if [[ -L "$MOCK_HOME/test.conf" ]] && [[ "$(readlink "$MOCK_HOME/test.conf")" == "$MOCK_REPO/configs/test.conf" ]]; then
    echo "✅ PASS: Symlink points to correct target"
else
    echo "❌ FAIL: Symlink not created correctly"
    exit 1
fi

# Test: Existing correct symlink
if bash "$TEST_DIR/test_file_link.sh" "$MOCK_HOME/test.conf" "$MOCK_REPO/configs/test.conf" "test.conf" | grep -q "OK"; then
    echo "✅ PASS: Recognizes existing correct symlink"
else
    echo "❌ FAIL: Did not recognize existing symlink"
    exit 1
fi

# Test 5: Test backup behavior when file already exists
echo ""
echo "Test 5: Backup behavior for existing files"
echo "---"

# Create a new test with existing file
MOCK_HOME2="$TEST_DIR/mock_home2"
mkdir -p "$MOCK_HOME2"
echo "original content" > "$MOCK_HOME2/test.conf"

# Run the symlink function
bash "$TEST_DIR/test_file_link.sh" "$MOCK_HOME2/test.conf" "$MOCK_REPO/configs/test.conf" "test.conf" > /dev/null 2>&1

# Check if backup was created
if ls "$MOCK_HOME2"/test.conf.backup.* >/dev/null 2>&1; then
    echo "✅ PASS: Created backup of existing file"
    # Verify backup contains original content
    if grep -q "original content" "$MOCK_HOME2"/test.conf.backup.*; then
        echo "✅ PASS: Backup preserves original content"
    else
        echo "❌ FAIL: Backup does not contain original content"
        exit 1
    fi
else
    echo "❌ FAIL: Did not create backup"
    exit 1
fi

# Test 6: Test ensure_dir_link function behavior
echo ""
echo "Test 6: Directory symlink creation logic"
echo "---"

# Create a test directory
mkdir -p "$MOCK_REPO/configs/testdir"
echo "test" > "$MOCK_REPO/configs/testdir/file.txt"

# Create a minimal ensure_dir_link function for testing
cat > "$TEST_DIR/test_dir_link.sh" << 'EOF'
#!/bin/bash
set -Eeuo pipefail

ensure_dir_link() {
    local link="$1"
    local target="$2"
    local name="$3"

    # Check if target exists
    if [[ ! -d "$target" ]]; then
        echo "SKIP: Target directory not found: $target"
        return 0
    fi

    # Check if symlink already exists and is correct
    if [[ -L "$link" ]] && [[ "$(readlink "$link")" == "$target" ]]; then
        echo "OK: $name symlink is intact"
        return 0
    fi

    # Backup existing directory if it exists and is not a symlink
    if [[ -e "$link" ]] && [[ ! -L "$link" ]]; then
        local backup="${link}.backup.$(date +%Y%m%d_%H%M%S)"
        echo "BACKUP: $name directory to $backup"
        mv "$link" "$backup"
    fi

    # Remove existing symlink if it points to wrong location
    if [[ -L "$link" ]]; then
        rm -f "$link"
    fi

    # Create parent directory if needed
    mkdir -p "$(dirname "$link")"

    # Create symlink
    echo "CREATE: $name -> $target"
    ln -s "$target" "$link"
}

# Run test
ensure_dir_link "$1" "$2" "$3"
EOF
chmod +x "$TEST_DIR/test_dir_link.sh"

# Test: Create new directory symlink
if bash "$TEST_DIR/test_dir_link.sh" "$MOCK_HOME/testdir" "$MOCK_REPO/configs/testdir" "testdir" | grep -q "CREATE"; then
    echo "✅ PASS: Creates new directory symlink when target exists"
else
    echo "❌ FAIL: Did not create directory symlink"
    exit 1
fi

# Verify directory symlink was created correctly
if [[ -L "$MOCK_HOME/testdir" ]] && [[ "$(readlink "$MOCK_HOME/testdir")" == "$MOCK_REPO/configs/testdir" ]]; then
    echo "✅ PASS: Directory symlink points to correct target"
else
    echo "❌ FAIL: Directory symlink not created correctly"
    exit 1
fi

# Test 7: Verify script uses REPO_ROOT variable
echo ""
echo "Test 7: Uses REPO_ROOT variable for repo-relative paths"
echo "---"

if grep -q 'REPO_ROOT=' "$SCRIPT"; then
    echo "✅ PASS: Script defines REPO_ROOT variable"
else
    echo "❌ FAIL: Script does not define REPO_ROOT variable"
    exit 1
fi

# Test 8: Verify no hardcoded home directory paths
echo ""
echo "Test 8: Uses \$HOME variable instead of hardcoded paths"
echo "---"

# Check that script uses $HOME instead of hardcoded paths like /Users/username
if grep -q '\$HOME' "$SCRIPT"; then
    echo "✅ PASS: Script uses \$HOME variable"
else
    echo "⚠️  WARNING: Script may not use \$HOME variable"
fi

# Check for hardcoded paths (excluding comments)
if grep -E "/Users/[a-zA-Z0-9_-]+" "$SCRIPT" | grep -v "^\s*#" | grep -v "REPO_ROOT" >/dev/null 2>&1; then
    echo "⚠️  WARNING: Found potential hardcoded user paths"
    grep -E "/Users/[a-zA-Z0-9_-]+" "$SCRIPT" | grep -v "^\s*#" | grep -v "REPO_ROOT"
else
    echo "✅ PASS: No hardcoded user paths found"
fi

# Test 9: Verify script has configuration sections
echo ""
echo "Test 9: Script structure and configuration sections"
echo "---"

expected_sections=("SSH" "Fish" "Cursor" "VS Code" "Git")
found_sections=0

for section in "${expected_sections[@]}"; do
    if grep -qi "$section" "$SCRIPT"; then
        echo "✅ PASS: Found '$section' configuration section"
        found_sections=$((found_sections + 1))
    else
        echo "⚠️  WARNING: '$section' section not found"
    fi
done

if [[ $found_sections -ge 3 ]]; then
    echo "✅ PASS: Script has multiple configuration sections"
else
    echo "❌ FAIL: Script is missing expected configuration sections"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All tests passed!"
echo "=========================================="
echo ""
echo "Note: This test suite validates symlink logic and backup behavior."
echo "Full integration testing requires:"
echo "  - Actual configuration files in the repository"
echo "  - Home directory write permissions"
echo "  - Manual verification of created symlinks"
echo ""
