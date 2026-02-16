#!/bin/bash

# Windscribe + Control D Connection Script
# Ensures DNS stays locked to Control D (127.0.0.1) after VPN connection
#
# Usage: ./scripts/windscribe-connect.sh [profile]
# Profile: privacy | browsing | gaming (default: browsing)

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PROFILE="${1:-browsing}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }

# Pre-flight checks
if [[ ! -x "$REPO_ROOT/scripts/network-mode-manager.sh" ]]; then
  error "network-mode-manager.sh not found at $REPO_ROOT/scripts/"
  exit 1
fi

if ! command -v windscribe >/dev/null 2>&1; then
  error "Windscribe CLI not found. Install from Windscribe app."
  exit 1
fi

echo ""
log "Windscribe + Control D Connection Sequence"
log "Profile: $PROFILE"
echo ""

# Step 1: Configure Control D with DoH (TCP) protocol for VPN compatibility
log "Step 1: Starting Control D in Windscribe-compatible mode (DoH/TCP)..."
cd "$REPO_ROOT"
sudo ./scripts/network-mode-manager.sh windscribe "$PROFILE"

# Wait for Control D to stabilize
sleep 2

# Step 2: Connect Windscribe
log "Step 2: Connecting Windscribe VPN..."
windscribe connect

# Wait for VPN to establish
sleep 3

# Step 3: Force DNS back to localhost (Windscribe may have overridden it)
log "Step 3: Re-enforcing DNS lock to Control D (127.0.0.1)..."
sudo networksetup -setdnsservers Wi-Fi 127.0.0.1

# Flush DNS cache to clear any stale ISP entries
sudo dscacheutil -flushcache 2>/dev/null || true
sudo killall -HUP mDNSResponder 2>/dev/null || true

sleep 1

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
  sudo networksetup -setdnsservers Wi-Fi 127.0.0.1
  sudo dscacheutil -flushcache
  sleep 1
  CURRENT_DNS=$(networksetup -getdnsservers Wi-Fi 2</dev/null || echo "")
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
if [[ -z "$BLOCKED_RESULT" ]]; then
  success "Ad blocking: ACTIVE (doubleclick.net blocked)"
elif [[ "$BLOCKED_RESULT" == "127.0.0.1" ]] || [[ "$BLOCKED_RESULT" == "0.0.0.0" ]]; then
  success "Ad blocking: ACTIVE (doubleclick.net → $BLOCKED_RESULT)"
else
  warn "Ad blocking: INACTIVE or bypassed (doubleclick.net → $BLOCKED_RESULT)"
fi

echo ""
success "✅ Windscribe + Control D connection complete!"
echo ""
log "Current configuration:"
log "  Profile: $PROFILE (DoH/TCP)"
log "  DNS: 127.0.0.1 (Control D)"
log "  IPv6: DISABLED"
log "  VPN: Windscribe"
echo ""
log "To disconnect safely:"
log "  1. windscribe disconnect"
log "  2. ./scripts/network-mode-manager.sh controld $PROFILE"
echo ""
