#!/bin/bash
set -euo pipefail

# Setup Mock Environment
export HOME=$(mktemp -d)
MOCK_BIN=$(mktemp -d)
mkdir -p "$HOME/Library/Logs"

# Mock pkill to prevent killing real processes
cat > "$MOCK_BIN/pkill" << 'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$MOCK_BIN/pkill"
# Create a mock rclone that prints env vars and args
cat > "$MOCK_BIN/rclone" << 'EOF'
#!/bin/bash
if [[ "$1" == "listremotes" ]]; then
    echo "media:"
    exit 0
fi
if [[ "$1" == "serve" ]]; then
    echo "MOCK RCLONE SERVE CALLED"
    echo "ENV_RCLONE_USER=$RCLONE_USER"
    echo "ENV_RCLONE_PASS=$RCLONE_PASS"
    # Check args for user/pass
    while [[ $# -gt 0 ]]; do
        case $1 in
            --user)
                echo "ARG_USER=$2"
                shift 2
                ;;
            --pass)
                echo "ARG_PASS=$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    # Keep running to simulate daemon if needed, but for test we exit
    exit 0
fi
EOF
chmod +x "$MOCK_BIN/rclone"

# Create a mock op (1Password)
cat > "$MOCK_BIN/op" << 'EOF'
#!/bin/bash
if [[ "$1" == "read" ]]; then
    if [[ "$2" == *"username"* ]]; then
        echo "mockuser"
    elif [[ "$2" == *"password"* ]]; then
        echo "mockpass"
    fi
    exit 0
fi
EOF
chmod +x "$MOCK_BIN/op"

# Create mock lsof
cat > "$MOCK_BIN/lsof" << 'EOF'
#!/bin/bash
exit 1 # No port listening
EOF
chmod +x "$MOCK_BIN/lsof"

# Create mock ifconfig, route, curl
cat > "$MOCK_BIN/ifconfig" << 'EOF'
#!/bin/bash
echo "inet 192.168.1.100"
EOF
chmod +x "$MOCK_BIN/ifconfig"

cat > "$MOCK_BIN/route" << 'EOF'
#!/bin/bash
echo "interface: en0"
EOF
chmod +x "$MOCK_BIN/route"

cat > "$MOCK_BIN/curl" << 'EOF'
#!/bin/bash
echo "1.2.3.4"
EOF
chmod +x "$MOCK_BIN/curl"

export PATH="$MOCK_BIN:$PATH"

# Setup dummy LOGS
mkdir -p "$HOME/Library/Logs"

# Test 1: media-server-daemon.sh
echo "Test 1: media-server-daemon.sh"
OUTPUT=$(./media-streaming/scripts/media-server-daemon.sh 2>&1 || true)
# Note: execution might fail because rclone exits immediately, but we capture output

if echo "$OUTPUT" | grep -q "ENV_RCLONE_USER=mockuser" && \
   echo "$OUTPUT" | grep -q "ENV_RCLONE_PASS=mockpass"; then
    echo "PASS: Environment variables exported correctly"
else
    echo "FAIL: Environment variables missing or incorrect"
    echo "Output: $OUTPUT"
    exit 1
fi

if echo "$OUTPUT" | grep -q "ARG_USER=" || \
   echo "$OUTPUT" | grep -q "ARG_PASS="; then
    echo "FAIL: Arguments --user or --pass still present"
    echo "Output: $OUTPUT"
    exit 1
else
    echo "PASS: No command line arguments for user/pass"
fi

# Test 2: final-media-server.sh
echo "Test 2: final-media-server.sh"
# This script uses nohup and & so we need to be careful.
# But since our mock rclone exits, it should be fine?
# Wait, final-media-server.sh checks `ps -p $SERVER_PID`.
# If mock rclone exits immediately, ps will fail and script will say failed.
# We need mock rclone to sleep a bit.

# Update mock rclone to sleep
cat > "$MOCK_BIN/rclone" << 'EOF'
#!/bin/bash
if [[ "$1" == "listremotes" ]]; then
    echo "media:"
    exit 0
fi
if [[ "$1" == "serve" ]]; then
    echo "MOCK RCLONE SERVE CALLED" > "$HOME/Library/Logs/media-server.log"
    echo "ENV_RCLONE_USER=$RCLONE_USER" >> "$HOME/Library/Logs/media-server.log"
    echo "ENV_RCLONE_PASS=$RCLONE_PASS" >> "$HOME/Library/Logs/media-server.log"

    while [[ $# -gt 0 ]]; do
        case $1 in
            --user)
                echo "ARG_USER=$2" >> "$HOME/Library/Logs/media-server.log"
                shift 2
                ;;
            --pass)
                echo "ARG_PASS=$2" >> "$HOME/Library/Logs/media-server.log"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    sleep 2
    exit 0
fi
EOF
chmod +x "$MOCK_BIN/rclone"

./media-streaming/scripts/final-media-server.sh >/dev/null 2>&1 || true

# Check log file
# Log file location might vary because $HOME is not mocked fully (only for .config if I set it)
# But in my script I used $HOME/Library/Logs
# But final-media-server.sh uses ~/Library/Logs which expands to $HOME/Library/Logs.

LOG_CONTENT=$(cat "$HOME/Library/Logs/media-server.log")

if echo "$LOG_CONTENT" | grep -q "ENV_RCLONE_USER=mockuser" && \
   echo "$LOG_CONTENT" | grep -q "ENV_RCLONE_PASS=mockpass"; then
    echo "PASS: final-media-server.sh exports env vars"
else
    echo "FAIL: final-media-server.sh missing env vars"
    echo "Log: $LOG_CONTENT"
    exit 1
fi

if echo "$LOG_CONTENT" | grep -q "ARG_USER=" || \
   echo "$LOG_CONTENT" | grep -q "ARG_PASS="; then
    echo "FAIL: final-media-server.sh still uses args"
    echo "Log: $LOG_CONTENT"
    exit 1
else
    echo "PASS: final-media-server.sh no args"
fi

rm -rf "$MOCK_BIN" "$HOME"
echo "ALL TESTS PASSED"
