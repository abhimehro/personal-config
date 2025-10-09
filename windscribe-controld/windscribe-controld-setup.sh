#!/bin/bash
# Windscribe + Control D DNS Setup Script
# This script handles the proper sequence of VPN connection and DNS configuration

set -e

echo "🔧 Windscribe + Control D DNS Setup"
echo "===================================="

# Function to check if Windscribe is connected
check_windscribe_connected() {
    # Look for Windscribe VPN interface with IPv4 address
    ifconfig | grep -A5 "utun" | grep "inet " | grep -v "127.0.0.1" >/dev/null 2>&1
}

# Function to set Control D DNS
set_controld_dns() {
    echo "📡 Setting Control D DNS (127.0.0.1)..."
    sudo networksetup -setdnsservers "Wi-Fi" 127.0.0.1
    sudo networksetup -setdnsservers "USB 10/100/1000 LAN" 127.0.0.1 2>/dev/null || true
    echo "🔄 Flushing DNS cache..."
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder
}

# Function to test DNS filtering
test_dns_filtering() {
    echo "🧪 Testing DNS filtering..."
    echo -n "Testing ad blocking (doubleclick.net): "
    result=$(dig doubleclick.net +short 2>/dev/null || echo "blocked")
    if [[ "$result" == "" ]] || [[ "$result" == "blocked" ]] || [[ "$result" =~ ^0\.0\.0\.0$ ]]; then
        echo "✅ BLOCKED"
    else
        echo "❌ NOT BLOCKED ($result)"
        return 1
    fi
    
    echo -n "Testing normal resolution (google.com): "
    if dig google.com +short >/dev/null 2>&1; then
        echo "✅ WORKING"
    else
        echo "❌ FAILED"
        return 1
    fi
}

# Function to check if system is actually using Control D
check_actual_dns_usage() {
    echo "🔍 Checking actual DNS usage..."
    
    # Check if 127.0.0.1 appears in resolver #1 (not just resolver #2)
    resolver1_dns=$(scutil --dns | grep -A5 "resolver #1" | grep "nameserver" | head -1)
    
    if echo "$resolver1_dns" | grep -q "*********"; then
        echo "✅ System is using Control D (127.0.0.1)"
        return 0
    else
        echo "❌ System is NOT using Control D"
        echo "Current primary DNS: $resolver1_dns"
        echo ""
        echo "🚨 Windscribe is overriding DNS settings!"
        echo "Solution: In Windscribe app, set Custom DNS to *********"
        echo "(Not 'Local DNS' - use 'Custom DNS' with ********* explicitly)"
        return 1
    fi
}

# Main execution
echo "1️⃣ Checking if Windscribe is connected..."
if check_windscribe_connected; then
    echo "✅ Windscribe VPN is connected"
    
    echo "2️⃣ Applying Control D DNS settings..."
    set_controld_dns
    
    echo "3️⃣ Testing the setup..."
    if check_actual_dns_usage && test_dns_filtering; then
        echo "🎉 SUCCESS! Windscribe VPN + Control D DNS is working!"
        echo ""
        echo "📊 Current DNS configuration:"
        scutil --dns | head -10
    else
        echo "❌ Setup verification failed"
        echo "Please configure Windscribe to use Custom DNS: *********"
        exit 1
    fi
else
    echo "❌ Windscribe VPN is not connected"
    echo ""
    echo "Please:"
    echo "1. Open Windscribe app"
    echo "2. Set DNS to 'Auto' or 'Windscribe'"
    echo "3. Connect to a VPN server"
    echo "4. Run this script again: bash ~/Documents/dev/personal-config/windscribe-controld-setup.sh"
    exit 1
fi