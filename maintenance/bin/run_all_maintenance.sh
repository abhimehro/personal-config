#!/bin/bash

# Master Maintenance Script
# Orchestrates all maintenance tasks with proper logging and error handling
# Created: $(date)

set -euo pipefail

# Configuration
export RUN_START=$(date +%s)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../tmp"
LOCK_DIR="/tmp/run_all_maintenance.lock"
LOCK_CONTEXT_LOG="$LOG_DIR/lock_context_$(date +%Y%m%d-%H%M%S).log"
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
MASTER_LOG="$LOG_DIR/maintenance_master_$TIMESTAMP.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Simple locking to prevent concurrent runs with stale lock detection
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    # Check if lock is stale (older than 2 hours)
    if [[ -d "$LOCK_DIR" ]]; then
        LOCK_AGE=$(($(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || date +%s)))
        if [[ $LOCK_AGE -gt 7200 ]]; then
            LOCK_MSG="WARNING: Removing stale lock (age: $((LOCK_AGE/60)) minutes)"
            echo "$LOCK_MSG"
            echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $LOCK_MSG [RUN_START: $RUN_START] [LOCK_DIR: $LOCK_DIR]" >> "$LOCK_CONTEXT_LOG"
            rm -rf "$LOCK_DIR" 2>/dev/null || true
            # Try to acquire lock again
            if ! mkdir "$LOCK_DIR" 2>/dev/null; then
                echo "ERROR: Failed to acquire lock after stale removal"
                exit 0
            fi
        else
            echo "Another instance is already running (lock: $LOCK_DIR, age: $((LOCK_AGE/60)) min)"
            exit 0
        fi
    fi
fi
trap 'rm -rf "$LOCK_DIR" "$LOG_DIR"/status_*_"$TIMESTAMP".log 2>/dev/null || true' EXIT INT TERM

# Initialize master log
echo "=== Master Maintenance Run Started: $(date) ===" | tee "$MASTER_LOG"

# Function to run a script with smart scheduling and logging
# Usage: run_script script_name task_type [log_target]
run_script() {
    local script_name="$1"
    local task_type="${2:-maintenance}"  # Default to maintenance type
    local log_target="${3:-$MASTER_LOG}" # Where to write status output (default: MASTER_LOG)
    local script_path="$SCRIPT_DIR/$script_name"
    local log_file="$LOG_DIR/${script_name%.sh}_$TIMESTAMP.log"
    local smart_scheduler="$SCRIPT_DIR/smart_scheduler.sh"
    
    # Helper to log to target (file or stdout)
    log_status() {
        if [[ "$log_target" == "/dev/stdout" ]]; then
            echo "$@"
        else
            echo "$@" | tee -a "$log_target"
        fi
    }

    if [[ -f "$script_path" && -x "$script_path" ]]; then
        log_status "Running $script_name with smart scheduling..."
        
        # Apply smart delay if scheduler is available
        if [[ -f "$smart_scheduler" && -x "$smart_scheduler" ]]; then
            "$smart_scheduler" delay "${script_name%.sh}" "$task_type" 2>&1 | tee -a "$log_target"
        fi
        
        # Execute the actual script
        if "$script_path" > "$log_file" 2>&1; then
            log_status "✅ $script_name completed successfully"
            
            # Send success notification if notifier is available
            local notifier="$SCRIPT_DIR/smart_notifier.sh"
            if [[ -f "$notifier" && -x "$notifier" ]]; then
                source "$notifier" 2>/dev/null || true
                smart_notify "success" "Maintenance Task Completed" "${script_name%.sh} finished successfully" 2>/dev/null || true
            fi
        else
            log_status "❌ $script_name failed (check $log_file)"
            
            # Send error notification if notifier is available
            local notifier="$SCRIPT_DIR/smart_notifier.sh"
            if [[ -f "$notifier" && -x "$notifier" ]]; then
                source "$notifier" 2>/dev/null || true
                smart_notify "critical" "Maintenance Task Failed" "${script_name%.sh} encountered errors" 2>/dev/null || true
            fi
        fi
    else
        log_status "⚠️  $script_name not found or not executable"
    fi
}

