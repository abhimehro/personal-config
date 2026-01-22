#!/usr/bin/env bash
#
# Test SSH Connections
# Tests all SSH connection methods defined in config
#
# Usage: ./scripts/test_ssh_connections.sh

set -Eeuo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()      { echo -e "${BLUE}[INFO]${NC} $@"; }
success()  { echo -e "${GREEN}[OK]${NC} $@"; }
warn()     { echo -e "${YELLOW}[WARN]${NC} $@"; }
error()    { echo -e "${RED}[ERROR]${NC} $@" >&2; }

echo "=========================================="
echo "Testing SSH Connection Methods"
echo "=========================================="
echo ""

# Test hosts
hosts=("cursor-mdns" "cursor-local" "cursor-auto")

for host in "${hosts[@]}"; do
    echo "Testing: $host"

    # Parse SSH config
    # ⚡ Bolt Optimization: Cache ssh -G output to avoid redundant calls
    if ssh_config=$(ssh -G "$host" 2>/dev/null); then
        hostname=$(echo "$ssh_config" | grep "^hostname " | awk '{print $2}')
        user=$(echo "$ssh_config" | grep "^user " | awk '{print $2}')

        echo "  Hostname: $hostname"
        echo "  User: $user"

        # Test connectivity (ping)
        if ping -c 1 -W 1000 "$hostname" >/dev/null 2>&1; then
            success "  Network: Reachable"
        else
            warn "  Network: Not reachable"
        fi

        # Test SSH connection (dry run)
        # ⚡ Bolt Optimization: Capture output once to avoid double execution on failure
        if result=$(ssh -o ConnectTimeout=3 -o BatchMode=yes "$host" exit 2>&1); then
            success "  SSH: Connection successful!"
        else
            # SSH failed. Analyze output.
            if echo "$result" | grep -q "Host key verification failed"; then
                warn "  SSH: Host key needs to be accepted (run: ssh $host)"
            elif echo "$result" | grep -q "Permission denied"; then
                warn "  SSH: Permission denied (check SSH keys)"
            elif echo "$result" | grep -q "Connection refused"; then
                error "  SSH: Connection refused (SSH service not running)"
            elif echo "$result" | grep -q "Connection timed out"; then
                error "  SSH: Connection timed out"
            else
                # ⚡ Bolt Fix: correctly report other errors (e.g. DNS failure) instead of reporting success
                warn "  SSH: $result"
            fi
        fi
    else
        error "  Failed to parse SSH config for $host"
    fi

    echo ""
done

echo "=========================================="
echo "Connection Test Summary"
echo "=========================================="
echo ""
echo "To accept host keys and test connections:"
echo "  ssh cursor-mdns    # Recommended (mDNS/Bonjour)"
echo "  ssh cursor-local    # Local network"
echo "  ssh cursor-auto     # Auto-detection"
echo ""
echo "Note: First connection will prompt to accept host key."
echo "      Use 'ssh -o StrictHostKeyChecking=no' to skip prompt (less secure)."
echo ""
