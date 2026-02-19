#!/usr/bin/env bash
set -e

# Setup mock environment
TEST_DIR=$(mktemp -d)
MOCK_HOME="$TEST_DIR/home"
MOCK_LOGS="$MOCK_HOME/Library/Logs/maintenance"
mkdir -p "$MOCK_LOGS/backups"
mkdir -p "$MOCK_HOME/conf"
mkdir -p "$MOCK_HOME/bin"

# Create dummy config
echo "dummy config" > "$MOCK_HOME/conf/config.env"
echo "dummy script" > "$MOCK_HOME/bin/script.sh"

# Mock HOME for the script
export HOME="$MOCK_HOME"

# Source the script
# We need to be careful because the script sets CONFIG_DIR based on its location
source maintenance/bin/security_manager.sh

# Override CONFIG_DIR and BACKUP_DIR for testing to point to our mock
# Note: We must override these AFTER sourcing; export so sourced functions see them
CONFIG_DIR="$MOCK_HOME"
BACKUP_DIR="$MOCK_LOGS/backups"
LOG_DIR="$MOCK_LOGS"
SECURITY_LOG="$LOG_DIR/security.log"
export CONFIG_DIR BACKUP_DIR LOG_DIR SECURITY_LOG

# 1. Create Backup
echo "Creating backup..."
# backup_config returns the path to stdout, but also logs to stdout.
# We take the last line as the path.
BACKUP_OUTPUT=$(backup_config full)
BACKUP_FILE=$(echo "$BACKUP_OUTPUT" | tail -n 1)
echo "Backup created at: $BACKUP_FILE"

# Verify checksum file exists
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [[ ! -f "$CHECKSUM_FILE" ]]; then
    echo "❌ Checksum file not created: $CHECKSUM_FILE"
    echo "Backup output:"
    echo "$BACKUP_OUTPUT"
    exit 1
fi
echo "✅ Checksum file created."

# 2. Verify Restore (should pass)
echo "Testing valid restore..."
if check_backup_safety "$BACKUP_FILE"; then
    echo "✅ Backup safety check passed."
else
    echo "❌ Backup safety check failed for valid backup!"
    exit 1
fi

# 3. Tamper with Backup
echo "Tampering with backup..."
# We append garbage to the end of the gzip file.
# Note: gzip might ignore trailing garbage, but shasum won't.
echo "CORRUPTION" >> "$BACKUP_FILE"

# 4. Verify Restore Fails
echo "Testing tampered restore (should fail)..."
# check_backup_safety returns 0 on success, 1 on failure.
if check_backup_safety "$BACKUP_FILE"; then
    echo "❌ Tampered backup passed safety check!"
    exit 1
else
    echo "✅ Tampered backup failed safety check as expected."
fi

# Clean up
rm -rf "$TEST_DIR"
echo "All tests passed."
