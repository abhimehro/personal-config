#!/bin/bash

# Use a temporary HOME to avoid writing artifacts into the real user directory
ORIG_HOME="$HOME"
TEST_HOME=$(mktemp -d)
export HOME="$TEST_HOME"
mkdir -p "$HOME/Library/Logs"

# Setup Mock Bin
MOCK_BIN=$(mktemp -d)
export PATH="$MOCK_BIN:$PATH"

# Cleanup trap — always remove temp dirs even on early failure
cleanup() {
    rm -rf "$MOCK_BIN" "$TEST_HOME"
    export HOME="$ORIG_HOME"
}
trap cleanup EXIT

# Mock utilities
cat > "$MOCK_BIN/rclone" << 'EOF'
#!/bin/bash
if [[ "$1" == "listremotes" ]]; then
    echo "media:"
    exit 0
fi
if [[ "$1" == "serve" ]]; then
    # Print arguments for verification
    echo "MOCK_RCLONE_CMD: $@"
    # Sleep to simulate running server
    sleep 2
    exit 0
fi
EOF

cat > "$MOCK_BIN/op" << 'EOF'
#!/bin/bash
if [[ "$1" == "read" ]]; then
    echo "mock-secret"
    exit 0
fi
exit 1
EOF

cat > "$MOCK_BIN/lsof" << 'EOF'
#!/bin/bash
exit 1 # No ports listening
EOF

cat > "$MOCK_BIN/route" << 'EOF'
#!/bin/bash
echo "interface: en0"
EOF

cat > "$MOCK_BIN/ifconfig" << 'EOF'
#!/bin/bash
# Return a mock LAN address for whichever interface is requested
echo "	inet 192.168.1.42 netmask 0xffffff00 broadcast 192.168.1.255"
EOF

cat > "$MOCK_BIN/curl" << 'EOF'
#!/bin/bash
echo "unknown"
EOF

cat > "$MOCK_BIN/pkill" << 'EOF'
#!/bin/bash
exit 0
EOF

chmod +x "$MOCK_BIN/"*

# Test media-server-daemon.sh
echo "Testing media-server-daemon.sh..."
OUTPUT=$(bash media-streaming/scripts/media-server-daemon.sh 2>&1)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "MOCK_RCLONE_CMD:.*--addr 0.0.0.0"; then
    echo "FAIL: media-server-daemon.sh still binding to 0.0.0.0"
    exit 1
elif echo "$OUTPUT" | grep -q "MOCK_RCLONE_CMD:.*--addr"; then
     echo "PASS: media-server-daemon.sh bound to specific IP (not 0.0.0.0)"
else
     echo "FAIL: usage of --addr not found in output"
     exit 1
fi

# Test final-media-server.sh (Auto mode)
echo "Testing final-media-server.sh (Auto)..."
LOG_FILE="$HOME/Library/Logs/media-server.log"

# Ensure we are not reading stale log content from a previous run
rm -f "$LOG_FILE"

# Reduce sleep in script to speed up test? The script sleeps 5.
# We can just run it. The mock sleeps 2. script sleeps 5. process will be dead by check.
# But we care about the LOG content.
bash media-streaming/scripts/final-media-server.sh >/dev/null 2>&1
FINAL_EXIT_CODE=$?

# Fail fast if the script itself failed; otherwise, later checks could be misleading
if [[ $FINAL_EXIT_CODE -ne 0 ]]; then
    echo "FAIL: final-media-server.sh (Auto) exited with status $FINAL_EXIT_CODE"
    exit 1
fi

# Ensure the log file was actually produced by this run
if [[ ! -f "$LOG_FILE" ]]; then
    echo "FAIL: final-media-server.sh (Auto) did not create log file at $LOG_FILE"
    exit 1
fi

LOG_CONTENT=$(cat "$LOG_FILE")
echo "LOG CONTENT:"
echo "$LOG_CONTENT"

if echo "$LOG_CONTENT" | grep -q "MOCK_RCLONE_CMD:.*--addr 0.0.0.0"; then
    echo "FAIL: final-media-server.sh (Auto) still binding to 0.0.0.0"
    exit 1
elif echo "$LOG_CONTENT" | grep -q "MOCK_RCLONE_CMD:.*--addr"; then
     echo "PASS: final-media-server.sh bound to specific IP (not 0.0.0.0)"
else
     echo "FAIL: usage of --addr not found in log"
     exit 1
fi

# Cleanup handled by EXIT trap
echo "All tests passed."
exit 0
