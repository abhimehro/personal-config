#!/usr/bin/env bash

# Advanced System Metrics Collector & Performance Monitor
# Collects detailed system performance data and trends
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
METRICS_DIR="$LOG_DIR/metrics"
mkdir -p "$METRICS_DIR"

# Basic logging with performance timestamps
log_metric() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    local metric_type="$1"
    local value="$2"
    local unit="${3:-}"
    echo "$ts [METRIC] [$metric_type] $value $unit" | tee -a "$LOG_DIR/system_metrics.log"
    
    # Also log to JSON format for analysis
    echo "{\"timestamp\":\"$ts\",\"type\":\"$metric_type\",\"value\":$value,\"unit\":\"$unit\"}" >> "$METRICS_DIR/$(date +%Y%m%d).jsonl"
}

log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [system_metrics] $*" | tee -a "$LOG_DIR/system_metrics.log"
}

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE" 2>/dev/null || true
fi

log_info "System metrics collection started"

# CPU and Load Metrics
LOAD_1MIN=$(uptime | awk -F'load averages:' '{print $2}' | awk '{print $1}' | tr -d ',' || echo "0")
LOAD_5MIN=$(uptime | awk -F'load averages:' '{print $2}' | awk '{print $2}' | tr -d ',' || echo "0")
LOAD_15MIN=$(uptime | awk -F'load averages:' '{print $2}' | awk '{print $3}' | tr -d ',' || echo "0")
CPU_COUNT=$(sysctl -n hw.ncpu 2>/dev/null || echo "1")

log_metric "load_1min" "$LOAD_1MIN" "avg"
log_metric "load_5min" "$LOAD_5MIN" "avg"
log_metric "load_15min" "$LOAD_15MIN" "avg"
log_metric "cpu_count" "$CPU_COUNT" "cores"

# Memory Metrics (enhanced)
if command -v vm_stat >/dev/null 2>&1; then
    VM_STAT=$(vm_stat)
    
    # Extract memory stats
    FREE_PAGES=$(echo "$VM_STAT" | awk '/Pages free:/ {print $3}' | tr -d '.' || echo "0")
    ACTIVE_PAGES=$(echo "$VM_STAT" | awk '/Pages active:/ {print $3}' | tr -d '.' || echo "0")
    INACTIVE_PAGES=$(echo "$VM_STAT" | awk '/Pages inactive:/ {print $3}' | tr -d '.' || echo "0")
    WIRED_PAGES=$(echo "$VM_STAT" | awk '/Pages wired down:/ {print $4}' | tr -d '.' || echo "0")
    COMPRESSED_PAGES=$(echo "$VM_STAT" | awk '/Pages stored in compressor:/ {print $5}' | tr -d '.' || echo "0")
    
    PAGE_SIZE=$(echo "$VM_STAT" | awk '/page size of/ {print $8}' || echo "4096")
    
    # Convert to MB
    FREE_MB=$(( (FREE_PAGES * PAGE_SIZE) / 1024 / 1024 ))
    ACTIVE_MB=$(( (ACTIVE_PAGES * PAGE_SIZE) / 1024 / 1024 ))
    INACTIVE_MB=$(( (INACTIVE_PAGES * PAGE_SIZE) / 1024 / 1024 ))
    WIRED_MB=$(( (WIRED_PAGES * PAGE_SIZE) / 1024 / 1024 ))
    COMPRESSED_MB=$(( (COMPRESSED_PAGES * PAGE_SIZE) / 1024 / 1024 ))
    TOTAL_USED_MB=$((ACTIVE_MB + INACTIVE_MB + WIRED_MB))
    
    log_metric "memory_free" "$FREE_MB" "MB"
    log_metric "memory_active" "$ACTIVE_MB" "MB"
    log_metric "memory_inactive" "$INACTIVE_MB" "MB"
    log_metric "memory_wired" "$WIRED_MB" "MB"
    log_metric "memory_compressed" "$COMPRESSED_MB" "MB"
    log_metric "memory_used_total" "$TOTAL_USED_MB" "MB"
    
    # Memory pressure indicator
    if [[ $FREE_MB -lt 500 ]]; then
        log_metric "memory_pressure" "high" "status"
    elif [[ $FREE_MB -lt 1000 ]]; then
        log_metric "memory_pressure" "medium" "status"
    else
        log_metric "memory_pressure" "low" "status"
    fi
fi

