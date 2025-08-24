#!/bin/bash
# VPN Connection Diagnostic Script

echo "🔍 Diagnosing VPN SSH Connection Issues..."
echo ""

# Get current network info
vpn_ip="100.105.30.135"
echo "Target VPN IP: $vpn_ip"
echo "Current machine IPs:"
ifconfig | grep 'inet ' | grep -v 127.0.0.1 | awk '{print "  " $2}'
echo ""

# Check if SSH is listening on all interfaces
echo "1. Checking SSH server configuration..."
if command -v lsof >/dev/null 2>&1; then
    echo "SSH daemon listening on:"
    lsof -i :22 | grep LISTEN
    echo ""
else
    echo "lsof not available, checking with netstat..."
    netstat -an | grep :22 | grep LISTEN
    echo ""
fi

# Check SSH configuration
echo "2. Checking SSH daemon config..."
if [ -f /etc/ssh/sshd_config ]; then
    listen_address=$(grep "^ListenAddress" /etc/ssh/sshd_config 2>/dev/null || echo "Default: all interfaces")
    echo "ListenAddress setting: $listen_address"
else
    echo "SSH config file not found - using defaults"
fi
echo ""

# Test basic connectivity to VPN IP
echo "3. Testing network connectivity to VPN IP..."
echo "Testing ping to $vpn_ip..."
if ping -c 1 -W 3000 "$vpn_ip" >/dev/null 2>&1; then
    echo "✅ Ping successful"
else
    echo "❌ Ping failed"
fi

echo ""
echo "Testing if SSH port is reachable on VPN IP..."
if command -v nc >/dev/null 2>&1; then
    if nc -z -w 3 "$vpn_ip" 22 >/dev/null 2>&1; then
        echo "✅ SSH port 22 is reachable on VPN IP"
    else
        echo "❌ SSH port 22 not reachable on VPN IP"
    fi
else
    echo "nc (netcat) not available for port testing"
fi
echo ""

# Check firewall status
echo "4. Checking firewall configuration..."
if command -v pfctl >/dev/null 2>&1; then
    firewall_status=$(sudo pfctl -s info 2>/dev/null | grep "Status" || echo "Unknown")
    echo "Firewall status: $firewall_status"
else
    echo "Unable to check firewall status"
fi
echo ""

# Check if this is a loopback issue
echo "5. Analyzing the issue..."
current_ips=$(ifconfig | grep 'inet ' | grep -v 127.0.0.1 | awk '{print $2}' | tr '\n' ' ')
if echo "$current_ips" | grep -q "$vpn_ip"; then
    echo "🔍 DIAGNOSIS: You're trying to SSH to your own machine's VPN IP!"
    echo ""
    echo "This is a common issue. Here's what's happening:"
    echo "• Your machine has VPN IP: $vpn_ip"
    echo "• You're trying to SSH TO: $vpn_ip (same machine)"
    echo "• SSH daemon may not be configured to accept connections on VPN interface"
    echo ""
    echo "SOLUTIONS:"
    echo ""
    echo "Option 1: Configure SSH to listen on VPN interface"
    echo "  - Edit /etc/ssh/sshd_config"
    echo "  - Add: ListenAddress $vpn_ip"
    echo "  - Restart SSH: sudo launchctl unload/load com.openssh.sshd"
    echo ""
    echo "Option 2: Use mDNS (RECOMMENDED)"
    echo "  - This works perfectly and is more reliable"
    echo "  - Use: ssh cursor-mdns"
    echo "  - Works regardless of VPN status"
    echo ""
    echo "Option 3: SSH to a different machine"
    echo "  - The VPN connection is for connecting to OTHER machines"
    echo "  - Not for connecting to your own machine"
else
    echo "This appears to be a connection to a different machine"
    echo "Check if the target machine at $vpn_ip is:"
    echo "• Powered on and connected to the VPN"
    echo "• Has SSH enabled (Remote Login)"
    echo "• Has proper firewall rules"
fi
echo ""

echo "6. RECOMMENDATION:"
echo "✅ For local development with Cursor IDE, use:"
echo "   ssh cursor-mdns"
echo ""
echo "The mDNS connection (cursor-mdns) is actually BETTER because:"
echo "• Works with or without VPN"
echo "• More reliable for local machine connections"
echo "• No network routing issues"
echo "• Automatically resolves to correct interface"