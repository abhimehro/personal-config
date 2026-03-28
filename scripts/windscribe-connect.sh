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
		local i=1
		local sp="/-\|"
		local iterations
		iterations=$((duration * 10))
		local c=0

		# Hide cursor
		tput civis 2>/dev/null || true

		# Trap to restore cursor if interrupted
		local previous_trap
		previous_trap=$(trap -p INT TERM 2>/dev/null || true)
		trap 'tput cnorm 2>/dev/null || true; builtin exit 1' INT TERM

		while [[ $c -lt $iterations ]]; do
			printf "\r${BLUE}[%c]${NC} %s..." "${sp:i++%${#sp}:1}" "$msg"
			sleep 0.1
			c=$((c + 1))
		done
		printf "\r\033[K" # Clear line

		# Restore cursor
		tput cnorm 2>/dev/null || true

		# Restore trap
		if [[ -n $previous_trap ]]; then
			eval "$previous_trap"
		else
			trap - INT TERM
		fi
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
elif command -v windscribe >/dev/null 2>&1; then
	export WINDSCRIBE_BIN="windscribe"
else
	error "Windscribe CLI not found. Install from Windscribe app."
	exit 1
fi

echo
log "Windscribe + Control D Connection Sequence"
log "Using Windscribe CLI: $WINDSCRIBE_BIN"
log "Profile:  $PROFILE"
log "Location: $LOCATION"
log "Protocol: $PROTOCOL"
echo

log "Step 1: Starting Control D in Windscribe-compatible mode (DoH/TCP)..."
cd "$REPO_ROOT"
./scripts/network-mode-manager.sh windscribe "$PROFILE"
spinner_wait 2 "Starting service"

log "Step 2: Connecting Windscribe static location..."
"$WINDSCRIBE_BIN" connect static "$LOCATION" "$PROTOCOL"
spinner_wait 5 "Establishing connection"

log "Step 3: Re-enforcing DNS lock to Control D (127.0.0.1)..."
sudo networksetup -setdnsservers Wi-Fi 127.0.0.1 2>/dev/null || true
sudo networksetup -setdnsservers "USB 10/100/1000 LAN" 127.0.0.1 2>/dev/null || true
sudo dscacheutil -flushcache 2>/dev/null || true
sudo killall -HUP mDNSResponder 2>/dev/null || true
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
	success "System DNS: 127.0.0.1 (Control D) ✅"
else
	error "System DNS: $CURRENT_DNS (NOT Control D!) ❌"
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

echo
success "Combined Windscribe + Control D mode active"
log "Disconnect path: $WINDSCRIBE_BIN disconnect && ./scripts/network-mode-manager.sh controld $PROFILE"
