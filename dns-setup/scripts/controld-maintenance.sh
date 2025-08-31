#!/bin/bash
# Control D DNS Maintenance Suite
# Created: 2025-08-30
# Purpose: Regular maintenance, monitoring, and optimization

set -euo pipefail

require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Required command not found: $cmd" >&2
        return 1
    fi
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CTRLD_CONFIG="/etc/controld/ctrld.toml"
CTRLD_BACKUP_DIR="/etc/controld/backups"
LOG_FILE="/var/log/controld-maintenance.log"
PERFORMANCE_LOG="/var/log/controld-performance.log"

# Ensure backup directory exists (with permission check)
if [ "$EUID" -ne 0 ]; then
    if sudo -n true 2>/dev/null; then
        sudo mkdir -p "$CTRLD_BACKUP_DIR"
    else
        echo "This script needs sudo privileges to create $CTRLD_BACKUP_DIR" >&2
        exit 1
    fi
else
    mkdir -p "$CTRLD_BACKUP_DIR"
fi

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Function: Health Check
health_check() {
    log "${BLUE}=== Control D Health Check $(date) ===${NC}"
    
    # Check service status
    if sudo launchctl list | grep -q ctrld; then
        log "${GREEN}✅ ctrld service is running${NC}"
        local pid=$(sudo launchctl list | grep ctrld | awk '{print $1}')
        log "   PID: $pid"
    else
        log "${RED}❌ ctrld service is NOT running${NC}"
        return 1
    fi
    
    # Check port binding
    if sudo lsof -i :53 | grep -q ctrld; then
        log "${GREEN}✅ ctrld is bound to port 53${NC}"
    else
        log "${RED}❌ ctrld is NOT bound to port 53${NC}"
        return 1
    fi
    
    # Test DNS resolution
    local test_result=$(dig +short +time=5 google.com @127.0.0.1 2>/dev/null | head -1)
    if [[ -n "$test_result" ]]; then
        log "${GREEN}✅ DNS resolution working (resolved to: $test_result)${NC}"
    else
        log "${RED}❌ DNS resolution FAILED${NC}"
        return 1
    fi
    
    # Check upstream connections
    local connections=$(sudo lsof -i | grep ctrld | grep -E "(controld\.com|dns\.controld\.com)" | wc -l)
    log "${GREEN}✅ Active upstream connections: $connections${NC}"
    
    return 0
}

# Function: Performance Monitoring
performance_check() {
    log "${BLUE}=== Performance Check $(date) ===${NC}"
    
    # DNS query speed test
    echo "$(date): DNS Performance Test" >> "$PERFORMANCE_LOG"
    
    # Helper for monotonic time in ns
    time_ns() { (gdate +%s%N 2>/dev/null) || python3 - <<'PY'
import time; print(int(time.time() * 1_000_000_000))
PY
    }

    for domain in google.com cloudflare.com github.com; do
        local start_time=$(time_ns)
        local result=$(dig +short "$domain" @127.0.0.1 >/dev/null 2>&1; echo $?)
        local end_time=$(time_ns)
        
        if [[ "$result" == "0" ]]; then
            local duration=$((($end_time - $start_time) / 1000000))
            log "   $domain: ${duration}ms"
            echo "$(date): $domain: ${duration}ms" >> "$PERFORMANCE_LOG"
        else
            log "${YELLOW}   $domain: FAILED${NC}"
            echo "$(date): $domain: FAILED" >> "$PERFORMANCE_LOG"
        fi
    done
    
    # Cache efficiency (if available)
    if [[ -f "/var/log/ctrld.log" ]]; then
        local cache_hits=$(grep -i "cache.*hit" /var/log/ctrld.log | tail -100 | wc -l)
        log "   Recent cache hits: $cache_hits"
    fi
}

# Function: Configuration Backup
backup_config() {
    log "${BLUE}=== Configuration Backup ===${NC}"
    
    local backup_file="$CTRLD_BACKUP_DIR/ctrld.toml.$(date +%Y%m%d_%H%M%S)"
    sudo cp "$CTRLD_CONFIG" "$backup_file"
    log "${GREEN}✅ Configuration backed up to: $backup_file${NC}"
    
    # Keep only last 10 backups
    sudo find "$CTRLD_BACKUP_DIR" -name "ctrld.toml.*" -type f | sort -r | tail -n +11 | sudo xargs rm -f
}

