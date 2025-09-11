#!/usr/bin/env bash
# DNS Common Utilities Library
# Shared functions for safe DNS profile switching
# Generated: 2025-09-11

set -Eeuo pipefail

# Configuration
readonly CTRLD_CONFIG="/usr/local/etc/ctrld/ctrld.yaml"
readonly CTRLD_SERVICE="com.controld.ctrld"
readonly LOCK_FILE="/tmp/ctrld-switch.lock"
readonly LOCK_FD=200
readonly DNS_TIMEOUT=5
readonly MAX_RETRIES=3
readonly RETRY_DELAY=2

# Logging
log() { 
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" 
}

error() { 
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2 
}

die() { 
    error "$*"
    exit 1 
}

# Lock management
acquire_lock() {
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        die "Another DNS switching operation is in progress. Wait and try again."
    fi
}

release_lock() {
    flock -u 200 2>/dev/null || true
}

# Cleanup on exit
cleanup() {
    release_lock
    exit "${1:-1}"
}
trap 'cleanup $?' EXIT INT TERM

# Root permission check
require_root() {
    if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
        die "This script requires root privileges. Run with sudo."
    fi
}

# Port verification
check_port_53() {
    local pids listening_procs
    
    # Check UDP port 53
    pids=$(lsof -nP -iUDP:53 -t 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        listening_procs=$(ps -o pid,comm,args -p $pids 2>/dev/null || true)
        
        # Check if it's ctrld or something else
        if echo "$listening_procs" | grep -q ctrld; then
            log "✅ ctrld is properly bound to UDP port 53"
            return 0
        else
            error "❌ Port 53 is occupied by non-ctrld process:"
            echo "$listening_procs" >&2
            return 1
        fi
    fi
    
    # Check TCP port 53 (less common for DNS but important)
    pids=$(lsof -nP -iTCP:53 -sTCP:LISTEN -t 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        listening_procs=$(ps -o pid,comm,args -p $pids 2>/dev/null || true)
        if ! echo "$listening_procs" | grep -q ctrld; then
            error "❌ TCP Port 53 occupied by non-ctrld process:"
            echo "$listening_procs" >&2
            return 1
        fi
    fi
    
    log "⚠️  No process bound to port 53"
    return 1
}

# VPN detection
detect_active_vpn() {
    local vpn_interfaces vpn_dns
    
    # Check for VPN interfaces
    vpn_interfaces=$(ifconfig 2>/dev/null | grep -E '^(utun|tun|wg)[0-9]+:' | cut -d: -f1 || true)
    if [[ -n "$vpn_interfaces" ]]; then
        log "🔍 VPN interfaces detected: $vpn_interfaces"
        
        # Check if VPN has DNS scoped
        vpn_dns=$(scutil --dns | grep -A5 "scoped queries" | grep -E "utun|tun|wg" || true)
        if [[ -n "$vpn_dns" ]]; then
            log "⚠️  VPN DNS scoping detected - VPN is managing DNS resolution"
            return 0
        fi
    fi
    
    # Check for common VPN processes
    local vpn_procs
    vpn_procs=$(ps aux | grep -E "(Windscribe|ProtonVPN|nordvpn|expressvpn)" | grep -v grep || true)
    if [[ -n "$vpn_procs" ]]; then
        log "🔍 VPN processes detected:"
        echo "$vpn_procs" | sed 's/^/    /' 
        return 0
    fi
    
    return 1
}

# DNS validation
validate_dns_resolution() {
    local server="$1"
    local test_domain="example.com"
    local result timeout_cmd
    
    log "🔍 Testing DNS resolution via $server..."
    
    # Use timeout command for better control
    if command -v timeout >/dev/null 2>&1; then
        timeout_cmd="timeout ${DNS_TIMEOUT}"
    elif command -v gtimeout >/dev/null 2>&1; then
        timeout_cmd="gtimeout ${DNS_TIMEOUT}"
    else
        timeout_cmd=""
    fi
    
    local output
    output=$($timeout_cmd dig +short +tries=1 +time=${DNS_TIMEOUT} "$test_domain" @"$server" 2>/dev/null)
    if [[ $? -eq 0 && -n "$output" ]]; then
        log "✅ DNS resolution working via $server (got: $(echo "$output" | head -1))"
        return 0
    fi
    
    error "❌ DNS resolution failed via $server"
    return 1
}

# System DNS configuration
get_primary_network_service() {
    local services primary_service
    
    services=$(networksetup -listallnetworkservices 2>/dev/null | tail -n +2 | grep -v "^*")
    
    # Prefer Wi-Fi, then Ethernet variants
    while IFS= read -r service; do
        if [[ "$service" =~ Wi-Fi ]]; then
            echo "$service"
            return 0
        fi
    done <<< "$services"
    
    while IFS= read -r service; do
        if [[ "$service" =~ (Ethernet|LAN|USB.*LAN) ]]; then
            echo "$service"
            return 0
        fi
    done <<< "$services"
    
    # Fallback to first non-VPN service
    while IFS= read -r service; do
        if ! [[ "$service" =~ (VPN|Windscribe|Proton|Tailscale|ZeroTier) ]]; then
            echo "$service"
            return 0
        fi
    done <<< "$services"
    
    die "No suitable primary network service found"
}

# Set system DNS
set_system_dns() {
    local dns_servers=("$@")
    local primary_service
    
    primary_service=$(get_primary_network_service)
    log "🔧 Setting DNS for '$primary_service' to: ${dns_servers[*]}"
    
    if networksetup -setdnsservers "$primary_service" "${dns_servers[@]}" 2>/dev/null; then
        log "✅ DNS configured successfully"
        return 0
    else
        error "❌ Failed to set DNS servers"
        return 1
    fi
}

# Reset system DNS to automatic
reset_system_dns() {
    local primary_service
    
    primary_service=$(get_primary_network_service)
    log "🔧 Resetting DNS for '$primary_service' to automatic"
    
    if networksetup -setdnsservers "$primary_service" "Empty" 2>/dev/null; then
        log "✅ DNS reset to automatic"
        return 0
    else
        error "❌ Failed to reset DNS"
        return 1
    fi
}

# Flush DNS caches
flush_dns_cache() {
    log "🔄 Flushing DNS caches..."
    
    dscacheutil -flushcache 2>/dev/null || true
    killall -HUP mDNSResponder 2>/dev/null || true
    killall mDNSResponderHelper 2>/dev/null 2>&1 || true
    
    log "✅ DNS caches flushed"
}

# Service management
is_service_running() {
    launchctl list "$CTRLD_SERVICE" >/dev/null 2>&1
}

wait_for_service() {
    local max_wait=30
    local count=0
    
    log "⏳ Waiting for ctrld service to be ready..."
    
    while [[ $count -lt $max_wait ]]; do
        if is_service_running && check_port_53; then
            log "✅ ctrld service is ready"
            return 0
        fi
        
        sleep 1
        ((count++))
    done
    
    error "❌ Timeout waiting for ctrld service"
    return 1
}

restart_ctrld_service() {
    log "🔄 Restarting ctrld service..."
    
    # Stop service if running
    if is_service_running; then
        launchctl kickstart -k "system/$CTRLD_SERVICE" 2>/dev/null || true
        sleep 2
    fi
    
    # Start service
    if ! launchctl bootstrap system "/Library/LaunchDaemons/${CTRLD_SERVICE}.plist" 2>/dev/null; then
        # Already loaded, just restart
        launchctl kickstart -k "system/$CTRLD_SERVICE" || {
            error "Failed to restart ctrld service"
            return 1
        }
    fi
    
    # Wait for service to be ready
    wait_for_service
}

# Profile switching
switch_ctrld_profile() {
    local profile="$1"
    local config_temp
    
    log "🔄 Switching ctrld to profile: $profile"
    
    # Update profile in config
    config_temp=$(mktemp)
    if sed "s/current_profile: \"[^\"]*\"/current_profile: \"$profile\"/" "$CTRLD_CONFIG" > "$config_temp"; then
        sudo mv "$config_temp" "$CTRLD_CONFIG"
    else
        rm -f "$config_temp"
        error "Failed to update configuration"
        return 1
    fi
    
    # Restart service with new profile
    restart_ctrld_service
}

# Comprehensive verification
verify_dns_setup() {
    local expected_profile="$1"
    
    log "🔍 Verifying DNS setup for profile: $expected_profile"
    
    # Check service is running
    if ! is_service_running; then
        error "❌ ctrld service is not running"
        return 1
    fi
    
    # Check port binding
    if ! check_port_53; then
        error "❌ ctrld not properly bound to port 53"
        return 1
    fi
    
    # Test DNS resolution
    if ! validate_dns_resolution "127.0.0.1"; then
        error "❌ DNS resolution test failed"
        return 1
    fi
    
    # Check system DNS configuration
    local dns_config
    dns_config=$(scutil --dns | grep "nameserver\[0\]" | head -1)
    if [[ "$dns_config" != *"127.0.0.1"* ]]; then
        error "❌ System DNS not pointing to 127.0.0.1"
        return 1
    fi
    
    log "✅ DNS setup verified successfully"
    return 0
}

# Emergency rollback
emergency_rollback() {
    local reason="$1"
    
    error "🚨 EMERGENCY ROLLBACK: $reason"
    
    # Stop ctrld service
    launchctl bootout "system/$CTRLD_SERVICE" 2>/dev/null || true
    
    # Reset DNS to automatic
    reset_system_dns
    
    # Flush caches
    flush_dns_cache
    
    # Wait a moment for changes to propagate
    sleep 2
    
    # Test basic DNS
    if validate_dns_resolution "8.8.8.8"; then
        log "✅ Emergency rollback successful - DNS working via system resolvers"
    else
        error "❌ Emergency rollback failed - manual intervention required"
        error "    Try: sudo networksetup -setdnsservers Wi-Fi 8.8.8.8 1.1.1.1"
    fi
}

# Preflight checks
run_preflight_checks() {
    local profile="$1"
    local skip_vpn_check="${2:-false}"
    
    log "🔍 Running preflight checks for profile: $profile"
    
    # Check root permissions
    require_root
    
    # Acquire lock
    acquire_lock
    
    # Check if ctrld binary exists
    if ! command -v ctrld >/dev/null 2>&1; then
        die "❌ ctrld binary not found. Please install Control D first."
    fi
    
    # Check configuration file
    if [[ ! -f "$CTRLD_CONFIG" ]]; then
        die "❌ Configuration file not found: $CTRLD_CONFIG"
    fi
    
    # Check VPN conflicts (unless in VPN mode)
    if [[ "$skip_vpn_check" != "true" ]] && detect_active_vpn; then
        error "❌ Active VPN detected. VPN may conflict with ctrld on port 53."
        error "    Consider using 'dns-gaming-vpn' mode instead, or disable VPN DNS features."
        return 1
    fi
    
    log "✅ Preflight checks passed"
    return 0
}

# Export functions for use in other scripts
export -f log error die
export -f acquire_lock release_lock cleanup
export -f require_root check_port_53 detect_active_vpn
export -f validate_dns_resolution get_primary_network_service
export -f set_system_dns reset_system_dns flush_dns_cache
export -f is_service_running wait_for_service restart_ctrld_service
export -f switch_ctrld_profile verify_dns_setup emergency_rollback
export -f run_preflight_checks
