#!/bin/bash

# Complete DNS/VPN Software Cleanup Script
# Removes Control D, Windscribe, AdGuard, and all related configurations
# Returns system to clean state

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

confirm_cleanup() {
    echo -e "${YELLOW}⚠️  COMPLETE CLEANUP WARNING ⚠️${NC}"
    echo
    echo "This script will remove ALL of the following:"
    echo "  • Control D (all services, configs, launch daemons)"
    echo "  • Windscribe VPN (app and configurations)"
    echo "  • AdGuard (if installed)"
    echo "  • All DNS overrides and custom configurations"
    echo "  • All related files and settings"
    echo
    echo "Your system will return to using default DNS (your ISP's DNS)."
    echo
    read -p "Are you absolutely sure you want to continue? (type 'YES' to confirm): " confirm
    
    if [ "$confirm" != "YES" ]; then
        echo "Cleanup cancelled."
        exit 0
    fi
}

stop_all_services() {
    print_status "Stopping all VPN/DNS services..."
    
    # Stop Control D services
    sudo pkill -f "ctrld" 2>/dev/null || true
    sudo pkill -f "dns-monitor" 2>/dev/null || true
    sudo pkill -f "controld" 2>/dev/null || true
    
    # Stop Windscribe
    sudo pkill -f "Windscribe" 2>/dev/null || true
    sudo pkill -f "windscribe" 2>/dev/null || true
    
    # Stop AdGuard
    sudo pkill -f "AdGuard" 2>/dev/null || true
    sudo pkill -f "adguard" 2>/dev/null || true
    
    print_success "Services stopped"
}

remove_launch_daemons() {
    print_status "Removing all VPN/DNS launch daemons..."
    
    # Control D daemons
    local controld_daemons=(
        "/Library/LaunchDaemons/com.controld.dns.plist"
        "/Library/LaunchDaemons/com.controld.dns.monitor.plist"
        "/Library/LaunchDaemons/ctrld.plist"
        "/Library/LaunchDaemons/com.controld.vpn.dns.plist"
    )
    
    for daemon in "${controld_daemons[@]}"; do
        if [ -f "$daemon" ]; then
            local daemon_name=$(basename "$daemon" .plist)
            sudo launchctl unload "$daemon" 2>/dev/null || true
            sudo launchctl remove "$daemon_name" 2>/dev/null || true
            sudo rm "$daemon"
            print_status "Removed $daemon_name"
        fi
    done
    
    # Windscribe daemons (if any)
    find /Library/LaunchDaemons -name "*windscribe*" -type f 2>/dev/null | while read daemon; do
        if [ -f "$daemon" ]; then
            local daemon_name=$(basename "$daemon" .plist)
            sudo launchctl unload "$daemon" 2>/dev/null || true
            sudo launchctl remove "$daemon_name" 2>/dev/null || true
            sudo rm "$daemon"
            print_status "Removed Windscribe daemon: $daemon_name"
        fi
    done
    
    # AdGuard daemons (if any)
    find /Library/LaunchDaemons -name "*adguard*" -type f 2>/dev/null | while read daemon; do
        if [ -f "$daemon" ]; then
            local daemon_name=$(basename "$daemon" .plist)
            sudo launchctl unload "$daemon" 2>/dev/null || true
            sudo launchctl remove "$daemon_name" 2>/dev/null || true
            sudo rm "$daemon"
            print_status "Removed AdGuard daemon: $daemon_name"
        fi
    done
    
    print_success "Launch daemons removed"
}

remove_applications() {
    print_status "Removing applications..."
    
    # Windscribe
    if [ -d "/Applications/Windscribe.app" ]; then
        sudo rm -rf "/Applications/Windscribe.app"
        print_status "Removed Windscribe app"
    fi
    
    # AdGuard
    if [ -d "/Applications/AdGuard for Safari.app" ]; then
        sudo rm -rf "/Applications/AdGuard for Safari.app"
        print_status "Removed AdGuard for Safari app"
    fi
    
    if [ -d "/Applications/AdGuard.app" ]; then
        sudo rm -rf "/Applications/AdGuard.app"
        print_status "Removed AdGuard app"
    fi
    
    print_success "Applications removed"
}

remove_configurations() {
    print_status "Removing all configurations and files..."
    
    # Control D
    if [ -d "/etc/controld" ]; then
        sudo rm -rf "/etc/controld"
        print_status "Removed Control D configurations"
    fi
    
    if [ -f "/usr/local/bin/ctrld" ]; then
        sudo rm "/usr/local/bin/ctrld"
        print_status "Removed Control D binary"
    fi
    
    if [ -f "/usr/local/bin/controld-manager" ]; then
        sudo rm "/usr/local/bin/controld-manager"
        print_status "Removed Control D manager"
    fi
    
    if [ -f "/usr/local/bin/dns-monitor" ]; then
        sudo rm "/usr/local/bin/dns-monitor"
        print_status "Removed DNS monitor"
    fi
    
    # DNS overrides
    if [ -f "/etc/resolver/controld" ]; then
        sudo rm "/etc/resolver/controld"
        print_status "Removed DNS resolver override"
    fi
    
    # User-specific configs
    rm -rf "$HOME/.config/windscribe" 2>/dev/null || true
    rm -rf "$HOME/.windscribe" 2>/dev/null || true
    rm -rf "$HOME/Library/Preferences/com.windscribe.*" 2>/dev/null || true
    rm -rf "$HOME/Library/Application Support/Windscribe" 2>/dev/null || true
    rm -rf "$HOME/Library/Application Support/AdGuard*" 2>/dev/null || true
    
    print_success "Configurations removed"
}

