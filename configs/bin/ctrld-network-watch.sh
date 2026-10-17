#!/bin/bash
# Watches for network interface state changes and validates ctrld health
# on every transition. Falls back to DHCP DNS if ctrld is unresponsive.
# Dynamically detects available network interfaces.
#
# REQUIREMENT: Passwordless sudo must be configured for the following commands:
#   - networksetup -setdnsservers *
#   - dscacheutil -flushcache
#   - killall -HUP mDNSResponder
#   - ctrld service restart
#
# To configure, add to /etc/sudoers (use visudo):
#   username ALL=(ALL) NOPASSWD: /usr/sbin/networksetup,/usr/bin/dscacheutil,/usr/bin/killall,/usr/local/bin/ctrld
#
# NOTE: `scutil --watch` is NOT a valid flag (macOS prints usage and exits).
# Use `scutil -w` on Global/IPv4 keys. KeepAlive on the LaunchAgent previously
# crash-looped this script ~1300 times because of the bad flag.

LOG="$HOME/Public/Scripts/controld_monitor.log"
mkdir -p "$(dirname "$LOG")"
FALLBACK_STATE="$HOME/Library/Application Support/ctrld-network-watch/dhcp-fallback"
fallback_active=0
[[ -f $FALLBACK_STATE ]] && fallback_active=1

# Function to get all active network services dynamically
# Uses the same pattern as scripts/lib/network-utils.sh
get_network_services() {
	networksetup -listallnetworkservices | grep -vE '^(An asterisk|\*)'
}

# Function to set DNS servers for all active interfaces
set_dns_all_interfaces() {
	local dns_value="$1"
	local services
	local failed=0
	services=$(get_network_services)

	if [[ -z $services ]]; then
		echo "$(date): No network services found" >>"$LOG"
		return 1
	fi

	while IFS= read -r iface; do
		[[ -z $iface ]] && continue
		if ! sudo networksetup -setdnsservers "$iface" "$dns_value" 2>/dev/null; then
			echo "$(date): failed to set DNS for $iface to $dns_value" >>"$LOG"
			failed=1
		fi
	done <<<"$services"
	return "$failed"
}

restore_dns_after_fallback() {
	[[ $fallback_active -eq 1 ]] || return 0
	echo "$(date): ctrld recovered — re-enforcing 127.0.0.1 DNS" >>"$LOG"
	if set_dns_all_interfaces "127.0.0.1" && rm -f "$FALLBACK_STATE"; then
		fallback_active=0
	else
		echo "$(date): failed to restore localhost DNS; will retry on next check" >>"$LOG"
	fi
}

# One health check + optional recovery. Debounced so rapid scutil events
# during profile switches do not thrash `ctrld service restart`.
check_and_recover() {
	sleep 3 # allow interface / ctrld start to stabilize

	# Foreign :53 (Colima limactl) — do not restart thrash; leave DHCP.
	if command -v lsof >/dev/null 2>&1; then
		if lsof -nP -iUDP:53 -iTCP:53 2>/dev/null | awk 'NR>1 && $1 !~ /ctrld/ {found=1} END{exit !found}'; then
			echo "$(date): foreign :53 holder present — skipping ctrld restart (free port first)" >>"$LOG"
			return 0
		fi
	fi

	if dig +time=3 +tries=1 @127.0.0.1 verify.controld.com &>/dev/null; then
		restore_dns_after_fallback
		return 0
	fi

	if (umask 077; mkdir -p "$(dirname "$FALLBACK_STATE")" && : >"$FALLBACK_STATE") 2>/dev/null; then
		fallback_active=1
		if set_dns_all_interfaces "Empty"; then
			echo "$(date): ctrld unresponsive after network event — falling back to DHCP" >>"$LOG"
		else
			echo "$(date): DHCP fallback incomplete; will restore DNS after recovery" >>"$LOG"
		fi
	else
		echo "$(date): could not save DHCP fallback state; leaving DNS unchanged" >>"$LOG"
	fi
	sudo dscacheutil -flushcache 2>/dev/null || true
	sudo killall -HUP mDNSResponder 2>/dev/null || true
	# Attempt service recovery (do not background-race overlapping restarts)
	sudo ctrld service restart >/dev/null 2>&1 || true
	sleep 5
	if dig +time=3 +tries=1 @127.0.0.1 verify.controld.com &>/dev/null; then
		restore_dns_after_fallback
	else
		if [[ $fallback_active -eq 1 ]]; then
			echo "$(date): ctrld failed to recover — DNS fallback remains active" >>"$LOG"
		else
			echo "$(date): ctrld failed to recover — DNS unchanged" >>"$LOG"
		fi
	fi
}

# Block until Global IPv4 changes, then re-check. Loop forever for KeepAlive.
while true; do
	# -w waits for the key to change (or appear). Timeout keeps us from wedging
	# forever if the key never updates; we still re-check periodically.
	scutil -w State:/Network/Global/IPv4 -t 300 >/dev/null 2>&1 || true
	check_and_recover
done
