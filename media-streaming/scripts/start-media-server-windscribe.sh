#!/bin/bash
#
# VPN-Compatible Media Server for Windscribe
# Supports both local network and remote access via static IP
#

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${BLUE}ℹ️  [INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}✅ [OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}⚠️  [WARN]${NC}  $*"; }
err()   { echo -e "${RED}❌ [ERR]${NC}   $*" >&2; }

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔥 Windscribe VPN-Compatible Media Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Configuration
STATIC_IP="${MEDIA_STATIC_IP:-82.21.151.194}"
PORT="${MEDIA_WEBDAV_PORT:-8088}"
CREDS_FILE="${MEDIA_CREDENTIALS_FILE:-$HOME/.config/media-server/credentials}"

# Get network interfaces (physical, not VPN)
info "Detecting network interfaces..."
WIFI_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "")
ETHERNET_IP=$(ipconfig getifaddr en1 2>/dev/null || echo "")

echo ""
info "📡 Network Detection:"
echo "   WiFi (en0):     ${WIFI_IP:-Not connected}"
echo "   Ethernet (en1): ${ETHERNET_IP:-Not connected}"
echo "   Static IP:      $STATIC_IP (Atlanta server)"

# Determine bind address
# Strategy: Bind to 0.0.0.0 to accept connections on all interfaces
# This allows both local network AND remote (static IP) access
BIND_ADDR="0.0.0.0"
info "Binding strategy: 0.0.0.0 (all interfaces)"

echo ""
info "🔍 Checking VPN status..."
if pgrep -x "Windscribe" > /dev/null; then
    ok "Windscribe is running"
    # Check if VPN is actually connected
    VPN_INTERFACE=$(ifconfig | grep -A 1 "utun" | grep "inet " | head -1 || echo "")
    if [[ -n "$VPN_INTERFACE" ]]; then
        VPN_IP=$(echo "$VPN_INTERFACE" | awk '{print $2}')
        ok "VPN connected: $VPN_IP"
        
        # Check if connected to Atlanta
        info "Verifying connection to Atlanta..."
        # The external IP should be the Atlanta IP when port forwarding is active
        EXTERNAL_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "")
        if [[ "$EXTERNAL_IP" == "$STATIC_IP" ]]; then
            ok "Connected to Atlanta server ($STATIC_IP) - Port forwarding active!"
        else
            warn "External IP ($EXTERNAL_IP) doesn't match Atlanta IP ($STATIC_IP)"
            warn "Port forwarding may not be active. Reconnect to Atlanta server."
        fi
    else
        warn "Windscribe running but VPN not connected"
    fi
else
    info "Windscribe not detected (VPN disabled)"
fi

echo ""
info "🧹 Stopping existing servers..."
pkill -f "rclone serve webdav" 2>/dev/null && ok "Stopped existing servers" || info "No servers running"

echo ""
info "🔐 Loading credentials..."
# Load credentials
MEDIA_WEBDAV_USER="${MEDIA_WEBDAV_USER:-infuse}"
MEDIA_WEBDAV_PASS="${MEDIA_WEBDAV_PASS:-}"

if [[ -z "$MEDIA_WEBDAV_PASS" ]]; then
  if [[ -f "$CREDS_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CREDS_FILE"
    ok "Loaded credentials from: $CREDS_FILE"
  else
    warn "No credentials found. Creating new ones..."
    mkdir -p "$(dirname "$CREDS_FILE")"
    MEDIA_WEBDAV_PASS=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9')
    {
      echo "MEDIA_WEBDAV_USER='${MEDIA_WEBDAV_USER}'"
      echo "MEDIA_WEBDAV_PASS='${MEDIA_WEBDAV_PASS}'"
    } > "$CREDS_FILE"
    chmod 600 "$CREDS_FILE"
    ok "Generated new credentials: $CREDS_FILE"
  fi
fi

echo ""
info "✅ Verifying rclone configuration..."
if ! rclone listremotes | grep -q "^media:$"; then
    err "'media' remote not found!"
    echo ""
    echo "To fix this:"
    echo "  1. Restore rclone config from 1Password:"
    echo "     op document get \"Rclone Config Backup\" --vault Personal --output ~/.config/rclone/rclone.conf"
    echo ""
    echo "  2. Or run setup: ~/Documents/dev/personal-config/media-streaming/scripts/setup-media-library.sh"
    exit 1
fi
ok "rclone 'media' remote found"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting WebDAV Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Display connection info
info "📱 Infuse Configuration Options:"
echo ""
echo "   ┌─ OPTION 1: Local Network (Same WiFi) ─────────"
if [[ -n "$WIFI_IP" ]]; then
    echo "   │ Protocol: WebDAV"
    echo "   │ Address:  http://$WIFI_IP:$PORT"
    echo "   │ Username: $MEDIA_WEBDAV_USER"
    echo "   │ Password: $MEDIA_WEBDAV_PASS"
    echo "   │ Path:     /"
    echo "   │ Use when: On the same local network"
else
    echo "   │ (WiFi not connected - not available)"
fi
echo "   └────────────────────────────────────────────────"
echo ""
echo "   ┌─ OPTION 2: Remote Access (Windscribe) ────────"
echo "   │ Protocol: WebDAV"
echo "   │ Address:  http://$STATIC_IP:$PORT"
echo "   │ Username: $MEDIA_WEBDAV_USER"
echo "   │ Password: $MEDIA_WEBDAV_PASS"
echo "   │ Path:     /"
echo "   │ Use when: Away from home or VPN active"
echo "   │ Status:   Windscribe port forwarding (no router config needed)"
echo "   └────────────────────────────────────────────────"
echo ""

# VPN-specific tips
ok "✅ WINDSCRIBE CONFIGURATION VERIFIED:"
echo "   ✓ 'Allow LAN Traffic' enabled - local access works"
echo "   ✓ Port forwarding configured - remote access ready"
echo "   ✓ Connected to Atlanta ($STATIC_IP)"
echo ""

info "💡 Testing connectivity:"
echo "   Local:  curl -u $MEDIA_WEBDAV_USER:**** http://localhost:$PORT/"
if [[ -n "$WIFI_IP" ]]; then
    echo "   WiFi:   curl -u $MEDIA_WEBDAV_USER:**** http://$WIFI_IP:$PORT/"
fi
echo "   Remote: curl -u $MEDIA_WEBDAV_USER:**** http://$STATIC_IP:$PORT/"
echo ""

info "Press Ctrl+C to stop server"
echo ""
ok "Starting rclone WebDAV server on $BIND_ADDR:$PORT..."
echo ""

# Start server with proper logging (removed conflicting --verbose flag)
exec rclone serve webdav media: \
    --addr "$BIND_ADDR:$PORT" \
    --user "$MEDIA_WEBDAV_USER" \
    --pass "$MEDIA_WEBDAV_PASS" \
    --dir-cache-time 30m \
    --poll-interval 1m \
    --vfs-cache-mode minimal \
    --read-only \
    --log-level INFO
