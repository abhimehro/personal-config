#!/bin/bash

# Control D Service Monitor
# Designed to integrate with existing maintenance system
# Performs lightweight health check and logs results

set -e

# Configuration
LOG_DIR="${HOME}/Public/Scripts"
LOG_FILE="${LOG_DIR}/controld_monitor.log"
ERROR_LOG="${LOG_DIR}/controld_monitor_error.log"
MAX_LOG_SIZE=1048576  # 1MB

# Source common functions if available
if [ -f "${HOME}/Public/Scripts/maintenance/common.sh" ]; then
    source "${HOME}/Public/Scripts/maintenance/common.sh"
fi

# Logging function
# Optimization: Use printf built-in for timestamp to avoid subshell overhead of $(date)
log() {
    printf "[%(%Y-%m-%d %H:%M:%S)T] %s\n" -1 "$1" | tee -a "$LOG_FILE"
}

log_error() {
    printf "[%(%Y-%m-%d %H:%M:%S)T] ERROR: %s\n" -1 "$1" | tee -a "$ERROR_LOG"
}

# Rotate logs if too large
rotate_log() {
    local file="$1"
    if [ -f "$file" ] && [ $(stat -f%z "$file") -gt $MAX_LOG_SIZE ]; then
        mv "$file" "${file}.old"
        touch "$file"
    fi
}

