#!/bin/bash

# Windscribe + Control D Connection Script
# Combined mode: start Control D on DoH/TCP, then connect Windscribe static IP,
# then re-enforce localhost DNS to avoid DNS drift.

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Handle user cancellations gracefully
trap 'echo -e "\n\033[1;33m[WARN]\033[0m Interrupted by user. Exiting gracefully..."; exit 130' SIGINT

PROFILE="${1:-browsing}"
LOCATION="${2:-Atlanta}"
PROTOCOL="${3:-wireguard:443}"
# Optional 4th arg or WINDSCRIBE_IPV6 env: auto|1|0
# auto (default) = detect IPv6 on tunnel after connect and reconcile.
IPV6_MODE="${4:-${WINDSCRIBE_IPV6:-auto}}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }

# Accessible Spinner
spinner_wait() {
	local duration=$1
	local msg="${2:-Working}"

	if [[ -t 1 && -z ${CI-} ]]; then
		(
			local i=1
			local sp="/-\|"
			local iterations
			iterations=$((duration * 10))
			local c=0

			# Hide cursor gracefully in TTY
			[ -t 1 ] && [ -z "${CI-}" ] && tput civis 2>/dev/null || true

			# Set temporary traps within subshell to avoid polluting parent
			trap '[ -t 1 ] && [ -z "${CI-}" ] && tput cnorm 2>/dev/null || true; printf "\r\033[K"; trap - INT; kill -INT $BASHPID' INT
			trap '[ -t 1 ] && [ -z "${CI-}" ] && tput cnorm 2>/dev/null || true; printf "\r\033[K"; trap - TERM; kill -TERM $BASHPID' TERM

			while [[ $c -lt $iterations ]]; do
				printf "\r${BLUE}[%c]${NC} %s..." "${sp:i++%${#sp}:1}" "$msg"
				sleep 0.1
				c=$((c + 1))
			done
			printf "\r\033[K" # Clear line

			# Restore cursor
			[ -t 1 ] && [ -z "${CI-}" ] && tput cnorm 2>/dev/null || true
		)
	else
		# Fallback for non-TTY environments (CI, screen readers)
		log "$msg (waiting ${duration}s)..."
		sleep "$duration"
	fi
}

# Pre-flight checks
if [[ ! -x "$REPO_ROOT/scripts/network-mode-manager.sh" ]]; then
	error "network-mode-manager.sh not found at $REPO_ROOT/scripts/"
	exit 1
fi

if command -v windscribe-cli >/dev/null 2>&1; then
	export WINDSCRIBE_BIN="windscribe-cli"
elif [[ -x /Applications/Windscribe.app/Contents/MacOS/windscribe-cli ]]; then
	export WINDSCRIBE_BIN="/Applications/Windscribe.app/Contents/MacOS/windscribe-cli"
elif command -v windscribe >/dev/null 2>&1; then
	export WINDSCRIBE_BIN="windscribe"
else
	error "Windscribe CLI not found. Install from Windscribe app."
	exit 1
fi

# Normalize IPv6 mode for network-mode-manager / reconcile.
case "$IPV6_MODE" in
auto | AUTO) unset WINDSCRIBE_IPV6 ;;
1 | true | TRUE | yes | YES | on | ON | enable) export WINDSCRIBE_IPV6=1 ;;
0 | false | FALSE | no | NO | off | OFF | disable) export WINDSCRIBE_IPV6=0 ;;
*)
	error "Invalid IPv6 mode '$IPV6_MODE'. Use auto, 1/enable, or 0/disable."
	exit 1
	;;
esac

if [[ $PROFILE == "disconnect" ]]; then
	# In disconnect mode the second positional argument is the profile to
	# reconcile to (not a location). Use a dedicated variable to avoid relying
	# on LOCATION, which was set from $2 for the connect path.
	DISCONNECT_PROFILE="${2:-privacy}"
	log "Disconnecting Windscribe and reconciling back to standalone Control D ($DISCONNECT_PROFILE)..."
	"$WINDSCRIBE_BIN" disconnect || true
	spinner_wait 3 "Waiting for VPN disconnect"
	cd "$REPO_ROOT"
	./scripts/network-mode-manager.sh reconcile "$DISCONNECT_PROFILE"
	exit 0
