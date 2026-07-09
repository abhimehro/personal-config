#!/bin/bash
#
# Unit tests for scripts/lib/controld-service.sh
# Covers: setup_directories (happy path + symlink rejection), safe_stop,
#         show_status (service stopped), source guard
# Mocks: ctrld, pgrep, pkill, networksetup

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-lib-controld-service')
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
trap 'rm -rf "$TEST_DIR"' EXIT

# --- Mocks ---
# ctrld mock: records every invocation so we can assert it was called correctly.
CTRLD_LOG="$TEST_DIR/ctrld.log"
cat >"$MOCK_BIN/ctrld" <<MOCK
#!/bin/bash
echo "ctrld \$*" >> "$CTRLD_LOG"
exit 0
MOCK
chmod +x "$MOCK_BIN/ctrld"

# pgrep mock: ctrld is NOT running in this test environment.
cat >"$MOCK_BIN/pgrep" <<'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"

# pkill mock: always succeeds (nothing to kill).
cat >"$MOCK_BIN/pkill" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/pkill"

# networksetup mock: returns a plausible DNS value.
cat >"$MOCK_BIN/networksetup" <<'MOCK'
#!/bin/bash
echo "1.1.1.1"
MOCK
chmod +x "$MOCK_BIN/networksetup"

export PATH="$MOCK_BIN:$PATH"

# Source the library under test
# shellcheck source=scripts/lib/controld-service.sh
source "$REPO_ROOT/scripts/lib/controld-service.sh"

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

check_grep() {
	local name="$1"
	local pattern="$2"
	local file="$3"
	# -- ends options so patterns like "--cd id" are not parsed as grep flags.
	if grep -qF -- "$pattern" "$file" 2>/dev/null; then
		echo "PASS: $name"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $name (pattern '$pattern' not found in $file)"
		FAIL=$((FAIL + 1))
	fi
}

echo "=== Testing scripts/lib/controld-service.sh ==="

# --- setup_directories: happy path ---
echo ""
echo "-- setup_directories (happy path) --"

SETUP_BASE="$TEST_DIR/setup_test"
C_DIR="$SETUP_BASE/controld"
P_DIR="$SETUP_BASE/profiles"
B_DIR="$SETUP_BASE/backup"
LOG_F="$SETUP_BASE/controld.log"
mkdir -p "$SETUP_BASE"

setup_directories "$C_DIR" "$P_DIR" "$B_DIR" "$LOG_F"

check "setup_directories creates controld_dir" test -d "$C_DIR"
check "setup_directories creates profiles_dir" test -d "$P_DIR"
check "setup_directories creates backup_dir" test -d "$B_DIR"
check "setup_directories creates log file" test -f "$LOG_F"
check "log file is a regular file (not symlink)" test ! -L "$LOG_F"

# --- setup_directories: symlink rejection ---
echo ""
echo "-- setup_directories (symlink rejection) --"

SYMLINK_TARGET="$TEST_DIR/target.log"
SYMLINK_LOG="$TEST_DIR/fake.log"
touch "$SYMLINK_TARGET"
ln -s "$SYMLINK_TARGET" "$SYMLINK_LOG"

SETUP_RC=0
setup_directories "$TEST_DIR/c2" "$TEST_DIR/p2" "$TEST_DIR/b2" "$SYMLINK_LOG" \
	>/dev/null 2>&1 || SETUP_RC=$?
check "setup_directories rejects symlink log file" test "$SETUP_RC" -ne 0

# --- safe_stop ---
echo ""
echo "-- safe_stop --"

: >"$CTRLD_LOG"
SAFESTOP_RC=0
safe_stop "$TEST_DIR" >/dev/null 2>&1 || SAFESTOP_RC=$?
check "safe_stop exits 0 when service is not running" test "$SAFESTOP_RC" -eq 0
check_grep "safe_stop prefers ctrld service stop first" "ctrld service stop" "$CTRLD_LOG"
check_grep "safe_stop also invokes ctrld stop" "ctrld stop" "$CTRLD_LOG"

# --- show_status (service stopped) ---
echo ""
echo "-- show_status (stopped) --"

show_status "$TEST_DIR" >"$TEST_DIR/status.out" 2>&1 || true
check "show_status produces output" test -s "$TEST_DIR/status.out"
check_grep "show_status reports Stopped state" "Stopped" "$TEST_DIR/status.out"
# --- _is_native_api_failure ---
echo ""
echo "-- _is_native_api_failure --"

