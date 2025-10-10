#!/bin/bash

# Master Maintenance Script
# Orchestrates all maintenance tasks with proper logging and error handling
# Created: $(date)

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$HOME/Documents/dev/personal-config/maintenance/tmp"
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
MASTER_LOG="$LOG_DIR/maintenance_master_$TIMESTAMP.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Initialize master log
echo "=== Master Maintenance Run Started: $(date) ===" | tee "$MASTER_LOG"

# Function to run a script with smart scheduling and logging
run_script() {
    local script_name="$1"
    local task_type="${2:-maintenance}"  # Default to maintenance type
    local script_path="$SCRIPT_DIR/$script_name"
    local log_file="$LOG_DIR/${script_name%.sh}_$TIMESTAMP.log"
    local smart_scheduler="$SCRIPT_DIR/smart_scheduler.sh"
    
    if [[ -f "$script_path" && -x "$script_path" ]]; then
        echo "Running $script_name with smart scheduling..." | tee -a "$MASTER_LOG"
        
        # Apply smart delay if scheduler is available
        if [[ -f "$smart_scheduler" && -x "$smart_scheduler" ]]; then
            "$smart_scheduler" delay "${script_name%.sh}" "$task_type" 2>&1 | tee -a "$MASTER_LOG"
        fi
        
        # Execute the actual script
        if "$script_path" > "$log_file" 2>&1; then
            echo "✅ $script_name completed successfully" | tee -a "$MASTER_LOG"
            
            # Send success notification if notifier is available
            local notifier="$SCRIPT_DIR/smart_notifier.sh"
            if [[ -f "$notifier" && -x "$notifier" ]]; then
                source "$notifier" 2>/dev/null || true
                smart_notify "success" "Maintenance Task Completed" "${script_name%.sh} finished successfully" 2>/dev/null || true
            fi
        else
            echo "❌ $script_name failed (check $log_file)" | tee -a "$MASTER_LOG"
            
            # Send error notification if notifier is available
            local notifier="$SCRIPT_DIR/smart_notifier.sh"
            if [[ -f "$notifier" && -x "$notifier" ]]; then
                source "$notifier" 2>/dev/null || true
                smart_notify "critical" "Maintenance Task Failed" "${script_name%.sh} encountered errors" 2>/dev/null || true
            fi
        fi
    else
        echo "⚠️  $script_name not found or not executable" | tee -a "$MASTER_LOG"
    fi
}

# Function to run lightweight scripts (weekly)
run_weekly_maintenance() {
    echo "=== Weekly Maintenance Tasks ===" | tee -a "$MASTER_LOG"
    
    # System health check (critical - always runs)
    run_script "health_check.sh" "critical"
    
    # Quick cleanup
    run_script "quick_cleanup.sh" "cleanup"
    
    # Homebrew maintenance
    run_script "brew_maintenance.sh" "maintenance"
    
    # Node.js maintenance
    run_script "node_maintenance.sh" "maintenance"
    
    # OneDrive monitoring
    run_script "onedrive_monitor.sh" "maintenance"
    
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

# Summary
echo "=== Master Maintenance Run Completed: $(date) ===" | tee -a "$MASTER_LOG"
echo "Logs saved to: $LOG_DIR" | tee -a "$MASTER_LOG"

# Clean up old log files (keep last 10 runs)
find "$LOG_DIR" -name "maintenance_master_*.log" -type f | sort -r | tail -n +11 | xargs rm -f

echo "Master maintenance script completed. Check $MASTER_LOG for details."