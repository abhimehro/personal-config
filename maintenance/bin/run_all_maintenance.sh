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

# Function to run a script with logging
run_script() {
    local script_name="$1"
    local script_path="$SCRIPT_DIR/$script_name"
    local log_file="$LOG_DIR/${script_name%.sh}_$TIMESTAMP.log"
    
    if [[ -f "$script_path" && -x "$script_path" ]]; then
        echo "Running $script_name..." | tee -a "$MASTER_LOG"
        if "$script_path" > "$log_file" 2>&1; then
            echo "✅ $script_name completed successfully" | tee -a "$MASTER_LOG"
        else
            echo "❌ $script_name failed (check $log_file)" | tee -a "$MASTER_LOG"
        fi
    else
        echo "⚠️  $script_name not found or not executable" | tee -a "$MASTER_LOG"
    fi
}

# Function to run lightweight scripts (weekly)
run_weekly_maintenance() {
    echo "=== Weekly Maintenance Tasks ===" | tee -a "$MASTER_LOG"
    
    # System health check
    run_script "health_check.sh"
    
    # Quick cleanup
    run_script "quick_cleanup.sh"
    
    # Homebrew maintenance
    run_script "brew_maintenance.sh"
    
    # Node.js maintenance
    run_script "node_maintenance.sh"
    
    # OneDrive monitoring
    run_script "onedrive_monitor.sh"
}

# Function to run comprehensive scripts (monthly)
run_monthly_maintenance() {
    echo "=== Monthly Maintenance Tasks ===" | tee -a "$MASTER_LOG"
    
    # Run weekly tasks first
    run_weekly_maintenance
    
    # System cleanup
    run_script "system_cleanup.sh"
    
    # Editor cleanup
    run_script "editor_cleanup.sh"
    
    # Deep cleaner (be careful with this one)
    echo "Running deep cleaner with caution..." | tee -a "$MASTER_LOG"
    run_script "deep_cleaner.sh"
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
            run_script "health_check.sh"
            ;;
        "quick")
            run_script "quick_cleanup.sh"
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