# Function to run lightweight scripts (weekly)
run_weekly_maintenance() {
    echo "=== Weekly Maintenance Tasks ===" | tee -a "$MASTER_LOG"
    
    # System health check (critical - always runs)
    run_script "health_check.sh" "critical"
    
    # Quick cleanup
    run_script "quick_cleanup.sh" "cleanup"
    
    echo "Starting parallel maintenance tasks..." | tee -a "$MASTER_LOG"
    # Parallel execution of independent tasks to speed up maintenance
    # Capture status output to separate files to avoid interleaved logs

    local brew_status="$LOG_DIR/status_brew_$TIMESTAMP.log"
    local node_status="$LOG_DIR/status_node_$TIMESTAMP.log"
    local onedrive_status="$LOG_DIR/status_onedrive_$TIMESTAMP.log"
    local service_status="$LOG_DIR/status_service_$TIMESTAMP.log"

    pids=""
    
    # Homebrew maintenance (heavy I/O + network)
    (run_script "brew_maintenance.sh" "maintenance" "$brew_status") &
    pids="$pids $!"
    
    # Node.js maintenance (heavy I/O + network)
    (run_script "node_maintenance.sh" "maintenance" "$node_status") &
    pids="$pids $!"

    # OneDrive monitoring (light)
    (run_script "onedrive_monitor.sh" "maintenance" "$onedrive_status") &
    pids="$pids $!"

    # Service optimization (light)
    (run_script "service_optimizer.sh" "optimization" "$service_status") &
    pids="$pids $!"

    # Wait for all parallel tasks to complete
    for pid in $pids; do
        wait $pid
    done

    # Aggregate status logs to master log
    cat "$brew_status" "$node_status" "$onedrive_status" "$service_status" >> "$MASTER_LOG"
    rm -f "$brew_status" "$node_status" "$onedrive_status" "$service_status"

    echo "Parallel maintenance tasks completed." | tee -a "$MASTER_LOG"
    
    # Performance optimization (run optimize command)
    echo "Running performance optimization..." | tee -a "$MASTER_LOG"
    local perf_optimizer="$SCRIPT_DIR/performance_optimizer.sh"
    if [[ -f "$perf_optimizer" && -x "$perf_optimizer" ]]; then
        local perf_log="$LOG_DIR/performance_optimizer_$TIMESTAMP.log"
        if "$perf_optimizer" optimize > "$perf_log" 2>&1; then
            echo "✅ Performance optimization completed successfully" | tee -a "$MASTER_LOG"
        else
            echo "❌ Performance optimization failed (check $perf_log)" | tee -a "$MASTER_LOG"
        fi
    else
        echo "⚠️  performance_optimizer.sh not found or not executable" | tee -a "$MASTER_LOG"
    fi
}

# Function to run comprehensive scripts (monthly)
run_monthly_maintenance() {
    echo "=== Monthly Maintenance Tasks ===" | tee -a "$MASTER_LOG"
    
    # Run weekly tasks first
    run_weekly_maintenance
    
    # System cleanup
    run_script "system_cleanup.sh" "cleanup"
    
    # Editor cleanup
    run_script "editor_cleanup.sh" "cleanup"
    
    # Deep cleaner (be careful with this one)
    echo "Running deep cleaner with caution..." | tee -a "$MASTER_LOG"
    run_script "deep_cleaner.sh" "cleanup"
}

# Determine what to run based on argument or day of month
if [[ $# -eq 1 ]]; then
    case "$1" in
        "weekly")
            run_weekly_maintenance
            ;;
        "monthly")
            run_monthly_maintenance
            ;;
        "health")
            run_script "health_check.sh" "critical"
            ;;
        "quick")
            run_script "quick_cleanup.sh" "cleanup"
            ;;
        *)
            echo "Usage: $0 [weekly|monthly|health|quick]"
            echo "  weekly  - Run weekly maintenance tasks"
            echo "  monthly - Run comprehensive monthly maintenance"
            echo "  health  - Run only health check"
            echo "  quick   - Run only quick cleanup"
            exit 1
            ;;
    esac
else
    # Default to weekly maintenance
    run_weekly_maintenance
fi

# Generate error summary
if [[ -x "$SCRIPT_DIR/generate_error_summary.sh" ]]; then
    SUMMARY_FILE=$("$SCRIPT_DIR/generate_error_summary.sh" 2>/dev/null || echo "")
    if [[ -n "$SUMMARY_FILE" ]] && [[ -f "$SUMMARY_FILE" ]]; then
        echo "Error summary generated: $SUMMARY_FILE" | tee -a "$MASTER_LOG"
    fi
fi

# Summary
echo "=== Master Maintenance Run Completed: $(date) ===" | tee -a "$MASTER_LOG"
echo "Logs saved to: $LOG_DIR" | tee -a "$MASTER_LOG"

# Clean up old log files (keep last 10 runs)
find "$LOG_DIR" -name "maintenance_master_*.log" -type f | sort -r | tail -n +11 | xargs rm -f

echo "Master maintenance script completed. Check $MASTER_LOG for details."