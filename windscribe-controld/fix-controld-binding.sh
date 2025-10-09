#!/bin/bash
# Permanent Control D Binding Fix for VPN Compatibility
# This script ensures Control D always listens on 0.0.0.0:53 for VPN access

set -e

echo "🔧 Control D Binding Fix - VPN Compatibility"
echo "============================================"

# Function to fix Control D configuration
fix_controld_config() {
    echo "📝 Ensuring Control D listens on all interfaces..."
    
    # Backup current config
    sudo cp /etc/controld/ctrld.privacy.toml /etc/controld/ctrld.privacy.toml.auto-backup-$(date +%Y%m%d_%H%M%S)
    
    # Apply fix - ensure 0.0.0.0 binding
    sudo sed -i '' 's/ip = \x27127\.0\.0\.1\x27/ip = \x270\.0\.0\.0\x27/g' /etc/controld/ctrld.privacy.toml
    
    # Verify the fix
    if sudo grep -q "ip = '0.0.0.0'" /etc/controld/ctrld.privacy.toml; then
        echo "✅ Configuration fixed: Control D will listen on 0.0.0.0:53"
        return 0
    else
        echo "❌ Configuration fix failed"
        return 1
    fi
}

# Function to restart Control D with correct binding
restart_controld() {
    echo "🚀 Restarting Control D with privacy profile..."
    
    # Start with privacy profile
    sudo controld-manager switch privacy doh
    
    # Wait for service to start
    sleep 3
    
    # Verify binding
    if sudo lsof -nP -iTCP:53 | grep -q "\*:53"; then
        echo "✅ Control D is listening on all interfaces (*:53)"
        return 0
    else
        echo "❌ Control D is still binding to localhost only"
        return 1
    fi
}

# Function to test DNS filtering
test_dns_filtering() {
    echo "🧪 Testing DNS filtering..."
    
    # Test ad blocking
    result=$(dig @127.0.0.1 doubleclick.net +short 2>/dev/null | head -1)
    if [[ "$result" == "127.0.0.1" ]] || [[ "$result" == "" ]]; then
        echo "✅ Ad blocking working (doubleclick.net blocked)"
    else
        echo "⚠️ Ad blocking may not be working (doubleclick.net → $result)"
    fi
    
    # Test normal resolution
    if dig @127.0.0.1 google.com +short >/dev/null 2>&1; then
        echo "✅ Normal DNS resolution working"
    else
        echo "❌ DNS resolution not working"
        return 1
    fi
}

# Main execution
echo "1️⃣ Fixing Control D configuration..."
if ! fix_controld_config; then
    echo "❌ Configuration fix failed - aborting"
    exit 1
fi

echo "2️⃣ Restarting Control D service..."
if ! restart_controld; then
    echo "❌ Control D restart failed - attempting manual fix"
    
    # Manual fix attempt
    echo "🔧 Attempting manual binding fix..."
    sudo controld-manager stop
    sleep 2
    
    # Ensure configuration is correct
    sudo sed -i '' 's/ip = \x27127\.0\.0\.1\x27/ip = \x270\.0\.0\.0\x27/g' /etc/controld/ctrld.privacy.toml
    sudo controld-manager switch privacy doh
    sleep 3
    
    if ! sudo lsof -nP -iTCP:53 | grep -q "\*:53"; then
        echo "❌ Manual fix also failed - may need deeper investigation"
        exit 1
    fi
fi

echo "3️⃣ Testing DNS functionality..."
test_dns_filtering

echo ""
echo "🎉 Control D binding fix completed!"
echo ""
echo "Current binding status:"
sudo lsof -nP -iTCP:53 2>/dev/null || echo "No TCP:53 binding found"
sudo lsof -nP -iUDP:53 2>/dev/null || echo "No UDP:53 binding found"
echo ""
echo "✅ Windscribe should now be able to connect with 'Local DNS' setting"
echo "📋 Next step: Try connecting Windscribe VPN with Local DNS"