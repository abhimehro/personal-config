#!/bin/bash
set -euo pipefail

# Setup Mock Environment
MOCK_HOME=$(mktemp -d)
export HOME="$MOCK_HOME"
MOCK_BIN=$(mktemp -d)
mkdir -p "$HOME/Library/Logs"
trap 'rm -rf "$MOCK_BIN" "$MOCK_HOME"' EXIT

# Mock pkill to prevent killing real processes
cat >"$MOCK_BIN/pkill" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$MOCK_BIN/pkill"
# Create a mock rclone that prints env vars and args
cat >"$MOCK_BIN/rclone" <<'EOF'
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
cat >"$MOCK_BIN/op" <<'EOF'
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
cat >"$MOCK_BIN/lsof" <<'EOF'
#!/bin/bash
exit 1 # No port listening
EOF
chmod +x "$MOCK_BIN/lsof"

# Create mock ifconfig, route, curl
cat >"$MOCK_BIN/ifconfig" <<'EOF'
#!/bin/bash
echo "inet 192.168.1.100"
EOF
chmod +x "$MOCK_BIN/ifconfig"

cat >"$MOCK_BIN/route" <<'EOF'
#!/bin/bash
echo "interface: en0"
EOF
chmod +x "$MOCK_BIN/route"

cat >"$MOCK_BIN/curl" <<'EOF'
#!/bin/bash
echo "1.2.3.4"
EOF
chmod +x "$MOCK_BIN/curl"

# Mock ps always succeeds so final-media-server.sh's `ps -p $SERVER_PID`
# check passes even when the mock rclone exits immediately.
cat >"$MOCK_BIN/ps" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$MOCK_BIN/ps"

# Mock sleep to collapse long cosmetic delays (spinner_wait, daemon startup
# grace periods) while still allowing sub-second polling sleeps to pass
# through to the real /bin/sleep.
cat >"$MOCK_BIN/sleep" <<'EOF'
#!/bin/bash
case "${1:-0}" in
    0.*) exec /bin/sleep "$1" ;;
    *)   exit 0 ;;
esac
EOF
chmod +x "$MOCK_BIN/sleep"

export PATH="$MOCK_BIN:$PATH"

# Poll a file until a marker string appears or a timeout is reached.
# Useful for tests that start a background process and must wait for it to
# write expected output before asserting.
wait_for_log_marker() {
	local file="$1"
	local marker="$2"
	local timeout_ms="${3:-2000}"
	local waited=0
	while ((waited < timeout_ms)); do
		[[ -f "$file" ]] && grep -q "$marker" "$file" 2>/dev/null && return 0
		sleep 0.05
		waited=$((waited + 50))
	done
	return 1
}

# Test 1: media-server-daemon.sh
echo "Test 1: media-server-daemon.sh"
OUTPUT=$(./media-streaming/scripts/media-server-daemon.sh 2>&1 || true)
# Note: execution might fail because rclone exits immediately, but we capture output

if echo "$OUTPUT" | grep -q "ENV_RCLONE_USER=mockuser" &&
	echo "$OUTPUT" | grep -q "ENV_RCLONE_PASS=mockpass"; then
	echo "PASS: Environment variables exported correctly"
else
	echo "FAIL: Environment variables missing or incorrect"
	echo "Output: $OUTPUT"
	exit 1
fi

if echo "$OUTPUT" | grep -q "ARG_USER=" ||
	echo "$OUTPUT" | grep -q "ARG_PASS="; then
	echo "FAIL: Arguments --user or --pass still present"
	echo "Output: $OUTPUT"
	exit 1
else
	echo "PASS: No command line arguments for user/pass"
fi

# Test 2: final-media-server.sh
echo "Test 2: final-media-server.sh"
# Execute the real script. The $MOCK_BIN/sleep shim collapses cosmetic
# spinner delays, and the $MOCK_BIN/ps mock lets the script proceed even
# though the mock rclone exits immediately.

# Update mock rclone: write env vars (with <UNSET> diagnostics) and arg
# checks, then exit immediately. The `ps` mock always succeeds, so we don't
# need a long-lived background process.
cat >"$MOCK_BIN/rclone" <<'EOF'
#!/bin/bash
if [[ "$1" == "listremotes" ]]; then
    echo "media:"
    exit 0
fi
if [[ "$1" == "serve" ]]; then
    : > "$HOME/Library/Logs/media-server.log"
    echo "MOCK RCLONE SERVE CALLED" >> "$HOME/Library/Logs/media-server.log"
    echo "ENV_RCLONE_USER=${RCLONE_USER-<UNSET>}" >> "$HOME/Library/Logs/media-server.log"
    echo "ENV_RCLONE_PASS=${RCLONE_PASS-<UNSET>}" >> "$HOME/Library/Logs/media-server.log"

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
    exit 0
fi
EOF
chmod +x "$MOCK_BIN/rclone"

./media-streaming/scripts/final-media-server.sh >/dev/null 2>&1 || true

# Check log file
# Log file location might vary because $HOME is not mocked fully (only for .config if I set it)
# But in my script I used $HOME/Library/Logs
# But final-media-server.sh uses ~/Library/Logs which expands to $HOME/Library/Logs.
LOG_FILE="$HOME/Library/Logs/media-server.log"

# Wait for the background rclone to flush its credential markers to the log
# before asserting. This avoids fixed-sleep races.
if ! wait_for_log_marker "$LOG_FILE" "ENV_RCLONE_PASS=" 2000; then
	echo "FAIL: expected log file not found or missing credential marker: $LOG_FILE"
	echo "Hint: final-media-server.sh may have failed before writing the log."
	exit 1
fi

# Read log content; if this fails (e.g., permissions), report clearly
if ! LOG_CONTENT=$(<"$LOG_FILE"); then
	echo "FAIL: unable to read log file: $LOG_FILE"
	exit 1
fi
if echo "$LOG_CONTENT" | grep -q "ENV_RCLONE_USER=mockuser" &&
	echo "$LOG_CONTENT" | grep -q "ENV_RCLONE_PASS=mockpass"; then
	echo "PASS: final-media-server.sh exports env vars"
else
	echo "FAIL: final-media-server.sh missing env vars"
	echo "Log: $LOG_CONTENT"
	exit 1
fi

if echo "$LOG_CONTENT" | grep -q "ARG_USER=" ||
	echo "$LOG_CONTENT" | grep -q "ARG_PASS="; then
	echo "FAIL: final-media-server.sh still uses args"
	echo "Log: $LOG_CONTENT"
	exit 1
else
	echo "PASS: final-media-server.sh no args"
fi

echo "ALL TESTS PASSED"