API_FAIL_LOG="$TEST_DIR/api_fail.log"
echo "WRN service not installed" >"$API_FAIL_LOG"
check_false "_is_native_api_failure ignores 'service not installed'" \
	_is_native_api_failure "$API_FAIL_LOG"

echo "failed to fetch resolver config from API" >"$API_FAIL_LOG"
check "_is_native_api_failure detects resolver fetch failure" \
	_is_native_api_failure "$API_FAIL_LOG"

echo "Maintenance is in progress" >"$API_FAIL_LOG"
check "_is_native_api_failure detects maintenance" \
	_is_native_api_failure "$API_FAIL_LOG"

echo "Starting ctrld..." >"$API_FAIL_LOG"
check_false "_is_native_api_failure ignores benign start logs" \
	_is_native_api_failure "$API_FAIL_LOG"

echo "Control D process is up but DNS listener is not ready; attempting recovery." >"$API_FAIL_LOG"
check_false "_is_native_api_failure ignores listener-not-ready noise" \
	_is_native_api_failure "$API_FAIL_LOG"
check_false "_should_static_api_fallback rejects listener-not-ready" \
	_should_static_api_fallback "$API_FAIL_LOG"

echo "dig timed out" >"$API_FAIL_LOG"
check_false "_should_static_api_fallback rejects dig timeout alone" \
	_should_static_api_fallback "$API_FAIL_LOG"

echo "failed to fetch resolver config from API" >"$API_FAIL_LOG"
check "_should_static_api_fallback accepts real resolver fetch failure" \
	_should_static_api_fallback "$API_FAIL_LOG"

echo -e "WRN service not installed\nMaintenance is in progress" >"$API_FAIL_LOG"
check "_should_static_api_fallback accepts maintenance even with install chatter" \
	_should_static_api_fallback "$API_FAIL_LOG"

# Schema incompat (Lesson 0dr): unmarshal number into exclude
echo 'error: json: cannot unmarshal number into Go struct field ResolverConfig.body.resolver.exclude of type string' >"$API_FAIL_LOG"
check "_is_ctrld_api_schema_incompat detects exclude unmarshal" \
	_is_ctrld_api_schema_incompat "$API_FAIL_LOG"
check "_should_static_api_fallback accepts schema incompat" \
	_should_static_api_fallback "$API_FAIL_LOG"
check "_is_native_api_failure accepts schema incompat" \
	_is_native_api_failure "$API_FAIL_LOG"

# Daemon-log path: start log clean, but recent daemon log has fatal
echo "NTC Service started" >"$API_FAIL_LOG"
DAEMON_LOG="$TEST_DIR/ctrld_daemon.log"
printf '%s\n' \
	'fetching Controld D configuration from API: 6m971e9jaf' \
	'error: json: cannot unmarshal number into Go struct field ResolverConfig.body.resolver.exclude of type string' \
	'fatal: failed to fetch resolver config' >"$DAEMON_LOG"
check "_is_ctrld_api_schema_incompat reads daemon log" \
	_is_ctrld_api_schema_incompat "$API_FAIL_LOG" "$DAEMON_LOG"
check "_should_static_api_fallback reads daemon log" \
	_should_static_api_fallback "$API_FAIL_LOG" "$DAEMON_LOG"

# --- _write_profile_local_config (profile-aware, never free DNS) ---
echo ""
echo "-- profile-aware local config --"
FB_DIR="$TEST_DIR/etc_fb"
FB_CFG="$FB_DIR/ctrld.toml"
mkdir -p "$FB_DIR/profiles"
# Source profile lib for generate_fallback_config
# shellcheck source=scripts/lib/controld-profile.sh
source "$REPO_ROOT/scripts/lib/controld-profile.sh"
check "_write_profile_local_config writes doh3 profile endpoint" \
	_write_profile_local_config "privacy" "6m971e9jaf" "$FB_CFG" "doh3"
check_grep "local config has profile endpoint" "https://dns.controld.com/6m971e9jaf" "$FB_CFG"
check_grep "local config uses doh3" "type = 'doh3'" "$FB_CFG"
check_grep "local config has bootstrap_ip" "bootstrap_ip" "$FB_CFG"
if grep -qE 'dns\.controld\.com/free' "$FB_CFG"; then
	echo "FAIL: local config must not use free DNS"
	FAIL=$((FAIL + 1))