# Disk Usage Metrics (enhanced)
ROOT_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
ROOT_AVAILABLE_GB=$(df -h / | awk 'NR==2 {print $4}' | sed 's/Gi*//')
ROOT_USED_GB=$(df -h / | awk 'NR==2 {print $3}' | sed 's/Gi*//')

log_metric "disk_usage_percent" "$ROOT_USAGE" "percent"
log_metric "disk_available" "$ROOT_AVAILABLE_GB" "GB"
log_metric "disk_used" "$ROOT_USED_GB" "GB"

# Disk I/O Performance Test (lightweight)
TEST_FILE="/tmp/maintenance_io_test.tmp"
if time dd if=/dev/zero of="$TEST_FILE" bs=1024 count=1024 2>/dev/null >/dev/null; then
    rm -f "$TEST_FILE" 2>/dev/null
    log_metric "disk_io_test" "passed" "status"
else
    log_metric "disk_io_test" "failed" "status"
fi

# Network Connectivity Metrics
PING_TARGET="8.8.8.8"
if PING_TIME=$(ping -c 1 -W 3000 $PING_TARGET 2>/dev/null | grep 'time=' | awk '{print $7}' | cut -d'=' -f2); then
    log_metric "network_latency_ms" "${PING_TIME:-999}" "ms"
    log_metric "network_status" "connected" "status"
else
    log_metric "network_latency_ms" "999" "ms"
    log_metric "network_status" "disconnected" "status"
fi

# Battery Metrics (for MacBooks)
if command -v pmset >/dev/null 2>&1; then
    BATTERY_INFO=$(pmset -g batt 2>/dev/null | grep -v "Battery Power" | tail -1)
    if [[ -n "$BATTERY_INFO" ]]; then
        BATTERY_PERCENT=$(echo "$BATTERY_INFO" | grep -o '[0-9]\+%' | tr -d '%')
        BATTERY_STATUS=$(echo "$BATTERY_INFO" | grep -o '\(charging\|discharging\|charged\)')
        
        log_metric "battery_percent" "${BATTERY_PERCENT:-0}" "percent"
        log_metric "battery_status" "${BATTERY_STATUS:-unknown}" "status"
        
        # Battery health warning
        if [[ ${BATTERY_PERCENT:-100} -lt 20 ]]; then
            log_metric "battery_warning" "low" "status"
        fi
    fi
fi

# Process and System Load Analysis
PROCESS_COUNT=$(ps aux | wc -l)
HIGH_CPU_PROCESSES=$(ps aux | awk '$3 > 10.0 {count++} END {print count+0}')
HIGH_MEM_PROCESSES=$(ps aux | awk '$4 > 5.0 {count++} END {print count+0}')

log_metric "process_count" "$PROCESS_COUNT" "count"
log_metric "high_cpu_processes" "$HIGH_CPU_PROCESSES" "count"
log_metric "high_memory_processes" "$HIGH_MEM_PROCESSES" "count"

# Maintenance System Health
MAINTENANCE_AGENTS=$(launchctl list | grep "com.abhimehrotra.maintenance" | wc -l | tr -d ' ')
FAILED_AGENTS=$(launchctl list | grep "com.abhimehrotra.maintenance" | awk '$3 != "0" {count++} END {print count+0}')

log_metric "maintenance_agents_total" "$MAINTENANCE_AGENTS" "count"
log_metric "maintenance_agents_failed" "$FAILED_AGENTS" "count"

# Homebrew Health
if command -v brew >/dev/null 2>&1; then
    BREW_OUTDATED=$(brew outdated 2>/dev/null | wc -l | tr -d ' ')
    BREW_INSTALLED=$(brew list 2>/dev/null | wc -l | tr -d ' ')
    
    log_metric "brew_packages_installed" "$BREW_INSTALLED" "count"
    log_metric "brew_packages_outdated" "$BREW_OUTDATED" "count"
    
    # Homebrew cask metrics
    BREW_CASKS_INSTALLED=$(brew list --cask 2>/dev/null | wc -l | tr -d ' ')
    BREW_CASKS_OUTDATED=$(brew outdated --cask 2>/dev/null | wc -l | tr -d ' ')
    
    log_metric "brew_casks_installed" "$BREW_CASKS_INSTALLED" "count"
    log_metric "brew_casks_outdated" "$BREW_CASKS_OUTDATED" "count"
fi

# System Uptime
UPTIME_DAYS=$(uptime | awk -F'up ' '{print $2}' | awk '{print $1}' | grep -o '[0-9]\+' | head -1 || echo "0")
log_metric "system_uptime_days" "${UPTIME_DAYS:-0}" "days"

