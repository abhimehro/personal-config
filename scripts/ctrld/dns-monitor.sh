#!/bin/bash

# DNS Performance Monitor & Health Checker
# Version: 2.1
# Real-time monitoring without excessive overhead

set -e

# Configuration
MONITOR_LOG="$HOME/.controld/monitor.log"
PERF_DB="$HOME/.controld/performance.db"
ALERT_THRESHOLD_MS=100  # Alert if DNS > 100ms
FAILOVER_THRESHOLD_MS=200  # Trigger failover if DNS > 200ms
CHECK_INTERVAL=15  # Faster checks for critical monitoring
HISTORY_LIMIT=1440  # Keep 24 hours of data (at 1-min intervals)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

TEST_DOMAINS_gaming="overwatch.blizzard.com nvidia.com geforcenow.com"
TEST_DOMAINS_general="cloudflare.com google.com amazon.com"
TEST_DOMAINS_privacy="duckduckgo.com protonmail.com signal.org"

# Initialize monitoring environment
init_monitor() {
    mkdir -p "$HOME/.controld"
    touch "$MONITOR_LOG"
    
    # Create performance database if it doesn't exist
    if [[ ! -f "$PERF_DB" ]]; then
        cat > "$PERF_DB" << EOF
# DNS Performance Database
# Format: timestamp,profile,dns_avg_ms,dns_min_ms,dns_max_ms,packet_loss,jitter_ms,status
EOF
    fi
}

# Function to measure DNS response time
measure_dns_response() {
    local domain=$1
    local server=${2:-"127.0.0.1"}
    
    # Use dig with timeout and time measurement
    local result=$(dig @$server $domain +short +time=2 +tries=1 +stats 2>/dev/null | grep "Query time:" | awk '{print $4}')
    
    if [[ -z "$result" ]]; then
        echo "9999"  # Return high value for timeout
    else
        echo "$result"
    fi
}

# Function to measure network jitter
measure_jitter() {
    local host=$1
    local count=10
    
    # Ping and calculate standard deviation
    local ping_times=$(ping -c $count -i 0.2 $host 2>/dev/null | grep "time=" | awk -F'time=' '{print $2}' | awk '{print $1}')
    
    if [[ -z "$ping_times" ]]; then
        echo "0"
        return
    fi
    
    # Calculate jitter (standard deviation)
    echo "$ping_times" | awk '{
        sum += $1
        sumsq += $1^2
        n++
    } END {
        if (n > 0) {
            mean = sum/n
            variance = (sumsq/n) - (mean^2)
            if (variance < 0) variance = 0
            print sqrt(variance)
        } else {
            print 0
        }
    }'
}

# Function to check packet loss
check_packet_loss() {
    local host=$1
    local count=20
    
    local loss=$(ping -c $count -i 0.1 $host 2>/dev/null | grep "packet loss" | awk -F', ' '{print $3}' | awk '{print $1}' | tr -d '%')
    
    if [[ -z "$loss" ]]; then
        echo "100"
    else
        echo "$loss"
    fi
}

# Get current profile
get_current_profile() {
    local cmd=$(ps -ax 2>/dev/null | grep "ctrld run" | grep -v grep | head -n1)
    
    if [[ "$cmd" =~ "1xfy57w34t7" ]]; then
        echo "gaming"
    elif [[ "$cmd" =~ "6m971e9jaf" ]]; then  # Updated Privacy Resolver ID
        echo "privacy"
    else
        echo "unknown"
    fi
}

