#!/usr/bin/env bash

# Log Viewer Script - Opens maintenance logs in a user-friendly way
# Usage: view_logs.sh [task_name|summary]

set -eo pipefail

LOG_DIR="$HOME/Library/Logs/maintenance"
TASK="${1:-summary}"

# Function to open files
open_files() {
    local files=("$@")
    
    if [[ ${#files[@]} -eq 0 ]]; then
        echo "No log files found for: $TASK"
        return 1
    fi
    
    # Try to open in GUI editor (macOS - use TextEdit explicitly for reliability)
    if command -v open >/dev/null 2>&1; then
        for file in "${files[@]}"; do
            open -a TextEdit "$file" 2>/dev/null || open "$file"
        done
    # Fallback to less for terminal viewing
    elif command -v less >/dev/null 2>&1; then
        less "${files[@]}"
    else
        # Last resort: cat
        cat "${files[@]}"
    fi
}

# Handle summary request
if [[ "$TASK" == "summary" ]] || [[ -z "$TASK" ]]; then
    # Find the latest error summary (suppress errors from ls to avoid set -e exit)
    SUMMARY_FILE=$(ls -t "$LOG_DIR"/error_summary_*.txt 2>/dev/null | head -1 || true)
    
    if [[ -n "$SUMMARY_FILE" ]] && [[ -f "$SUMMARY_FILE" ]]; then
        echo "Opening latest error summary: $SUMMARY_FILE"
        open_files "$SUMMARY_FILE"
    else
        echo "No error summary found. Run a maintenance task first."
        exit 1
    fi
else
    # Find log files matching the task name (case-insensitive)
    mapfile -t LOG_FILES < <(find "$LOG_DIR" -type f -iname "*${TASK}*.log" 2>/dev/null | sort -r | head -5)
    
    if [[ ${#LOG_FILES[@]} -gt 0 ]]; then
        echo "Opening ${#LOG_FILES[@]} log file(s) for: $TASK"
        for log in "${LOG_FILES[@]}"; do
            echo "  - $(basename "$log")"
        done
        open_files "${LOG_FILES[@]}"
    else
        echo "No log files found matching: $TASK"
        echo "Available logs in $LOG_DIR:"
        ls -1t "$LOG_DIR"/*.log 2>/dev/null | head -10 | xargs -n1 basename || echo "  (no logs found)"
        exit 1
    fi
fi
