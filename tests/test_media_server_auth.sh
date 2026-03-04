#!/usr/bin/env bash
#
# Unit tests for media-streaming/archive/scripts/start-media-server.sh
# Tests: credential file loading, auto-generated credentials, and security mock portability
# Mocks: security, rclone, pkill, ipconfig, openssl
#
# NOTE: The macOS `security` command is mocked via $MOCK_BIN so these tests run on Linux CI.
# Current media-server scripts use file-based credentials (not macOS Keychain); the mock
# is included so the test suite remains CI-portable if future scripts add Keychain support,
# and to validate that the mock infrastructure itself behaves correctly.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/media-streaming/archive/scripts/start-media-server.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-media-server-auth')
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0

check_grep() {
    local name="$1" pattern="$2" file="$3"
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "PASS: $name"; PASS=$((PASS + 1))
    else
        echo "FAIL: $name (pattern '$pattern' not found in $file)"; FAIL=$((FAIL + 1))
    fi
}

# ---- mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

SECURITY_LOG="$TEST_DIR/security.log"
RCLONE_LOG="$TEST_DIR/rclone.log"

# Mock security: records each invocation; returns a canned password for
# find-generic-password -w; exits non-zero for all other operations
# (simulates missing credential store on Linux CI).
cat > "$MOCK_BIN/security" << MOCK
#!/bin/bash
echo "security: \$*" >> "$SECURITY_LOG"
case "\$*" in
  *find-generic-password*-w*)
    echo "test-media-server-password"
    ;;
  *)
    exit 1
    ;;
esac
MOCK
chmod +x "$MOCK_BIN/security"

# Mock rclone: logs --user and --pass values; returns success for serve/listremotes
cat > "$MOCK_BIN/rclone" << MOCK
#!/bin/bash
if [[ "\$1" == "listremotes" ]]; then echo "media:"; exit 0; fi
if [[ "\$1" == "serve" ]]; then
  while [[ \$# -gt 0 ]]; do
    case \$1 in
      --user) echo "USER=\$2" >> "$RCLONE_LOG"; shift 2 ;;
      --pass) echo "PASS=\$2" >> "$RCLONE_LOG"; shift 2 ;;
      *) shift ;;
    esac
  done
  exit 0
fi
MOCK
chmod +x "$MOCK_BIN/rclone"

# Mock pkill: always succeeds (prevents killing real processes in CI)
cat > "$MOCK_BIN/pkill" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/pkill"

# Mock ipconfig: returns a LAN address (real script has a fallback, but mock avoids
# relying on the macOS ipconfig binary on Linux)
cat > "$MOCK_BIN/ipconfig" << 'MOCK'
#!/bin/bash
echo "192.168.1.100"
MOCK
chmod +x "$MOCK_BIN/ipconfig"

# Mock openssl: returns a predictable alphanumeric string so credential-generation
# tests can assert a known value rather than a random one
cat > "$MOCK_BIN/openssl" << 'MOCK'
#!/bin/bash
echo "testpasswordABC"
MOCK
chmod +x "$MOCK_BIN/openssl"

# ---- mock HOME isolation ----
MOCK_HOME="$TEST_DIR/home"
mkdir -p "$MOCK_HOME/.config/media-server"

echo "=== Testing media-streaming/archive/scripts/start-media-server.sh ==="

# ---- Test 1: credentials from file are passed to rclone ----
echo "Test 1: credentials from credentials file"
{
    echo "MEDIA_WEBDAV_USER='fileuser'"
    echo "MEDIA_WEBDAV_PASS='filepass'"
} > "$MOCK_HOME/.config/media-server/credentials"
: > "$RCLONE_LOG"
HOME="$MOCK_HOME" PATH="$MOCK_BIN:$PATH" bash "$SCRIPT" > "$TEST_DIR/t1.log" 2>&1 || true
check_grep "file credentials: user passed to rclone" "USER=fileuser" "$RCLONE_LOG"
check_grep "file credentials: pass passed to rclone" "PASS=filepass" "$RCLONE_LOG"

