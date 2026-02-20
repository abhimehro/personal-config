#!/usr/bin/env bash

# Advanced Error Handling and Recovery System
# Provides retry mechanisms, circuit breakers, and intelligent failure recovery

# Error handling configuration
ERROR_LOG="$HOME/Library/Logs/maintenance/error_handler.log"
RETRY_CONFIG_FILE="$HOME/Library/Logs/maintenance/retry_config.json"
CIRCUIT_BREAKER_STATE_FILE="$HOME/Library/Logs/maintenance/circuit_breaker_state.json"

mkdir -p "$(dirname "$ERROR_LOG")"

# Initialize configuration files if they don't exist
if [[ ! -f "$RETRY_CONFIG_FILE" ]]; then
    cat > "$RETRY_CONFIG_FILE" << 'EOF'
{
  "default": {
    "max_retries": 3,
    "base_delay": 1,
    "max_delay": 30,
    "backoff_multiplier": 2
  },
  "network": {
    "max_retries": 5,
    "base_delay": 2,
    "max_delay": 60,
    "backoff_multiplier": 2
  },
  "disk": {
    "max_retries": 2,
    "base_delay": 5,
    "max_delay": 30,
    "backoff_multiplier": 1.5
  },
  "homebrew": {
    "max_retries": 3,
    "base_delay": 10,
    "max_delay": 120,
    "backoff_multiplier": 2
  }
}
EOF
fi

if [[ ! -f "$CIRCUIT_BREAKER_STATE_FILE" ]]; then
    echo '{}' > "$CIRCUIT_BREAKER_STATE_FILE"
fi

# Logging function
error_log() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$timestamp [ERROR_HANDLER] $*" | tee -a "$ERROR_LOG"
}

# Retry mechanism with exponential backoff
retry_with_backoff() {
    local operation_name="$1"
    local category="${2:-default}"
    shift 2
    local command=("$@")
    
    # Get retry configuration
    local max_retries=$(get_config_value "$category" "max_retries" 3)
    local base_delay=$(get_config_value "$category" "base_delay" 1)
    local max_delay=$(get_config_value "$category" "max_delay" 30)
    local backoff_multiplier=$(get_config_value "$category" "backoff_multiplier" 2)
    
    local attempt=1
    local delay=$base_delay
    
    while [[ $attempt -le $max_retries ]]; do
        error_log "Attempting '$operation_name' (attempt $attempt/$max_retries)"
        
        if "${command[@]}"; then
            error_log "Operation '$operation_name' succeeded on attempt $attempt"
            return 0
        fi
        
        local exit_code=$?
        error_log "Operation '$operation_name' failed on attempt $attempt (exit code: $exit_code)"
        
        if [[ $attempt -eq $max_retries ]]; then
            error_log "Operation '$operation_name' failed after $max_retries attempts"
            record_failure "$operation_name" "$exit_code"
            return $exit_code
        fi
        
        error_log "Waiting ${delay}s before retry..."
        sleep "$delay"
        
        # Calculate next delay with exponential backoff
        delay=$(( delay * backoff_multiplier ))
        if [[ $delay -gt $max_delay ]]; then
            delay=$max_delay
        fi
        
        ((attempt++))
    done
    
    return 1
}

# Circuit breaker pattern
circuit_breaker_check() {
    local service_name="$1"
    local failure_threshold="${2:-5}"
    local recovery_timeout="${3:-300}" # 5 minutes default
    
    local current_time=$(date +%s)
    
    # Get current state
    local cb_state=$(get_circuit_breaker_state "$service_name")
    local state_status=$(echo "$cb_state" | jq -r '.status // "closed"')
    local failure_count=$(echo "$cb_state" | jq -r '.failure_count // 0')
    local last_failure=$(echo "$cb_state" | jq -r '.last_failure // 0')
    
    case "$state_status" in
        "closed")
            # Normal operation
            return 0
            ;;
        "open")
            # Circuit is open, check if recovery timeout has passed
            local time_since_failure=$((current_time - last_failure))
            if [[ $time_since_failure -gt $recovery_timeout ]]; then
                error_log "Circuit breaker for '$service_name' moving from OPEN to HALF_OPEN"
                set_circuit_breaker_state "$service_name" "half_open" "$failure_count" "$last_failure"
                return 0
            else
                local wait_time=$((recovery_timeout - time_since_failure))
                error_log "Circuit breaker for '$service_name' is OPEN. Waiting ${wait_time}s before retry"
                return 1
            fi
            ;;
        "half_open")
            # Testing if service has recovered
            return 0
            ;;
        *)
            # Unknown state, default to closed
            set_circuit_breaker_state "$service_name" "closed" 0 0
            return 0
            ;;
    esac
}