fi

echo
log "Windscribe + Control D Connection Sequence"
log "Using Windscribe CLI: $WINDSCRIBE_BIN"
log "Profile:  $PROFILE"
log "Location: $LOCATION"
log "Protocol: $PROTOCOL"
log "IPv6:     ${WINDSCRIBE_IPV6:-auto (detect after connect)}"
echo

log "Step 1: Starting Control D in Windscribe-compatible mode (DoH/TCP)..."
cd "$REPO_ROOT"
# Pre-connect: default DoH + IPv6 off (leak-safe for IPv4-only/static).
# After connect, reconcile upgrades to DoH + IPv6 on when the tunnel supports it.
./scripts/network-mode-manager.sh windscribe "$PROFILE"
spinner_wait 2 "Starting service"

log "Step 2: Connecting Windscribe..."
# Prefer static IP when LOCATION looks like a static slot; otherwise normal connect.
# Callers can pass a city/nickname; static is used when explicitly requested via
# LOCATION prefixed with "static:" or when PROTOCOL path historically used static.
if [[ $LOCATION == static:* ]]; then
	LOCATION="${LOCATION#static:}"
	"$WINDSCRIBE_BIN" connect static "$LOCATION" "$PROTOCOL"
elif [[ ${WINDSCRIBE_CONNECT_STATIC:-1} == "1" ]]; then
	# Default remains static for backward compatibility with existing callers.
	"$WINDSCRIBE_BIN" connect static "$LOCATION" "$PROTOCOL"
else
	"$WINDSCRIBE_BIN" connect "$LOCATION" "$PROTOCOL"
fi
spinner_wait 5 "Establishing connection"

log "Step 3: Reconciling IPv6 + DNS lock for connected tunnel..."
# Detect IPv6-capable WireGuard egress and flip to doh-ipv6 when appropriate;
# keep doh-ipv4 (IPv6 off) for IPv4-only / static IP servers.
./scripts/network-mode-manager.sh reconcile "$PROFILE"
# SECURITY: only pin system DNS to localhost after the listener answers.
if dig @127.0.0.1 google.com +short +time=2 +tries=1 >/dev/null 2>&1; then
	sudo networksetup -setdnsservers Wi-Fi 127.0.0.1 2>/dev/null || true
	sudo networksetup -setdnsservers "USB 10/100/1000 LAN" 127.0.0.1 2>/dev/null || true
	sudo dscacheutil -flushcache 2>/dev/null || true
	sudo killall -HUP mDNSResponder 2>/dev/null || true
else
	warn "Control D listener not ready after reconcile; leaving system DNS unchanged to avoid lockout."
fi
spinner_wait 2 "Applying DNS changes"

# Step 4: Verification
echo ""
log "Step 4: Verifying configuration..."

# Check Control D is running
if pgrep -x ctrld >/dev/null; then
	success "Control D service: RUNNING"
else
	error "Control D service: STOPPED"
	exit 1
fi

# Check VPN is connected
if ifconfig | grep -A5 "utun" | grep "inet " | grep -v "127.0.0.1" >/dev/null 2>&1; then
	success "VPN tunnel: CONNECTED"
else
	warn "VPN tunnel: NOT DETECTED (may still be connecting...)"
fi

# Check DNS configuration
CURRENT_DNS=$(networksetup -getdnsservers Wi-Fi 2>/dev/null || echo "")
if echo "$CURRENT_DNS" | grep -q "127.0.0.1"; then
	success "System DNS: 127.0.0.1 (Control D)"