else
	echo "PASS: local config omits free DNS"
	PASS=$((PASS + 1))
fi
check_false "_write_profile_local_config refuses free id" \
	_write_profile_local_config "privacy" "free" "$FB_CFG" "doh"

# --- bash 3.2: progress line must not use Unicode ellipsis after $listener_ip ---
echo ""
echo "-- bash 3.2 ellipsis / set -u (Lesson 0dr) --"
if command -v rg >/dev/null 2>&1; then
	if rg -n '\$listener_ip…' "$REPO_ROOT/scripts/lib/controld-service.sh" >/dev/null 2>&1; then
		echo 'FAIL: $listener_ip followed by Unicode ellipsis still present'
		FAIL=$((FAIL + 1))
	else
		echo 'PASS: no $listener_ip… Unicode ellipsis in controld-service.sh'
		PASS=$((PASS + 1))
	fi
else
	if grep -n $'\$listener_ip…' "$REPO_ROOT/scripts/lib/controld-service.sh" >/dev/null 2>&1; then
		echo 'FAIL: $listener_ip followed by Unicode ellipsis still present'
		FAIL=$((FAIL + 1))
	else
		echo 'PASS: no $listener_ip… Unicode ellipsis in controld-service.sh'
		PASS=$((PASS + 1))
	fi
fi
# Runtime: progress path under set -u must not abort on listener_ip
# Force progress logs (PROGRESS_S=1) so the old `$listener_ip…` line would fire.
export CONTROLD_DNS_READY_GRACE_S=0
export CONTROLD_DNS_READY_RETRIES=40
export CONTROLD_DNS_READY_SLEEP=0.05
export CONTROLD_DNS_READY_BUDGET_S=2
export CONTROLD_DNS_READY_PROGRESS_S=1
export CONTROLD_DNS_NO_TOML_FAIL_S=120
export CONTROLD_DNS_DEAD_STREAK=100
export CONTROLD_CONFIG_ABS="$TEST_DIR/missing-for-ellipsis.toml"
cat >"$MOCK_BIN/dig" <<'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$MOCK_BIN/dig"
cat >"$MOCK_BIN/pgrep" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/pgrep"
# Fake now() so progress interval elapses without real wall clock.
_controld_now_s() {
	echo "${_FAKE_NOW:-0}"
}
_FAKE_NOW=0
WAIT_RC=0
WAIT_ERR="$TEST_DIR/wait_ellipsis.err"
(
	# Advance fake clock inside the wait by wrapping sleep.
	sleep() {
		_FAKE_NOW=$((_FAKE_NOW + 1))
		:
	}
	export -f sleep 2>/dev/null || true
	_wait_for_dns_ready "127.0.0.1"
) >"$WAIT_ERR" 2>&1 || WAIT_RC=$?
# Subshell may not share function overrides on bash 3.2 — also run direct with real sleep.
if ! grep -qi 'Still waiting for dig' "$WAIT_ERR" 2>/dev/null; then
	WAIT_RC=0
	_FAKE_NOW=0
	# Direct call: budget 2s with progress every 1s will hit the progress echo.
	export CONTROLD_DNS_READY_BUDGET_S=3
	export CONTROLD_DNS_READY_SLEEP=0.3
	_wait_for_dns_ready "127.0.0.1" >"$WAIT_ERR" 2>&1 || WAIT_RC=$?
fi
if grep -qi 'listener_ip: unbound variable' "$WAIT_ERR"; then
	echo "FAIL: _wait_for_dns_ready hit unbound listener_ip under set -u"
	FAIL=$((FAIL + 1))
	cat "$WAIT_ERR" || true
else
	echo "PASS: _wait_for_dns_ready no unbound listener_ip under set -u"
	PASS=$((PASS + 1))
fi
check "_wait_for_dns_ready still returns failure when dig fails" test "$WAIT_RC" -eq 1
# Restore real _controld_now_s if we overrode it (re-source is heavy; redefine from epoch).
_controld_now_s() {
	date +%s
}
rm -f "$MOCK_BIN/dig"
unset CONTROLD_DNS_READY_GRACE_S CONTROLD_DNS_READY_RETRIES CONTROLD_DNS_READY_SLEEP
unset CONTROLD_DNS_DEAD_STREAK CONTROLD_DNS_READY_BUDGET_S CONTROLD_DNS_READY_PROGRESS_S
unset CONTROLD_DNS_NO_TOML_FAIL_S CONTROLD_CONFIG_ABS _FAKE_NOW

