#!/bin/bash

# Performance Optimizer - Fine-tune system performance and optimize resource usage
# Part of the enhanced maintenance automation system

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HOME/Library/Logs/maintenance"
PERFORMANCE_LOG="$LOG_DIR/performance_optimizer.log"
METRICS_DIR="$LOG_DIR/metrics"
CONFIG_DIR="$SCRIPT_DIR/../config"
PERF_CONFIG="$CONFIG_DIR/performance_config.json"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$METRICS_DIR" "$CONFIG_DIR"

# Logging functions
log_message() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$PERFORMANCE_LOG"
}

log_info() { log_message "INFO" "$@"; }
log_warn() { log_message "WARN" "$@"; }
log_error() { log_message "ERROR" "$@"; }

# Initialize performance configuration if it doesn't exist
init_performance_config() {
    if [[ ! -f "$PERF_CONFIG" ]]; then
        log_info "Creating performance configuration file"
        cat > "$PERF_CONFIG" <<EOF
{
    "cpu_optimization": {
        "enabled": true,
        "max_background_processes": 50,
        "nice_level": 10,
        "cpu_threshold": 80
    },
    "memory_optimization": {
        "enabled": true,
        "swap_usage_threshold": 50,
        "memory_pressure_threshold": 75,
        "purge_inactive_memory": true
    },
    "disk_optimization": {
        "enabled": true,
        "trim_ssd": true,
        "spotlight_optimization": true,
        "cache_cleanup": true
    },
    "network_optimization": {
        "enabled": true,
        "dns_cache_flush": true,
        "tcp_optimization": true
    },
    "application_optimization": {
        "enabled": true,
        "kill_zombie_processes": true,
        "optimize_launch_agents": true,
        "cleanup_temp_files": true
    }
}
EOF
    fi
}

# CPU optimization functions
optimize_cpu_usage() {
    log_info "Starting CPU optimization..."
    
    # Get current CPU load
    local cpu_load
    cpu_load=$(uptime | awk '{print $(NF-2)}' | tr -d ',')
    local cpu_count
    cpu_count=$(sysctl -n hw.ncpu)
    local cpu_percent
    cpu_percent=$(echo "scale=1; $cpu_load / $cpu_count * 100" | bc -l)
    
    log_info "Current CPU load: ${cpu_percent}%"
    
    # If CPU load is high, optimize background processes
    if (( $(echo "$cpu_percent > 70" | bc -l) )); then
        log_info "High CPU load detected, optimizing background processes"
        
        # Reduce priority of non-essential processes
        local background_procs
        background_procs=$(ps -eo pid,nice,comm | grep -E "(Spotlight|mds|mdworker)" | awk '$2 == 0 {print $1}')
        
        if [[ -n "$background_procs" ]]; then
            echo "$background_procs" | while read -r pid; do
                if [[ -n "$pid" ]]; then
                    renice 15 "$pid" >/dev/null 2>&1 || true
                    log_info "Reduced priority for process $pid"
                fi
            done
        fi
        
        # Throttle CPU-intensive maintenance tasks
        export MAINTENANCE_CPU_THROTTLE=1
        log_info "CPU throttling enabled for maintenance tasks"
    fi
    
    log_info "CPU optimization completed"
}