# Performance test suite
run_performance_tests() {
    local profile=$(get_current_profile)
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    local epoch=$(date +%s)
    
    echo -e "${BLUE}🔍 Running performance tests...${NC}"
    
    # Select test domains based on profile
    local domains=$(eval echo \$TEST_DOMAINS_$profile) || echo "$TEST_DOMAINS_general"
    
    # DNS Response Time Tests
    local dns_times=()
    local dns_failures=0
    
    for domain in $domains; do
        local response_time=$(measure_dns_response "$domain")
        if [[ "$response_time" -eq 9999 ]]; then
            ((dns_failures++))
        else
            dns_times+=("$response_time")
        fi
    done
    
    # Calculate DNS statistics
    local dns_avg=0
    local dns_min=9999
    local dns_max=0
    
    if [[ ${#dns_times[@]} -gt 0 ]]; then
        for time in "${dns_times[@]}"; do
            dns_avg=$((dns_avg + time))
            [[ $time -lt $dns_min ]] && dns_min=$time
            [[ $time -gt $dns_max ]] && dns_max=$time
        done
        dns_avg=$((dns_avg / ${#dns_times[@]}))
    else
        dns_avg=9999
        dns_min=9999
        dns_max=9999
    fi
    
    # Network Performance Tests
    local primary_host="8.8.8.8"
    local packet_loss=$(check_packet_loss "$primary_host")
    local jitter=$(measure_jitter "$primary_host")
    
    # Determine status
    local status="HEALTHY"
    if [[ $dns_avg -gt $FAILOVER_THRESHOLD_MS ]] || [[ $packet_loss -gt 5 ]]; then
        status="CRITICAL"
    elif [[ $dns_avg -gt $ALERT_THRESHOLD_MS ]] || [[ $packet_loss -gt 2 ]]; then
        status="WARNING"
    fi
    
    # Log to database
    echo "$epoch,$profile,$dns_avg,$dns_min,$dns_max,$packet_loss,$jitter,$status" >> "$PERF_DB"
    
    # Display results
    display_results "$profile" "$dns_avg" "$dns_min" "$dns_max" "$packet_loss" "$jitter" "$status"
    
    # Return status for failover decision
    echo "$status"
}

# Display results with color coding
display_results() {
    local profile=$1
    local dns_avg=$2
    local dns_min=$3
    local dns_max=$4
    local packet_loss=$5
    local jitter=$6
    local status=$7
    
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}     Performance Report - $(date +"%H:%M:%S")${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    
    echo -e "Profile: ${BLUE}$profile${NC}"
    
    # DNS Performance
    local dns_color=$GREEN
    [[ $dns_avg -gt $ALERT_THRESHOLD_MS ]] && dns_color=$YELLOW
    [[ $dns_avg -gt $FAILOVER_THRESHOLD_MS ]] && dns_color=$RED
    
    echo -e "DNS Response: ${dns_color}${dns_avg}ms${NC} (min: ${dns_min}ms, max: ${dns_max}ms)"
    
    # Packet Loss
    local loss_color=$GREEN
    [[ $(echo "$packet_loss > 2" | bc) -eq 1 ]] && loss_color=$YELLOW
    [[ $(echo "$packet_loss > 5" | bc) -eq 1 ]] && loss_color=$RED
    
    echo -e "Packet Loss: ${loss_color}${packet_loss}%${NC}"
    
    # Jitter
    local jitter_rounded=$(printf "%.1f" "$jitter")
    local jitter_color=$GREEN
    [[ $(echo "$jitter > 10" | bc) -eq 1 ]] && jitter_color=$YELLOW
    [[ $(echo "$jitter > 20" | bc) -eq 1 ]] && jitter_color=$RED
    
    echo -e "Jitter: ${jitter_color}${jitter_rounded}ms${NC}"
    
    # Overall Status
    local status_color=$GREEN
    [[ "$status" == "WARNING" ]] && status_color=$YELLOW
    [[ "$status" == "CRITICAL" ]] && status_color=$RED
    
    echo -e "Status: ${status_color}${status}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
}

# Cleanup old data
cleanup_old_data() {
    local current_epoch=$(date +%s)
    local cutoff=$((current_epoch - 86400))  # 24 hours ago
    
    # Keep only recent data
    awk -F',' -v cutoff="$cutoff" '$1 > cutoff' "$PERF_DB" > "$PERF_DB.tmp" && mv "$PERF_DB.tmp" "$PERF_DB"
}

# Main monitoring loop
monitor_loop() {
    init_monitor
    
    echo -e "${GREEN}🚀 DNS Performance Monitor Started${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"
    
    while true; do
        local status=$(run_performance_tests)
        
        # Check if failover is needed
        if [[ "$status" == "CRITICAL" ]]; then
            handle_failover
        fi
        
        # Cleanup old data periodically
        if [[ $(($(date +%s) % 3600)) -eq 0 ]]; then
            cleanup_old_data
        fi
        
        sleep $CHECK_INTERVAL
    done
}

# Handle failover
handle_failover() {
    echo -e "${RED}⚠️  CRITICAL: Initiating failover...${NC}"
    
    local current_profile=$(get_current_profile)
    
    # Try to restart current profile first
    echo -e "${YELLOW}Attempting to restart $current_profile profile...${NC}"
    if ! sudo ~/bin/ctrld-switcher.sh restart; then
        log "ERROR" "Restart failed, proceeding to failover."
    else
        log "INFO" "Restart successful."
        return
    fi
    
    sleep 5
    
    # Re-test
    local retest_status=$(run_performance_tests)
    
    if [[ "$retest_status" == "CRITICAL" ]]; then
        echo -e "${RED}Restart failed, switching to fallback DNS...${NC}"
        
        # Switch to direct Cloudflare DNS temporarily
        networksetup -setdnsservers "USB 10/100/1000 LAN" 1.1.1.1 1.0.0.1
        networksetup -setdnsservers "Wi-Fi" 1.1.1.1 1.0.0.1
        
        # Alert user
        osascript -e 'display notification "DNS failover activated due to poor performance" with title "Control D Monitor" sound name "Basso"'
        
        # Log incident
        echo "$(date '+%Y-%m-%d %H:%M:%S'): Failover triggered - $current_profile profile failed" >> "$MONITOR_LOG"
    else
        echo -e "${GREEN}✅ Recovery successful${NC}"
    fi
}

# Start monitoring
monitor_loop