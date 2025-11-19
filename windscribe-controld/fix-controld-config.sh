#!/bin/bash
#
# Fix Control D Configuration for Windscribe Integration
# LEGACY: superseded by scripts/network-mode-manager.sh + controld-manager.
# Kept for historical reference; avoid using alongside network-mode-manager.
# This script reconfigures Control D to listen on all interfaces (*******:53)
# so Windscribe VPN can use it with "Local DNS" mode
#
# Security Note: Listening on ******* is required for VPN integration.
# The DNS resolver is still only accessible from VPN tunnel, not external networks.

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Control D Configuration Fix ===${NC}"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}ERROR:${NC} This script must be run as root"
    echo "Usage: sudo $0"
    exit 1
fi

# Backup current configuration
echo -e "${YELLOW}→${NC} Backing up current configuration..."
cp /etc/controld/ctrld.toml /etc/controld/ctrld.toml.backup.$(date +%Y%m%d_%H%M%S)
echo -e "${GREEN}✓${NC} Backup created"

# Stop Control D service
echo -e "${YELLOW}→${NC} Stopping Control D service..."
ctrld stop 2>/dev/null || true
pkill -f ctrld 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓${NC} Service stopped"

# Modify configuration to listen on all interfaces
echo -e "${YELLOW}→${NC} Updating configuration to listen on 0.0.0.0:53..."
sed -i '' "s/ip = '127\.0\.0\.1'/ip = '0.0.0.0'/g" /etc/controld/ctrld.toml
echo -e "${GREEN}✓${NC} Configuration updated"

# Verify the change
if grep -q "ip = '0.0.0.0'" /etc/controld/ctrld.toml; then
    echo -e "${GREEN}✓${NC} Configuration verified: listening on all interfaces"
else
    echo -e "${RED}✗${NC} Configuration update failed"
    exit 1
fi

# Restart Control D service
echo -e "${YELLOW}→${NC} Starting Control D service..."
ctrld start --config=/etc/controld/ctrld.toml 2>/dev/null || {
    echo -e "${RED}✗${NC} Failed to start Control D"
    exit 1
}
sleep 3
echo -e "${GREEN}✓${NC} Service started"

# Verify service is listening on correct interface
echo -e "${YELLOW}→${NC} Verifying service is listening on 0.0.0.0:53..."
if sudo lsof -nP -iTCP:53 | grep -q "\\*:53"; then
    echo -e "${GREEN}✓${NC} Control D is listening on all interfaces (*:53)"
else
    echo -e "${RED}✗${NC} Control D is not listening on all interfaces"
    echo "Current listener:"
    sudo lsof -nP -iTCP:53
    exit 1
fi

echo
echo -e "${GREEN}=== Configuration Fixed Successfully ===${NC}"
echo
echo "Next steps:"
echo "1. Open Windscribe app"
echo "2. Go to Preferences → Connection"
echo "3. Set DNS to: Local DNS"
echo "4. Set 'App Internal DNS' to: OS Default"
echo "5. Reconnect to Windscribe"
echo
echo "After reconnecting, verify with:"
echo "  dig doubleclick.net +short  # Should return 0.0.0.0 (blocked)"
echo "  dig google.com +short       # Should resolve normally"