# Record success for circuit breaker
circuit_breaker_success() {
    local service_name="$1"
    error_log "Circuit breaker for '$service_name' recording SUCCESS"
    set_circuit_breaker_state "$service_name" "closed" 0 0
}

# Record failure for circuit breaker
circuit_breaker_failure() {
    local service_name="$1"
    local failure_threshold="${2:-5}"
    
    local cb_state=$(get_circuit_breaker_state "$service_name")
    local failure_count=$(echo "$cb_state" | jq -r '.failure_count // 0')
    local current_time=$(date +%s)
    
    ((failure_count++))
    
    error_log "Circuit breaker for '$service_name' recording FAILURE ($failure_count/$failure_threshold)"
    
    if [[ $failure_count -ge $failure_threshold ]]; then
        error_log "Circuit breaker for '$service_name' opening due to failure threshold"
        set_circuit_breaker_state "$service_name" "open" "$failure_count" "$current_time"
    else
        set_circuit_breaker_state "$service_name" "closed" "$failure_count" "$current_time"
    fi
}

# Execute command with circuit breaker protection
execute_with_circuit_breaker() {
    local service_name="$1"
    local operation_name="$2"
    local failure_threshold="${3:-5}"
    local recovery_timeout="${4:-300}"
    shift 4
    local command=("$@")
    
    if ! circuit_breaker_check "$service_name" "$failure_threshold" "$recovery_timeout"; then
        error_log "Circuit breaker prevented execution of '$operation_name' for service '$service_name'"
        return 1
    fi
    
    if "${command[@]}"; then
        circuit_breaker_success "$service_name"
        return 0
    else
        local exit_code=$?
        circuit_breaker_failure "$service_name" "$failure_threshold"
        return $exit_code
    fi
}

# Enhanced retry with circuit breaker
retry_with_circuit_breaker() {
    local service_name="$1"
    local operation_name="$2"
    local category="${3:-default}"
    local failure_threshold="${4:-5}"
    local recovery_timeout="${5:-300}"
    shift 5
    local command=("$@")
    
    execute_with_circuit_breaker "$service_name" "$operation_name" "$failure_threshold" "$recovery_timeout" \
        retry_with_backoff "$operation_name" "$category" "${command[@]}"
}

# Helper functions
get_config_value() {
    local category="$1"
    local key="$2"
    local default="$3"
    
    if [[ -f "$RETRY_CONFIG_FILE" ]] && command -v jq >/dev/null 2>&1; then
        jq -r ".${category}.${key} // .default.${key} // ${default}" "$RETRY_CONFIG_FILE" 2>/dev/null || echo "$default"
    else
        echo "$default"
    fi
}

get_circuit_breaker_state() {
    local service_name="$1"
    
    if [[ -f "$CIRCUIT_BREAKER_STATE_FILE" ]] && command -v jq >/dev/null 2>&1; then
        jq -r ".\"$service_name\" // {}" "$CIRCUIT_BREAKER_STATE_FILE" 2>/dev/null || echo '{}'
    else
        echo '{}'
    fi
}

set_circuit_breaker_state() {
    local service_name="$1"
    local status="$2"
    local failure_count="$3"
    local last_failure="$4"
    
    if command -v jq >/dev/null 2>&1; then
        local temp_file=$(mktemp)
        jq --arg service "$service_name" \
           --arg status "$status" \
           --argjson count "$failure_count" \
           --argjson timestamp "$last_failure" \
           '.[$service] = {status: $status, failure_count: $count, last_failure: $timestamp}' \
           "$CIRCUIT_BREAKER_STATE_FILE" > "$temp_file" && mv "$temp_file" "$CIRCUIT_BREAKER_STATE_FILE"
    fi
}

record_failure() {
    local operation="$1"
    local exit_code="$2"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    
    error_log "FAILURE RECORDED: Operation='$operation', ExitCode='$exit_code', Time='$timestamp'"
    
    # Record in failure history for analysis
    local failure_file="$HOME/Library/Logs/maintenance/failure_history.jsonl"
    if command -v jq >/dev/null 2>&1; then
        echo "{\"timestamp\":\"$timestamp\",\"operation\":\"$operation\",\"exit_code\":$exit_code}" >> "$failure_file"
    fi
}

