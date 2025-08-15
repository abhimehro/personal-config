#!/bin/bash
# Check all SSH connection methods

# Preferred terminal integrations: Zed, Warp Preview, Cursor
# Run this to validate local connectivity before launching profiles

echo "🔍 Checking all SSH connection methods for Cursor IDE..."
echo ""

# Function to test connectivity
test_ssh_connection() {
    local host_alias=$1
    local description=$2
    
    echo -n "Testing $description... "
    
    if command -v nc >/dev/null 2>&1; then
        # Get hostname from SSH config
        hostname=$(ssh -G "$host_alias" | grep "^hostname " | awk '{print $2}')
        if nc -z -w 3 "$hostname" 22 >/dev/null 2>&1; then
            echo "✅ Available"
            return 0
        else
            echo "❌ Failed"
            return 1
        fi
    else
        # Fallback method
        if ssh -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=no "$host_alias" exit >/dev/null 2>&1; then
            echo "✅ Available"
            return 0
        else
            echo "❌ Failed"
            return 1
        fi
    fi
}

# Check network status
echo "Network Status:"
vpn_network=$(ifconfig | grep "inet 100\." | head -1 | awk '{print $2}')
if [ -n "$vpn_network" ]; then
    echo "  🌐 VPN/Tailscale detected: $vpn_network"
    vpn_active=true
else
    echo "  🏠 Local network mode"
    vpn_active=false
fi

local_ips=$(ifconfig | grep 'inet ' | grep -v 127.0.0.1 | awk '{print $2}' | tr '\n' ' ')
echo "  📍 Local IPs: $local_ips"
echo ""

# Test all connection methods
echo "Connection Methods:"
test_ssh_connection "cursor-local" "Local hostname (abhis-macbook-air)"
test_ssh_connection "cursor-mdns" "mDNS (Abhis-MacBook-Air.local)"

if [ "$vpn_active" = true ]; then
    test_ssh_connection "cursor-vpn" "VPN connection (100.105.30.135)"
else
    echo "Testing VPN connection (100.105.30.135)... ⚠️  VPN not active"
fi

echo ""
echo "Recommendations:"

if [ "$vpn_active" = true ]; then
    echo "  🎯 VPN is active - try: ssh cursor-vpn"
    echo "  🎯 Alternative: ssh cursor-local"
else
    echo "  🎯 VPN is off - try: ssh cursor-local"
    echo "  🎯 Alternative: ssh cursor-mdns"
fi

echo ""
echo "For Cursor IDE, use host: cursor-local, cursor-vpn, or cursor-mdns"