# Memory optimization functions
optimize_memory_usage() {
    log_info "Starting memory optimization..."
    
    # Get memory statistics
    local memory_stats
    memory_stats=$(vm_stat)
    local pages_free pages_inactive pages_speculative page_size
    pages_free=$(echo "$memory_stats" | grep "Pages free" | awk '{print $3}' | tr -d '.')
    pages_inactive=$(echo "$memory_stats" | grep "Pages inactive" | awk '{print $3}' | tr -d '.')
    pages_speculative=$(echo "$memory_stats" | grep "Pages speculative" | awk '{print $3}' | tr -d '.')
    page_size=$(vm_stat | grep "page size" | awk '{print $8}')
    
    # Calculate available memory percentage
    local total_memory available_memory memory_percent
    total_memory=$(sysctl -n hw.memsize)
    available_memory=$(( (pages_free + pages_inactive + pages_speculative) * page_size ))
    memory_percent=$(echo "scale=1; $available_memory / $total_memory * 100" | bc -l)
    
    log_info "Available memory: ${memory_percent}%"
    
    # If memory is low, perform cleanup
    if (( $(echo "$memory_percent < 20" | bc -l) )); then
        log_info "Low memory detected, performing memory cleanup"
        
        # Purge inactive memory
        sudo purge >/dev/null 2>&1 || true
        log_info "Purged inactive memory"
        
        # Clear various caches
        sudo dscacheutil -flushcache >/dev/null 2>&1 || true
        log_info "Cleared DNS cache"
        
        # Kill memory-heavy inactive applications
        local memory_hogs
        memory_hogs=$(ps -axo pid,rss,comm | sort -k2 -nr | head -10 | awk '$2 > 100000 && $3 !~ /(kernel|launchd|WindowServer|loginwindow)/ {print $1}')
        
        if [[ -n "$memory_hogs" ]]; then
            echo "$memory_hogs" | head -3 | while read -r pid; do
                if [[ -n "$pid" ]]; then
                    # Check if process is safe to terminate
                    local proc_name
                    proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
                    if [[ "$proc_name" =~ (Chrome|Firefox|Safari|Slack|Electron) ]]; then
                        log_info "High memory process detected: $proc_name (PID: $pid) - skipping automatic termination"
                    fi
                fi
            done
        fi
    fi
    
    log_info "Memory optimization completed"
}

# Disk optimization functions
optimize_disk_usage() {
    log_info "Starting disk optimization..."
    
    # Get disk usage
    local disk_usage
    disk_usage=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
    log_info "Current disk usage: ${disk_usage}%"
    
    # Trim SSD if usage is high
    if [[ $disk_usage -gt 80 ]]; then
        log_info "High disk usage detected, performing optimization"
        
        # Run first aid on disk
        diskutil verifyVolume / >/dev/null 2>&1 || true
        
        # Clean up system caches
        local cache_dirs=(
            "$HOME/Library/Caches"
            "/Library/Caches"
            "/System/Library/Caches"
            "$HOME/Library/Logs"
            "/var/log"
            "$HOME/.Trash"
        )
        
        for cache_dir in "${cache_dirs[@]}"; do
            if [[ -d "$cache_dir" ]]; then
                local cache_size_before
                cache_size_before=$(du -sm "$cache_dir" 2>/dev/null | awk '{print $1}' || echo "0")
                
                # Clean old cache files (older than 7 days)
                find "$cache_dir" -type f -mtime +7 -delete 2>/dev/null || true
                
                local cache_size_after
                cache_size_after=$(du -sm "$cache_dir" 2>/dev/null | awk '{print $1}' || echo "0")
                local freed=$((cache_size_before - cache_size_after))
                
                if [[ $freed -gt 0 ]]; then
                    log_info "Cleaned $cache_dir: freed ${freed}MB"
                fi
            fi
        done
    fi
    
    # Optimize Spotlight indexing
    local spotlight_status
    spotlight_status=$(mdutil -s / | grep "Indexing enabled")
    if [[ "$spotlight_status" == *"enabled"* ]]; then
        # Exclude common development directories from Spotlight
        local exclude_dirs=(
            "$HOME/node_modules"
            "$HOME/.npm"
            "$HOME/.cache"
            "$HOME/Library/Developer"
            "$HOME/Documents/dev/*/node_modules"
        )
        
        for exclude_dir in "${exclude_dirs[@]}"; do
            if [[ -d "$exclude_dir" ]]; then
                mdutil -i off "$exclude_dir" >/dev/null 2>&1 || true
            fi
        done
        
        log_info "Optimized Spotlight indexing exclusions"
    fi
    
    log_info "Disk optimization completed"
}

