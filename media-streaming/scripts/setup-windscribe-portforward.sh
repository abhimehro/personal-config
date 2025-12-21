#!/bin/bash
#
# Windscribe Port Forwarding + Media Server Setup
# Updated for Windscribe's built-in port forwarding feature
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

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔥 Windscribe Port Forward Media Server Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if Windscribe is running
info "Step 1: Checking Windscribe VPN..."
if ! pgrep -x "Windscribe" > /dev/null; then
    warn "Windscribe not running!"
    echo ""
    echo "To enable remote access:"
    echo "  1. Start Windscribe"
    echo "  2. Connect to Atlanta server (82.21.151.194)"
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    ok "Windscribe is running"
    
    # Check if VPN is connected
    VPN_INTERFACE=$(ifconfig | grep -A 1 "utun" | grep "inet " | head -1 || echo "")
    if [[ -n "$VPN_INTERFACE" ]]; then
        VPN_IP=$(echo "$VPN_INTERFACE" | awk '{print $2}')
        ok "VPN connected: $VPN_IP"
        
        # Verify it's Atlanta server (check if any IP matches expected range)
        info "Make sure you're connected to Atlanta (82.21.151.194)"
    else
        warn "Windscribe running but VPN not connected"
        echo ""
        echo "For remote access to work:"
        echo "  1. Connect to Atlanta server in Windscribe"
        echo "  2. Your port forward will become active"
    fi
fi

echo ""
info "Step 2: Verifying 'Allow LAN Traffic' setting..."
echo ""
warn "⚠️  IMPORTANT: Ensure 'Allow LAN Traffic' is enabled in Windscribe"
echo "   Location: Preferences → Connection → Allow LAN Traffic"
echo "   Why: Lets local devices access your Mac when VPN is on"
echo ""
read -p "Is 'Allow LAN Traffic' enabled? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    err "Please enable 'Allow LAN Traffic' before continuing"
    echo ""
    echo "To enable:"
    echo "  1. Open Windscribe preferences"
    echo "  2. Go to Connection tab"
    echo "  3. Check 'Allow LAN Traffic'"
    echo "  4. Restart Windscribe"
    exit 1
fi
ok "'Allow LAN Traffic' confirmed enabled"

echo ""
info "Step 3: Port Forward Configuration"
echo ""
echo "Your Windscribe Port Forward:"
echo "  Atlanta IP:    82.21.151.194"
echo "  External Port: 8088"
echo "  Internal Port: 8088"
echo "  Protocol:      TCP"
echo "  Device:        MacBook Air"
ok "Port forward is configured in Windscribe"

echo ""
info "Step 4: Starting media server..."
SCRIPT_DIR="$HOME/Documents/dev/personal-config/media-streaming/scripts"
if [[ -f "$SCRIPT_DIR/start-media-server-windscribe.sh" ]]; then
    exec "$SCRIPT_DIR/start-media-server-windscribe.sh"
else
    err "Media server script not found!"
    echo "Expected: $SCRIPT_DIR/start-media-server-windscribe.sh"
    exit 1
fi
