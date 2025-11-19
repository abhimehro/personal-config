#!/usr/bin/env bash
#
# Control D DNS Configuration Enforcement Script (Separation Strategy aware)
# Ensures that when Control D mode is active, the network state remains
# consistent. This script now delegates to the unified network-mode-manager
# rather than directly forcing DNS/IPv4/IPv6, to avoid fighting Windscribe.
#
# Usage: bash controld-ensure.sh
# Auto-runs via LaunchAgent at login
#
# Last Updated: Phase 1 Separation Strategy

set -euo pipefail

LOG_FILE="$HOME/Library/Logs/controld-ensure.log"
MANAGER_SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/scripts/network-mode-manager.sh"
VERIFY_SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/scripts/network-mode-verify.sh"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

main() {
    log "🚀 Starting Control D DNS enforcement (Separation Strategy)..."

    if [[ $EUID -eq 0 ]]; then
        log "❌ Do not run this script as root. It will prompt for sudo when needed."
        exit 1
    fi

    if [[ ! -x "$MANAGER_SCRIPT" ]]; then
        log "❌ network-mode-manager.sh not found or not executable at $MANAGER_SCRIPT"
        exit 1
    fi

    if [[ ! -x "$VERIFY_SCRIPT" ]]; then
        log "❌ network-mode-verify.sh not found or not executable at $VERIFY_SCRIPT"
        exit 1
    fi

    # Give the system a moment to stabilize at login
    sleep 2

    # Ensure Control D DNS mode is active using the default browsing profile
    log "🔧 Ensuring Control D DNS mode is active (browsing profile)..."
    "$MANAGER_SCRIPT" controld browsing || log "⚠️  Manager reported issues switching to Control D mode."

    # Run verification for CONTROL D ACTIVE state
    log "🧪 Running Control D verification..."
    if "$VERIFY_SCRIPT" controld; then
        log "🎉 Control D DNS configuration verified successfully."
        log "📊 You can also verify via: https://verify.controld.com"
        exit 0
    else
        log "❌ Control D DNS verification failed. Manual troubleshooting may be required."
        exit 1
    fi
}

main "$@"
    log "🔧 Setting network service priority order..."
    
    # Get actual available services (excluding disabled ones)
    local available_services=()
    while IFS= read -r service; do
        # Skip header line and disabled services (marked with *)
        if [[ "$service" != "An asterisk"* && "$service" != *"*"* && -n "$service" ]]; then
            available_services+=("$service")
        fi
    done < <(networksetup -listallnetworkservices)
    
    # Only set order if we have multiple services
    if [[ ${#available_services[@]} -gt 1 ]]; then
        if networksetup -ordernetworkservices "${available_services[@]}" 2>/dev/null; then
            log "✅ Network service order configured: ${available_services[*]}"
        else
            log "ℹ️  Network service order unchanged (current order is fine)"
        fi
    else
        log "ℹ️  Only one network service available, order setting not needed"
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