#!/bin/bash
#
# Verify Control D + Windscribe VPN Integration
# LEGACY: superseded by scripts/network-mode-verify.sh and
# scripts/network-mode-regression.sh; kept for deep-dive debugging.
# Tests DNS filtering, VPN protection, and proper configuration

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Control D + Windscribe Integration Verification ===${NC}"
echo

# 1. Check Control D service
echo -e "${YELLOW}[1/6]${NC} Checking Control D service..."
if pgrep -f ctrld >/dev/null; then
    echo -e "  ${GREEN}✓${NC} Control D is running"
else
    echo -e "  ${RED}✗${NC} Control D is not running"
    exit 1
fi

# 2. Check Control D listener
echo -e "${YELLOW}[2/6]${NC} Checking Control D listener..."
LISTENER=$(sudo lsof -nP -iTCP:53 2>/dev/null | grep ctrld | awk '{print $9}')
if echo "$LISTENER" | grep -q "\*:53"; then
    echo -e "  ${GREEN}✓${NC} Control D listening on all interfaces (*:53)"
elif echo "$LISTENER" | grep -q "127.0.0.1:53"; then
    echo -e "  ${RED}✗${NC} Control D listening on localhost only (127.0.0.1:53)"
    echo -e "  ${YELLOW}→${NC} Run fix-controld-config.sh to fix this"
    exit 1
else
    echo -e "  ${RED}✗${NC} Control D listener configuration unknown"
    exit 1
fi

# 3. Check system DNS configuration
echo -e "${YELLOW}[3/6]${NC} Checking system DNS configuration..."
DNS_CONFIG=$(scutil --dns | head -10)
if echo "$DNS_CONFIG" | grep -q "127.0.0.1"; then
    echo -e "  ${GREEN}✓${NC} System using Control D (127.0.0.1)"
elif echo "$DNS_CONFIG" | grep -q "100.64.0"; then
    echo -e "  ${YELLOW}⚠${NC} System using Windscribe DNS - Local DNS may not be configured"
    echo -e "  ${YELLOW}→${NC} Set Windscribe DNS to 'Local DNS' in app settings"
else
    echo -e "  ${RED}✗${NC} System DNS not configured for Control D"
    scutil --dns | head -6
fi

# 4. Test ad blocking
echo -e "${YELLOW}[4/6]${NC} Testing ad blocking..."
AD_RESULT=$(dig doubleclick.net +short +timeout=3 2>/dev/null)
if [ -z "$AD_RESULT" ] || echo "$AD_RESULT" | grep -q "^0\.0\.0\.0$\|^127\."; then
    echo -e "  ${GREEN}✓${NC} Ad blocking active (doubleclick.net blocked)"
else
    echo -e "  ${RED}✗${NC} Ad blocking not working (doubleclick.net resolves)"
    echo -e "  ${YELLOW}→${NC} Ensure Windscribe DNS is set to 'Local DNS'"
fi

# 5. Test normal DNS resolution
echo -e "${YELLOW}[5/6]${NC} Testing normal DNS resolution..."
NORMAL_RESULT=$(dig google.com +short +timeout=3 2>/dev/null)
if [ -n "$NORMAL_RESULT" ]; then
    echo -e "  ${GREEN}✓${NC} Normal sites resolve correctly (google.com works)"
else
    echo -e "  ${RED}✗${NC} DNS resolution not working"
    exit 1
fi

# 6. Check VPN connection (optional)
echo -e "${YELLOW}[6/6]${NC} Checking VPN status..."
# Try to detect Windscribe VPN interface
if ifconfig | grep -q "utun"; then
    echo -e "  ${GREEN}✓${NC} VPN tunnel interface detected"
else
    echo -e "  ${YELLOW}⚠${NC} No VPN tunnel detected - Windscribe may not be connected"
fi

echo
echo -e "${GREEN}=== Verification Complete ===${NC}"
echo

# Summary
echo "Summary:"
if [ -z "$AD_RESULT" ] || echo "$AD_RESULT" | grep -q "^0\.0\.0\.0$\|^127\."; then
    echo -e "  ${GREEN}✓ Control D DNS filtering is ACTIVE${NC}"
    echo -e "  ${GREEN}✓ Ads and trackers are being blocked${NC}"
    echo
    echo "Your setup is working correctly! 🎉"
else
    echo -e "  ${RED}✗ Control D DNS filtering is NOT active${NC}"
    echo
    echo "To fix this:"
    echo "  1. Open Windscribe app"
    echo "  2. Go to Preferences → Connection"
    echo "  3. Set DNS to: Local DNS"
    echo "  4. Set 'App Internal DNS' to: OS Default"
    echo "  5. Reconnect to Windscribe"
    echo "  6. Run this script again"
fi
