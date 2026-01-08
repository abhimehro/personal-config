#!/usr/bin/env bash

# Service Monitor - Check disabled background services stay disabled
# Part of the macOS maintenance system
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/service_monitor.log"

# User ID
USER_ID=$(id -u)

# Basic logging
log_info() {
    local ts
    if (( BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 2) )); then
        printf -v ts '%(%Y-%m-%d %H:%M:%S)T' -1
    else
        ts="$(date '+%Y-%m-%d %H:%M:%S')"
    fi
    echo "$ts [INFO] [service_monitor] $*" | tee -a "$LOG_FILE"
}

log_warn() {
    local ts
    if (( BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 2) )); then
        printf -v ts '%(%Y-%m-%d %H:%M:%S)T' -1
    else
        ts="$(date '+%Y-%m-%d %H:%M:%S')"
    fi
    echo "$ts [WARNING] [service_monitor] $*" | tee -a "$LOG_FILE"
}

log_error() {
    local ts
    if (( BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 2) )); then
        printf -v ts '%(%Y-%m-%d %H:%M:%S)T' -1
    else
        ts="$(date '+%Y-%m-%d %H:%M:%S')"
    fi
    echo "$ts [ERROR] [service_monitor] $*" | tee -a "$LOG_FILE"
}

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE" 2>/dev/null || true
fi

log_info "Service monitoring started"

# =============================================================================
# Services that should stay disabled
# =============================================================================

SYSTEM_SERVICES=(
    "com.apple.chronod"
    "com.apple.duetexpertd"
    "com.apple.suggestd"
    "com.apple.ReportCrash.Root"
)

USER_SERVICES=(
    "com.apple.ReportCrash"
    "com.apple.calendar.CalendarAgentBookmarkMigrationService"
    "com.apple.podcasts.PodcastContentService"
    "com.apple.proactived"
    "com.apple.peopled"
    "com.apple.knowledge-agent"
    "com.apple.appstoreagent"
    "com.apple.commerce"
    "com.apple.photoanalysisd"
    "com.apple.photolibraryd"
)

# Problem services that should not be running (or should be killed if found)
PROBLEM_PROCESSES=(
    "CalendarWidgetExtension"
    "PodcastsWidget"
)

# =============================================================================
# Monitoring Functions
# =============================================================================

# Cache disabled status to avoid repeated expensive launchctl calls
SYSTEM_DISABLED_STATUS=""
USER_DISABLED_STATUS=""

init_disabled_status_cache() {
    log_info "Initializing service status cache..."
    SYSTEM_DISABLED_STATUS=$(sudo launchctl print-disabled system 2>/dev/null || true)
    USER_DISABLED_STATUS=$(sudo launchctl print-disabled "gui/$USER_ID" 2>/dev/null || true)
}

check_disabled_status() {
    local domain=$1
    local service=$2
    
    if [[ "$domain" == "system" ]]; then
        if [[ -z "$SYSTEM_DISABLED_STATUS" ]]; then
            # Fallback if cache empty (though it shouldn't be if init called)
            sudo launchctl print-disabled system 2>/dev/null | grep -q "\"$service\" => disabled"
            return $?
        fi
        echo "$SYSTEM_DISABLED_STATUS" | grep -q "\"$service\" => disabled"
    else
        if [[ -z "$USER_DISABLED_STATUS" ]]; then
            # Fallback
            sudo launchctl print-disabled "gui/$USER_ID" 2>/dev/null | grep -q "\"$service\" => disabled"
            return $?
        fi
        echo "$USER_DISABLED_STATUS" | grep -q "\"$service\" => disabled"
    fi
}

check_process_running() {
    local process=$1
    ps aux | grep -i "$process" | grep -v grep >/dev/null 2>&1
}

count_widget_extensions() {
    ps aux | grep -E "\.appex/Contents/MacOS" | grep -v grep | wc -l | tr -d ' '
}

count_diagnostic_reports() {
    find "$HOME/Library/Logs/DiagnosticReports" -type f -name "*.ips" 2>/dev/null | wc -l | tr -d ' '
}

get_top_crash_reports() {
    if [[ -d "$HOME/Library/Logs/DiagnosticReports" ]]; then
        ls "$HOME/Library/Logs/DiagnosticReports" 2>/dev/null | \
            sed 's/-[0-9].*$//' | sort | uniq -c | sort -rn | head -5
    fi
}

# =============================================================================
# Main Monitoring Logic
# =============================================================================

REPORT=""
ISSUES=0
WARNINGS=0
ACTIONS_TAKEN=0

append() { REPORT+="$1"$'\n'; }

# Initialize cache
init_disabled_status_cache

append "========================================="
append "Service Monitor Report - $(date)"
append "========================================="
append ""

# Check system-level services
append "System Services Status:"
append "-----------------------"
for service in "${SYSTEM_SERVICES[@]}"; do
    if check_disabled_status "system" "$service"; then
        append "✅ $service: DISABLED"
        log_info "$service is correctly disabled"
    else
        append "❌ $service: NOT DISABLED (ISSUE!)"
        log_error "$service is not disabled - attempting to re-disable"
        if sudo launchctl disable "system/$service" 2>/dev/null; then
            append "   ↳ Successfully re-disabled"
            ((ACTIONS_TAKEN++))
            # Invalidate cache for this domain since we changed state
            # Though strictly we only need to if we re-check, but good practice
            SYSTEM_DISABLED_STATUS=""
        else
            append "   ↳ Failed to re-disable"
            ((ISSUES++))
        fi
    fi
