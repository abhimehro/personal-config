#!/bin/bash

# Quick Windscribe + Control D Integration Test
# LEGACY: older test harness; for reference only.
# Tests VPN connection and DNS privacy filtering

echo "🧪 Testing Windscribe + Control D Integration"
echo "=============================================="

# Check if Control D is running
if pgrep -f "ctrld run" >/dev/null; then
	echo "✅ Control D service: RUNNING"
else
	echo "❌ Control D service: NOT RUNNING"
	echo "   Run: sudo /Users/abhimehrotra/Documents/dev/personal-config/windscribe-controld/controld-service-manager.sh start"
	exit 1
fi

# Check VPN connection
echo
echo "🔍 Checking VPN Status..."
vpn_interface=$(ifconfig | grep -A1 "utun" | grep "inet " | head -1)
if [[ -n $vpn_interface ]]; then
	echo "✅ VPN interface: CONNECTED"
	echo "   $vpn_interface"
else
	echo "❌ VPN interface: NOT CONNECTED"
	echo "   Connect Windscribe VPN with 'Local DNS' setting"
fi

# Test DNS filtering
echo
echo "🛡️  Testing DNS Filtering..."
blocked_result=$(dig doubleclick.net +short 2>/dev/null)
if [[ $blocked_result == "127.0.0.1" ]]; then
	echo "✅ Ad blocking: ACTIVE (doubleclick.net → 127.0.0.1)"
else
	echo "❌ Ad blocking: INACTIVE (got: $blocked_result)"
fi

# Test normal DNS resolution
normal_result=$(dig google.com +short 2>/dev/null | head -1)
if [[ -n $normal_result && $normal_result != "127.0.0.1" ]]; then
	echo "✅ Normal DNS: WORKING (google.com → $normal_result)"
else
	echo "❌ Normal DNS: FAILED"
fi

# Check IP location (if VPN connected)
if [[ -n $vpn_interface ]]; then
	echo
	echo "🌍 Checking IP Location..."
	location_info=$(curl -s --max-time 10 https://ipinfo.io/json 2>/dev/null)
	if [[ -n $location_info ]]; then
		city=$(echo "$location_info" | grep -o '"city": "[^"]*"' | cut -d'"' -f4)
		country=$(echo "$location_info" | grep -o '"country": "[^"]*"' | cut -d'"' -f4)
		org=$(echo "$location_info" | grep -o '"org": "[^"]*"' | cut -d'"' -f4)
		echo "✅ VPN location: $city, $country ($org)"
	else
		echo "❌ Could not check location"
	fi
fi

echo
echo "🎯 Integration Test Summary:"
if pgrep -f "ctrld run" >/dev/null && [[ $blocked_result == "127.0.0.1" ]]; then
	if [[ -n $vpn_interface ]]; then
		echo "🟢 PERFECT! Windscribe + Control D working together"
		echo "   - VPN encryption: ✅"
		echo "   - DNS privacy filtering: ✅"
		echo "   - Ad blocking: ✅"
	else
		echo "🟡 Control D ready, connect Windscribe VPN"
		echo "   - DNS privacy filtering: ✅"
		echo "   - Ad blocking: ✅"
		echo "   - VPN encryption: Connect Windscribe"
	fi
else
	echo "🔴 Issues detected - check Control D service"
fi
