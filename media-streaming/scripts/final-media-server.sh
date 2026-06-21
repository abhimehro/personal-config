#!/bin/bash
#
# Media Server - Local & Remote WebDAV (Windscribe Static IP Ready)
# Auto-starts on login, 1Password integrated
#
# Usage:
#   ./final-media-server.sh              # Start with auto-detected mode
#   ./final-media-server.sh --local      # Force LAN-only mode
#   ./final-media-server.sh --external   # Force external/VPN mode
#
set -euo pipefail

echo "🔧 Media Server - Rclone WebDAV (1Password Integrated)"
echo "=========================================================="
echo

# Determine mode
MODE="${1:-auto}"

# Accessible Spinner
spinner_wait() {
	local duration=$1
	local msg="${2:-Working}"

	if [[ -t 1 && -z ${CI-} ]]; then
		local i=1
		local sp="/-\|"
		local iterations=$((duration * 10))
		local c=0

		if [ -t 1 ] && [ -z "${CI-}" ]; then tput civis 2>/dev/null || true; fi

		local old_int_trap old_term_trap
		old_int_trap=$(trap -p INT)
		trap '[ -t 1 ] && [ -z "${CI-}" ] && tput cnorm 2>/dev/null || true; printf "\r\033[K"; eval "${old_int_trap:-trap - INT}"; kill -INT "$$"' INT
		old_term_trap=$(trap -p TERM)
		trap '[ -t 1 ] && [ -z "${CI-}" ] && tput cnorm 2>/dev/null || true; printf "\r\033[K"; eval "${old_term_trap:-trap - TERM}"; kill -TERM "$$"' TERM

		while [[ $c -lt $iterations ]]; do
			printf "\r   %s [%c]" "$msg" "${sp:i++%${#sp}:1}"
			sleep 0.1
			c=$((c + 1))
		done
		printf "\r\033[K"

		if [ -t 1 ] && [ -z "${CI-}" ]; then tput cnorm 2>/dev/null || true; fi
		# SECURITY: false positive, trap -p output is safely escaped
		eval "${old_int_trap:-trap - INT}"
		eval "${old_term_trap:-trap - TERM}"
	else
		echo "   $msg (waiting ${duration}s)..."
		sleep "$duration"
	fi
}

# Kill any existing servers
echo "🧹 Cleaning up existing servers..."
pkill -f "rclone serve" 2>/dev/null || true
spinner_wait 2 "🧹 Waiting for cleanup..."

# Network discovery
echo "🔍 Network Discovery:"
DEFAULT_INTERFACE=$(route get default 2>/dev/null | grep interface | awk '{print $2}' || echo "en0")
echo "   Default Interface: $DEFAULT_INTERFACE"

PRIMARY_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
echo "   🎯 Local IP: $PRIMARY_IP"

# Check if connected via VPN (Windscribe)
PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "unknown")
echo "   🌐 Public IP: $PUBLIC_IP"

VPN_CONNECTED=false
if [[ $PUBLIC_IP == "82.21.151.194" ]]; then
	VPN_CONNECTED=true
	echo "   ✅ Windscribe VPN: CONNECTED"
else
	echo "   ⚠️  Windscribe VPN: NOT CONNECTED (Public IP: $PUBLIC_IP)"
fi

echo

# WebDAV must use a stable internal port for Windscribe forwarding.
echo "🔌 Checking stable WebDAV port..."
MEDIA_WEBDAV_PORT="${MEDIA_WEBDAV_PORT:-8080}"
AVAILABLE_PORT="$MEDIA_WEBDAV_PORT"

if lsof -nP -iTCP:"$MEDIA_WEBDAV_PORT" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; then
	echo "   ❌ Required WebDAV port $MEDIA_WEBDAV_PORT is already in use."
	echo "   Windscribe forwarding expects a stable internal port: $MEDIA_WEBDAV_PORT/TCP."
	echo "   Free the port and restart the WebDAV server."
	lsof -nP -iTCP:"$MEDIA_WEBDAV_PORT" -sTCP:LISTEN 2>/dev/null || true
	exit 1
fi
echo "   ✅ Using stable WebDAV internal port: $AVAILABLE_PORT"

# Check rclone
echo "📡 Checking rclone configuration..."
if ! rclone listremotes | grep -q "media:"; then
	echo "❌ Error: 'media:' remote not found"
	exit 1
fi

echo

# 🔐 Authentication Setup (1Password)
echo "🔐 Configuring Authentication..."
if ! command -v op &>/dev/null; then
	echo "   ❌ 'op' CLI not found. Please install 1Password CLI."
	exit 1
fi

# Attempt to fetch credentials from 1Password
echo "   Reading credentials from 1Password (Item: 'MediaServer')..."
WEB_USER=$(op read "op://Personal/MediaServer/username" 2>/dev/null) || WEB_USER=""
WEB_PASS=$(op read "op://Personal/MediaServer/password" 2>/dev/null) || WEB_PASS=""

