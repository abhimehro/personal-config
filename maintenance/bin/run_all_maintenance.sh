#!/bin/bash

# Master Maintenance Script
# Orchestrates all maintenance tasks with proper logging and error handling
# Created: $(date)

set -euo pipefail

# --- Colors (Defined early for help message) ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Spinner Characters (Global) ---
SPIN_CHARS_UNICODE=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
SPIN_CHARS_ASCII=('|' '/' '-' '\\')
if [[ "${LC_CTYPE:-}" == *"UTF-8"* ]] || [[ "${LC_ALL:-}" == *"UTF-8"* ]] || [[ "${LANG:-}" == *"UTF-8"* ]]; then
    SPIN_CHARS=("${SPIN_CHARS_UNICODE[@]}")
else
    SPIN_CHARS=("${SPIN_CHARS_ASCII[@]}")
fi

# Configuration
export RUN_START=$(date +%s)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../tmp"

print_help() {
    echo -e "${BOLD}${BLUE}🛠️  Master Maintenance Script${NC}"
    echo -e "Orchestrates system maintenance tasks with logging, locking, and summaries."
    echo -e ""
    echo -e "${BOLD}Usage:${NC} $(basename "$0") [command]"
    echo -e ""
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${GREEN}weekly${NC}   Run weekly maintenance tasks (Health, Brew, Node, Services)"
    echo -e "           ${YELLOW}(Default if no argument provided)${NC}"
    echo -e "  ${GREEN}monthly${NC}  Run comprehensive monthly maintenance (Weekly + System/Editor cleanup)"
    echo -e "  ${GREEN}health${NC}   Run system health check only"
    echo -e "  ${GREEN}quick${NC}    Run quick system cleanup"
    echo -e "  ${GREEN}help${NC}     Show this help message"
    echo -e ""
    echo -e "${BOLD}Features:${NC}"
    echo -e "  • 🔒 Prevents concurrent runs"
    echo -e "  • 📝 Logs to $LOG_DIR"
    echo -e "  • 📊 Generates summary report"
    echo -e ""
}

# Check for help argument before acquiring lock or creating logs
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || "${1:-}" == "help" ]]; then
    print_help
    exit 0
fi

LOCK_CONTEXT_LOG="$LOG_DIR/lock_context_$(date +%Y%m%d-%H%M%S).log"
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
MASTER_LOG="$LOG_DIR/maintenance_master_$TIMESTAMP.log"
PARALLEL_RESULTS_LOG="$LOG_DIR/parallel_results_$TIMESTAMP.tmp"

