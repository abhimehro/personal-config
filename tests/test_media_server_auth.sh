#!/bin/bash

# Setup Mock Bin
MOCK_BIN=$(mktemp -d)
cat > "$MOCK_BIN/rclone" << 'EOF'
#!/bin/bash
if [[ "$1" == "listremotes" ]]; then
    echo "media:"
    exit 0
fi
if [[ "$1" == "serve" ]]; then
    echo "MOCK RCLONE SERVE CALLED"
    # Check args
    while [[ $# -gt 0 ]]; do
        case $1 in
            --user)
                echo "USER=$2"
                shift
                shift
                ;;
            --pass)
                echo "PASS=$2"
                shift
                shift
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
export PATH="$MOCK_BIN:$PATH"

# Mock HOME
TEST_HOME=$(mktemp -d)
export HOME="$TEST_HOME"

# Setup config
mkdir -p "$HOME/.config/media-server"

FAIL=0

# Case 1: Missing credentials
echo "Test 1: Missing credentials"
if ./media-streaming/scripts/start-media-server.sh >/dev/null 2>&1; then
    echo "FAIL: Should have failed with missing credentials"
    FAIL=1
else
    echo "PASS: Failed as expected"
fi

# Case 2: Credentials in file
echo "MEDIA_USER=testuser" > "$HOME/.config/media-server/credentials"
echo "MEDIA_PASS=testpass" >> "$HOME/.config/media-server/credentials"

echo "Test 2: Credentials in file"
OUTPUT=$(./media-streaming/scripts/start-media-server.sh)
if echo "$OUTPUT" | grep -q "USER=testuser" && echo "$OUTPUT" | grep -q "PASS=testpass"; then
    echo "PASS: Credentials loaded correctly"
else
    echo "FAIL: Credentials not loaded correctly"
    echo "Output: $OUTPUT"
    FAIL=1
fi

# Cleanup
rm -rf "$TEST_HOME"
rm -rf "$MOCK_BIN"

exit $FAIL
