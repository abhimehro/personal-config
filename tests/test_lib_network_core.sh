#!/bin/bash
#
# Unit tests for scripts/lib/network-core.sh
# Covers: color/emoji exports, log helpers, smart_grep, smart_find,
#         ensure_not_root, check_cmd, source guard
# Mocks: ifconfig, dscacheutil, killall, networksetup, sudo

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-lib-network-core')
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
trap 'rm -rf "$TEST_DIR"' EXIT

# --- Mocks (prevent real system calls) ---
cat >"$MOCK_BIN/ifconfig" <<'EOF'
#!/bin/bash
echo "utun0: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1380"
echo "	inet 10.0.0.1 --> 10.0.0.1 netmask 0xffffffff"
EOF
chmod +x "$MOCK_BIN/ifconfig"

cat >"$MOCK_BIN/dscacheutil" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$MOCK_BIN/dscacheutil"

cat >"$MOCK_BIN/killall" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$MOCK_BIN/killall"

cat >"$MOCK_BIN/networksetup" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$MOCK_BIN/networksetup"

# sudo mock: delegate to the real command (safe – mocked cmds have no side-effects)
cat >"$MOCK_BIN/sudo" <<'EOF'
#!/bin/bash
exec "$@"
EOF
chmod +x "$MOCK_BIN/sudo"

export PATH="$MOCK_BIN:$PATH"

# Source the library under test
# shellcheck source=scripts/lib/network-core.sh
source "$REPO_ROOT/scripts/lib/network-core.sh"

PASS=0
FAIL=0

check() {
	local name="$1"
	shift
	if "$@" >/dev/null 2>&1; then
		echo "PASS: $name"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $name"
		FAIL=$((FAIL + 1))
	fi
}

check_false() {
	local name="$1"
	shift
	if ! "$@" >/dev/null 2>&1; then
		echo "PASS: $name"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $name"
		FAIL=$((FAIL + 1))
	fi
}

check_output() {
	local name="$1"
	local expected="$2"
	local actual="$3"
	if [[ $actual == "$expected" ]]; then
		echo "PASS: $name"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $name (expected='$expected', got='$actual')"
		FAIL=$((FAIL + 1))
	fi
}

echo "=== Testing scripts/lib/network-core.sh ==="

# --- Color and emoji exports ---
echo ""
echo "-- Color and emoji exports --"
check "RED is exported and non-empty" test -n "${RED-}"
check "GREEN is exported and non-empty" test -n "${GREEN-}"
check "YELLOW is exported and non-empty" test -n "${YELLOW-}"
check "BLUE is exported and non-empty" test -n "${BLUE-}"
check "NC is exported and non-empty" test -n "${NC-}"
check "BOLD is exported and non-empty" test -n "${BOLD-}"
check "E_PASS is exported and non-empty" test -n "${E_PASS-}"
check "E_FAIL is exported and non-empty" test -n "${E_FAIL-}"
check "E_INFO is exported and non-empty" test -n "${E_INFO-}"
check "E_VPN is exported and non-empty" test -n "${E_VPN-}"
check "E_PRIVACY is exported and non-empty" test -n "${E_PRIVACY-}"
check "E_GAMING is exported and non-empty" test -n "${E_GAMING-}"
check "E_BROWSING is exported and non-empty" test -n "${E_BROWSING-}"

# --- Logging helpers ---
echo ""
echo "-- Logging helpers --"
LOG_OUT=$(log "test log message" 2>/dev/null)
check "log() produces output" test -n "$LOG_OUT"

SUCCESS_OUT=$(success "test ok message" 2>/dev/null)
check "success() produces output" test -n "$SUCCESS_OUT"

WARN_OUT=$(warn "test warning" 2>/dev/null)
check "warn() produces output" test -n "$WARN_OUT"

# error() calls exit 1 — test in a subshell to prevent aborting the test run
ERROR_EXIT=0
(error "test error" >/dev/null 2>&1) || ERROR_EXIT=$?
check "error() exits non-zero" test "$ERROR_EXIT" -ne 0

# --- smart_grep ---
echo ""
echo "-- smart_grep --"
# /etc/passwd is present on both Linux and macOS; "root" always appears in it.
GREP_RESULT=$(smart_grep "root" /etc/passwd 2>/dev/null || true)
check "smart_grep finds 'root' in /etc/passwd" test -n "$GREP_RESULT"

# With a mock rg in PATH, smart_grep should delegate to it.
cat >"$MOCK_BIN/rg" <<'EOF'
#!/bin/bash
echo "mock_rg_result"
EOF
chmod +x "$MOCK_BIN/rg"
RG_RESULT=$(smart_grep "anything" /dev/null 2>/dev/null || true)
check "smart_grep uses rg when rg is available" test -n "$RG_RESULT"

# --- smart_find ---
echo ""
echo "-- smart_find --"
check_false "smart_find without args returns non-zero" smart_find

# Locate a file known to exist in the lib directory.
SF_RESULT=$(smart_find "network-core.sh" "$REPO_ROOT/scripts/lib" 2>/dev/null || true)
check "smart_find locates network-core.sh in lib dir" test -n "$SF_RESULT"

# Searching for a non-existent file should return empty output.
SF_EMPTY=$(smart_find "no_such_file_xyz_abc.sh" "$REPO_ROOT/scripts/lib" 2>/dev/null || true)
check "smart_find returns empty for nonexistent file" test -z "$SF_EMPTY"

# --- ensure_not_root ---
echo ""
echo "-- ensure_not_root --"
if [[ $EUID -ne 0 ]]; then
	check "ensure_not_root succeeds for non-root user" ensure_not_root
else
	echo "SKIP: ensure_not_root (running as root)"
fi

# --- check_cmd ---
echo ""
echo "-- check_cmd --"
check "check_cmd succeeds for 'bash'" check_cmd bash

# check_cmd for a missing command calls error() which exits; test in a subshell.
CHECK_EXIT=0
(check_cmd "no_such_cmd_xyz_test_abc" >/dev/null 2>&1) || CHECK_EXIT=$?
check "check_cmd exits non-zero for missing command" test "$CHECK_EXIT" -ne 0

# --- Source guard ---
echo ""
echo "-- source guard --"
# shellcheck source=scripts/lib/network-core.sh
source "$REPO_ROOT/scripts/lib/network-core.sh"
check_output "source guard variable is set to 'true'" "true" "$_NETWORK_CORE_SH_"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
	exit 1
fi