else
	error "System DNS: $CURRENT_DNS (NOT Control D!)"
	if dig @127.0.0.1 google.com +short +time=2 +tries=1 >/dev/null 2>&1; then
		warn "DNS was overridden. Attempting recovery..."
		sudo networksetup -setdnsservers Wi-Fi 127.0.0.1 2>/dev/null || true
		sudo networksetup -setdnsservers "USB 10/100/1000 LAN" 127.0.0.1 2>/dev/null || true
		sudo dscacheutil -flushcache
		spinner_wait 1 "Waiting for recovery"
		CURRENT_DNS=$(networksetup -getdnsservers Wi-Fi 2>/dev/null || echo "")
		if echo "$CURRENT_DNS" | grep -q "127.0.0.1"; then
			success "Recovery successful: DNS now locked to 127.0.0.1"
		else
			error "Recovery failed: DNS still showing $CURRENT_DNS"
			exit 1
		fi
	else
		error "Control D listener is not answering; refusing to pin DNS to 127.0.0.1"
		exit 1
	fi
fi

# Test DNS resolution
if dig @127.0.0.1 google.com +short +timeout=5 >/dev/null 2>&1; then
	success "DNS resolution: WORKING"
else
	error "DNS resolution: FAILED"
	exit 1
fi

# Check filtering
BLOCKED_RESULT=$(dig @127.0.0.1 doubleclick.net +short 2>/dev/null || echo "")
if [[ -z $BLOCKED_RESULT ]]; then
	success "Ad blocking: ACTIVE (doubleclick.net blocked)"
elif [[ $BLOCKED_RESULT == "127.0.0.1" ]] || [[ $BLOCKED_RESULT == "0.0.0.0" ]]; then
	success "Ad blocking: ACTIVE (doubleclick.net → $BLOCKED_RESULT)"
else
	warn "Ad blocking: INACTIVE or bypassed (doubleclick.net → $BLOCKED_RESULT)"
fi

# Check IPv6 policy vs tunnel capability (inline; avoid re-sourcing network-core)
IPV6_LINE=$(networksetup -getinfo "Wi-Fi" 2>/dev/null | grep "IPv6:" || true)
tunnel_has_ipv6=0
case "${WINDSCRIBE_IPV6-}" in
1 | true | TRUE | yes | YES | on | ON) tunnel_has_ipv6=1 ;;
0 | false | FALSE | no | NO | off | OFF) tunnel_has_ipv6=0 ;;
*)
	if ifconfig 2>/dev/null | awk '
		/^utun/ {in_utun=1; next}
		in_utun && /^[a-z]/ {in_utun=0}
		in_utun && /inet6 / && $2 !~ /^fe80:/ && $2 != "::1" {found=1; exit}
		END {exit !found}
	'; then
		tunnel_has_ipv6=1
	fi
	;;
esac
if [[ $tunnel_has_ipv6 -eq 1 ]]; then
	if echo "$IPV6_LINE" | grep -q "Automatic"; then
		success "IPv6: ENABLED (matches IPv6-capable Windscribe tunnel / doh-ipv6)"
	else
		warn "IPv6-capable tunnel detected but Wi-Fi IPv6 is not Automatic ($IPV6_LINE). Run: ./scripts/network-mode-manager.sh reconcile $PROFILE"
	fi
else
	if echo "$IPV6_LINE" | grep -q "Off"; then
		success "IPv6: DISABLED (matches IPv4-only/static tunnel / doh-ipv4 leak prevention)"
	else
		warn "IPv4-only/static tunnel but IPv6 is not Off ($IPV6_LINE). Leak risk — run reconcile or set WINDSCRIBE_IPV6=0."
	fi
fi

echo
success "Combined Windscribe + Control D mode active"
log "Disconnect path: ./scripts/windscribe-connect.sh disconnect $PROFILE"
log "Force IPv6 on (bash/zsh):  WINDSCRIBE_IPV6=1 ./scripts/windscribe-connect.sh $PROFILE <location>"
log "Force IPv6 off (bash/zsh): WINDSCRIBE_IPV6=0 ./scripts/windscribe-connect.sh $PROFILE <location>"
log "Force IPv6 (fish):         env WINDSCRIBE_IPV6=0 ./scripts/windscribe-connect.sh $PROFILE <location>"
log "                           env WINDSCRIBE_IPV6=1 ./scripts/windscribe-connect.sh $PROFILE <location>"
