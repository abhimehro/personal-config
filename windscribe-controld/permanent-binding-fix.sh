#!/bin/bash
# Permanent Control D Binding Fix - All Configuration Files
# This script fixes ALL Control D configuration files to prevent reversion

set -e

echo "🔧 Permanent Control D Binding Fix"
echo "================================="

# Function to apply binding fix to all config files
fix_all_configs() {
    echo "📝 Fixing all Control D configuration files..."
    
    # List of all config files to fix
    local config_files=(
        "/etc/controld/ctrld.privacy.toml"
        "/etc/controld/ctrld.gaming.toml"
        "/etc/controld/profiles/ctrld.privacy.toml"
        "/etc/controld/profiles/ctrld.gaming.toml"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            echo "  Fixing: $config_file"
            # Backup first
            sudo cp "$config_file" "$config_file.binding-backup-$(date +%Y%m%d_%H%M%S)"
            # Apply fix
            sudo sed -i '' 's/ip = \x27127\.0\.0\.1\x27/ip = \x270\.0\.0\.0\x27/g' "$config_file"
            echo "    ✅ Fixed"
        else
            echo "  ⚠️ Not found: $config_file"
        fi
    done
    
    echo "✅ All configuration files updated"
}

# Function to verify configurations
verify_configs() {
    echo "🔍 Verifying configuration files..."
    
    local config_files=(
        "/etc/controld/ctrld.privacy.toml"
        "/etc/controld/ctrld.gaming.toml"
        "/etc/controld/profiles/ctrld.privacy.toml"
        "/etc/controld/profiles/ctrld.gaming.toml"
    )
    
    local all_good=true
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            if sudo grep -q "ip = '0.0.0.0'" "$config_file"; then
                echo "  ✅ $config_file: Correct (0.0.0.0)"
            else
                echo "  ❌ $config_file: Still has 127.0.0.1"
                all_good=false
            fi
        fi
    done
    
    if $all_good; then
        echo "✅ All configuration files have correct binding"
        return 0
    else
        echo "❌ Some configuration files still need fixing"
        return 1
    fi
}

# Function to restart and verify Control D
restart_and_verify() {
    echo "🚀 Restarting Control D service..."
    
    # Restart with privacy profile
    sudo controld-manager switch privacy doh
    sleep 3
    
    # Check if it's binding to all interfaces
    if sudo lsof -nP -iTCP:53 | grep -q "\*:53"; then
        echo "✅ Control D is binding to all interfaces (*:53)"
        return 0
    else
        echo "❌ Control D is still binding to localhost only"
        return 1
    fi
}

# Function to test functionality
test_functionality() {
    echo "🧪 Testing DNS functionality..."
    
    # Test ad blocking
    local result
    result=$(dig @127.0.0.1 doubleclick.net +short 2>/dev/null | head -1)
    if [[ "$result" == "127.0.0.1" ]] || [[ "$result" == "" ]]; then
        echo "✅ Ad blocking working"
    else
        echo "⚠️ Ad blocking status unclear (result: $result)"
    fi
    
    # Test normal resolution
    if dig @127.0.0.1 google.com +short >/dev/null 2>&1; then
        echo "✅ Normal DNS resolution working"
    else
        echo "❌ DNS resolution failed"
        return 1
    fi
}

# Main execution
echo "1️⃣ Applying binding fix to all configuration files..."
fix_all_configs

echo ""
echo "2️⃣ Verifying all configurations..."
if ! verify_configs; then
    echo "❌ Configuration verification failed"
    exit 1
fi

echo ""
echo "3️⃣ Restarting Control D with corrected configuration..."
if ! restart_and_verify; then
    echo "❌ Control D restart/verification failed"
    exit 1
fi

echo ""
echo "4️⃣ Testing DNS functionality..."
test_functionality

echo ""
echo "🎉 Permanent binding fix completed successfully!"
echo ""
echo "📊 Current status:"
echo "Active config: $(sudo readlink /etc/controld/ctrld.toml)"
echo "Binding status:"
sudo lsof -nP -iTCP:53 2>/dev/null | grep ":53" || echo "No TCP binding found"
sudo lsof -nP -iUDP:53 2>/dev/null | grep ":53" || echo "No UDP binding found"
echo ""
echo "✅ Windscribe can now connect with 'Local DNS' setting!"
echo "📋 Next: Try connecting Windscribe VPN"
echo ""
echo "🛠️ If this reverts again, run:"
echo "   bash ~/Documents/dev/personal-config/windscribe-controld/permanent-binding-fix.sh"