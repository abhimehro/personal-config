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
PARALLEL_RESULTS_LOG="$LOG_DIR/parallel_results_$TIMESTAMP.tmp"

# Global array to store results for summary
declare -a SUMMARY_RESULTS=()

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# --- Locking Mechanism ---
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    if [[ -d "$LOCK_DIR" ]]; then
        # Cross-platform stat check (macOS vs Linux)
        if stat -f %m "$LOCK_DIR" >/dev/null 2>&1; then
            LOCK_TIME=$(stat -f %m "$LOCK_DIR") # macOS
        else
             LOCK_TIME=$(stat -c %Y "$LOCK_DIR" 2>/dev/null || date +%s) # Linux
        fi
        
        LOCK_AGE=$(($(date +%s) - LOCK_TIME))
        if [[ $LOCK_AGE -gt 7200 ]]; then
            LOCK_MSG="WARNING: Removing stale lock (age: $((LOCK_AGE/60)) minutes)"
            echo "$LOCK_MSG"
            echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $LOCK_MSG" >> "$LOCK_CONTEXT_LOG"
            rm -rf "$LOCK_DIR" 2>/dev/null || true
            if ! mkdir "$LOCK_DIR" 2>/dev/null; then
                echo "ERROR: Failed to acquire lock after stale removal"
                exit 1
            fi
        else
            echo "Another instance is already running (age: $((LOCK_AGE/60)) min)"
            exit 0
        fi
    fi
fi
# Cleanup trap
trap 'rm -rf "$LOCK_DIR" "$LOG_DIR"/status_*_"$TIMESTAMP".log "$PARALLEL_RESULTS_LOG" 2>/dev/null || true' EXIT INT TERM

# Initialize master log
echo "=== Master Maintenance Run Started: $(date) ===" | tee "$MASTER_LOG"

# --- Global Helper Functions ---

# Helper to log to target (file or stdout)
# Usage: log_status "Message" [log_file]
log_status() {
    local msg="$1"
    local target="${2:-$MASTER_LOG}"
    
    if [[ "$target" == "/dev/stdout" ]]; then
        echo -e "$msg"
    else
        echo -e "$msg" | tee -a "$target"
    fi
}

