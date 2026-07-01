#!/bin/bash
#
# Pure-function unit tests for network-mode-manager.sh
#
# These tests exercise check_reconcile_needed() and get_active_profile_name()
# without touching the network, real DNS, or the Control D daemon. They run
# entirely in a temporary directory and stub out any filesystem/env reads.

set -euo pipefail

TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

# Minimal stubs for functions the script sources or calls.
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
export PATH="$MOCK_BIN:$PATH"

cat >"$MOCK_BIN/sudo" <<'EOF'
#!/bin/bash
exec "$@"
EOF
chmod +x "$MOCK_BIN/sudo"

cat >"$MOCK_BIN/networksetup" <<'EOF'
#!/bin/bash
echo "MOCK_NETWORKSETUP: $*"
EOF
chmod +x "$MOCK_BIN/networksetup"

# Source the script under test in a way that loads only the pure functions.
# We source it with a dummy load_network_env and ensure_prereqs so it does not
# try to call real tools.
load_network_env() { :; }
ensure_not_root() { :; }
check_cmd() { :; }

# The script expects E_* variables for emoji output; provide safe defaults.
E_PRIVACY="🛡️"
E_BROWSING="🌐"
E_GAMING="🎮"
E_VPN="🔐"
E_INFO="ℹ️"

# Override the IPv6 manager path so it never runs.
IPV6_MANAGER="$MOCK_BIN/ipv6-manager.sh"
cat >"$IPV6_MANAGER" <<'EOF'
#!/bin/bash
echo "mock ipv6-manager: $*"
EOF
chmod +x "$IPV6_MANAGER"

# Source the script. This is safe because the functions we care about are pure
# and the entry-point guard prevents main() from running.
# shellcheck source=scripts/network-mode-manager.sh
source "./scripts/network-mode-manager.sh" >/dev/null 2>&1 || true

# Helper: assert a function returns 1 (false).
assert_false() {
	local name="$1"
	shift
	if "$@"; then
		echo "FAIL: $name expected false (non-zero), got true"
		return 1
	else
		echo "PASS: $name"
	fi
}

# Helper: assert a function returns 0 (true).
assert_true() {
	local name="$1"
	shift
	if "$@"; then
		echo "PASS: $name"
	else
		echo "FAIL: $name expected true (zero), got false"
		return 1
	fi
}

# Helper: assert string equality.
assert_eq() {
	local name="$1" expected="$2" actual="$3"
	if [[ $expected == "$actual" ]]; then
		echo "PASS: $name"
	else
		echo "FAIL: $name expected '$expected', got '$actual'"
		return 1
	fi
}

EXIT_CODE=0

# ---------------------------------------------------------------------------
# check_reconcile_needed tests
# ---------------------------------------------------------------------------

# VPN disconnected, ctrld running, IPv6 disabled => reconcile needed
assert_true "check_reconcile_needed: disconnected + ctrld + IPv6 disabled" \
	check_reconcile_needed "false" "true" "false" || EXIT_CODE=1

# VPN disconnected, ctrld running, IPv6 enabled => no reconcile
assert_false "check_reconcile_needed: disconnected + ctrld + IPv6 enabled" \
	check_reconcile_needed "false" "true" "true" || EXIT_CODE=1

# VPN connected, ctrld running, IPv6 disabled => no reconcile
assert_false "check_reconcile_needed: connected + ctrld + IPv6 disabled" \
	check_reconcile_needed "true" "true" "false" || EXIT_CODE=1

# ctrld stopped, DNS localhost => reconcile needed.
# We stub system_dns_has_localhost by mocking networksetup to return 127.0.0.1.
cat >"$MOCK_BIN/networksetup" <<'EOF'
#!/bin/bash
if [[ "$1" == "-getdnsservers" ]]; then
	echo "127.0.0.1"
fi
EOF
chmod +x "$MOCK_BIN/networksetup"
assert_true "check_reconcile_needed: ctrld stopped + DNS localhost" \
	check_reconcile_needed "false" "false" "true" || EXIT_CODE=1

# ctrld stopped, DNS not localhost => no reconcile.
cat >"$MOCK_BIN/networksetup" <<'EOF'
#!/bin/bash
if [[ "$1" == "-getdnsservers" ]]; then
	echo "There aren't any DNS Servers set on $2."
fi
EOF
chmod +x "$MOCK_BIN/networksetup"
assert_false "check_reconcile_needed: ctrld stopped + DNS DHCP" \
	check_reconcile_needed "false" "false" "true" || EXIT_CODE=1

# ---------------------------------------------------------------------------
# get_active_profile_name tests
# ---------------------------------------------------------------------------

# Stub /etc/controld with a temporary directory.
CONTROLD_DIR="$TEST_DIR/controld"
mkdir -p "$CONTROLD_DIR/profiles"

# Case 1: active_profile file exists and names a profile.
cat >"$CONTROLD_DIR/active_profile" <<'EOF'
PROFILE_NAME=privacy
PROFILE_ID=6m971e9jaf
PROTOCOL=doh3
LISTENER_IP=127.0.0.1
EOF
assert_eq "get_active_profile_name: from active_profile" \
	"Privacy" "$(get_active_profile_name)" || EXIT_CODE=1

# Case 2: active_profile missing, symlink points to ctrld.browsing.toml.
rm -f "$CONTROLD_DIR/active_profile"
ln -sf "$CONTROLD_DIR/profiles/ctrld.browsing.toml" "$CONTROLD_DIR/ctrld.toml"
assert_eq "get_active_profile_name: from symlink" \
	"Browsing" "$(get_active_profile_name)" || EXIT_CODE=1

# Case 3: active_profile missing, symlink points to fallback config.
ln -sf "$CONTROLD_DIR/profiles/ctrld.gaming.fallback.toml" "$CONTROLD_DIR/ctrld.toml"
assert_eq "get_active_profile_name: from fallback symlink" \
	"Gaming" "$(get_active_profile_name)" || EXIT_CODE=1

# Case 4: nothing useful present => Unknown.
rm -f "$CONTROLD_DIR/active_profile" "$CONTROLD_DIR/ctrld.toml"
assert_eq "get_active_profile_name: unknown state" \
	"Unknown" "$(get_active_profile_name)" || EXIT_CODE=1

# Case 5: active_profile file exists but is empty; symlink should win.
cat >"$CONTROLD_DIR/active_profile" <<'EOF'
EOF
ln -sf "$CONTROLD_DIR/profiles/ctrld.privacy.toml" "$CONTROLD_DIR/ctrld.toml"
assert_eq "get_active_profile_name: empty active_profile falls back to symlink" \
	"Privacy" "$(get_active_profile_name)" || EXIT_CODE=1

exit $EXIT_CODE
