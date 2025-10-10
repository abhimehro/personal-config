#!/usr/bin/env bash
#
# Control D DNS Configuration Enforcement Script
# Ensures Control D DNS settings are properly configured on macOS
#
# Usage: bash controld-ensure.sh
# Auto-runs via LaunchAgent at login
#
# Last Updated: October 10, 2025
# Status: Active and working

set -euo pipefail

# Configuration
SERVICES=("Wi-Fi" "USB 10/100/1000 LAN")
CONTROL_D_DNS="127.0.0.1"
LOG_FILE="$HOME/Library/Logs/controld-ensure.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Check if Control D is running
check_controld_status() {
    if sudo lsof -i :53 2>/dev/null | grep -q ctrld; then
        log "✅ Control D (ctrld) is running and listening on port 53"
        return 0
    else
        log "❌ Control D (ctrld) is not running on port 53"
        return 1
    fi
}

# Configure DNS for network services
configure_dns() {
    log "🔧 Configuring DNS settings for network services..."
    
    for service in "${SERVICES[@]}"; do
        log "Setting DNS for: $service"
        if sudo networksetup -setdnsservers "$service" "$CONTROL_D_DNS" 2>/dev/null; then
            log "✅ DNS configured for $service"
        else
            log "⚠️  Failed to configure DNS for $service (may not be available)"
        fi
    done
}

# Set network service order
set_service_order() {
    log "🔧 Setting network service priority order..."
    if networksetup -ordernetworkservices "USB 10/100/1000 LAN" "Wi-Fi" "Thunderbolt Bridge" "Bluetooth PAN" 2>/dev/null; then
        log "✅ Network service order configured"
    else
        log "⚠️  Could not set network service order (some services may not exist)"
    fi
}

# Flush DNS caches
flush_dns() {
    log "🔄 Flushing DNS caches..."
    if sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder 2>/dev/null; then
        log "✅ DNS caches flushed"
    else
        log "⚠️  DNS cache flush may have failed"
    fi
}

# Validate DNS configuration
validate_dns() {
    log "🧪 Validating DNS configuration..."
    
    # Test Control D DNS resolution
    if dig +timeout=3 +tries=1 +short verify.controld.com @"$CONTROL_D_DNS" >/dev/null 2>&1; then
        log "✅ Control D DNS resolution working"
    else
        log "❌ Control D DNS resolution failed"
        return 1
    fi
    
    # Test system DNS resolution
    if dig +timeout=3 +tries=1 +short google.com >/dev/null 2>&1; then
        log "✅ System DNS resolution working"
    else
        log "❌ System DNS resolution failed"
        return 1
    fi
    
    return 0
}

# Main execution
main() {
    log "🚀 Starting Control D DNS configuration enforcement..."
    
    # Check if running with appropriate permissions
    if [[ $EUID -eq 0 ]]; then
        log "❌ Do not run this script as root. It will prompt for sudo when needed."
        exit 1
    fi
    
    # Wait a moment for system to stabilize (useful at login)
    sleep 2
    
    # Check if Control D is running
    if ! check_controld_status; then
        log "⚠️  Control D not detected. Configuration will be applied anyway."
        log "💡 Make sure Control D app is running and configured for DoH protocol."
    fi
    
    # Configure DNS settings
    configure_dns
    
    # Set service order
    set_service_order
    
    # Flush DNS caches
    flush_dns
    
    # Wait for changes to take effect
    sleep 3
    
    # Validate configuration
    if validate_dns; then
        log "🎉 Control D DNS configuration successful!"
        log "📊 Verify at: https://verify.controld.com"
    else
        log "❌ DNS configuration validation failed"
        log "🔧 Manual troubleshooting may be required"
        exit 1
    fi
    
    log "✅ Control D DNS enforcement completed successfully"
}

# Run main function
main "$@"