#!/usr/bin/env bash

# Weekly maintenance orchestrator script
# Note: Not using -e flag to allow individual tasks to fail without stopping the whole process
set -o pipefail

# Configuration
export RUN_START=$(date +%s)
LOG_DIR="$HOME/Library/Logs/maintenance"
LOCK_DIR="/tmp/weekly_maintenance.lock"
LOCK_CONTEXT_LOG="$LOG_DIR/lock_context_$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$LOG_DIR"

# Simple locking to prevent concurrent runs with stale lock detection
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    # Check if lock is stale (older than 2 hours)
    if [[ -d "$LOCK_DIR" ]]; then
        LOCK_AGE=$(($(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || date +%s)))
        if [[ $LOCK_AGE -gt 7200 ]]; then
            LOCK_MSG="$(date '+%Y-%m-%d %H:%M:%S') [WARNING] Removing stale lock (age: $((LOCK_AGE/60)) minutes)"
            echo "$LOCK_MSG"
            echo "$LOCK_MSG [RUN_START: $RUN_START] [LOCK_DIR: $LOCK_DIR]" >> "$LOCK_CONTEXT_LOG"
            rm -rf "$LOCK_DIR" 2>/dev/null || true
            # Try to acquire lock again
            if ! mkdir "$LOCK_DIR" 2>/dev/null; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] Failed to acquire lock after stale removal"
                exit 0
            fi
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] Another instance is already running (lock: $LOCK_DIR, age: $((LOCK_AGE/60)) min)"
            exit 0
        fi
    fi
fi
trap 'rm -rf "$LOCK_DIR" 2>/dev/null || true' EXIT INT TERM

# Only run on Mondays or if FORCE_RUN is set
DAY_OF_WEEK=$(date +%u)  # 1 = Monday
if [[ "$DAY_OF_WEEK" -ne 1 ]] && [[ "${FORCE_RUN:-0}" != "1" ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] [weekly_maintenance] Weekly maintenance skipped - only runs on Mondays (today is $(date +%A))"
    exit 0
fi

# Basic logging
log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [weekly_maintenance] $*" | tee -a "$LOG_DIR/weekly_maintenance.log"
}

log_warn() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [WARNING] [weekly_maintenance] $*" | tee -a "$LOG_DIR/weekly_maintenance.log"
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_info "Weekly maintenance started for $(date +%A), $(date +%B) $(date +%d), $(date +%Y)"

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
    
    log_info "Running weekly task: $script_name"
    
    # Set AUTOMATED_RUN and run the script
    if AUTOMATED_RUN=1 "$script_path" 2>&1 | tee -a "$LOG_DIR/weekly_maintenance.log"; then
        log_info "Weekly task completed successfully: $script_name"
        ((TASKS_COMPLETED++))
        return 0
    else
        log_warn "Weekly task failed: $script_name"
        ((TASKS_FAILED++))
        return 1
    fi
}

# Run weekly maintenance tasks
log_info "=== WEEKLY MAINTENANCE TASKS ==="

# 1) Quick system cleanup (lighter weekly version)
run_task "quick_cleanup.sh"

# 2) Node.js maintenance (weekly is appropriate for node modules)
run_task "node_maintenance.sh"

# 3) Google Drive monitoring and health check (UPDATED)
run_task "google_drive_monitor.sh"

# Summary
log_info "=== WEEKLY MAINTENANCE SUMMARY ==="
log_info "Tasks completed: $TASKS_COMPLETED"
log_info "Tasks failed: $TASKS_FAILED"

TOTAL_TASKS=$((TASKS_COMPLETED + TASKS_FAILED))
if [[ $TASKS_FAILED -eq 0 ]]; then
    STATUS="✅ All weekly tasks completed successfully ($TASKS_COMPLETED/$TOTAL_TASKS)"
    log_info "Weekly maintenance completed successfully"
else
    STATUS="⚠️ Weekly maintenance completed with ${TASKS_FAILED} failures ($TASKS_COMPLETED/$TOTAL_TASKS)"
    log_warn "Weekly maintenance had $TASKS_FAILED failures"
fi

# Notification
if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"$STATUS\" with title \"Weekly Maintenance\"" 2>/dev/null || true
fi

log_info "Weekly maintenance finished: $STATUS"

# Generate error summary
if [[ -x "$SCRIPT_DIR/generate_error_summary.sh" ]]; then
    SUMMARY_FILE=$("$SCRIPT_DIR/generate_error_summary.sh" 2>/dev/null || echo "")
    if [[ -n "$SUMMARY_FILE" ]] && [[ -f "$SUMMARY_FILE" ]]; then
        log_info "Error summary generated: $SUMMARY_FILE"
    fi
fi

# Enhanced notification with terminal-notifier (actionable)
if command -v terminal-notifier >/dev/null 2>&1; then
    if [[ $TASKS_FAILED -gt 0 ]]; then
  terminal-notifier -title "Weekly Maintenance" \
    -subtitle "Completed with $TASKS_FAILED task error(s)" \
    -message "Click for details" \
    -group "maintenance" \
    -execute "/Users/speedybee/Library/Maintenance/bin/view_logs.sh weekly" 2>/dev/null || true
    else
        terminal-notifier -title "Weekly Maintenance" \
            -subtitle "All tasks completed successfully" \
            -message "$TASKS_COMPLETED/$TASKS_COMPLETED tasks passed" \
            -group "maintenance" 2>/dev/null || true
    fi
elif command -v osascript >/dev/null 2>&1; then
    # Fallback to osascript
    osascript -e "display notification \"$STATUS\" with title \"Weekly Maintenance\"" 2>/dev/null || true
fi

echo "Weekly maintenance completed!"

# Exit with error code if any tasks failed
exit $TASKS_FAILED
