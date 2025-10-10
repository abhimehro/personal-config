#!/usr/bin/env bash

# Monthly maintenance orchestrator script - Runs 1st of each month at 9:00 AM
# Note: Not using -e flag to allow individual tasks to fail without stopping the whole process
set -o pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

# Only run on the 1st of the month or if FORCE_RUN is set
DAY_OF_MONTH=$(date +%-d)  # %-d removes leading zero
if [[ "$DAY_OF_MONTH" -ne 1 ]] && [[ "${FORCE_RUN:-0}" != "1" ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] [monthly_maintenance] Monthly maintenance skipped - only runs on 1st of month (today is $(date +%B) $(date +%d))"
    exit 0
fi

# Basic logging
log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [monthly_maintenance] $*" | tee -a "$LOG_DIR/monthly_maintenance.log"
}

log_warn() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [WARNING] [monthly_maintenance] $*" | tee -a "$LOG_DIR/monthly_maintenance.log"
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_info "Monthly maintenance started for $(date +%B) $(date +%Y)"

TASKS_COMPLETED=0
TASKS_FAILED=0

# Function to run a maintenance script
run_task() {
    local script_name="$1"
    local script_path="$SCRIPT_DIR/$script_name"
    
    if [[ ! -f "$script_path" ]]; then
        log_warn "Script not found: $script_path"
        ((TASKS_FAILED++))
        return 1
    fi
    
    if [[ ! -x "$script_path" ]]; then
        log_warn "Script not executable: $script_path"
        ((TASKS_FAILED++))
        return 1
    fi
    
    log_info "Running monthly task: $script_name"
    
    # Set AUTOMATED_RUN and run the script
    if AUTOMATED_RUN=1 "$script_path" 2>&1 | tee -a "$LOG_DIR/monthly_maintenance.log"; then
        log_info "Monthly task completed successfully: $script_name"
        ((TASKS_COMPLETED++))
        return 0
    else
        log_warn "Monthly task failed: $script_name"
        ((TASKS_FAILED++))
        return 1
    fi
}

# Run monthly maintenance tasks
log_info "=== MONTHLY DEEP CLEANING TASKS ==="

# 1) System cleanup (deep monthly version)
run_task "system_cleanup.sh"

# 2) Editor cache cleanup
run_task "editor_cleanup.sh" 

# 3) Deep system analysis and recommendations
run_task "deep_cleaner.sh"

# Summary
log_info "=== MONTHLY MAINTENANCE SUMMARY ==="
log_info "Tasks completed: $TASKS_COMPLETED"
log_info "Tasks failed: $TASKS_FAILED"

TOTAL_TASKS=$((TASKS_COMPLETED + TASKS_FAILED))
if [[ $TASKS_FAILED -eq 0 ]]; then
    STATUS="✅ All monthly tasks completed successfully ($TASKS_COMPLETED/$TOTAL_TASKS)"
    log_info "Monthly maintenance completed successfully"
else
    STATUS="⚠️ Monthly maintenance completed with ${TASKS_FAILED} failures ($TASKS_COMPLETED/$TOTAL_TASKS)"
    log_warn "Monthly maintenance had $TASKS_FAILED failures"
fi

# Notification
if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"$STATUS\" with title \"Monthly Maintenance\"" 2>/dev/null || true
fi

log_info "Monthly maintenance finished: $STATUS"
echo "Monthly maintenance completed!"

# Exit with error code if any tasks failed
exit $TASKS_FAILED