# Progress spinner for long-running tasks
# Usage: spinner PID
spinner() {
    local pid=$1
    local delay=0.1
    local spin_chars_unicode=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
    local spin_chars_ascii=('|' '/' '-' '\\')
    local spin_chars
    local i=0
    local start_time=$(date +%s)

    # Detect UTF-8 support
    if [[ "${LC_CTYPE:-}" == *"UTF-8"* ]] || [[ "${LC_ALL:-}" == *"UTF-8"* ]] || [[ "${LANG:-}" == *"UTF-8"* ]]; then
        spin_chars=("${spin_chars_unicode[@]}")
    else
        spin_chars=("${spin_chars_ascii[@]}")
    fi

    local num_chars=${#spin_chars[@]}

    # Only show spinner if running interactively (TTY) and not redirecting to file only
    # Also disable in CI environments to prevent log clutter
    if [ -t 1 ] && [ -z "${CI:-}" ]; then
        # Hide cursor
        tput civis 2>/dev/null || true

        # Trap to restore cursor if interrupted
        trap 'tput cnorm 2>/dev/null || true; exit' INT TERM

        local elapsed=0
        local update_counter=0
        while kill -0 "$pid" 2>/dev/null; do
            # Update elapsed time only every 10 iterations (every second)
            if (( update_counter % 10 == 0 )); then
                local current_time=$(date +%s)
                elapsed=$((current_time - start_time))
            fi

            # Print spinner and elapsed time
            # \r moves to start, \033[K (optional) or spaces to clear
            printf "\r %s  Running... (%ds)   " "${spin_chars[i]}" "$elapsed"

            i=$(( (i + 1) % num_chars ))
            update_counter=$((update_counter + 1))
            sleep $delay
        done

        # Restore cursor
        tput cnorm 2>/dev/null || true

        # Clear spinner line completely
        printf "\r\033[K"

        # Remove trap
        trap - INT TERM
    else
        # If not interactive or in CI, just wait
        wait "$pid"
    fi
}

# Add result to summary (handles writing to file if in subshell)
# Usage: register_result "Script Name" "Status" "Is_Parallel_Subshell"
register_result() {
    local name="$1"
    local status="$2"
    local is_subshell="${3:-false}"

    if [[ "$is_subshell" == "true" ]]; then
        echo "${name}|${status}" >> "$PARALLEL_RESULTS_LOG"
    else
        SUMMARY_RESULTS+=("${name}|${status}")
    fi
}

# Wrapper to run a script
# Usage: run_script script_name task_type [log_target] [is_parallel]
run_script() {
    local script_name="$1"
    local task_type="${2:-maintenance}"
    local log_target="${3:-$MASTER_LOG}"
    local is_parallel="${4:-false}"

    local script_path="$SCRIPT_DIR/$script_name"
    local log_file="$LOG_DIR/${script_name%.sh}_$TIMESTAMP.log"
    local smart_scheduler="$SCRIPT_DIR/smart_scheduler.sh"
    local clean_name="${script_name%.sh}"

    if [[ -f "$script_path" && -x "$script_path" ]]; then
        log_status "Running $script_name..." "$log_target"

        # Apply smart delay if scheduler is available
        if [[ -f "$smart_scheduler" && -x "$smart_scheduler" ]]; then
            "$smart_scheduler" delay "$clean_name" "$task_type" 2>&1 | tee -a "$log_target"
        fi

        # Execute script
        if [[ "$is_parallel" == "true" ]]; then
            # Run directly for parallel (background) tasks
            if "$script_path" > "$log_file" 2>&1; then
                log_status "✅ $script_name completed" "$log_target"
                register_result "$clean_name" "✅ Success" "$is_parallel"
                return 0
            else
                log_status "❌ $script_name failed (see $log_file)" "$log_target"
                register_result "$clean_name" "❌ Failed" "$is_parallel"
                return 1
            fi
        else
            # Run with spinner for serial tasks
            "$script_path" > "$log_file" 2>&1 &
            local pid=$!

            spinner $pid

            wait $pid
            local exit_code=$?

            if [[ $exit_code -eq 0 ]]; then
                log_status "✅ $script_name completed" "$log_target"
                register_result "$clean_name" "✅ Success" "$is_parallel"
                return 0
            else
                log_status "❌ $script_name failed (see $log_file)" "$log_target"
                register_result "$clean_name" "❌ Failed" "$is_parallel"
                return 1
            fi
        fi
    else
        log_status "⚠️  $script_name not found/executable" "$log_target"
        register_result "$clean_name" "⚠️  Missing" "$is_parallel"
        return 1
    fi
}

# --- Task Groups ---

# Function to run lightweight scripts (weekly)
run_weekly_maintenance() {
    echo "=== Weekly Maintenance Tasks ===" | tee -a "$MASTER_LOG"
    
    # Serial tasks
    run_script "health_check.sh" "critical"
    run_script "quick_cleanup.sh" "cleanup"
    
    echo "Starting parallel maintenance tasks..." | tee -a "$MASTER_LOG"

    local brew_status="$LOG_DIR/status_brew_$TIMESTAMP.log"
    local node_status="$LOG_DIR/status_node_$TIMESTAMP.log"
    local google_drive_status="$LOG_DIR/status_google_drive_$TIMESTAMP.log"
    local service_status="$LOG_DIR/status_service_$TIMESTAMP.log"

    pids=""
    
    # Note: Passed "true" as 4th arg to indicate parallel execution
    (run_script "brew_maintenance.sh" "maintenance" "$brew_status" "true") &
    pids="$pids $!"
    
    (run_script "node_maintenance.sh" "maintenance" "$node_status" "true") &
    pids="$pids $!"

    (run_script "google_drive_monitor.sh" "maintenance" "$google_drive_status" "true") &
    pids="$pids $!"

    (run_script "service_optimizer.sh" "optimization" "$service_status" "true") &
    pids="$pids $!"

    # Wait for all
    for pid in $pids; do
        wait "$pid"
    done

    # Consolidate logs
    cat "$brew_status" "$node_status" "$google_drive_status" "$service_status" >> "$MASTER_LOG"
    
    # Consolidate Results from temp file
    if [[ -f "$PARALLEL_RESULTS_LOG" ]]; then
        while IFS= read -r line; do
            SUMMARY_RESULTS+=("$line")
        done < "$PARALLEL_RESULTS_LOG"
    fi

    echo "Parallel tasks completed." | tee -a "$MASTER_LOG"
    
    # Performance optimizer (Serial)
    run_script "performance_optimizer.sh" "optimization"
}

# Function to run comprehensive scripts (monthly)
run_monthly_maintenance() {
    echo "=== Monthly Maintenance Tasks ===" | tee -a "$MASTER_LOG"
    
    run_weekly_maintenance
    
    echo "Starting monthly parallel cleanup tasks..." | tee -a "$MASTER_LOG"

    local system_cleanup_status="$LOG_DIR/status_system_cleanup_$TIMESTAMP.log"
    local editor_cleanup_status="$LOG_DIR/status_editor_cleanup_$TIMESTAMP.log"

    pids=""

    (run_script "system_cleanup.sh" "cleanup" "$system_cleanup_status" "true") &
    pids="$pids $!"

    (run_script "editor_cleanup.sh" "cleanup" "$editor_cleanup_status" "true") &
    pids="$pids $!"

    # Wait for all
    for pid in $pids; do
        wait "$pid"
    done

    # Consolidate logs
    cat "$system_cleanup_status" "$editor_cleanup_status" >> "$MASTER_LOG"

    # Consolidate Results from temp file
    if [[ -f "$PARALLEL_RESULTS_LOG" ]]; then
        while IFS= read -r line; do
            SUMMARY_RESULTS+=("$line")
        done < "$PARALLEL_RESULTS_LOG"
    fi

    echo "Monthly parallel tasks completed." | tee -a "$MASTER_LOG"
    
    echo "Running deep cleaner with caution..." | tee -a "$MASTER_LOG"
    run_script "deep_cleaner.sh" "cleanup"
}

# Function to print summary table
print_summary() {
    echo "" | tee -a "$MASTER_LOG"
    echo "┌────────────────────────────────────────────────────────┐" | tee -a "$MASTER_LOG"
    echo "│               MAINTENANCE RUN SUMMARY                  │" | tee -a "$MASTER_LOG"
    echo "├────────────────────────────────────────────────────────┤" | tee -a "$MASTER_LOG"

    if [[ ${#SUMMARY_RESULTS[@]} -eq 0 ]]; then
        echo "│ No tasks recorded.                                     │" | tee -a "$MASTER_LOG"
    else
        for entry in "${SUMMARY_RESULTS[@]}"; do
            IFS="|" read -r name status <<< "$entry"

            # Manual padding
            local status_pad=""
            if [[ "$status" == *"Success"* ]]; then
                 status_pad="✅ Success  "
            elif [[ "$status" == *"Failed"* ]]; then
                 status_pad="❌ Failed   "
            elif [[ "$status" == *"Missing"* ]]; then
                 status_pad="⚠️  Missing  "
            else
                 status_pad="$(printf "%-12s" "$status")"
            fi

            printf "│ %s : %-37s │
" "$status_pad" "$name" | tee -a "$MASTER_LOG"
        done
    fi

    echo "└────────────────────────────────────────────────────────┘" | tee -a "$MASTER_LOG"
}

# --- Execution Entry Point ---

if [[ $# -eq 1 ]]; then
    case "$1" in
        "weekly")  run_weekly_maintenance ;;
        "monthly") run_monthly_maintenance ;;
        "health")  run_script "health_check.sh" "critical" ;;
        "quick")   run_script "quick_cleanup.sh" "cleanup" ;;
        *)
            echo "Usage: $0 [weekly|monthly|health|quick]"
            exit 1
            ;;
    esac
else
    # Default
    run_weekly_maintenance
fi

# Generate error summary if script exists
if [[ -x "$SCRIPT_DIR/generate_error_summary.sh" ]]; then
    SUMMARY_FILE=$("$SCRIPT_DIR/generate_error_summary.sh" 2>/dev/null || echo "")
    if [[ -n "$SUMMARY_FILE" && -f "$SUMMARY_FILE" ]]; then
        echo "Error summary generated: $SUMMARY_FILE" | tee -a "$MASTER_LOG"
    fi
fi

print_summary

# Footer
echo "=== Master Maintenance Run Completed: $(date) ===" | tee -a "$MASTER_LOG"
echo "Logs saved to: $LOG_DIR" | tee -a "$MASTER_LOG"

# Clean up old logs (Keep 10)
find "$LOG_DIR" -name "maintenance_master_*.log" -type f | sort -r | tail -n +11 | xargs rm -f 2>/dev/null || true