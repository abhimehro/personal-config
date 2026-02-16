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

# Kill any existing servers
echo "🧹 Cleaning up existing servers..."
pkill -f "rclone serve" 2>/dev/null || true
sleep 2

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
if [[ "$PUBLIC_IP" == "82.21.151.194" ]]; then
    VPN_CONNECTED=true
    echo "   ✅ Windscribe VPN: CONNECTED"
else
    echo "   ⚠️  Windscribe VPN: NOT CONNECTED (Public IP: $PUBLIC_IP)"
fi

echo

# Find available port
echo "🔌 Finding available port..."
AVAILABLE_PORT=8080
for port in 8080 8081 8082 8083; do
    if ! lsof -nP -i:$port | grep -q LISTEN; then
        AVAILABLE_PORT=$port
        break
    fi
done
echo "   ✅ Using Port: $AVAILABLE_PORT"

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

if [[ -z "$WEB_USER" || -z "$WEB_PASS" ]]; then
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
        if [[ "$VPN_CONNECTED" == false ]]; then
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
    > ~/Library/Logs/media-server.log 2>&1 &

SERVER_PID=$!
echo "   PID: $SERVER_PID"
sleep 5

# Validation
if ps -p $SERVER_PID > /dev/null; then
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

if [[ "$VPN_CONNECTED" == true ]]; then
    echo "🌐 SECONDARY (External/VPN) - Remote Access"
    echo "─────────────────────────────────────────────────────────────"
    echo "   Protocol:  WebDAV (HTTP)"
    echo "   Address:   82.21.151.194"
    echo "   Port:      22650  (⚠️ PORT FORWARD MAY NEED CONFIGURATION)"
    echo "   Username:  $WEB_USER"
    echo "   Password:  (from 1Password MediaServer)"
    echo
    echo "⚠️  WINDSCRIBE PORT FORWARD STATUS: UNKNOWN"
    echo "   The external connection requires Windscribe Static IP"
    echo "   port forwarding to be configured:"
    echo "     External: 82.21.151.194:22650 → Internal: $PRIMARY_IP:$AVAILABLE_PORT"
    echo
    echo "   If external access fails, check Windscribe settings."
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