# Network optimization functions
optimize_network() {
    log_info "Starting network optimization..."
    
    # Flush DNS cache for better performance
    sudo dscacheutil -flushcache >/dev/null 2>&1 || true
    sudo killall -HUP mDNSResponder >/dev/null 2>&1 || true
    log_info "DNS cache flushed"
    
    # Test network connectivity and latency
    local ping_result
    ping_result=$(ping -c 3 8.8.8.8 2>/dev/null | tail -1 | awk -F '/' '{print $5}' | cut -d. -f1 || echo "999")
    
    if [[ $ping_result -gt 100 ]]; then
        log_warn "High network latency detected: ${ping_result}ms"
        
        # Reset network interfaces if latency is very high
        if [[ $ping_result -gt 500 ]]; then
            log_info "Attempting network interface reset"
            sudo ifconfig en0 down && sudo ifconfig en0 up >/dev/null 2>&1 || true
        fi
    else
        log_info "Network latency: ${ping_result}ms (good)"
    fi
    
    log_info "Network optimization completed"
}

# Application optimization functions
optimize_applications() {
    log_info "Starting application optimization..."
    
    # Kill zombie processes
    local zombies
    zombies=$(ps aux | awk '$8 ~ /^Z/ {print $2}')
    if [[ -n "$zombies" ]]; then
        echo "$zombies" | while read -r pid; do
            if [[ -n "$pid" ]]; then
                kill -TERM "$pid" >/dev/null 2>&1 || true
                log_info "Cleaned zombie process $pid"
            fi
        done
    fi
    
    # Optimize launch agents and daemons
    local inactive_agents
    inactive_agents=$(launchctl list | grep -E "^-.*\.(plist|agent)" | awk '{print $3}')
    
    if [[ -n "$inactive_agents" ]]; then
        echo "$inactive_agents" | while read -r agent; do
            if [[ -n "$agent" && "$agent" != *"apple"* && "$agent" != *"system"* ]]; then
                # Only unload non-system agents that are inactive
                launchctl unload "$agent" >/dev/null 2>&1 || true
                log_info "Unloaded inactive agent: $agent"
            fi
        done
    fi
    
    # Clean temporary files
    local temp_dirs=(
        "/tmp"
        "$HOME/tmp"
        "$HOME/.tmp"
        "/var/tmp"
    )
    
    for temp_dir in "${temp_dirs[@]}"; do
        if [[ -d "$temp_dir" ]]; then
            # Clean files older than 1 day
            find "$temp_dir" -type f -mtime +1 -delete 2>/dev/null || true
            log_info "Cleaned temporary files from $temp_dir"
        fi
    done
    
    log_info "Application optimization completed"
}