# Temperature Monitoring (if available)
if command -v osx-cpu-temp >/dev/null 2>&1; then
    CPU_TEMP=$(osx-cpu-temp | grep -o '[0-9]\+\.[0-9]\+' | head -1)
    log_metric "cpu_temperature" "${CPU_TEMP:-0}" "celsius"
elif [[ -f /sys/class/thermal/thermal_zone0/temp ]]; then
    CPU_TEMP_RAW=$(cat /sys/class/thermal/thermal_zone0/temp)
    CPU_TEMP=$((CPU_TEMP_RAW / 1000))
    log_metric "cpu_temperature" "$CPU_TEMP" "celsius"
fi

# Generate summary metrics
OVERALL_HEALTH="healthy"
WARNING_COUNT=0

# Health checks
if [[ ${ROOT_USAGE:-0} -gt 85 ]]; then
    OVERALL_HEALTH="warning"
    ((WARNING_COUNT++))
fi

if [[ ${FREE_MB:-1000} -lt 500 ]]; then
    OVERALL_HEALTH="warning"
    ((WARNING_COUNT++))
fi

if [[ ${FAILED_AGENTS:-0} -gt 0 ]]; then
    OVERALL_HEALTH="warning"
    ((WARNING_COUNT++))
fi

if [[ $WARNING_COUNT -gt 2 ]]; then
    OVERALL_HEALTH="critical"
fi

log_metric "system_health" "$OVERALL_HEALTH" "status"
log_metric "health_warnings" "$WARNING_COUNT" "count"

# Performance Score (0-100)
PERF_SCORE=100

# Deduct points for issues
if [[ ${ROOT_USAGE:-0} -gt 90 ]]; then ((PERF_SCORE -= 20)); fi
if [[ ${ROOT_USAGE:-0} -gt 80 ]]; then ((PERF_SCORE -= 10)); fi
if [[ ${FREE_MB:-1000} -lt 500 ]]; then ((PERF_SCORE -= 15)); fi
if [[ ${FREE_MB:-1000} -lt 1000 ]]; then ((PERF_SCORE -= 10)); fi
if [[ ${FAILED_AGENTS:-0} -gt 0 ]]; then ((PERF_SCORE -= 25)); fi
if [[ ${HIGH_CPU_PROCESSES:-0} -gt 3 ]]; then ((PERF_SCORE -= 10)); fi

# Ensure score doesn't go below 0
if [[ $PERF_SCORE -lt 0 ]]; then PERF_SCORE=0; fi

log_metric "performance_score" "$PERF_SCORE" "score"

# Create daily summary if this is the first run of the day
SUMMARY_FILE="$METRICS_DIR/daily_summary_$(date +%Y%m%d).txt"
if [[ ! -f "$SUMMARY_FILE" ]]; then
    cat > "$SUMMARY_FILE" << EOF
Daily System Summary - $(date +"%B %d, %Y")
=========================================

System Health: $OVERALL_HEALTH
Performance Score: $PERF_SCORE/100
Warnings: $WARNING_COUNT

Resource Usage:
- Disk Usage: ${ROOT_USAGE}% (${ROOT_AVAILABLE_GB}GB available)
- Memory Usage: ${TOTAL_USED_MB}MB used, ${FREE_MB}MB free
- Load Average: ${LOAD_1MIN} (1min), ${LOAD_5MIN} (5min), ${LOAD_15MIN} (15min)

Maintenance System:
- Active Agents: $MAINTENANCE_AGENTS
- Failed Agents: $FAILED_AGENTS

Package Management:
- Homebrew Packages: $BREW_INSTALLED installed, $BREW_OUTDATED outdated
- Homebrew Casks: $BREW_CASKS_INSTALLED installed, $BREW_CASKS_OUTDATED outdated

System Info:
- Uptime: ${UPTIME_DAYS} days
- Process Count: $PROCESS_COUNT
- High CPU Processes: $HIGH_CPU_PROCESSES
- High Memory Processes: $HIGH_MEM_PROCESSES
EOF
fi

log_info "System metrics collection complete - Health: $OVERALL_HEALTH, Performance: $PERF_SCORE/100"

# Optional notification for critical issues
if [[ "$OVERALL_HEALTH" == "critical" ]] && command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"System health is critical! Check metrics for details.\" with title \"System Alert\" sound name \"Basso\"" 2>/dev/null || true
fi

echo "System metrics collection completed successfully!"