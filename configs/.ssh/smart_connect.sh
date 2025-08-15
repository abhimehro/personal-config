#!/bin/bash
# Smart SSH Connection Script - Auto-detects VPN status and connects accordingly

echo "🔍 Smart SSH Connection - Auto-detecting best connection method..."
echo ""

# Function to test connectivity with timeout (macOS compatible)
test_connection() {
    local host=$1
    local timeout_sec=3
    
    # Use nc (netcat) for connection test since timeout command isn't available
    if command -v nc >/dev/null 2>&1; then
        nc -z -w $timeout_sec "$host" 22 >/dev/null 2>&1
        return $?
    else
        # Fallback to ssh with short timeout
        ssh -o ConnectTimeout=$timeout_sec -o BatchMode=yes -o StrictHostKeyChecking=no "$host" exit >/dev/null 2>&1
        return $?
    fi
}

# Function to get current IP addresses
get_network_info() {
    echo "Current network configuration:"
    local_ips=$(ifconfig | grep 'inet ' | grep -v 127.0.0.1 | awk '{print $2}' | tr '\n' ' ')
    echo "  Local IPs: $local_ips"
    
    # Check if we're on a VPN-like network
    if ifconfig | grep -q "100\."; then
        vpn_ip=$(ifconfig | grep "inet 100\." | head -1 | awk '{print $2}')
        echo "  Status: Connected to VPN/Tailscale (IP: $vpn_ip)"
        return 0
    else
        echo "  Status: Local network connection"
        return 1
    fi
}

# Preferred terminal profiles (Zed, Warp Preview, Cursor) can call this script directly
# e.g., set up a profile/command to run: ~/.ssh/smart_connect.sh

echo "1. Analyzing network configuration..."
get_network_info
vpn_detected=$?
echo ""

echo "2. Testing connection methods..."

# For local machine connections, mDNS is usually the most reliable
echo "   Testing mDNS connection (Abhis-MacBook-Air.local)..."
if test_connection "Abhis-MacBook-Air.local"; then
    echo "   ✅ mDNS connection available (RECOMMENDED for local machine)"
    echo ""
    echo "🚀 Connecting via mDNS (most reliable for local connections)..."
    ssh cursor-mdns
    exit $?
else
    echo "   ❌ mDNS connection failed"
fi

# Test local hostname connection
echo "   Testing local hostname (abhis-macbook-air)..."
if test_connection "abhis-macbook-air"; then
    echo "   ✅ Local hostname connection available"
    echo ""
    echo "🚀 Connecting via local hostname..."
    ssh cursor-local
    exit $?
else
    echo "   ❌ Local hostname connection failed"
fi

# Test VPN connection (but explain why it might not work for same machine)
if [ $vpn_detected -eq 0 ]; then
    echo "   Testing VPN connection (100.105.30.135)..."
    if test_connection "100.105.30.135"; then
        echo "   ✅ VPN connection available"
        echo ""
        echo "🚀 Connecting via VPN..."
        ssh cursor-vpn
        exit $?
    else
        echo "   ❌ VPN connection failed"
        echo "   ℹ️  Note: VPN connection to same machine often requires special configuration"
    fi
fi

echo ""
echo "❌ All connection methods failed!"
echo ""
echo "Troubleshooting suggestions:"
echo "1. Make sure your MacBook Air is powered on and connected to network"
echo "2. Check if SSH is enabled on the target machine:"
echo "   System Preferences → Sharing → Remote Login"
echo "3. For VPN connection issues, run: ./diagnose_vpn.sh"
echo "4. Verify network connectivity:"
echo "   ping Abhis-MacBook-Air.local"
echo "   ping abhis-macbook-air"
if [ $vpn_detected -eq 0 ]; then
    echo "   ping 100.105.30.135"
fi
echo "5. Check firewall settings on target machine"
echo ""
echo "Manual connection commands to try:"
echo "   ssh cursor-mdns     # mDNS/Bonjour (RECOMMENDED)"
echo "   ssh cursor-local    # Local network"
if [ $vpn_detected -eq 0 ]; then
    echo "   ssh cursor-vpn      # VPN connection (may need special config)"
fi