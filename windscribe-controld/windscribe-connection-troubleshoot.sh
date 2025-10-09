#!/bin/bash
# Windscribe VPN Connection Troubleshooting
# Diagnoses and fixes common Windscribe + Control D connection issues

set -e

echo "🔧 Windscribe VPN Connection Troubleshooting"
echo "============================================"

# Function to check Control D status
check_controld_status() {
    echo "📊 Checking Control D status..."
    
    if sudo controld-manager status | grep -q "Service Status: ✅ Running"; then
        echo "✅ Control D is running"
    else
        echo "❌ Control D is not running"
        return 1
    fi
    
    # Check binding
    if sudo lsof -nP -iTCP:53 | grep -q "\*:53"; then
        echo "✅ Control D is listening on all interfaces (*:53)"
    else
        echo "❌ Control D is only listening on localhost"
        echo "🔧 Applying VPN binding fix..."
        bash ~/Documents/dev/personal-config/windscribe-controld/permanent-binding-fix.sh
    fi
    
    # Test functionality
    if dig @127.0.0.1 +short google.com >/dev/null 2>&1; then
        echo "✅ Control D DNS resolution working"
    else
        echo "❌ Control D DNS resolution failed"
        return 1
    fi
}

# Function to prepare system for Windscribe connection
prepare_for_windscribe() {
    echo "🚀 Preparing system for Windscribe connection..."
    
    # Ensure DOH protocol (more VPN-compatible than DOH3)
    echo "Switching to DOH protocol for VPN compatibility..."
    sudo controld-manager switch privacy doh
    sleep 3
    
    # Verify binding after switch
    if ! sudo lsof -nP -iTCP:53 | grep -q "\*:53"; then
        echo "❌ Binding reverted after switch - applying fix..."
        bash ~/Documents/dev/personal-config/windscribe-controld/permanent-binding-fix.sh
    fi
    
    # Reset system DNS to automatic (prevents conflicts)
    echo "Resetting system DNS to automatic for clean VPN connection..."
    sudo networksetup -setdnsservers "Wi-Fi" empty
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder
    
    echo "✅ System prepared for Windscribe connection"
}

# Function to check network conflicts
check_network_conflicts() {
    echo "🔍 Checking for network conflicts..."
    
    # Check what's using port 53
    echo "Services using port 53:"
    sudo lsof -nP -iTCP:53 -iUDP:53 | grep -v "COMMAND" || echo "No conflicts found"
    
    # Check for existing VPN connections
    echo "Checking for existing VPN interfaces:"
    ifconfig | grep -E "utun|ppp" | grep -E "inet|flags" || echo "No existing VPN connections"
    
    # Check DNS configuration conflicts
    echo "Current system DNS:"
    scutil --dns | head -10
}

# Function to provide Windscribe connection instructions
windscribe_connection_steps() {
    echo "📋 Windscribe Connection Steps:"
    echo "================================"
    echo ""
    echo "1. Open Windscribe application"
    echo ""
    echo "2. Configure Windscribe settings:"
    echo "   • DNS Setting: Local DNS (NOT Custom DNS)"
    echo "   • App Internal DNS: OS Default" 
    echo "   • Split Tunneling: OFF (disabled)"
    echo ""
    echo "3. Connect to Windscribe VPN server"
    echo ""
    echo "4. After connection, run verification:"
    echo "   bash ~/Documents/dev/personal-config/windscribe-controld/windscribe-controld-setup.sh"
    echo ""
    echo "🚨 Common Issues:"
    echo ""
    echo "Issue: Windscribe shows 'DNS leak detected' warning"
    echo "Solution: Click 'OK' - this is a false positive (127.0.0.1 is secure)"
    echo ""
    echo "Issue: Connection keeps failing"
    echo "Solutions:"
    echo "• Try different Windscribe server locations"
    echo "• Temporarily set DNS to 'Auto', connect, then switch back to 'Local DNS'"
    echo "• Restart Windscribe application"
    echo "• Check firewall settings aren't blocking Windscribe"
}

# Function to test post-connection
test_connection() {
    echo "🧪 Testing VPN + DNS setup..."
    
    # Check if VPN is connected
    if ifconfig | grep -A5 "utun" | grep -q "inet "; then
        echo "✅ VPN interface detected"
        
        # Test DNS filtering
        result=$(dig +short doubleclick.net 2>/dev/null | head -1)
        if [[ "$result" == "127.0.0.1" ]] || [[ -z "$result" ]]; then
            echo "✅ DNS filtering working (doubleclick.net blocked)"
        else
            echo "⚠️ DNS filtering unclear (doubleclick.net → $result)"
        fi
        
        # Test normal resolution
        if dig +short google.com >/dev/null 2>&1; then
            echo "✅ Normal DNS resolution working"
        else
            echo "❌ DNS resolution failed"
        fi
        
        # Check IP location
        echo "Checking IP location:"
        curl -s --max-time 10 https://ipinfo.io/json | grep -E '(city|region|country|org)' || echo "Could not determine location"
        
    else
        echo "❌ No VPN connection detected"
        return 1
    fi
}

# Emergency reset function
emergency_reset() {
    echo "🚨 Emergency Reset - Cleaning up network configuration..."
    
    # Stop Control D
    sudo controld-manager stop 2>/dev/null || true
    
    # Reset all network DNS
    for service in $(networksetup -listallnetworkservices | tail -n +2 | sed 's/^*//'); do
        sudo networksetup -setdnsservers "$service" empty 2>/dev/null || true
    done
    
    # Flush DNS
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder
    
    # Kill any stuck VPN processes
    sudo pkill -f windscribe 2>/dev/null || true
    
    echo "✅ Emergency reset completed"
    echo "🔄 Restart Windscribe app and Control D:"
    echo "   sudo controld-manager switch privacy doh"
}

# Main menu
main() {
    case "${1:-""}" in
        "check")
            check_controld_status && echo "✅ All Control D checks passed"
            ;;
        "prepare")
            check_controld_status
            prepare_for_windscribe
            check_network_conflicts
            windscribe_connection_steps
            ;;
        "test")
            test_connection
            ;;
        "emergency")
            emergency_reset
            ;;
        *)
            echo "Windscribe VPN Connection Troubleshooting"
            echo "Usage: $0 <command>"
            echo ""
            echo "Commands:"
            echo "  check     - Check Control D status and configuration"
            echo "  prepare   - Prepare system for Windscribe connection"
            echo "  test      - Test VPN + DNS setup after connection"
            echo "  emergency - Emergency reset of network configuration"
            echo ""
            echo "Quick diagnosis:"
            check_controld_status
            echo ""
            prepare_for_windscribe
            echo ""
            windscribe_connection_steps
            ;;
    esac
}

main "$@"