# Global array to store results for summary
declare -a SUMMARY_RESULTS=()

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Lock file location (inside LOG_DIR to avoid /tmp vulnerabilities)
LOCK_DIR="$LOG_DIR/run_all_maintenance.lock"

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
    else
        # 🛡️ Sentinel: Fix logic flaw where script continued if LOCK_DIR existed but wasn't a directory
        echo "ERROR: Failed to acquire lock (path exists but is not a directory or permission denied): $LOCK_DIR"
        exit 1
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
# Usage: spinner PID [Label]
spinner() {
    local pid=$1
    local label="${2:-Running...}"
    local delay=0.1
    local i=0
    local num_chars=${#SPIN_CHARS[@]}

    # Only show spinner if running interactively (TTY) and not redirecting to file only
    # Also disable in CI environments to prevent log clutter
    if [ -t 1 ] && [ -z "${CI:-}" ]; then
        # Hide cursor
        tput civis 2>/dev/null || true

        # Trap to restore cursor if interrupted
        trap 'tput cnorm 2>/dev/null || true; exit' INT TERM

        local start_time=$(date +%s)
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
            printf "\r %s  %s (%ds)   " "${SPIN_CHARS[i]}" "$label" "$elapsed"

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

# Wait for multiple PIDs with spinner
# Usage: wait_for_pids "pid1 pid2 ..." [Label]
wait_for_pids() {
    local pids_list="$1"
    local label="${2:-Running parallel tasks...}"
    local delay=0.1
    local i=0
    local num_chars=${#SPIN_CHARS[@]}

    if [ -t 1 ] && [ -z "${CI:-}" ]; then
        tput civis 2>/dev/null || true
        trap 'tput cnorm 2>/dev/null || true; trap - INT TERM; kill -s INT $$' INT TERM

        local start_time=$(date +%s)
        local elapsed=0
        local update_counter=0

        while true; do
            local running_count=0
            local any_running=false

            for pid in $pids_list; do
                if kill -0 "$pid" 2>/dev/null; then
                    any_running=true
                    running_count=$((running_count + 1))
                fi
            done

            if [[ "$any_running" == "false" ]]; then
                break
            fi

            if (( update_counter % 10 == 0 )); then
                local current_time=$(date +%s)
                elapsed=$((current_time - start_time))
            fi

            # Update label with count if multiple tasks were running
            local status_label="$label"
            if [[ $running_count -gt 1 ]]; then
                status_label="$label ($running_count active)"
            fi

            printf "\r %s  %s (%ds)   " "${SPIN_CHARS[i]}" "$status_label" "$elapsed"

            i=$(( (i + 1) % num_chars ))
            update_counter=$((update_counter + 1))
            sleep $delay
        done

        tput cnorm 2>/dev/null || true
        printf "\r\033[K"
        trap - INT TERM

        # Ensure we reap exit codes, though we don't use them here directly
        for pid in $pids_list; do
            wait "$pid" 2>/dev/null || true
        done
    else
        for pid in $pids_list; do
            wait "$pid" || true
        done
    fi
}

# Add result to summary (handles writing to file if in subshell)
# Usage: register_result "Script Name" "Status" "Is_Parallel_Subshell" "Duration"
register_result() {
    local name="$1"
    local status="$2"
    local is_subshell="${3:-false}"
    local duration="${4:-0s}"

    if [[ "$is_subshell" == "true" ]]; then
        echo "${name}|${status}|${duration}" >> "$PARALLEL_RESULTS_LOG"
    else
        SUMMARY_RESULTS+=("${name}|${status}|${duration}")
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

    local start_time
    local end_time
    local duration_sec
    local duration_fmt

    if [[ -f "$script_path" && -x "$script_path" ]]; then
        log_status "Running $script_name..." "$log_target"

        # Apply smart delay if scheduler is available
        if [[ -f "$smart_scheduler" && -x "$smart_scheduler" ]]; then
            "$smart_scheduler" delay "$clean_name" "$task_type" 2>&1 | tee -a "$log_target"
        fi

        start_time=$(date +%s)

        # Execute script
        if [[ "$is_parallel" == "true" ]]; then
            # Run directly for parallel (background) tasks
            if "$script_path" > "$log_file" 2>&1; then
                end_time=$(date +%s)
                duration_sec=$((end_time - start_time))
                duration_fmt="${duration_sec}s"

                log_status "✅ $script_name completed in $duration_fmt" "$log_target"
                register_result "$clean_name" "✅ Success" "$is_parallel" "$duration_fmt"
                return 0
            else
                end_time=$(date +%s)
                duration_sec=$((end_time - start_time))
                duration_fmt="${duration_sec}s"

                log_status "❌ $script_name failed (see $log_file)" "$log_target"
                register_result "$clean_name" "❌ Failed" "$is_parallel" "$duration_fmt"
                return 1
            fi
        else
            # Run with spinner for serial tasks
            "$script_path" > "$log_file" 2>&1 &
            local pid=$!

            spinner $pid "Running $clean_name..."

            wait $pid
            local exit_code=$?

            end_time=$(date +%s)
            duration_sec=$((end_time - start_time))
            duration_fmt="${duration_sec}s"

            if [[ $exit_code -eq 0 ]]; then
                log_status "✅ $script_name completed in $duration_fmt" "$log_target"
                register_result "$clean_name" "✅ Success" "$is_parallel" "$duration_fmt"
                return 0
            else
                log_status "❌ $script_name failed (see $log_file)" "$log_target"
                register_result "$clean_name" "❌ Failed" "$is_parallel" "$duration_fmt"
                return 1
            fi
        fi
    else
        log_status "⚠️  $script_name not found/executable" "$log_target"
        register_result "$clean_name" "⚠️  Missing" "$is_parallel" "0s"
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
    local gdrive_status="$LOG_DIR/status_gdrive_$TIMESTAMP.log"
    local service_status="$LOG_DIR/status_service_$TIMESTAMP.log"

    pids=""
    
    # Note: Passed "true" as 4th arg to indicate parallel execution
    (run_script "brew_maintenance.sh" "maintenance" "$brew_status" "true") &
    pids="$pids $!"
    
    (run_script "node_maintenance.sh" "maintenance" "$node_status" "true") &
    pids="$pids $!"

    (run_script "google_drive_monitor.sh" "maintenance" "$gdrive_status" "true") &
    pids="$pids $!"

    (run_script "service_optimizer.sh" "optimization" "$service_status" "true") &
    pids="$pids $!"

    # Wait for all
    wait_for_pids "$pids" "Running parallel tasks..."

    # Consolidate logs
    cat "$brew_status" "$node_status" "$gdrive_status" "$service_status" >> "$MASTER_LOG"
    
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
    wait_for_pids "$pids" "Running cleanup tasks..."

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
    # Calculate total duration
    local current_time=$(date +%s)
    local total_duration=$((current_time - RUN_START))
    local total_fmt
    if (( total_duration > 60 )); then
        total_fmt="$((total_duration / 60))m $((total_duration % 60))s"
    else
        total_fmt="${total_duration}s"
    fi

    echo "" | tee -a "$MASTER_LOG"
    echo "┌────────────────────────────────────────────────────────────────────────┐" | tee -a "$MASTER_LOG"
    echo "│                        MAINTENANCE RUN SUMMARY                         │" | tee -a "$MASTER_LOG"
    echo "├────────────────────────────────────────────────────────────────────────┤" | tee -a "$MASTER_LOG"

    # Header row
    printf "│ %-12s │ %-40s │ %-10s │\n" "STATUS" "TASK" "DURATION" | tee -a "$MASTER_LOG"
    echo "├──────────────┼──────────────────────────────────────────┼────────────┤" | tee -a "$MASTER_LOG"

    if [[ ${#SUMMARY_RESULTS[@]} -eq 0 ]]; then
        echo "│ No tasks recorded.                                                     │" | tee -a "$MASTER_LOG"
    else
        for entry in "${SUMMARY_RESULTS[@]}"; do
            IFS="|" read -r name status duration <<< "$entry"

            # Prepare padded string and color
            local status_text=""
            local color=""

            if [[ "$status" == *"Success"* ]]; then
                 status_text="✅ Success  "
                 color="$GREEN"
            elif [[ "$status" == *"Failed"* ]]; then
                 status_text="❌ Failed   "
                 color="$RED"
            elif [[ "$status" == *"Missing"* ]]; then
                 status_text="⚠️  Missing  "
                 color="$YELLOW"
            else
                 status_text="$(printf "%-12s" "$status")"
                 color=""
            fi

            # Truncate name if too long
            if [[ ${#name} -gt 40 ]]; then
                name="${name:0:37}..."
            fi

            # Print row with colors (ANSI codes)
            printf "│ ${color}%s${NC} │ %-40s │ %-10s │\n" "$status_text" "$name" "$duration" | tee -a "$MASTER_LOG"
        done
    fi

    # Footer with Total Duration
    echo "├──────────────┴──────────────────────────────────────────┼────────────┤" | tee -a "$MASTER_LOG"
    printf "│ %55s │ %-10s │\n" "TOTAL DURATION" "$total_fmt" | tee -a "$MASTER_LOG"
    echo "└─────────────────────────────────────────────────────────┴────────────┘" | tee -a "$MASTER_LOG"
}

# --- Execution Entry Point ---

if [[ $# -eq 1 ]]; then
    case "$1" in
        "weekly")  run_weekly_maintenance ;;
        "monthly") run_monthly_maintenance ;;
        "health")  run_script "health_check.sh" "critical" ;;
        "quick")   run_script "quick_cleanup.sh" "cleanup" ;;
        *)
            print_help
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