done
append ""

# Check user-level services
append "User Services Status:"
append "---------------------"
for service in "${USER_SERVICES[@]}"; do
    if check_disabled_status "user" "$service"; then
        append "✅ $service: DISABLED"
        log_info "$service is correctly disabled"
    else
        append "❌ $service: NOT DISABLED (ISSUE!)"
        log_error "$service is not disabled - attempting to re-disable"
        if sudo launchctl disable "gui/$USER_ID/$service" 2>/dev/null; then
            append "   ↳ Successfully re-disabled"
            ((ACTIONS_TAKEN++))
            USER_DISABLED_STATUS=""
        else
            append "   ↳ Failed to re-disable"
            ((ISSUES++))
        fi
    fi
done
append ""

# Check for problematic running processes
append "Problematic Processes:"
append "----------------------"
for process in "${PROBLEM_PROCESSES[@]}"; do
    if check_process_running "$process"; then
        append "⚠️  $process: RUNNING (should not be)"
        log_warn "$process is running - killing process"
        if pkill -9 "$process" 2>/dev/null; then
            append "   ↳ Successfully killed"
            ((ACTIONS_TAKEN++))
        else
            append "   ↳ Failed to kill"
            ((WARNINGS++))
        fi
    else
        append "✅ $process: NOT RUNNING"
    fi
done
append ""

# Count widget extensions
WIDGET_COUNT=$(count_widget_extensions)
append "Widget Extensions Running: $WIDGET_COUNT"
if (( WIDGET_COUNT > 60 )); then
    append "⚠️  High widget count detected (threshold: 60)"
    log_warn "Widget count is high: $WIDGET_COUNT"
    ((WARNINGS++))
fi
append ""

# Check for key background services that shouldn't be running persistently
append "Background Services Check:"
append "--------------------------"
CHRONOD_RUNNING=$(ps aux | grep -E "chronod" | grep -v grep | wc -l | tr -d ' ')
DUET_RUNNING=$(ps aux | grep -E "duetexpertd" | grep -v grep | wc -l | tr -d ' ')
SUGGESTD_RUNNING=$(ps aux | grep -E "suggestd" | grep -v grep | wc -l | tr -d ' ')
PROACTIVED_RUNNING=$(ps aux | grep -E "proactived" | grep -v grep | wc -l | tr -d ' ')

append "chronod instances: $CHRONOD_RUNNING"
append "duetexpertd instances: $DUET_RUNNING"
append "suggestd instances: $SUGGESTD_RUNNING"
append "proactived instances: $PROACTIVED_RUNNING"

# Note: These may respawn on-demand, so we only warn if they persist across checks
if (( CHRONOD_RUNNING > 0 || DUET_RUNNING > 0 )); then
    append "ℹ️  Note: Some services respawned on-demand (expected behavior)"
    log_info "Background services respawned on-demand (chronod: $CHRONOD_RUNNING, duet: $DUET_RUNNING)"
fi
append ""

# Check diagnostic reports
REPORT_COUNT=$(count_diagnostic_reports)
append "Diagnostic Reports: $REPORT_COUNT crash reports found"
if (( REPORT_COUNT > 10 )); then
    append "⚠️  High number of crash reports detected"
    log_warn "Found $REPORT_COUNT crash reports"
    append ""
    append "Top crash sources:"
    get_top_crash_reports | while read -r line; do
        append "  $line"
    done
    ((WARNINGS++))
elif (( REPORT_COUNT > 0 )); then
    append "ℹ️  Some crash reports present but within normal range"
else
    append "✅ No crash reports found"
fi
append ""

# Summary
append "========================================="
append "Summary"
append "========================================="
append "Issues detected: $ISSUES"
append "Warnings: $WARNINGS"
append "Remediation actions taken: $ACTIONS_TAKEN"
append "Widget extensions running: $WIDGET_COUNT"
append "Crash reports: $REPORT_COUNT"
append ""

# Determine overall status
if (( ISSUES > 0 )); then
    STATUS="❌ ISSUES DETECTED"
    EXIT_CODE=2
elif (( WARNINGS > 0 )); then
    STATUS="⚠️  WARNINGS"
    EXIT_CODE=1
else
    STATUS="✅ ALL CLEAR"
    EXIT_CODE=0
fi

append "Overall Status: $STATUS"
append "========================================="

# Save report
REPORT_FILE="$LOG_DIR/service_monitor-$(date +%Y%m%d-%H%M).txt"
printf "%s\n" "$REPORT" > "$REPORT_FILE"
log_info "Service monitor report saved to $REPORT_FILE"

# Display summary to stdout
echo "$REPORT"

# Send notification if not in automated mode
if [[ "${AUTOMATED_RUN:-0}" != "1" ]] && command -v osascript >/dev/null 2>&1; then
    if (( ISSUES > 0 )); then
        osascript -e "display notification \"Issues: $ISSUES | Actions: $ACTIONS_TAKEN | Widgets: $WIDGET_COUNT\" with title \"⚠️ Service Monitor\"" 2>/dev/null || true
    elif (( WARNINGS > 0 )); then
        osascript -e "display notification \"Warnings: $WARNINGS | Widgets: $WIDGET_COUNT | Reports: $REPORT_COUNT\" with title \"ℹ️ Service Monitor\"" 2>/dev/null || true
    fi
fi

log_info "Service monitoring complete: $STATUS"
exit $EXIT_CODE