# --- _foreign_port53_holder / _reset_system_dns_to_dhcp ---
echo ""
echo "-- port53 conflict helpers --"

# Mock lsof: limactl holds TCP :53 (Colima DNS forward regression).
cat >"$MOCK_BIN/lsof" <<'MOCK'
#!/bin/bash
cat <<'EOF'
COMMAND  PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
limactl 3431 user    8u  IPv6 0x1      0t0  TCP *:53 (LISTEN)
EOF
MOCK
chmod +x "$MOCK_BIN/lsof"
holder=$(_foreign_port53_holder)
if [[ $holder == limactl* ]]; then
	echo "PASS: _foreign_port53_holder detects limactl"
	PASS=$((PASS + 1))
else
	echo "FAIL: _foreign_port53_holder detects limactl (got '$holder')"
	FAIL=$((FAIL + 1))
fi

# Mock lsof: only ctrld — no foreign holder.
cat >"$MOCK_BIN/lsof" <<'MOCK'
#!/bin/bash
cat <<'EOF'
COMMAND PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
ctrld   99  root   5u  IPv4 0x1      0t0  UDP 127.0.0.1:53
EOF
MOCK
chmod +x "$MOCK_BIN/lsof"
holder=$(_foreign_port53_holder)
if [[ -z $holder ]]; then
	echo "PASS: _foreign_port53_holder empty when only ctrld"
	PASS=$((PASS + 1))
else
	echo "FAIL: _foreign_port53_holder empty when only ctrld (got '$holder')"
	FAIL=$((FAIL + 1))
fi

# Fail-safe DHCP reset must call networksetup Empty (not leave 127.0.0.1).
DNS_RESET_LOG="$TEST_DIR/dns_reset.log"
: >"$DNS_RESET_LOG"
cat >"$MOCK_BIN/networksetup" <<MOCK
#!/bin/bash
echo "networksetup \$*" >> "$DNS_RESET_LOG"
echo "There aren't any DNS Servers set on Wi-Fi."
MOCK
chmod +x "$MOCK_BIN/networksetup"
_reset_system_dns_to_dhcp
check_grep "_reset_system_dns_to_dhcp sets Wi-Fi Empty" "setdnsservers Wi-Fi Empty" "$DNS_RESET_LOG"
check_grep "_reset_system_dns_to_dhcp sets LAN Empty" "setdnsservers USB 10/100/1000 LAN Empty" "$DNS_RESET_LOG"

# Restore benign networksetup mock for later tests.
cat >"$MOCK_BIN/networksetup" <<'MOCK'
#!/bin/bash
echo "1.1.1.1"
MOCK
chmod +x "$MOCK_BIN/networksetup"
rm -f "$MOCK_BIN/lsof"

# --- _wait_for_dns_ready: dead-streak (do not abort on one pgrep miss) ---
echo ""
echo "-- readiness dead-streak --"
# dig always fails; pgrep fails once then succeeds — must NOT abort early.
DIG_CALLS=0
cat >"$MOCK_BIN/dig" <<MOCK
#!/bin/bash
echo "dig \$*" >> "$TEST_DIR/dig.log"
exit 1
MOCK
chmod +x "$MOCK_BIN/dig"
PGREP_N=0
cat >"$MOCK_BIN/pgrep" <<MOCK
#!/bin/bash
# First call: miss (KeepAlive gap). Subsequent: alive.
COUNT_FILE="$TEST_DIR/pgrep.count"
n=\$(cat "\$COUNT_FILE" 2>/dev/null || echo 0)
n=\$((n + 1))
echo "\$n" >"\$COUNT_FILE"
if [[ \$n -eq 1 ]]; then
	exit 1
