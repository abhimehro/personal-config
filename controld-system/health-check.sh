#!/bin/bash

# Control D Health Check Script
# Verifies that Control D DNS mode is healthy using the network-mode-verify
# checklist. This script is Separation-Strategy aware and no longer assumes
# a specific local ctrld.toml file.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

VERIFY_SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/scripts/network-mode-verify.sh"

if [[ ! -x "$VERIFY_SCRIPT" ]]; then
  echo -e "${RED}[ERR]${NC} network-mode-verify.sh not found or not executable at $VERIFY_SCRIPT" >&2
  exit 1
fi

echo "=================================================="
echo "   Control D Health Check (Separation Strategy)   "
echo "=================================================="
echo ""

# 1. DEEP VERIFICATION
# Delegate to the unified verification checklist for CONTROL D ACTIVE state.
# We pass the default browsing profile so profile-aware and DoH3 checks run.

echo -e "${BLUE}Running deep verification...${NC}"
echo ""

VERIFY_STATUS=0
if "$VERIFY_SCRIPT" controld browsing; then
  VERIFY_STATUS=0
else
  VERIFY_STATUS=1
fi

echo ""
echo "=================================================="
echo "             System Diagnostics                   "
echo "=================================================="
echo ""

# 2. SYSTEM DIAGNOSTICS
# These checks help pinpoint specific issues if the deep verification fails,
# or provide reassurance if it passes.

# Check 1: Service Status
echo -n "1. Checking if ctrld service is running... "
if sudo ctrld service status &>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC}"
    SERVICE_RUNNING=true
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "   Service is not running. Start it with:"
    echo -e "   ${YELLOW}sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks${NC}"
    SERVICE_RUNNING=false
fi

echo ""

# Check 2: DNS Resolution (only if service is running)
if [ "$SERVICE_RUNNING" = true ]; then
    echo -n "2. Testing DNS resolution via ctrld... "
    if dig @127.0.0.1 example.com +short +timeout=5 &>/dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        DNS_WORKING=true
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "   DNS queries are not being resolved via localhost."
        DNS_WORKING=false
    fi
else
    echo "2. Skipping DNS resolution test (service not running)"
    DNS_WORKING=false
fi

echo ""

# Check 3: Log file errors
echo -n "3. Checking for recent errors in logs... "
# Use a mockable path for logs if needed, but for now standard path
ERROR_COUNT=$(sudo tail -20 /var/log/ctrld.log 2>/dev/null | grep -c "\"level\":\"error\"" || true)
if [ -z "$ERROR_COUNT" ]; then
    ERROR_COUNT=0
fi

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ PASS${NC} (no errors in last 20 log lines)"
elif [ "$ERROR_COUNT" -lt 5 ]; then
    echo -e "${YELLOW}⚠ WARNING${NC} (${ERROR_COUNT} errors found)"
    echo "   This may be normal if you just restarted the service."
else
    echo -e "${RED}✗ FAIL${NC} (${ERROR_COUNT} errors found)"
    echo "   Run: sudo tail -20 /var/log/ctrld.log | grep error"
fi

echo ""

# Check 4: Upstream connectivity
if [ "$SERVICE_RUNNING" = true ] && [ "$DNS_WORKING" = true ]; then
    echo -n "4. Checking upstream DoH connectivity... "
    
    # Look for "upstream marked as down" in recent logs
    if sudo tail -50 /var/log/ctrld.log 2>/dev/null | grep -q "marked as down"; then
        echo -e "${RED}✗ FAIL${NC}"
        echo "   Upstream is marked as down. Check logs:"
        echo "   sudo tail -50 /var/log/ctrld.log | grep upstream"
    else
        echo -e "${GREEN}✓ PASS${NC}"
    fi
else
    echo "4. Skipping upstream check (prerequisites failed)"
fi

echo ""

# Check 5: Configuration file
echo -n "5. Verifying configuration file exists... "
if [ -f "$HOME/.config/controld/ctrld.toml" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "   Config file not found at ~/.config/controld/ctrld.toml"
fi

echo ""

# Check 6: Firewall exception
echo -n "6. Checking firewall exception... "
if sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps 2>/dev/null | grep -q ctrld; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${YELLOW}⚠ WARNING${NC}"
    echo "   ctrld not found in firewall allowlist."
    echo "   Add with: sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/homebrew/bin/ctrld"
fi

echo ""
echo "=================================================="

# Final Summary
# Considers both the deep verification (network state) and local diagnostics (service health)
ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ "$VERIFY_STATUS" -eq 0 ] && [ "$SERVICE_RUNNING" = true ] && [ "$DNS_WORKING" = true ]; then
    echo -e "${GREEN}Overall Status: HEALTHY ✓${NC}"
    echo ""
    if [ -f "$HOME/.config/controld/ctrld.toml" ]; then
      echo "Active profile:"
      grep "upstream = " "$HOME/.config/controld/ctrld.toml" | head -1 || echo "Unknown"
    fi
    echo "SUMMARY TS=${ts} MODE=health-check RESULT=PASS PROFILE=browsing"
    exit 0
else
    echo -e "${RED}Overall Status: UNHEALTHY ✗${NC}"
    echo ""
    echo "Please address the issues highlighted above."
    echo "SUMMARY TS=${ts} MODE=health-check RESULT=FAIL PROFILE=browsing"
    exit 1
fi
