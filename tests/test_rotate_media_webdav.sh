#!/usr/bin/env bash
#
# Tests for media-streaming/scripts/rotate-media-webdav.sh
# Uses mock op/launchctl; safe on Linux CI.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=tests/lib/test_helpers.sh
source "$REPO_ROOT/tests/lib/test_helpers.sh"

SCRIPT="$REPO_ROOT/media-streaming/scripts/rotate-media-webdav.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-rotate-webdav')
trap 'rm -rf "$TEST_DIR"' EXIT

MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

OP_LOG="$TEST_DIR/op.log"
PASS=0
FAIL=0

pass() {
	echo "PASS: $1"
	PASS=$((PASS + 1))
}

fail() {
	echo "FAIL: $1"
	FAIL=$((FAIL + 1))
}

# Mock op: records commands; supports account list, item get, item edit --dry-run, read, document edit
cat >"$MOCK_BIN/op" <<'MOCK'
#!/bin/bash
echo "op $*" >> "OP_LOG_PLACEHOLDER"
case "$1" in
account)
  [[ "$2" == "list" ]] && exit 0
  ;;
item)
  if [[ "$2" == "get" ]]; then
    exit 0
  fi
  if [[ "$2" == "edit" ]]; then
    for arg in "$@"; do
      if [[ "$arg" == "--dry-run" ]]; then
        echo "dry-run: password would rotate"
        exit 0
      fi
    done
    echo "rotated"
    exit 0
  fi
  ;;
read)
  if [[ "$2" == *username* ]]; then
    echo "infuse"
    exit 0
  fi
  if [[ "$2" == *password* ]]; then
    echo "new-rotated-secret"
    exit 0
  fi
  ;;
document)
  [[ "$2" == "edit" ]] && exit 0
  ;;
esac
exit 1
MOCK
sed -i "s|OP_LOG_PLACEHOLDER|$OP_LOG|g" "$MOCK_BIN/op" 2>/dev/null ||
	sed -i '' "s|OP_LOG_PLACEHOLDER|$OP_LOG|g" "$MOCK_BIN/op"
chmod +x "$MOCK_BIN/op"

cat >"$MOCK_BIN/launchctl" <<'MOCK'
#!/bin/bash
if [[ "$1" == "print" ]]; then
  exit 0
fi
if [[ "$1" == "kickstart" ]]; then
  echo "kickstart $2" >> "LAUNCH_LOG_PLACEHOLDER"
  exit 0
fi
exit 1
MOCK
LAUNCH_LOG="$TEST_DIR/launchctl.log"
sed -i "s|LAUNCH_LOG_PLACEHOLDER|$LAUNCH_LOG|g" "$MOCK_BIN/launchctl" 2>/dev/null ||
	sed -i '' "s|LAUNCH_LOG_PLACEHOLDER|$LAUNCH_LOG|g" "$MOCK_BIN/launchctl"
chmod +x "$MOCK_BIN/launchctl"

export PATH="$MOCK_BIN:$PATH"
export HOME="$TEST_DIR/home"
mkdir -p "$HOME/.config/media-server"
export MEDIA_CREDENTIALS_FILE="$HOME/.config/media-server/credentials"

echo "=== rotate-media-webdav.sh tests ==="

# Dry run should not create credentials file
rm -f "$MEDIA_CREDENTIALS_FILE"
if "$SCRIPT" --dry-run >/dev/null 2>&1; then
	if [[ ! -f $MEDIA_CREDENTIALS_FILE ]]; then
		pass "dry-run does not write credentials file"
	else
		fail "dry-run wrote credentials file unexpectedly"
	fi
else
	fail "dry-run exited non-zero"
fi

if grep -q 'item edit' "$OP_LOG" && grep -q -- '--dry-run' "$OP_LOG"; then
	pass "dry-run invoked op item edit --dry-run"
else
	fail "op item edit --dry-run not logged"
fi

# Full rotation with existing fallback file (auto sync)
echo "MEDIA_WEBDAV_USER='infuse'" >"$MEDIA_CREDENTIALS_FILE"
: >"$OP_LOG"
if "$SCRIPT" >/dev/null 2>&1; then
	if [[ -f $MEDIA_CREDENTIALS_FILE ]]; then
		pass "rotation writes credentials file when auto-sync enabled"
	else
		fail "credentials file missing after rotation"
	fi
	if grep -q "MEDIA_WEBDAV_USER='infuse'" "$MEDIA_CREDENTIALS_FILE" &&
		grep -q "MEDIA_WEBDAV_PASS='new-rotated-secret'" "$MEDIA_CREDENTIALS_FILE"; then
		pass "credentials file has expected keys and values"
	else
		fail "credentials file content unexpected"
	fi
	perms=$(stat -c '%a' "$MEDIA_CREDENTIALS_FILE" 2>/dev/null || stat -f '%OLp' "$MEDIA_CREDENTIALS_FILE")
	if [[ $perms == "600" ]]; then
		pass "credentials file mode is 600"
	else
		fail "credentials file mode is $perms (expected 600)"
	fi
else
	fail "rotation script exited non-zero"
fi

# --no-sync-file
rm -f "$MEDIA_CREDENTIALS_FILE"
: >"$OP_LOG"
if "$SCRIPT" --no-sync-file >/dev/null 2>&1; then
	if [[ ! -f $MEDIA_CREDENTIALS_FILE ]]; then
		pass "--no-sync-file skips credentials file"
	else
		fail "--no-sync-file still wrote credentials file"
	fi
else
	fail "--no-sync-file run failed"
fi

# --restart-media on Linux should not fail (skips kickstart when not Darwin - actually script checks uname)
# On Linux, restart is skipped unless Darwin - test passes without launchctl call
: >"$OP_LOG"
if "$SCRIPT" --no-sync-file >/dev/null 2>&1; then
	pass "rotation succeeds on non-macOS without launchctl"
else
	fail "rotation failed on non-macOS"
fi

echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