# Check 1: Service status
check_service() {
    if sudo ctrld service status &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Check 2: DNS resolution
check_dns() {
    if dig @127.0.0.1 example.com +short +timeout=5 &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Check 3: Upstream connectivity (check for "marked as down" in recent logs)
check_upstream() {
    if sudo tail -30 /var/log/ctrld.log 2>/dev/null | grep -q "marked as down"; then
        return 1
    else
        return 0
    fi
}

# Check 4: Detect split-horizon DNS (multiple active resolvers)
check_split_dns() {
    # Get unique DNS servers from system config
    local dns_count=$(scutil --dns 2>/dev/null | grep "nameserver\[0\]" | awk '{print $3}' | sort -u | wc -l | tr -d ' ')
    
    # If more than 2 unique DNS servers and Control D is running, might be split-horizon
    # (Allow 2: one for Control D 127.0.0.1, one fallback)
    if [ "$dns_count" -gt 2 ]; then
        return 1
    else
        return 0
    fi
}

# Check 5: Verify Control D is the primary resolver
check_primary_resolver() {
    # Check if 127.0.0.1 appears as a nameserver OR if DNS resolution works locally
    if scutil --dns 2>/dev/null | grep -q "nameserver.*127\.0\.0\.1"; then
        return 0
    # If Control D isn't in scutil (macOS caching issue), but DNS works, that's OK
    elif dig @127.0.0.1 example.com +short +timeout=2 &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Check 6: Detect stale mDNSResponder cache
check_mdns_cache() {
    # Test with a timestamp-based query to ensure fresh resolution
    local test_domain="test-$(date +%s).example.com"
    
    # This should fail fast (NXDOMAIN) if cache is healthy
    # If it hangs, cache might be stuck
    if timeout 3 dig @127.0.0.1 "$test_domain" +short &>/dev/null; then
        return 0
    else
        # Timeout or error - might indicate cache issues
        return 1
    fi
}

# Check 7: Verify listener configuration (must be * or 0.0.0.0 for VPN)
check_listener() {
    if sudo lsof -nP -iTCP:53 2>/dev/null | grep ctrld | grep -qE "\*:53|0\.0\.0\.0:53"; then
        return 0
    else
        return 1
    fi
}

# Check 8: Verify filtering based on active profile
get_active_profile() {
    if sudo test -L "/etc/controld/ctrld.toml"; then
        local link_target
        link_target=$(sudo readlink "/etc/controld/ctrld.toml")
        # Bolt optimization: Use parameter expansion instead of basename|sed pipeline
        local filename="${link_target##*/}"
        if [[ "$filename" =~ ^ctrld\..*\.toml$ ]]; then
            local profile="${filename#ctrld.}"
            echo "${profile%.toml}"
        else
            echo "$filename"
        fi
    else
        echo "unknown"
    fi
}

check_filtering() {
    local profile=$(get_active_profile)
    # Check for blocking (expecting NXDOMAIN/empty result for blocked domains)
    local block_test=$(dig @********* doubleclick.net +short 2>/dev/null | wc -l)
    
    # If we can't determine profile, skip strict validation but log it
    if [ "$profile" == "unknown" ]; then
        return 0
    fi
    
    if [ "$profile" == "gaming" ]; then
        # Gaming profile: Ads might NOT be blocked (latency priority)
        return 0
    else
        # Privacy/Browsing profiles: Ads SHOULD be blocked (NXDOMAIN or *******)
        # If wc -l > 0, it means we got a result (IP), so blocking failed
        if [ "$block_test" -gt 0 ]; then
            return 1
        else
            return 0
        fi
    fi
}

# Check 9: Ensure active profile config is using DoH3-only upstreams
check_doh3_enforced() {
    if ! sudo test -L "/etc/controld/ctrld.toml"; then
        # If we can't see the symlink, we can't make a strong statement.
        return 0
    fi

    local link_target
    link_target=$(sudo readlink "/etc/controld/ctrld.toml" 2>/dev/null || true)
    if [ -z "$link_target" ] || [ ! -f "$link_target" ]; then
        return 0
    fi

    # Look for any upstream type declarations and ensure they are all doh3.
    local doh_types
    doh_types=$(grep -E "^\s*type = 'doh" "$link_target" 2>/dev/null || true)
    if [ -z "$doh_types" ]; then
        # No explicit types found; treat as unknown but not fatal.
        return 0
    fi

    # If any plain doh entries remain, treat as a failure for DoH3 enforcement.
    if echo "$doh_types" | grep -q "type = 'doh'"; then
        return 1
    fi

    return 0
}

# Main monitoring function
monitor_controld() {
    rotate_log "$LOG_FILE"
    rotate_log "$ERROR_LOG"
    
    log "=== Control D Health Monitor ==="
    
    local all_checks_passed=true
    
    # Service status check
    if check_service; then
        log "✓ Service is running"
    else
        log_error "Service is not running"
        log_error "Attempting automatic restart..."
        
        if sudo ctrld service start --config /etc/controld/ctrld.toml --skip_self_checks &>/dev/null; then
            log "✓ Service restarted successfully"
        else
            log_error "Failed to restart service - manual intervention required"
            all_checks_passed=false
        fi
    fi
    
    # Listener check
    if check_listener; then
        log "✓ Listener configured correctly (all interfaces)"
    else
        log_error "Listener not binding to all interfaces - VPN integration may be broken"
        log_error "Run: sudo ~/Documents/dev/personal-config/windscribe-controld/fix-controld-config.sh"
        all_checks_passed=false
    fi

    # DNS resolution check
    if check_dns; then
        log "✓ DNS resolution working"
    else
        log_error "DNS resolution failed"
        all_checks_passed=false
    fi
    
    # Upstream connectivity check
    if check_upstream; then
        log "✓ Upstream connectivity healthy"
    else
        log_error "Upstream marked as down - may recover automatically"
        # Don't mark as failed - upstreams can recover
    fi

    # Filtering check
    if check_filtering; then
        log "✓ Filtering active for profile: $(get_active_profile)"
    else
        log_error "Filtering check failed for profile: $(get_active_profile)"
        log_error "Ads are resolving when they should be blocked"
        all_checks_passed=false
    fi

    # DoH3 enforcement check (config-level)
    if check_doh3_enforced; then
        log "✓ Active Control D profile config is using DoH3-only upstreams"
    else
        log_error "Active Control D profile config is not strictly DoH3-only; legacy DoH/TCP upstreams detected"
        all_checks_passed=false
    fi
    
    # Network transition checks (only if service is running)
    local service_running=false
    if check_service; then
        service_running=true
    fi
    
    if [ "$service_running" = true ]; then
        # Check for split-horizon DNS
        if check_split_dns; then
            log "✓ No split-horizon DNS detected"
        else
            log_error "Multiple DNS resolvers detected (split-horizon)"
            log_error "Flushing DNS cache to recover..."
            sudo dscacheutil -flushcache 2>/dev/null
            sudo killall -HUP mDNSResponder 2>/dev/null
            sleep 2
            # Recheck
            if check_split_dns; then
                log "✓ Split-horizon resolved after cache flush"
            else
                log_error "Split-horizon persists - manual intervention may be needed"
                all_checks_passed=false
            fi
        fi
        
        # Check Control D is primary resolver
        if check_primary_resolver; then
            log "✓ Control D is primary resolver"
        else
            log_error "Control D not found as primary resolver"
            log_error "System may be using fallback DNS"
            all_checks_passed=false
        fi
        
        # Check mDNS cache health
        if check_mdns_cache; then
            log "✓ mDNS cache responding normally"
        else
            log_error "mDNS cache may be stale or hung"
            log_error "Flushing DNS cache..."
            sudo dscacheutil -flushcache 2>/dev/null
            sudo killall -HUP mDNSResponder 2>/dev/null
            log "✓ Cache flushed"
        fi
    fi
    
    # Summary
    if [ "$all_checks_passed" = true ]; then
        log "Status: HEALTHY"
        return 0
    else
        log_error "Status: UNHEALTHY - check error log for details"
        return 1
    fi
}

# Run monitoring
monitor_controld
exit_code=$?

# If monitoring failed, output instructions
if [ $exit_code -ne 0 ]; then
    log ""
    log "Troubleshooting steps:"
    log "1. Check service: sudo ctrld service status"
    log "2. Check logs: sudo tail -20 /var/log/ctrld.log"
    log "3. Run full health check: ~/Documents/dev/personal-config/maintenance/bin/health_check.sh"
    log "4. See break-glass guide: ~/Documents/dev/personal-config/windscribe-controld/TROUBLESHOOTING.md"
fi

exit $exit_code
