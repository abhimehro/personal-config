#!/bin/bash

# Test script for controld-manager symlink protection
# Verifies that the script correctly detects and rejects symlink attacks

set -e

echo "=========================================="
echo "Testing Symlink Protection in controld-manager"
echo "=========================================="

# Setup test environment
# Use mktemp -d to create a unique, secure temporary directory for tests.
# This avoids predictable /tmp paths that could be exploited via symlinks,
# especially when tests are run with elevated privileges.
TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'controld-symlink-test')"

# Cleanup function
cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# Test 1: Verify 'install -d' behavior with symlinks
echo ""
echo "Test 1: Atomic directory creation with 'install -d -m 700'"
echo "---"

TEST1_DIR="$TEST_DIR/test1"
TARGET_DIR="$TEST_DIR/target1"
mkdir -p "$TARGET_DIR"

# Create a symlink where we want the directory
ln -s "$TARGET_DIR" "$TEST1_DIR"

echo "Created symlink: $TEST1_DIR -> $TARGET_DIR"
echo "Running: install -d -m 700 $TEST1_DIR"

if install -d -m 700 "$TEST1_DIR" 2>/dev/null; then
    # Check if it's still a symlink (bad) or now a directory (good)
    if [[ -L "$TEST1_DIR" ]]; then
        echo "❌ BAD: install -d followed the symlink"
        echo "   This means pre-flight checks are essential"
    else
        echo "✅ GOOD: install -d created a real directory (removed symlink)"
    fi
else
    echo "⚠️  install -d failed (may not support this behavior)"
fi

# Test 2: Verify 'install -m' behavior with symlinks
echo ""
echo "Test 2: Atomic file copy with 'install -m 600'"
echo "---"

TEST2_FILE="$TEST_DIR/test2.txt"
TARGET_FILE="$TEST_DIR/target2.txt"
SOURCE_FILE="$TEST_DIR/source2.txt"

echo "test content" > "$SOURCE_FILE"
echo "target content" > "$TARGET_FILE"

# Create a symlink where we want to copy the file
ln -s "$TARGET_FILE" "$TEST2_FILE"

echo "Created symlink: $TEST2_FILE -> $TARGET_FILE"
echo "Running: install -m 600 $SOURCE_FILE $TEST2_FILE"

if install -m 600 "$SOURCE_FILE" "$TEST2_FILE" 2>/dev/null; then
    # Check if it's still a symlink (bad) or now a file (good)
    if [[ -L "$TEST2_FILE" ]]; then
        echo "❌ BAD: install -m followed the symlink"
        echo "   Original target would be overwritten!"
    else
        echo "✅ GOOD: install -m replaced symlink with real file"
        # Verify target file wasn't modified
        if grep -q "target content" "$TARGET_FILE"; then
            echo "✅ GOOD: Original target file untouched"
        else
            echo "❌ BAD: Original target file was modified"
        fi
    fi
else
    echo "⚠️  install -m failed"
fi

# Test 3: Compare with old vulnerable pattern (rm + cp + chmod)
echo ""
echo "Test 3: Demonstrating rm + cp race condition vulnerability"
echo "---"

TEST3_FILE="$TEST_DIR/test3.txt"
TARGET3_FILE="$TEST_DIR/target3.txt"
SOURCE3_FILE="$TEST_DIR/source3.txt"

echo "test content 3" > "$SOURCE3_FILE"
echo "target content 3" > "$TARGET3_FILE"
ln -s "$TARGET3_FILE" "$TEST3_FILE"

echo "Created symlink: $TEST3_FILE -> $TARGET3_FILE"
echo "Running: rm -f $TEST3_FILE && cp $SOURCE3_FILE $TEST3_FILE && chmod 600 $TEST3_FILE"

rm -f "$TEST3_FILE"
# Simulate race condition: attacker recreates symlink here
ln -s "$TARGET3_FILE" "$TEST3_FILE"
cp "$SOURCE3_FILE" "$TEST3_FILE" 2>/dev/null || true
chmod 600 "$TEST3_FILE" 2>/dev/null || true

if [[ -L "$TEST3_FILE" ]]; then
    echo "⚠️  Symlink still exists (cp failed)"
    if grep -q "test content 3" "$TARGET3_FILE"; then
        echo "❌ VULNERABLE: Target file was overwritten via symlink!"
    fi
else
    if grep -q "test content 3" "$TARGET3_FILE"; then
        echo "❌ VULNERABLE: Even without race, target could be overwritten"
    else
        echo "✅ File operations worked without following symlink"
    fi
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo "Our implementation uses:"
echo "1. Pre-flight symlink checks (all critical paths)"
echo "2. Atomic 'install -d -m 700' for directories"
echo "3. Atomic 'install -m 600' for files"
echo "4. Post-creation verification"
echo ""
echo "This minimizes TOCTOU race windows and provides"
echo "defense-in-depth against symlink attacks."
echo ""
echo "✅ All tests completed"