# ---- Test 2: missing credentials file → credentials are auto-generated ----
echo "Test 2: missing credentials → auto-generated"
rm -f "$MOCK_HOME/.config/media-server/credentials"
: > "$RCLONE_LOG"
HOME="$MOCK_HOME" PATH="$MOCK_BIN:$PATH" bash "$SCRIPT" > "$TEST_DIR/t2.log" 2>&1 || true
if [[ -f "$MOCK_HOME/.config/media-server/credentials" ]]; then
    echo "PASS: credentials file created on first run"; PASS=$((PASS + 1))
else
    echo "FAIL: credentials file not created on first run"
    cat "$TEST_DIR/t2.log"
    FAIL=$((FAIL + 1))
fi

# Validate generated credentials content and ensure rclone received exact values.
GENERATED_CREDS_FILE="$MOCK_HOME/.config/media-server/credentials"
GENERATED_USER=""
GENERATED_PASS=""
if [[ -f "$GENERATED_CREDS_FILE" ]]; then
    GENERATED_USER=$(grep '^MEDIA_WEBDAV_USER=' "$GENERATED_CREDS_FILE" | cut -d'=' -f2- || true)
    GENERATED_PASS=$(grep '^MEDIA_WEBDAV_PASS=' "$GENERATED_CREDS_FILE" | cut -d'=' -f2- || true)
fi

if [[ "$GENERATED_USER" == "infuse" ]]; then
    echo "PASS: generated credentials use default user 'infuse'"; PASS=$((PASS + 1))
else
    echo "FAIL: generated credentials user is '$GENERATED_USER', expected 'infuse'"; FAIL=$((FAIL + 1))
fi

if [[ -n "$GENERATED_PASS" ]]; then
    echo "PASS: generated credentials password is non-empty"; PASS=$((PASS + 1))
else
    echo "FAIL: generated credentials password is empty"; FAIL=$((FAIL + 1))
fi

check_grep "generated credentials: rclone called with default user" "USER=infuse" "$RCLONE_LOG"
if [[ -n "$GENERATED_PASS" ]]; then
    check_grep "generated credentials: rclone called with generated pass" "PASS=$GENERATED_PASS" "$RCLONE_LOG"
else
    echo "FAIL: skipping rclone password pattern check because generated password is empty"; FAIL=$((FAIL + 1))
fi
# ---- Test 3: security mock — find-generic-password returns expected password ----
# NOTE: start-media-server-fast.sh uses file-based credentials, not Keychain, so the
# security binary is not called by the script under test. Tests 3 and 4 validate the
# mock's portability (correct output and exit codes) in isolation so future scripts that
# do integrate Keychain can rely on this mock infrastructure without changes.
echo "Test 3: security mock — find-generic-password success"
MOCK_PASS=$(PATH="$MOCK_BIN:$PATH" "$MOCK_BIN/security" find-generic-password -w 2>&1 || true)
if [[ "$MOCK_PASS" == "test-media-server-password" ]]; then
    echo "PASS: security mock returns expected password"; PASS=$((PASS + 1))
else
    echo "FAIL: security mock returned unexpected output: $MOCK_PASS"; FAIL=$((FAIL + 1))
fi

# ---- Test 4: security mock — missing credentials exits non-zero ----
echo "Test 4: security mock — missing credentials (invalid store) exits non-zero"
MOCK_EXIT=0
"$MOCK_BIN/security" invalid-operation > /dev/null 2>&1 || MOCK_EXIT=$?
if [[ "$MOCK_EXIT" -ne 0 ]]; then
    echo "PASS: security mock exits non-zero for unsupported operations"; PASS=$((PASS + 1))
else
    echo "FAIL: security mock should exit non-zero for unsupported operations"; FAIL=$((FAIL + 1))
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
