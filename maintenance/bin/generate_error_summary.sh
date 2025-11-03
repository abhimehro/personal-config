#!/usr/bin/env bash

# Error Summary Generator - Consolidates errors from maintenance logs
# Usage: generate_error_summary.sh

set -eo pipefail

LOG_DIR="$HOME/Library/Logs/maintenance"
SUMMARY_FILE="$LOG_DIR/error_summary_$(date +%Y%m%d-%H%M%S).txt"

# Determine time window for log collection
if [[ -n "${RUN_START:-}" ]]; then
    # Use RUN_START epoch if provided by orchestrator
    MARKER_FILE="/tmp/maintenance_run_marker_$$"
    touch -t "$(date -r "$RUN_START" +%Y%m%d%H%M.%S)" "$MARKER_FILE" 2>/dev/null || touch "$MARKER_FILE"
    TIME_DESC="since $(date -r "$RUN_START" '+%Y-%m-%d %H:%M:%S')"
else
    # Fallback: last 120 minutes
    MARKER_FILE="/tmp/maintenance_run_marker_$$"
    touch -d "120 minutes ago" "$MARKER_FILE" 2>/dev/null || touch -t "$(date -v-120M +%Y%m%d%H%M.%S)" "$MARKER_FILE" 2>/dev/null || touch "$MARKER_FILE"
    TIME_DESC="in last 120 minutes"
fi

# Initialize summary
{
    echo "========================================"
    echo "  Maintenance Error Summary"
    echo "  Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  Time window: $TIME_DESC"
    echo "========================================"
    echo ""
} > "$SUMMARY_FILE"

# Collect lock context if available
mapfile -t LOCK_CONTEXT_FILES < <(find "$LOG_DIR" -type f -name "lock_context_*.log" -newer "$MARKER_FILE" 2>/dev/null)

if [[ ${#LOCK_CONTEXT_FILES[@]} -gt 0 ]]; then
    LOCK_EVENTS=0
    for lock_file in "${LOCK_CONTEXT_FILES[@]}"; do
        LINE_COUNT=$(wc -l < "$lock_file" 2>/dev/null | tr -d ' \n' || echo 0)
        LOCK_EVENTS=$((LOCK_EVENTS + ${LINE_COUNT:-0}))
    done
    
    if [[ $LOCK_EVENTS -gt 0 ]]; then
        {
            echo "## LOCK CONTEXT"
            echo "Lock events detected: $LOCK_EVENTS"
            echo ""
            echo "Recent lock activity:"
            for lock_file in "${LOCK_CONTEXT_FILES[@]}"; do
                cat "$lock_file" 2>/dev/null | sed 's/^/  /'
            done
            echo ""
        } >> "$SUMMARY_FILE"
    fi
fi

# Find recent log files
mapfile -t LOG_FILES < <(find "$LOG_DIR" -type f -name "*.log" -newer "$MARKER_FILE" 2>/dev/null)

if [[ ${#LOG_FILES[@]} -eq 0 ]]; then
    echo "No recent log files found $TIME_DESC" >> "$SUMMARY_FILE"
else
    TOTAL_ERRORS=0
    TOTAL_WARNINGS=0
    
    for log_file in "${LOG_FILES[@]}"; do
        # Extract error and warning lines (sanitize output)
        ERRORS_RAW=$(grep -Eic 'ERROR|CRITICAL|FATAL' "$log_file" 2>/dev/null | tr -d ' \n' || echo "0")
        WARNINGS_RAW=$(grep -Eic 'WARN|WARNING' "$log_file" 2>/dev/null | tr -d ' \n' || echo "0")
        
        # Convert to integer, ensuring no leading zeros or empty values
        ERRORS=$((${ERRORS_RAW:-0}))
        WARNINGS=$((${WARNINGS_RAW:-0}))
        
        TOTAL_ERRORS=$((TOTAL_ERRORS + ERRORS))
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + WARNINGS))
        
        if [[ $ERRORS -gt 0 ]] || [[ $WARNINGS -gt 0 ]]; then
            echo "----------------------------------------" >> "$SUMMARY_FILE"
            echo "File: $(basename "$log_file")" >> "$SUMMARY_FILE"
            echo "  Errors: $ERRORS" >> "$SUMMARY_FILE"
            echo "  Warnings: $WARNINGS" >> "$SUMMARY_FILE"
            
            # Get first and last timestamp if available
            FIRST_TS=$(grep -E '^\[?20[0-9]{2}-' "$log_file" 2>/dev/null | head -1 | awk '{print $1, $2}' || echo "N/A")
            LAST_TS=$(grep -E '^\[?20[0-9]{2}-' "$log_file" 2>/dev/null | tail -1 | awk '{print $1, $2}' || echo "N/A")
            echo "  Period: $FIRST_TS to $LAST_TS" >> "$SUMMARY_FILE"
            echo "" >> "$SUMMARY_FILE"
            
            # Show sample of errors/warnings
            if [[ $ERRORS -gt 0 ]]; then
                echo "  Sample errors:" >> "$SUMMARY_FILE"
                grep -Ein 'ERROR|CRITICAL|FATAL' "$log_file" 2>/dev/null | head -3 | sed 's/^/    /' >> "$SUMMARY_FILE"
                echo "" >> "$SUMMARY_FILE"
            fi
            
            if [[ $WARNINGS -gt 0 ]]; then
                echo "  Sample warnings:" >> "$SUMMARY_FILE"
                grep -Ein 'WARN|WARNING' "$log_file" 2>/dev/null | head -2 | sed 's/^/    /' >> "$SUMMARY_FILE"
                echo "" >> "$SUMMARY_FILE"
            fi
        fi
    done
    
    {
        echo "========================================"
        echo "  SUMMARY TOTALS"
        echo "  Total Errors: $TOTAL_ERRORS"
        echo "  Total Warnings: $TOTAL_WARNINGS"
        echo "  Files analyzed: ${#LOG_FILES[@]}"
        echo "========================================"
    } >> "$SUMMARY_FILE"
fi

# Clean up marker file
rm -f "$MARKER_FILE" 2>/dev/null || true

# Keep only last 10 summaries
find "$LOG_DIR" -name "error_summary_*.txt" -type f | sort -r | tail -n +11 | xargs rm -f 2>/dev/null || true

# Output the summary file path for orchestrator scripts
echo "$SUMMARY_FILE"
