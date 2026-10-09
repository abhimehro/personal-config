#!/bin/bash
# Exercise DNS fallback and later recovery without touching macOS networking.
set -euo pipefail

TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT
export HOME="$TEST_DIR/home"
mkdir -p "$HOME"
DNS_CALLS="$TEST_DIR/dns-calls"
: >"$DNS_CALLS"
SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/configs/bin/ctrld-network-watch.sh"

# Source the worker functions without entering its endless scutil loop.
load_worker() {
	# shellcheck disable=SC1090
	source <(sed '/^# Block until Global IPv4 changes/,$d' "$SCRIPT")
}

sleep() { :; }
lsof() { return 1; }
networksetup() {
	if [[ $1 == -listallnetworkservices ]]; then
		printf 'An asterisk denotes a disabled service.\nWi-Fi\nEthernet\n*Disabled\n'
	fi
}
sudo() {
	if [[ $1 == networksetup ]]; then
		printf '%s\n' "${*:2}" >>"$DNS_CALLS"
		if [[ ${FAIL_FALLBACK_ONCE:-0} -eq 1 && $3 == Ethernet && $4 == Empty ]]; then
			FAIL_FALLBACK_ONCE=0
			return 1
		fi
		if [[ ${FAIL_RESTORE_ONCE:-0} -eq 1 && $3 == Ethernet && $4 == 127.0.0.1 ]]; then
			FAIL_RESTORE_ONCE=0
			return 1
		fi
	fi
}
dig() {
	DIG_CALLS=$((DIG_CALLS + 1))
	((DIG_CALLS > DIG_FAIL_COUNT))
}

assert_calls() {
	local expected="$1" call="$2" actual
	actual=$(grep -Fxc -- "$call" "$DNS_CALLS" || true)
	[[ $actual == "$expected" ]] || {
		echo "Expected $expected calls to '$call', got $actual" >&2
		exit 1
	}
}

load_worker
DIG_CALLS=0
DIG_FAIL_COUNT=0
check_and_recover
[[ ! -e $FALLBACK_STATE ]]
[[ ! -s $DNS_CALLS ]]

# The immediate restart fails, then a later periodic check sees a healthy listener.
DIG_CALLS=0
DIG_FAIL_COUNT=2
check_and_recover
[[ -f $FALLBACK_STATE ]]
assert_calls 1 '-setdnsservers Wi-Fi Empty'
assert_calls 0 '-setdnsservers Wi-Fi 127.0.0.1'
check_and_recover
[[ ! -e $FALLBACK_STATE ]]
assert_calls 1 '-setdnsservers Wi-Fi 127.0.0.1'
check_and_recover
assert_calls 1 '-setdnsservers Wi-Fi 127.0.0.1'

# A worker restart must remember that it left DNS on DHCP.
DIG_CALLS=0
DIG_FAIL_COUNT=2
check_and_recover
[[ -f $FALLBACK_STATE ]]
load_worker
check_and_recover
[[ ! -e $FALLBACK_STATE ]]
assert_calls 2 '-setdnsservers Wi-Fi 127.0.0.1'

# A partial restore keeps the marker and retries on the next healthy check.
DIG_CALLS=0
DIG_FAIL_COUNT=2
check_and_recover
FAIL_RESTORE_ONCE=1
check_and_recover
[[ -f $FALLBACK_STATE ]]
check_and_recover
[[ ! -e $FALLBACK_STATE ]]
assert_calls 4 '-setdnsservers Ethernet 127.0.0.1'

# Recovery on the immediate retry still restores localhost DNS.
DIG_CALLS=0
DIG_FAIL_COUNT=1
check_and_recover
[[ ! -e $FALLBACK_STATE ]]
assert_calls 5 '-setdnsservers Wi-Fi 127.0.0.1'

# A partial DHCP switch remains tracked until the healthy listener is restored.
DIG_CALLS=0
DIG_FAIL_COUNT=2
FAIL_FALLBACK_ONCE=1
check_and_recover
[[ -f $FALLBACK_STATE ]]
grep -Fq 'failed to set DNS for Ethernet to Empty' "$LOG"
grep -Fq 'DHCP fallback incomplete' "$LOG"
check_and_recover
[[ ! -e $FALLBACK_STATE ]]
assert_calls 6 '-setdnsservers Wi-Fi 127.0.0.1'

# Failure to persist state must not switch DNS to DHCP.
mkdir -p "$FALLBACK_STATE"
DIG_CALLS=0
DIG_FAIL_COUNT=2
check_and_recover
assert_calls 5 '-setdnsservers Wi-Fi Empty'
[[ -d $FALLBACK_STATE ]]
rmdir "$FALLBACK_STATE"
check_and_recover
assert_calls 6 '-setdnsservers Wi-Fi 127.0.0.1'

if grep -Fq -- 'Disabled' "$DNS_CALLS"; then
	echo 'Disabled network service was changed' >&2
	exit 1
fi

echo 'PASS: ctrld network watch restores DNS after immediate and delayed recovery'