if [[ -z $WEB_USER || -z $WEB_PASS ]]; then
	echo "   ❌ ERROR: Could not retrieve 'MediaServer' credentials from 1Password."
	echo "   Please ensure:"
	echo "     1. You're signed into 1Password CLI (run: op signin)"
	echo "     2. Item 'MediaServer' exists in 'Personal' vault"
	echo "     3. Item has 'username' and 'password' fields"
	exit 1
else
	echo "   ✅ Credentials loaded from 1Password"
fi

echo

# Determine bind address based on mode and VPN status
BIND_ADDR="0.0.0.0"
INFO_MESSAGE=""

case "$MODE" in
--local)
	BIND_ADDR="$PRIMARY_IP"
	INFO_MESSAGE="LAN-ONLY Mode: Server bound to $PRIMARY_IP"
	;;
--external)
	if [[ $VPN_CONNECTED == false ]]; then
		echo "⚠️  WARNING: External mode requested but Windscribe VPN not detected!"
		echo "   Continuing anyway, but external access may not work."
	fi
	BIND_ADDR="0.0.0.0"
	INFO_MESSAGE="EXTERNAL Mode: Server listening on all interfaces (VPN: $VPN_CONNECTED)"
	;;
*)
	BIND_ADDR="0.0.0.0"
	INFO_MESSAGE="AUTO Mode: Server listening on all interfaces"
	;;
esac

echo "🚀 Starting Rclone WebDAV Server..."
echo "   Mode: $INFO_MESSAGE"
echo "   Bind Address: $BIND_ADDR:$AVAILABLE_PORT"

# 🛡️ Sentinel: Use env vars for credentials to hide them from process list (ps aux)
export RCLONE_USER="$WEB_USER"
export RCLONE_PASS="$WEB_PASS"

# Start Rclone WebDAV (Performance Tuned)
nohup rclone serve webdav "media:" \
	--addr "$BIND_ADDR:$AVAILABLE_PORT" \
	--vfs-cache-mode full \
	--vfs-read-chunk-size 32M \
	--vfs-read-chunk-size-limit 2G \
	--transfers 8 \
	--checkers 16 \
	--read-only \
	--no-modtime \
	>~/Library/Logs/media-server.log 2>&1 &

SERVER_PID=$!
echo "   PID: $SERVER_PID"
spinner_wait 5 "⏳ Waiting for server to initialize..."

# Validation
if ps -p $SERVER_PID >/dev/null; then
	echo "   ✅ Server is RUNNING"
else
	echo "   ❌ Server FAILED to start. Check logs:"
	tail -20 ~/Library/Logs/media-server.log
	exit 1
fi

echo
echo "════════════════════════════════════════════════════════════════"
echo "🎬 INFUSE CONFIGURATION"
echo "════════════════════════════════════════════════════════════════"
echo
echo "📱 PRIMARY (LAN/Home Network) - Best Performance"
echo "─────────────────────────────────────────────────────────────"
echo "   Protocol:  WebDAV (HTTP)"
echo "   Address:   $PRIMARY_IP"
echo "   Port:      $AVAILABLE_PORT"
echo "   Username:  $WEB_USER"
echo "   Password:  (from 1Password MediaServer)"
echo

if [[ $VPN_CONNECTED == true ]]; then
	echo "🌐 SECONDARY (External/VPN) - Remote Access"
	echo "─────────────────────────────────────────────────────────────"
	echo "   Protocol:  WebDAV (HTTP)"
	echo "   Address:   82.21.151.194"
	echo "   Port:      8088  (Windscribe external WebDAV port)"
	echo "   Username:  $WEB_USER"
	echo "   Password:  (from 1Password MediaServer)"
	echo
	echo "ℹ️  WINDSCRIBE PORT FORWARDING"
	echo "   Configure one stable TCP mapping:"
	echo "     External: 82.21.151.194:8088 -> Internal: $PRIMARY_IP:$AVAILABLE_PORT"
	echo "   If Windscribe assigns a different external port, keep the internal port at $AVAILABLE_PORT"
	echo "   and use the assigned external port in Infuse."
else
	echo "ℹ️  External/VPN Access: NOT AVAILABLE"
	echo "   Connect to Windscribe VPN with static IP to enable remote access"
fi

echo
echo "════════════════════════════════════════════════════════════════"
echo "📝 Server Information"
echo "════════════════════════════════════════════════════════════════"
echo "   PID:           $SERVER_PID"
echo "   Log File:      ~/Library/Logs/media-server.log"
echo "   Kill Command:  pkill -f 'rclone serve'"
echo
echo "This server is now running in the background."
echo "════════════════════════════════════════════════════════════════"