# Resource monitoring
monitor_resources() {
    local monitor_duration="${1:-60}"  # Default 1 minute
    log_info "Starting resource monitoring for $monitor_duration seconds..."
    
    local monitor_file="$METRICS_DIR/resource_monitor_$(date +%Y%m%d_%H%M%S).log"
    local start_time end_time
    start_time=$(date +%s)
    end_time=$((start_time + monitor_duration))
    
    echo "Resource Monitoring Started: $(date)" > "$monitor_file"
    echo "Duration: $monitor_duration seconds" >> "$monitor_file"
    echo "----------------------------------------" >> "$monitor_file"
    
    while [[ $(date +%s) -lt $end_time ]]; do
        local timestamp cpu_load memory_free disk_usage
        timestamp=$(date '+%H:%M:%S')
        cpu_load=$(uptime | awk '{print $(NF-2)}' | tr -d ',')
        memory_free=$(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.')
        disk_usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
        
        echo "$timestamp CPU:$cpu_load MEM_FREE:$memory_free DISK:${disk_usage}%" >> "$monitor_file"
        sleep 5
    done
    
    echo "----------------------------------------" >> "$monitor_file"
    echo "Resource Monitoring Completed: $(date)" >> "$monitor_file"
    log_info "Resource monitoring completed, results saved to $monitor_file"
}

# Performance benchmark
run_benchmark() {
    log_info "Running performance benchmark..."
    
    local benchmark_file="$METRICS_DIR/performance_benchmark_$(date +%Y%m%d_%H%M%S).log"
    
    echo "Performance Benchmark - $(date)" > "$benchmark_file"
    echo "================================" >> "$benchmark_file"
    
    # CPU benchmark
    log_info "Running CPU benchmark..."
    local cpu_start cpu_end cpu_time
    cpu_start=$(date +%s.%3N)
    yes > /dev/null &
    local cpu_pid=$!
    sleep 10
    kill $cpu_pid >/dev/null 2>&1
    cpu_end=$(date +%s.%3N)
    cpu_time=$(echo "scale=3; $cpu_end - $cpu_start" | bc -l)
    echo "CPU Test: ${cpu_time}s" >> "$benchmark_file"
    
    # Memory benchmark
    log_info "Running memory benchmark..."
    local mem_start mem_end mem_time
    mem_start=$(date +%s.%3N)
    # Simple memory allocation test
    python3 -c "
import time
start = time.time()
data = [i for i in range(1000000)]
del data
print(f'Memory allocation test: {time.time() - start:.3f}s')
" >> "$benchmark_file" 2>/dev/null || echo "Memory Test: N/A (Python not available)" >> "$benchmark_file"
    
    # Disk I/O benchmark
    log_info "Running disk I/O benchmark..."
    local io_start io_end io_time
    io_start=$(date +%s.%3N)
    dd if=/dev/zero of=/tmp/benchmark_test bs=1024 count=10240 2>/dev/null
    sync
    io_end=$(date +%s.%3N)
    rm -f /tmp/benchmark_test
    io_time=$(echo "scale=3; $io_end - $io_start" | bc -l)
    echo "Disk I/O Test: ${io_time}s" >> "$benchmark_file"
    
    log_info "Performance benchmark completed, results saved to $benchmark_file"
}

# Generate performance report
generate_performance_report() {
    log_info "Generating performance report..."
    
    local report_file="$SCRIPT_DIR/../reports/performance_report_$(date +%Y%m%d).html"
    mkdir -p "$(dirname "$report_file")"
    
    # Get system information
    local system_info cpu_info memory_info disk_info
    system_info=$(system_profiler SPSoftwareDataType | grep "System Version" | awk -F: '{print $2}' | xargs)
    cpu_info=$(sysctl -n machdep.cpu.brand_string)
    memory_info=$(echo "$(sysctl -n hw.memsize) / 1024 / 1024 / 1024" | bc) # GB
    disk_info=$(df -h / | tail -1 | awk '{print $2}')
    
    cat > "$report_file" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>Performance Report - $(date +%Y-%m-%d)</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 10px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ccc; border-radius: 5px; }
        .metric { margin: 5px 0; }
        .good { color: green; }
        .warning { color: orange; }
        .critical { color: red; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #f0f0f0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Performance Report</h1>
        <p>Generated: $(date)</p>
    </div>
    
    <div class="section">
        <h2>System Information</h2>
        <div class="metric">System: $system_info</div>
        <div class="metric">CPU: $cpu_info</div>
        <div class="metric">Memory: ${memory_info} GB</div>
        <div class="metric">Disk: $disk_info</div>
    </div>
    
    <div class="section">
        <h2>Current Performance Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th><th>Status</th></tr>
EOF
    
    # Add current metrics
    local cpu_load memory_usage disk_usage
    cpu_load=$(uptime | awk '{print $(NF-2)}' | tr -d ',')
    memory_usage=$(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.' | head -1)
    disk_usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
    
    # Determine status colors
    local cpu_status="good"
    [[ $(echo "$cpu_load > 2" | bc -l) == "1" ]] && cpu_status="warning"
    [[ $(echo "$cpu_load > 4" | bc -l) == "1" ]] && cpu_status="critical"
    
    local disk_status="good"
    [[ $disk_usage -gt 70 ]] && disk_status="warning"
    [[ $disk_usage -gt 90 ]] && disk_status="critical"
    
    cat >> "$report_file" <<EOF
            <tr><td>CPU Load</td><td>$cpu_load</td><td class="$cpu_status">$(echo $cpu_status | tr '[:lower:]' '[:upper:]')</td></tr>
            <tr><td>Memory Free Pages</td><td>$memory_usage</td><td class="good">GOOD</td></tr>
            <tr><td>Disk Usage</td><td>${disk_usage}%</td><td class="$disk_status">$(echo $disk_status | tr '[:lower:]' '[:upper:]')</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Optimization Recommendations</h2>
        <ul>
EOF
    
    # Add recommendations based on current state
    [[ $(echo "$cpu_load > 2" | bc -l) == "1" ]] && echo "            <li>Consider reducing CPU-intensive background tasks</li>" >> "$report_file"
    [[ $disk_usage -gt 80 ]] && echo "            <li>Disk usage is high - consider cleaning up old files</li>" >> "$report_file"
    [[ $disk_usage -le 60 ]] && echo "            <li>Disk usage is optimal</li>" >> "$report_file"
    
    cat >> "$report_file" <<EOF
        </ul>
    </div>
    
    <div class="section">
        <h2>Recent Optimizations</h2>
        <p>Last optimization run: $(tail -1 "$PERFORMANCE_LOG" 2>/dev/null || echo "Never")</p>
    </div>
</body>
</html>
EOF
    
    log_info "Performance report generated: $report_file"
}

# Main execution
main() {
    local action="${1:-help}"
    
    # Initialize configuration
    init_performance_config
    
    case "$action" in
        "optimize")
            log_info "Starting comprehensive performance optimization"
            optimize_cpu_usage
            optimize_memory_usage
            optimize_disk_usage
            optimize_network
            optimize_applications
            log_info "Performance optimization completed"
            
            # Send notification if available
            if command -v "$SCRIPT_DIR/smart_notifier.sh" >/dev/null 2>&1; then
                "$SCRIPT_DIR/smart_notifier.sh" send_notification "success" \
                    "Performance Optimization Completed" \
                    "System performance has been optimized"
            fi
            ;;
        "cpu")
            optimize_cpu_usage
            ;;
        "memory")
            optimize_memory_usage
            ;;
        "disk")
            optimize_disk_usage
            ;;
        "network")
            optimize_network
            ;;
        "apps")
            optimize_applications
            ;;
        "monitor")
            monitor_resources "${2:-60}"
            ;;
        "benchmark")
            run_benchmark
            ;;
        "report")
            generate_performance_report
            ;;
        "status")
            log_info "Current System Status:"
            log_info "CPU Load: $(uptime | awk '{print $(NF-2)}' | tr -d ',')"
            log_info "Memory Free: $(vm_stat | grep 'Pages free' | awk '{print $3}' | tr -d '.') pages"
            log_info "Disk Usage: $(df / | tail -1 | awk '{print $5}')"
            log_info "Active Processes: $(ps aux | wc -l)"
            ;;
        "help")
            cat << EOF
Performance Optimizer - System performance and resource optimization

Usage: $0 <action> [arguments]

Actions:
  optimize          - Run comprehensive performance optimization
  cpu              - Optimize CPU usage only
  memory           - Optimize memory usage only
  disk             - Optimize disk usage only
  network          - Optimize network performance only
  apps             - Optimize applications only
  monitor [time]   - Monitor resources for specified seconds (default: 60)
  benchmark        - Run performance benchmark tests
  report           - Generate HTML performance report
  status           - Show current system status
  help             - Show this help message

Examples:
  $0 optimize                    # Full system optimization
  $0 monitor 300                 # Monitor for 5 minutes
  $0 benchmark                   # Run performance tests
  $0 report                      # Generate performance report
EOF
            ;;
        *)
            log_error "Unknown action: $action"
            log_error "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"