#!/bin/bash
# Updated SSH Connection Test Script for VPN/Proxy Setup

echo "🔧 Testing SSH connection with VPN/Proxy considerations..."
echo ""

# Test basic connectivity first
echo "1. Testing basic network connectivity to 192.168.0.190..."
if ping -c 1 -W 3000 192.168.0.190 >/dev/null 2>&1; then
    echo "✅ Host 192.168.0.190 is reachable"
else
    echo "⚠️  Host 192.168.0.190 not reachable via ping"
    echo "   → This might be normal if ICMP is blocked"
fi
echo ""

# Test SSH connection with verbose output
echo "2. Testing SSH connection (accepting new host key)..."
echo "   This will automatically accept the new host key"
echo ""

# First, let's try a simple connection test
if timeout 10 ssh -v -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -o BatchMode=yes cursor-local echo "Connection successful" 2>&1; then
    echo "✅ SSH connection successful!"
else
    echo "⚠️  SSH connection failed. Let's try with verbose output..."
    echo ""
    echo "3. Attempting connection with verbose output for debugging:"
    echo "   (This may show VPN/proxy related issues)"
    timeout 15 ssh -vvv -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new cursor-local echo "Verbose connection test"
fi
echo ""

echo "4. Checking if we need proxy configuration..."
echo "   Your VPN setup: Windscribe SOCKS proxy on 192.168.0.190:443"
echo ""
echo "If the connection still fails, you might need to:"
echo "1. Add proxy command to SSH config"
echo "2. Check if the SSH port (22) is accessible through the VPN"
echo "3. Verify the target machine (192.168.0.190) is actually your MacBook"
echo ""

echo "To enable SOCKS proxy for SSH connections:"
echo "Uncomment this line in ~/.ssh/config under cursor-local:"
echo "ProxyCommand nc -X 5 -x 192.168.0.190:443 %h %p"
echo ""

echo "5. Current host keys:"
cat ~/.ssh/known_hosts