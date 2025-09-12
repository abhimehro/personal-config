#!/bin/bash
# Emergency DNS Recovery Script - Control D DNS Switcher
# Version: 3.0.0
# Purpose: Complete DNS recovery and system restoration

set -euo pipefail

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log_emergency() {
    echo -e "${RED}🚨 EMERGENCY:${NC} $1" >&2
    logger -t "controld-emergency" "$1"
}

log_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
    logger -t "controld-emergency" "$1"
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS:${NC} $1"
    logger -t "controld-emergency" "$1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
    logger -t "controld-emergency" "$1"
}

# Emergency DNS Recovery Function
emergency_dns_recovery() {
    log_emergency "INITIATING EMERGENCY DNS RECOVERY"
    
    echo "🚨 EMERGENCY DNS RECOVERY PROCEDURE"
    echo "=================================="
    echo
    
    # Step 1: Stop Control D services
    log_info "Step 1: Stopping Control D services..."
    if sudo launchctl list | grep -q "com.controld.ctrld"; then
        sudo launchctl stop com.controld.ctrld 2>/dev/null || true
        sudo launchctl unload /Library/LaunchDaemons/com.controld.ctrld.plist 2>/dev/null || true
        log_success "Control D service stopped"
    else
        log_info "Control D service not running"
    fi
    
    # Step 2: Reset DNS to system defaults
    log_info "Step 2: Resetting DNS to system defaults..."
    
    # Get all network services
    network_services=$(networksetup -listallnetworkservices | grep -v "An asterisk")
    
    # Reset DNS for each service
    while IFS= read -r service; do
        if [[ -n "$service" && "$service" != "An asterisk"* ]]; then
            log_info "Resetting DNS for: $service"
            sudo networksetup -setdnsservers "$service" Empty 2>/dev/null || true
        fi
    done <<< "$network_services"
    
    log_success "DNS reset to system defaults for all network services"
    
    # Step 3: Clear all DNS caches
    log_info "Step 3: Clearing all DNS caches..."
    
    # Clear system DNS cache
    sudo dscacheutil -flushcache 2>/dev/null || true
    
    # Restart mDNSResponder
    sudo killall -HUP mDNSResponder 2>/dev/null || true
    
    # Additional cache clearing for different macOS versions
    if command -v sudo >/dev/null; then
        # macOS 10.10.4+
        sudo killall -HUP mDNSResponder 2>/dev/null || true
        sudo killall mDNSResponderHelper 2>/dev/null || true
        
        # Clear additional caches
        sudo dscacheutil -flushcache 2>/dev/null || true
    fi
    
    log_success "DNS caches cleared"
    
    # Step 4: Remove Control D configurations
    log_info "Step 4: Cleaning up Control D configurations..."
    
    # Remove LaunchDaemon
    if [[ -f "/Library/LaunchDaemons/com.controld.ctrld.plist" ]]; then
        sudo rm -f /Library/LaunchDaemons/com.controld.ctrld.plist
        log_success "Removed LaunchDaemon configuration"
    fi
    
    # Remove Control D binary
    if [[ -f "/usr/local/bin/ctrld" ]]; then
        sudo rm -f /usr/local/bin/ctrld
        log_success "Removed Control D binary"
    fi
    
    # Clean up runtime files
    if [[ -d "/var/run/ctrld-switcher" ]]; then
        sudo rm -rf /var/run/ctrld-switcher
        log_success "Removed runtime state files"
    fi
    
    # Step 5: Verify DNS resolution
    log_info "Step 5: Testing DNS resolution..."
    
    # Test DNS resolution with multiple domains
    test_domains=("google.com" "apple.com" "cloudflare.com")
    working_count=0
    
    for domain in "${test_domains[@]}"; do
        if nslookup "$domain" >/dev/null 2>&1; then
            working_count=$((working_count + 1))
            log_success "DNS resolution working for $domain"
        else
            log_warning "DNS resolution failed for $domain"
        fi
    done
    
    if [[ $working_count -gt 0 ]]; then
        log_success "DNS resolution restored (${working_count}/${#test_domains[@]} domains working)"
    else
        log_emergency "DNS resolution still not working - may require manual intervention"
    fi
    
    # Step 6: Final system status
    log_info "Step 6: Displaying final system status..."
    
    echo
    echo "📊 FINAL SYSTEM STATUS"
    echo "====================="
    
    # Show current DNS servers
    echo "🌐 Current DNS Configuration:"
    for service in "Wi-Fi" "Ethernet"; do
        if networksetup -listallnetworkservices | grep -q "$service"; then
            dns_servers=$(networksetup -getdnsservers "$service" 2>/dev/null || echo "System Default")
            echo "  $service: $dns_servers"
        fi
    done
    
    # Show network connectivity
    echo
    echo "🔍 Network Connectivity Test:"
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_success "Internet connectivity: WORKING"
    else
        log_warning "Internet connectivity: FAILED"
    fi
    
    echo
    log_success "EMERGENCY DNS RECOVERY COMPLETED"
    echo
    echo "🎯 NEXT STEPS:"
    echo "  1. Test your internet browsing in a web browser"
    echo "  2. If issues persist, restart your network adapter or reboot"
    echo "  3. To reinstall Control D, run the installation script again"
    echo
}

# Main execution
main() {
    # Check if running as root for some operations
    if [[ $EUID -ne 0 && "$1" != "--help" ]]; then
        echo "This script requires sudo privileges for DNS configuration changes."
        echo "Please run: sudo $0"
        exit 1
    fi
    
    # Handle help option
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        cat << 'EOF'
🚨 Emergency DNS Recovery Script

USAGE:
    sudo ./emergency-recovery.sh

DESCRIPTION:
    This script performs complete DNS emergency recovery by:
    
    1. Stopping all Control D services
    2. Resetting DNS to system defaults for all network services
    3. Clearing all DNS caches (system and mDNSResponder)
    4. Removing Control D configurations and binaries
    5. Testing DNS resolution with multiple domains
    6. Displaying final system status and next steps
    
    This script is safe to run multiple times and will restore your
    system to working DNS resolution using system defaults.

WHEN TO USE:
    - DNS resolution is completely broken
    - Control D service is malfunctioning
    - Need to completely reset DNS configuration
    - Emergency network recovery situation

SAFETY:
    This script only resets to system defaults and does not make
    any permanent system changes beyond removing Control D.

EOF
        exit 0
    fi
    
    # Confirm emergency recovery
    echo -e "${YELLOW}⚠️  WARNING: Emergency DNS Recovery${NC}"
    echo "This will:"
    echo "  • Stop Control D services"
    echo "  • Reset DNS to system defaults"
    echo "  • Remove Control D configurations"
    echo "  • Clear all DNS caches"
    echo
    read -p "Continue with emergency recovery? [y/N]: " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        emergency_dns_recovery
    else
        echo "Emergency recovery cancelled."
        exit 0
    fi
}

# Execute main function with all arguments
main "$@"