fi
exit 0
MOCK
chmod +x "$MOCK_BIN/pgrep"
# launchctl: no ctrld row (force reliance on pgrep streak)
cat >"$MOCK_BIN/launchctl" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/launchctl"
: >"$TEST_DIR/pgrep.count"
export CONTROLD_DNS_READY_GRACE_S=0
export CONTROLD_DNS_READY_RETRIES=5
export CONTROLD_DNS_READY_SLEEP=0.01
export CONTROLD_DNS_READY_BUDGET_S=60
export CONTROLD_DNS_READY_PROGRESS_S=0
export CONTROLD_DNS_NO_TOML_FAIL_S=120
export CONTROLD_DNS_DEAD_STREAK=20
export CONTROLD_DNS_PORT_CONFLICT_RETRIES=100
WAIT_RC=0
_wait_for_dns_ready "127.0.0.1" || WAIT_RC=$?
# Should time out (dig never succeeds) NOT abort on first pgrep miss.
# With dead_streak=20 and only 5 retries, process "alive" after first miss → timeout=1.
check "_wait_for_dns_ready survives single pgrep miss (times out, not instant death)" test "$WAIT_RC" -eq 1
pgrep_count=$(cat "$TEST_DIR/pgrep.count")
if [[ $pgrep_count -gt 1 ]]; then
	echo "PASS: _wait_for_dns_ready continued after first pgrep miss (calls=$pgrep_count)"
	PASS=$((PASS + 1))
else
	echo "FAIL: _wait_for_dns_ready aborted after first pgrep miss (calls=$pgrep_count)"
	FAIL=$((FAIL + 1))
fi
# Instant death: pgrep always fails for dead_streak limit within retries.
cat >"$MOCK_BIN/pgrep" <<'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"
export CONTROLD_DNS_READY_RETRIES=50
export CONTROLD_DNS_DEAD_STREAK=3
export CONTROLD_DNS_NO_TOML_FAIL_S=120
WAIT_RC=0
_wait_for_dns_ready "127.0.0.1" || WAIT_RC=$?
check "_wait_for_dns_ready fails after sustained dead streak" test "$WAIT_RC" -eq 1

# No-toml / never-alive fail-fast (Lesson 0dp): do not burn full budget silently.
export CONTROLD_DNS_READY_RETRIES=50
export CONTROLD_DNS_DEAD_STREAK=100
export CONTROLD_DNS_NO_TOML_FAIL_S=1
export CONTROLD_DNS_READY_BUDGET_S=30
export CONTROLD_CONFIG_ABS="$TEST_DIR/missing-ctrld.toml"
WAIT_RC=0
WAIT_ERR="$TEST_DIR/wait_no_toml.err"
_wait_for_dns_ready "127.0.0.1" >"$WAIT_ERR" 2>&1 || WAIT_RC=$?
check "_wait_for_dns_ready fails fast when toml+process never appear" test "$WAIT_RC" -eq 1
if grep -qiE 'no .*toml|never stayed up|MISSING|Post-start' "$WAIT_ERR"; then
	echo "PASS: no-toml fail-fast emitted diagnostic"
	PASS=$((PASS + 1))
else
	echo "FAIL: expected no-toml diagnostic in wait stderr"
	FAIL=$((FAIL + 1))
	cat "$WAIT_ERR" || true
fi

# Restore default pgrep (not running)
cat >"$MOCK_BIN/pgrep" <<'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"
rm -f "$MOCK_BIN/dig" "$MOCK_BIN/launchctl"
unset CONTROLD_DNS_READY_GRACE_S CONTROLD_DNS_READY_RETRIES CONTROLD_DNS_READY_SLEEP
unset CONTROLD_DNS_DEAD_STREAK CONTROLD_DNS_PORT_CONFLICT_RETRIES
unset CONTROLD_DNS_READY_BUDGET_S CONTROLD_DNS_READY_PROGRESS_S CONTROLD_DNS_NO_TOML_FAIL_S
unset CONTROLD_CONFIG_ABS

# --- _force_reinstall_ctrld_native: --cd + absolute --config, NO --listen ---
echo ""
echo "-- native CD Mode start (absolute config, no --listen, no uninstall thrash) --"
: >"$CTRLD_LOG"
# pgrep: not running → must NOT uninstall
cat >"$MOCK_BIN/pgrep" <<'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"
NATIVE_ERR="$TEST_DIR/native_start.err"
: >"$NATIVE_ERR"
ABS_CFG="$TEST_DIR/etc_controld/ctrld.toml"
mkdir -p "$(dirname "$ABS_CFG")"
_force_reinstall_ctrld_native "testid123" "doh3" "$NATIVE_ERR" "" "$ABS_CFG" || true
check_grep "native start uses --cd profile id" "--cd testid123" "$CTRLD_LOG"
check_grep "native start uses --proto doh3" "--proto doh3" "$CTRLD_LOG"
check_grep "native start uses absolute --config" "--config=$ABS_CFG" "$CTRLD_LOG"
check_grep "native start logs real argv" "ctrld argv:" "$NATIVE_ERR"
# Lesson 0do: --listen with --cd triggers no-config-mode fatal
if grep -E -- '--listen' "$CTRLD_LOG" >/dev/null 2>&1; then
	echo "FAIL: native start must NOT pass --listen (breaks CD Mode)"
	FAIL=$((FAIL + 1))