reset_dns_settings() {
    print_status "Resetting DNS to system defaults..."
    
    # Reset Wi-Fi DNS to automatic
    sudo networksetup -setdnsservers "Wi-Fi" "Empty" 2>/dev/null || true
    
    # Reset any other network services
    networksetup -listallnetworkservices | grep -v "An asterisk" | while read service; do
        if [ -n "$service" ] && [ "$service" != "Wi-Fi" ]; then
            sudo networksetup -setdnsservers "$service" "Empty" 2>/dev/null || true
        fi
    done
    
    # Flush DNS cache
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder 2>/dev/null || true
    
    print_success "DNS settings reset to defaults"
}

clean_logs() {
    print_status "Cleaning up log files..."
    
    # Control D logs
    sudo rm -f /var/log/ctrld*.log 2>/dev/null || true
    sudo rm -f /var/log/controld*.log 2>/dev/null || true
    sudo rm -f /var/log/dns_monitor*.log 2>/dev/null || true
    sudo rm -f /usr/local/var/log/ctrld*.log 2>/dev/null || true
    
    print_success "Log files cleaned"
}

verify_cleanup() {
    print_status "Verifying cleanup..."
    
    echo
    echo -e "${BLUE}=== Cleanup Verification ===${NC}"
    
    # Check for remaining processes
    remaining_processes=$(pgrep -f "ctrld|controld|windscribe|adguard" 2>/dev/null || true)
    if [ -z "$remaining_processes" ]; then
        echo "✅ No VPN/DNS processes running"
    else
        echo "⚠️  Some processes still running: $remaining_processes"
    fi
    
    # Check DNS settings
    current_dns=$(networksetup -getdnsservers "Wi-Fi" 2>/dev/null)
    if [[ "$current_dns" == *"There aren't any DNS Servers set"* ]]; then
        echo "✅ DNS reset to automatic (ISP default)"
    else
        echo "ℹ️  DNS servers: $current_dns"
    fi
    
    # Check for remaining config files
    if [ ! -d "/etc/controld" ] && [ ! -f "/etc/resolver/controld" ]; then
        echo "✅ Configuration files removed"
    else
        echo "⚠️  Some configuration files may remain"
    fi
    
    # Test basic internet connectivity
    if ping -c 1 google.com &> /dev/null; then
        echo "✅ Internet connectivity working"
    else
        echo "❌ Internet connectivity issues"
    fi
    
    print_success "Cleanup verification complete"
}

create_simple_solution_guide() {
    print_status "Creating simple solution guide..."
    
    cat > "$HOME/Desktop/SIMPLE_DNS_SOLUTIONS.md" << 'EOF'
# Simple DNS/Privacy Solutions

Your system is now clean and using default DNS. Here are some SIMPLE alternatives if you want basic privacy without complexity:

## Option 1: Browser-Only Privacy (EASIEST)
- Use **Firefox** with built-in tracking protection
- Install **uBlock Origin** extension
- Enable **DNS over HTTPS** in Firefox settings
- No system-level changes needed!

## Option 2: Simple DNS Change (EASY)
Change your DNS to a privacy-focused service:

### Cloudflare DNS (Fast + Some Privacy)
```bash
sudo networksetup -setdnsservers "Wi-Fi" 1.1.1.1 1.0.0.1
```

### Quad9 DNS (Security + Privacy)  
```bash
sudo networksetup -setdnsservers "Wi-Fi" 9.9.9.9 149.112.112.112
```

### To Revert to Automatic:
```bash
sudo networksetup -setdnsservers "Wi-Fi" "Empty"
```

## Option 3: VPN Only (NO DNS Complexity)
- Use a simple VPN like **ProtonVPN** or **Mullvad**
- Let the VPN handle DNS automatically
- No custom configurations needed

## Option 4: Router-Level (SET AND FORGET)
- Change DNS settings on your router once
- Affects all devices automatically
- No per-device configuration needed

## Current Status
✅ System is clean and working
✅ Using your ISP's default DNS
✅ No conflicting services
✅ Normal internet browsing works

**Remember: Perfect privacy isn't worth constant frustration. Sometimes "good enough" is actually perfect.**
EOF
    
    print_success "Simple solutions guide created on Desktop"
}

show_summary() {
    echo
    echo -e "${GREEN}🎉 COMPLETE CLEANUP FINISHED! 🎉${NC}"
    echo
    echo "What was removed:"
    echo "  ✅ All Control D services and configurations"
    echo "  ✅ Windscribe VPN application"  
    echo "  ✅ AdGuard applications"
    echo "  ✅ All launch daemons and background services"
    echo "  ✅ All DNS overrides and custom configurations"
    echo "  ✅ All log files and temporary data"
    echo
    echo "Your system now:"
    echo "  ✅ Uses your ISP's default DNS (simple and reliable)"
    echo "  ✅ Has normal internet browsing with no conflicts"
    echo "  ✅ Is completely clean of problematic software"
    echo
    echo -e "${BLUE}📋 Next steps (optional):${NC}"
    echo "  • Check the simple solutions guide on your Desktop"
    echo "  • Restart your Mac for a completely fresh start"
    echo "  • Enjoy conflict-free internet browsing!"
    echo
    echo -e "${YELLOW}💡 Remember: Sometimes the best solution is the simplest one.${NC}"
}

# Main cleanup process
confirm_cleanup
print_status "Starting complete cleanup process..."

stop_all_services
remove_launch_daemons  
remove_applications
remove_configurations
reset_dns_settings
clean_logs
verify_cleanup
create_simple_solution_guide
show_summary