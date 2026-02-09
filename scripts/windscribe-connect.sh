#!/bin/bash

# Windscribe + Control D Connection Script
# Ensures DNS stays locked to Control D (127.0.0.1) after VPN connection
#
# Usage: ./scripts/windscribe-connect.sh [profile]
# Profile: privacy | browsing | gaming (default: browsing)

set -euo pipefail

# Cache sudo credentials upfront
sudo -v

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

PROFILE="${1:-browsing}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# UX Helpers (Palette 🎨 Enhanced)
info()  { echo -e "${BLUE}ℹ️  [INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}✅ [OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}⚠️  [WARN]${NC}  $*"; }
err()   { echo -e "${RED}❌ [ERR]${NC}   $*" >&2; }
header() { echo -e "\n${BOLD}${BLUE}$*${NC}\n"; }

# Pre-flight checks
if [[ ! -x "$REPO_ROOT/scripts/network-mode-manager.sh" ]]; then
  err "network-mode-manager.sh not found at $REPO_ROOT/scripts/"
  exit 1
fi

if ! command -v windscribe >/dev/null 2>&1; then
  err "Windscribe CLI not found. Install from Windscribe app."
  exit 1
fi

header "🌪️  Windscribe + Control D Connection Sequence"
info "Profile: ${BOLD}$PROFILE${NC}"

# Step 1: Configure Control D
info "Setting up Control D (DoH/TCP)..."
cd "$REPO_ROOT"
sudo ./scripts/network-mode-manager.sh windscribe "$PROFILE"
sleep 2

# Step 2: Connect Windscribe
info "Connecting Windscribe VPN..."
windscribe connect
sleep 3

# Step 3: Force DNS back to localhost
info "Locking DNS to 127.0.0.1..."
sudo networksetup -setdnsservers Wi-Fi 127.0.0.1
sudo dscacheutil -flushcache 2>/dev/null || true
sudo killall -HUP mDNSResponder 2>/dev/null || true
sleep 1

# Step 4: Verification
header "🔍 Verifying configuration"

# Check Control D
if pgrep -x ctrld >/dev/null; then
  ok "Control D service is RUNNING"
else
  err "Control D service is STOPPED"
  exit 1
fi

# Check VPN
if ifconfig | grep -A5 "utun" | grep "inet " | grep -v "127.0.0.1" >/dev/null 2>&1; then
  ok "VPN tunnel is CONNECTED"
else
  warn "VPN tunnel NOT DETECTED (may still be connecting...)"
fi

# Check DNS configuration
CURRENT_DNS=$(networksetup -getdnsservers Wi-Fi 2>/dev/null || echo "")
if echo "$CURRENT_DNS" | grep -q "127.0.0.1"; then
  ok "System DNS is 127.0.0.1 (Control D)"
else
  err "System DNS: $CURRENT_DNS (NOT Control D!)"
  warn "DNS was overridden. Attempting recovery..."

  info "Recovering DNS configuration..."
  sudo networksetup -setdnsservers Wi-Fi 127.0.0.1
  sudo dscacheutil -flushcache

  sleep 1
  CURRENT_DNS=$(networksetup -getdnsservers Wi-Fi 2>/dev/null || echo "")
  if echo "$CURRENT_DNS" | grep -q "127.0.0.1"; then
    ok "Recovery successful: DNS now locked to 127.0.0.1"
  else
    err "Recovery failed: DNS still showing $CURRENT_DNS"
    exit 1
  fi
fi

# Test DNS resolution
if dig @127.0.0.1 google.com +short +timeout=5 >/dev/null 2>&1; then
  ok "DNS resolution is WORKING"
else
  err "DNS resolution FAILED"
  exit 1
fi

# Check filtering
BLOCKED_RESULT=$(dig @127.0.0.1 doubleclick.net +short 2>/dev/null || echo "")
if [[ -z "$BLOCKED_RESULT" ]]; then
  ok "Ad blocking is ACTIVE (doubleclick.net blocked)"
elif [[ "$BLOCKED_RESULT" == "127.0.0.1" ]] || [[ "$BLOCKED_RESULT" == "0.0.0.0" ]]; then
  ok "Ad blocking is ACTIVE (doubleclick.net → $BLOCKED_RESULT)"
else
  warn "Ad blocking INACTIVE or bypassed (doubleclick.net → $BLOCKED_RESULT)"
fi

header "✨ Connection Complete!"

echo -e "   ${BLUE}Profile:${NC} $PROFILE (DoH/TCP)"
echo -e "   ${BLUE}DNS:${NC}     127.0.0.1 (Control D)"
echo -e "   ${BLUE}IPv6:${NC}    DISABLED"
echo -e "   ${BLUE}VPN:${NC}     Windscribe"
echo ""
info "To disconnect safely:"
echo -e "   1. ${YELLOW}windscribe disconnect${NC}"
echo -e "   2. ${YELLOW}./scripts/network-mode-manager.sh controld $PROFILE${NC}"
echo ""
