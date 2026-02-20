#!/bin/bash

# Smart Scheduler - Adaptive maintenance scheduling based on system load and usage patterns
# Part of the enhanced maintenance automation system

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HOME/Library/Logs/maintenance"
SCHEDULE_LOG="$LOG_DIR/smart_scheduler.log"
METRICS_DIR="$LOG_DIR/metrics"
SCHEDULE_CONFIG="$SCRIPT_DIR/../config/schedule_config.json"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$METRICS_DIR" "$(dirname "$SCHEDULE_CONFIG")"

# Logging functions
log_message() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$SCHEDULE_LOG"
}

log_info() { log_message "INFO" "$@"; }
log_warn() { log_message "WARN" "$@"; }
log_error() { log_message "ERROR" "$@"; }

# System load assessment
get_system_load() {
    local load_1min cpu_count
    read -r load_1min _ _ < <(uptime | awk '{print $(NF-2), $(NF-1), $NF}' | tr ',' ' ')
    cpu_count=$(sysctl -n hw.ncpu)
    
    # Calculate load percentage (1min load / cpu_count * 100)
    local load_percent
    load_percent=$(echo "scale=1; $load_1min / $cpu_count * 100" | bc -l 2>/dev/null || echo "0")
    
    echo "$load_percent"
}

# Memory usage assessment
get_memory_usage() {
    local memory_pressure
    memory_pressure=$(memory_pressure | grep "System-wide memory free percentage" | awk '{print 100-$5}' | tr -d '%' || echo "0")
    echo "$memory_pressure"
}

# Disk I/O assessment
get_disk_io_load() {
    # Simple disk I/O test - time a small write operation
    local start_time end_time duration
    start_time=$(gdate +%s.%3N 2>/dev/null || date +%s)
    dd if=/dev/zero of=/tmp/io_test bs=1024 count=1024 2>/dev/null
    rm -f /tmp/io_test
    end_time=$(gdate +%s.%3N 2>/dev/null || date +%s)
    
    duration=$(echo "scale=3; $end_time - $start_time" | bc -l 2>/dev/null || echo "1")
    
    # Convert to load score (higher is worse)
    local io_score
    io_score=$(echo "scale=1; $duration * 10" | bc -l 2>/dev/null || echo "10")
    echo "$io_score"
}

# Usage pattern analysis
analyze_usage_patterns() {
    local hour=$(date +%H)
    # Remove leading zero to avoid octal interpretation
    hour=$((10#$hour))
    local day=$(date +%u)  # 1=Monday, 7=Sunday
    
    # Define usage patterns based on typical work schedule
    local usage_level="low"
    
    # Working hours (9 AM - 6 PM, Monday-Friday)
    if [[ $day -le 5 ]] && [[ $hour -ge 9 ]] && [[ $hour -le 18 ]]; then
        usage_level="high"
    # Evening hours (6 PM - 10 PM)
    elif [[ $hour -ge 18 ]] && [[ $hour -le 22 ]]; then
        usage_level="medium"
    # Night/early morning (10 PM - 8 AM) or weekends during day
    else
        usage_level="low"
    fi
    
    echo "$usage_level"
}

# Calculate optimal delay
calculate_optimal_delay() {
    local task_type="$1"
    local current_load current_memory current_io usage_pattern
    
    current_load=$(get_system_load)
    current_memory=$(get_memory_usage)
    current_io=$(get_disk_io_load)
    usage_pattern=$(analyze_usage_patterns)
    
    log_info "System assessment - Load: ${current_load}%, Memory: ${current_memory}%, I/O: ${current_io}, Pattern: $usage_pattern"
    
    local base_delay=0
    local load_threshold=70
    local memory_threshold=80
    local io_threshold=15
    
    # Adjust thresholds based on task type
    case "$task_type" in
        "critical")
            load_threshold=90
            memory_threshold=95
            ;;
        "maintenance")
            load_threshold=50
            memory_threshold=70
            ;;
        "cleanup")
            load_threshold=30
            memory_threshold=60
            ;;
    esac
    
    # Calculate delay based on system load
    if (( $(echo "$current_load > $load_threshold" | bc -l) )); then
        base_delay=$((base_delay + 300))  # 5 minutes
        log_info "High system load detected, adding 5 minute delay"
    fi
    
    if (( $(echo "$current_memory > $memory_threshold" | bc -l) )); then
        base_delay=$((base_delay + 180))  # 3 minutes
        log_info "High memory usage detected, adding 3 minute delay"
    fi
    
    if (( $(echo "$current_io > $io_threshold" | bc -l) )); then
        base_delay=$((base_delay + 240))  # 4 minutes
        log_info "High I/O load detected, adding 4 minute delay"
    fi
    
    # Adjust based on usage pattern
    case "$usage_pattern" in
        "high")
            base_delay=$((base_delay + 600))  # 10 minutes during high usage
            ;;
        "medium")
            base_delay=$((base_delay + 300))  # 5 minutes during medium usage
            ;;
    esac
    
    echo "$base_delay"
}