else
	echo "PASS: native start omits --listen"
	PASS=$((PASS + 1))
fi
if grep -q "service uninstall" "$CTRLD_LOG"; then
	echo "FAIL: native start must not uninstall when process already stopped"
	FAIL=$((FAIL + 1))
else
	echo "PASS: native start skips uninstall when process stopped"
	PASS=$((PASS + 1))
fi
# Must prefer service start (not only bare start)
check_grep "native start prefers service start" "service start" "$CTRLD_LOG"

# When process still alive after stop → uninstall once
: >"$CTRLD_LOG"
: >"$TEST_DIR/pgrep.alive.count"
cat >"$MOCK_BIN/pgrep" <<MOCK
#!/bin/bash
# First few calls: alive (triggers uninstall). Then dead (stop wait ends).
COUNT_FILE="$TEST_DIR/pgrep.alive.count"
n=\$(cat "\$COUNT_FILE" 2>/dev/null || echo 0)
n=\$((n + 1))
echo "\$n" >"\$COUNT_FILE"
if [[ \$n -le 3 ]]; then
	exit 0
fi
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"
_force_reinstall_ctrld_native "testid123" "doh" "$NATIVE_ERR" "" "$ABS_CFG" || true
check_grep "native start uninstalls once when process alive" "service uninstall" "$CTRLD_LOG"
check_grep "alive-path still uses --cd" "--cd testid123" "$CTRLD_LOG"
check_grep "alive-path still uses absolute --config" "--config=$ABS_CFG" "$CTRLD_LOG"
check_grep "alive-path uses --proto doh" "--proto doh" "$CTRLD_LOG"
if grep -E -- '--listen' "$CTRLD_LOG" >/dev/null 2>&1; then
	echo "FAIL: alive-path must NOT pass --listen"
	FAIL=$((FAIL + 1))
else
	echo "PASS: alive-path omits --listen"
	PASS=$((PASS + 1))
fi

# Restore pgrep not-running
cat >"$MOCK_BIN/pgrep" <<'MOCK'
#!/bin/bash
exit 1
MOCK
chmod +x "$MOCK_BIN/pgrep"

# --- resolve_network_profile_mode (network-core) ---
echo ""
echo "-- network profile mode helpers --"
# shellcheck source=scripts/lib/network-core.sh
source "$REPO_ROOT/scripts/lib/network-core.sh"

mode_out=$(resolve_network_profile_mode doh disable)
if [[ $mode_out == "doh-ipv4" ]]; then
	echo "PASS: resolve_network_profile_mode doh/disable"
	PASS=$((PASS + 1))
else
	echo "FAIL: resolve_network_profile_mode doh/disable (got '$mode_out')"
	FAIL=$((FAIL + 1))
fi
mode_out=$(resolve_network_profile_mode doh enable)
if [[ $mode_out == "doh-ipv6" ]]; then
	echo "PASS: resolve_network_profile_mode doh/enable"
	PASS=$((PASS + 1))
else
	echo "FAIL: resolve_network_profile_mode doh/enable (got '$mode_out')"
	FAIL=$((FAIL + 1))
fi
mode_out=$(resolve_network_profile_mode doh3 enable)
if [[ $mode_out == "doh3-ipv6" ]]; then
	echo "PASS: resolve_network_profile_mode doh3/enable"
	PASS=$((PASS + 1))
else
	echo "FAIL: resolve_network_profile_mode doh3/enable (got '$mode_out')"
	FAIL=$((FAIL + 1))
fi

# --- Source guard ---
echo ""
echo "-- source guard --"
# shellcheck source=scripts/lib/controld-service.sh
source "$REPO_ROOT/scripts/lib/controld-service.sh"
check "source guard variable is set to 'true'" test "$_CONTROLD_SERVICE_SH_" = "true"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
	exit 1
fi