# Function: Update Check
update_check() {
    log "${BLUE}=== Update Check ===${NC}"
    
    require_cmd curl || true
    require_cmd ctrld || true
    local current_version=$(ctrld --version 2>/dev/null | grep -o 'v[0-9.]*' || echo "unknown")
    log "   Current version: $current_version"
    
    # Download latest version info (safely)
    local latest_version=$(curl -s --connect-timeout 10 --max-time 30 https://api.github.com/repos/Control-D-Inc/ctrld/releases/latest 2>/dev/null | grep '"tag_name"' | cut -d'"' -f4 || echo "unknown")
    
    if [[ "$latest_version" != "unknown" && "$latest_version" != "$current_version" ]]; then
        log "${YELLOW}⚠️  Update available: $latest_version${NC}"
        log "   Run: curl -sSL https://api.controld.com/dl -o /tmp/ctrld-installer.sh && sudo sh /tmp/ctrld-installer.sh update"
    else
        log "${GREEN}✅ Running latest version${NC}"
    fi
}

# Function: Network Diagnostics
network_diagnostics() {
    log "${BLUE}=== Network Diagnostics ===${NC}"
    
    # Check DNS leak
    require_cmd dig || true
    require_cmd ping || true
    local leak_test=$(dig +short whoami.akamai.net @127.0.0.1 2>/dev/null | head -1)
    if [[ -n "$leak_test" ]]; then
        log "   External IP via DNS: $leak_test"
    fi
    
    # Check Control D connectivity
    local controld_ip=$(dig +short dns.controld.com @8.8.8.8 2>/dev/null | head -1)
    if [[ -n "$controld_ip" ]]; then
        local ping_result=$(ping -c 3 "$controld_ip" 2>/dev/null | grep "avg" | cut -d'/' -f5 || echo "N/A")
        log "   Control D latency: ${ping_result}ms"
    fi
    
    # Check for DNS over port 53 leakage
    log "   Checking for DNS leakage..."
    require_cmd timeout || true
    require_cmd tcpdump || true
    timeout 5s sudo tcpdump -c 5 -i any port 53 and not host 127.0.0.1 >/dev/null 2>&1 || true
    if [[ $? -eq 124 ]]; then
        log "${GREEN}✅ No DNS leakage detected${NC}"
    else
        log "${YELLOW}⚠️  Possible DNS leakage detected${NC}"
    fi
}

# Function: Restart Service
restart_service() {
    log "${BLUE}=== Restarting ctrld Service ===${NC}"
    
    backup_config
    
    sudo launchctl kickstart -k system/ctrld
    sleep 3
    
    if health_check; then
        log "${GREEN}✅ Service restarted successfully${NC}"
    else
        log "${RED}❌ Service restart failed${NC}"
        return 1
    fi
}

# Function: Emergency Restore
emergency_restore() {
    log "${BLUE}=== Emergency DNS Restore ===${NC}"
    
    log "${YELLOW}⚠️  Restoring system DNS to fallback...${NC}"
    
    # Stop ctrld
    sudo launchctl bootout system/ctrld 2>/dev/null || true
    
    # Restore original DNS
    sudo networksetup -setdnsservers "Wi-Fi" 1.1.1.1 8.8.8.8
    
    # Flush DNS cache
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder 2>/dev/null || true
    
    log "${GREEN}✅ Emergency restore complete. System using fallback DNS.${NC}"
    log "   To restore ctrld: sudo launchctl bootstrap system /Library/LaunchDaemons/com.controld.ctrld.plist"
}

# Main execution
case "${1:-health}" in
    "health")
        health_check
        ;;
    "performance")
        performance_check
        ;;
    "full")
        backup_config
        health_check
        performance_check
        update_check
        network_diagnostics
        ;;
    "restart")
        restart_service
        ;;
    "emergency")
        emergency_restore
        ;;
    "backup")
        backup_config
        ;;
    *)
        echo "Control D DNS Maintenance Suite"
        echo "Usage: $0 [health|performance|full|restart|emergency|backup]"
        echo ""
        echo "Commands:"
        echo "  health      - Basic health check (default)"
        echo "  performance - DNS performance testing"
        echo "  full        - Complete maintenance check"
        echo "  restart     - Restart ctrld service"
        echo "  emergency   - Emergency DNS restore"
        echo "  backup      - Backup configuration"
        exit 1
        ;;
esac