# Smart delay implementation
smart_delay() {
    local task_name="$1"
    local task_type="$2"
    
    log_info "Calculating optimal delay for task: $task_name (type: $task_type)"
    
    local optimal_delay
    optimal_delay=$(calculate_optimal_delay "$task_type")
    
    # Sanitize optimal_delay - remove any whitespace/newlines and validate it's numeric
    optimal_delay=$(printf '%s' "$optimal_delay" | tr -d '[:space:]')
    [[ "$optimal_delay" =~ ^[0-9]+$ ]] || optimal_delay=0
    
    if [[ -n "$optimal_delay" ]] && [[ "$optimal_delay" != "0" ]] && (( optimal_delay > 0 )); then
        log_info "Optimal delay calculated: ${optimal_delay} seconds for $task_name"
        
        # Send notification about delay
        if command -v "$SCRIPT_DIR/smart_notifier.sh" >/dev/null 2>&1; then
            "$SCRIPT_DIR/smart_notifier.sh" send_notification "info" \
                "Maintenance Delayed" \
                "Task '$task_name' delayed by $((optimal_delay / 60)) minutes due to system load"
        fi
        
        sleep "$optimal_delay"
        log_info "Delay completed for $task_name"
    else
        log_info "No delay needed for $task_name - system resources available"
    fi
}

# Adaptive rescheduling
adaptive_reschedule() {
    local task_name="$1"
    
    log_info "Attempting adaptive reschedule for $task_name"
    
    local reschedule_attempts=0
    local max_attempts=12  # Check every 20 minutes for up to 4 hours
    
    while [[ $reschedule_attempts -lt $max_attempts ]]; do
        local system_load memory_usage
        system_load=$(get_system_load)
        memory_usage=$(get_memory_usage)
        
        # Check if system is now suitable
        if (( $(echo "$system_load < 40" | bc -l) )) && (( $(echo "$memory_usage < 60" | bc -l) )); then
            log_info "System resources now available for $task_name after $((reschedule_attempts * 20)) minutes"
            return 0
        fi
        
        log_info "System still busy (Load: ${system_load}%, Memory: ${memory_usage}%), waiting 20 minutes..."
        sleep 1200  # 20 minutes
        reschedule_attempts=$((reschedule_attempts + 1))
    done
    
    log_warn "Maximum reschedule time reached for $task_name, proceeding anyway"
    return 1
}

# Schedule optimization analysis
analyze_schedule_performance() {
    log_info "Analyzing schedule performance..."
    
    local metrics_files
    metrics_files=$(find "$METRICS_DIR" -name "system_metrics_*.log" -mtime -7 | sort)
    
    if [[ -z "$metrics_files" ]]; then
        log_warn "No recent metrics files found for schedule analysis"
        return 1
    fi
    
    # Analyze timing patterns
    local optimal_hours=()
    
    for hour in {0..23}; do
        local hour_load=0
        local hour_count=0
        
        while IFS= read -r metrics_file; do
            if [[ -f "$metrics_file" ]]; then
                while IFS= read -r line; do
                    if [[ "$line" == *"$(printf "%02d:" "$hour")"* ]] && [[ "$line" == *"Load:"* ]]; then
                        local load_value
                        load_value=$(echo "$line" | grep -o "Load: [0-9.]*" | awk '{print $2}')
                        if [[ -n "$load_value" ]]; then
                            hour_load=$(echo "scale=2; $hour_load + $load_value" | bc -l)
                            hour_count=$((hour_count + 1))
                        fi
                    fi
                done < "$metrics_file"
            fi
        done <<< "$metrics_files"
        
        if [[ $hour_count -gt 0 ]]; then
            local avg_load
            avg_load=$(echo "scale=2; $hour_load / $hour_count" | bc -l)
            
            # Consider hours with average load < 30% as optimal
            if (( $(echo "$avg_load < 30" | bc -l) )); then
                optimal_hours+=("$hour")
            fi
        fi
    done
    
    log_info "Optimal maintenance hours identified: ${optimal_hours[*]}"
    
    # Save recommendations
    cat > "$SCRIPT_DIR/../reports/schedule_recommendations.txt" <<EOF
Schedule Performance Analysis - $(date)

Optimal maintenance hours based on 7-day analysis:
$(printf "%s\n" "${optimal_hours[@]}" | while read -r hour; do echo "  - $(printf "%02d:00" "$hour")"; done)

Current schedule efficiency can be improved by:
1. Moving intensive tasks to identified low-load hours
2. Using adaptive delays during peak usage
3. Implementing smart rescheduling for resource-heavy operations

EOF
    
    log_info "Schedule recommendations saved to reports/schedule_recommendations.txt"
}

# Main execution
main() {
    local action="${1:-help}"
    
    case "$action" in
        "delay")
            if [[ $# -lt 3 ]]; then
                log_error "Usage: $0 delay <task_name> <task_type>"
                exit 1
            fi
            smart_delay "$2" "$3"
            ;;
        "reschedule")
            if [[ $# -lt 2 ]]; then
                log_error "Usage: $0 reschedule <task_name> [max_hours]"
                exit 1
            fi
            adaptive_reschedule "$2" "$(date)" "${3:-4}"
            ;;
        "analyze")
            analyze_schedule_performance
            ;;
        "status")
            log_info "System Status:"
            log_info "  Load: $(get_system_load)%"
            log_info "  Memory: $(get_memory_usage)%"
            log_info "  I/O Load: $(get_disk_io_load)"
            log_info "  Usage Pattern: $(analyze_usage_patterns)"
            ;;
        "help")
            cat << EOF
Smart Scheduler - Adaptive maintenance scheduling

Usage: $0 <action> [arguments]

Actions:
  delay <task_name> <task_type>    - Calculate and apply optimal delay
  reschedule <task_name> [hours]   - Adaptively reschedule task
  analyze                          - Analyze schedule performance
  status                           - Show current system status
  help                            - Show this help message

Task Types:
  critical    - Critical system tasks (higher thresholds)
  maintenance - Regular maintenance tasks
  cleanup     - Cleanup and optimization tasks

Examples:
  $0 delay "brew_maintenance" "maintenance"
  $0 reschedule "monthly_cleanup" 6
  $0 analyze
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