# Self-healing functions
auto_recover() {
    local service_name="$1"
    local recovery_script="$2"
    
    error_log "Attempting auto-recovery for service '$service_name'"
    
    if [[ -x "$recovery_script" ]]; then
        if "$recovery_script"; then
            error_log "Auto-recovery succeeded for service '$service_name'"
            circuit_breaker_success "$service_name"
            return 0
        else
            error_log "Auto-recovery failed for service '$service_name'"
            return 1
        fi
    else
        error_log "Recovery script not found or not executable: $recovery_script"
        return 1
    fi
}

# Health check function
system_health_check() {
    local issues_found=0
    
    error_log "Starting system health check"
    
    # Check disk space
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    if [[ ${disk_usage:-0} -gt 90 ]]; then
        error_log "CRITICAL: Disk usage is ${disk_usage}%"
        ((issues_found++))
    fi
    
    # Check memory pressure
    if command -v vm_stat >/dev/null 2>&1; then
        local free_pages=$(vm_stat | awk '/Pages free:/ {print $3}' | tr -d '.' || echo "0")
        local page_size=$(vm_stat | awk '/page size of/ {print $8}' || echo "4096")
        local free_mb=$(( (free_pages * page_size) / 1024 / 1024 ))
        
        if [[ $free_mb -lt 500 ]]; then
            error_log "WARNING: Low memory - only ${free_mb}MB free"
            ((issues_found++))
        fi
    fi
    
    # Check maintenance agents
    local failed_agents=$(launchctl list | grep "com.abhimehrotra.maintenance" | awk '$3 != "0" {count++} END {print count+0}')
    if [[ ${failed_agents:-0} -gt 0 ]]; then
        error_log "WARNING: $failed_agents maintenance agents have failed"
        ((issues_found++))
    fi
    
    if [[ $issues_found -eq 0 ]]; then
        error_log "System health check passed - no issues found"
        return 0
    else
        error_log "System health check found $issues_found issues"
        return 1
    fi
}

# Emergency recovery function
emergency_recovery() {
    error_log "EMERGENCY RECOVERY initiated"
    
    local recovery_actions=0
    
    # 1. Try to restart failed launch agents
    local failed_agents=$(launchctl list | grep "com.abhimehrotra.maintenance" | awk '$3 != "0" {print $1}')
    if [[ -n "$failed_agents" ]]; then
        error_log "Attempting to restart failed maintenance agents"
        echo "$failed_agents" | while read -r agent; do
            if launchctl stop "$agent" 2>/dev/null && launchctl start "$agent" 2>/dev/null; then
                error_log "Successfully restarted agent: $agent"
                ((recovery_actions++))
            fi
        done
    fi
    
    # 2. Clear temporary files if disk space is critical
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    if [[ ${disk_usage:-0} -gt 95 ]]; then
        error_log "Critical disk space - attempting emergency cleanup"
        if rm -rf /tmp/maintenance_* 2>/dev/null; then
            error_log "Emergency cleanup of maintenance temp files completed"
            ((recovery_actions++))
        fi
    fi
    
    # 3. Reset circuit breakers if all are open
    local open_breakers=$(jq -r 'to_entries[] | select(.value.status == "open") | .key' "$CIRCUIT_BREAKER_STATE_FILE" 2>/dev/null | wc -l)
    if [[ ${open_breakers:-0} -gt 3 ]]; then
        error_log "Too many circuit breakers open - resetting all"
        echo '{}' > "$CIRCUIT_BREAKER_STATE_FILE"
        ((recovery_actions++))
    fi
    
    error_log "Emergency recovery completed - $recovery_actions actions taken"
    return 0
}

# Example usage and testing functions
test_error_handler() {
    error_log "Testing error handling system"
    
    # Test retry mechanism
    echo "Testing retry mechanism..."
    retry_with_backoff "test_operation" "default" false
    
    # Test circuit breaker
    echo "Testing circuit breaker..."
    for i in {1..6}; do
        execute_with_circuit_breaker "test_service" "test_op_$i" 3 60 false
    done
    
    # Test health check
    echo "Testing health check..."
    system_health_check
    
    error_log "Error handling system test completed"
}

# Export functions for use in other scripts
export -f retry_with_backoff
export -f retry_with_circuit_breaker
export -f execute_with_circuit_breaker
export -f circuit_breaker_check
export -f system_health_check
export -f emergency_recovery
export -f error_log

error_log "Error handling system loaded successfully"