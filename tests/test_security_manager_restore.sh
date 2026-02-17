#!/usr/bin/env bash
set -e

# Setup mock environment
TEST_DIR=$(mktemp -d)
MOCK_HOME="$TEST_DIR/home"
MOCK_LOGS="$MOCK_HOME/Library/Logs/maintenance"
mkdir -p "$MOCK_LOGS/backups"
mkdir -p "$MOCK_HOME/conf"
mkdir -p "$MOCK_HOME/bin"
mkdir -p "$MOCK_HOME/launchd"

# Create dummy config
echo "dummy config" > "$MOCK_HOME/conf/config.env"
echo "dummy script" > "$MOCK_HOME/bin/script.sh"
chmod +x "$MOCK_HOME/bin/script.sh"

# Mock HOME for the script
export HOME="$MOCK_HOME"

# Source the script
# We need to be careful because the script sets CONFIG_DIR based on its location
# We'll copy the script to our temp dir to control CONFIG_DIR
cp maintenance/bin/security_manager.sh "$TEST_DIR/security_manager.sh"
chmod +x "$TEST_DIR/security_manager.sh"

# Override CONFIG_DIR and BACKUP_DIR for testing to point to our mock
# We can't easily source it because it sets constants at top level.
# So we modify the script to inject our paths.
sed -i "s|LOG_DIR=\"\$HOME/Library/Logs/maintenance\"|LOG_DIR=\"$MOCK_LOGS\"|g" "$TEST_DIR/security_manager.sh"
sed -i "s|BACKUP_DIR=\"\$HOME/Library/Logs/maintenance/backups\"|BACKUP_DIR=\"$MOCK_LOGS/backups\"|g" "$TEST_DIR/security_manager.sh"
# Allow CONFIG_DIR override
sed -i 's|CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE\[0\]}")/../" && pwd)"|CONFIG_DIR="${CONFIG_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)}"|' "$TEST_DIR/security_manager.sh"

# Create a wrapper script to export internal functions and set CONFIG_DIR
WRAPPER="$TEST_DIR/wrapper.sh"
cat > "$WRAPPER" <<EOF
#!/bin/bash
export HOME="$MOCK_HOME"
# Override CONFIG_DIR logic
CONFIG_DIR="$MOCK_HOME"
source "$TEST_DIR/security_manager.sh"

# Helper to capture last line of output
get_last_line() {
    tail -n 1
}

# Expose internal functions
cmd="\$1"
shift
if [[ "\$cmd" == "backup_config" ]]; then
    backup_config "\$@"
elif [[ "\$cmd" == "restore_config" ]]; then
    restore_config "\$@"
fi
EOF
chmod +x "$WRAPPER"

echo "Creating backup..."
# Capture output to get path
BACKUP_OUTPUT=$("$WRAPPER" backup_config full)
BACKUP_PATH=$(echo "$BACKUP_OUTPUT" | tail -n 1)
echo "Backup created at: $BACKUP_PATH"

if [[ ! -f "$BACKUP_PATH" ]]; then
    echo "❌ Backup file not created!"
    echo "Output: $BACKUP_OUTPUT"
    rm -rf "$TEST_DIR"
    exit 1
fi

# Verify restore preview works
echo "Testing restore preview..."
"$WRAPPER" restore_config "$BACKUP_PATH" preview

# Verify actual restore
echo "Testing actual restore..."
# Modify the config file to verify restore overwrites it
echo "modified config" > "$MOCK_HOME/conf/config.env"
# Use 'yes' to answer prompts (system config restore, etc.)
echo "y" | "$WRAPPER" restore_config "$BACKUP_PATH" restore

if grep -q "dummy config" "$MOCK_HOME/conf/config.env"; then
    echo "✅ Restore successful (config overwritten)"
else
    echo "❌ Restore failed (config not overwritten)"
    echo "Content of config.env:"
    cat "$MOCK_HOME/conf/config.env"
    rm -rf "$TEST_DIR"
    exit 1
fi

# Test tamper detection during restore
echo "Tampering with backup..."
echo "CORRUPTION" >> "$BACKUP_PATH"

echo "Testing restore with tampered backup (should fail)..."
# Expect failure, so prompts might not be reached, but pipe 'y' just in case
if echo "y" | "$WRAPPER" restore_config "$BACKUP_PATH" restore; then
    echo "❌ Tampered backup restore succeeded (should have failed)!"
    rm -rf "$TEST_DIR"
    exit 1
else
    echo "✅ Tampered backup restore failed as expected."
fi

rm -rf "$TEST_DIR"
echo "All tests passed."
