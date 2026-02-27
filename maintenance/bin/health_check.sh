#!/usr/bin/env bash

# Self-contained health check script with enhanced panic diagnostics
# Added timeouts to prevent hanging on slow log commands
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Helper functions to sanitize counts for arithmetic
count_clean() { awk '{print $1}' | tr -d '\n'; }
to_int() { printf '%d' "${1:-0}" 2>/dev/null || echo 0; }

# Basic logging
log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [health_check] $*" | tee -a "$LOG_DIR/health_check.log"
}

log_warn() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [WARNING] [health_check] $*" | tee -a "$LOG_DIR/health_check.log"
}

# Basic utility functions
percent_used() {
    local path="${1:-/}"
    df -P "$path" | awk 'NR==2 {print $5}' | tr -d '%'
}

# Timeout wrapper for commands that might hang
run_with_timeout() {
    local timeout_seconds="$1"
    shift
    local cmd="$*"
    
    # Use timeout if available (installed via homebrew coreutils)
    if command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$timeout_seconds" bash -c "$cmd" 2>/dev/null || echo ""
    else
        # Fallback: use background process with kill
        local output_file=$(mktemp)
        bash -c "$cmd" > "$output_file" 2>/dev/null &
        local pid=$!
        local count=0
        while kill -0 $pid 2>/dev/null && [ $count -lt $timeout_seconds ]; do
            sleep 1
            ((count++))
        done
        if kill -0 $pid 2>/dev/null; then
            kill -9 $pid 2>/dev/null || true
            wait $pid 2>/dev/null || true
            echo ""
        else
            wait $pid 2>/dev/null || true
            cat "$output_file" 2>/dev/null || echo ""
        fi
        rm -f "$output_file"
    fi
}

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE" 2>/dev/null || true
fi

log_info "Health check started"

REPORT=""
append() { REPORT+="$1"$'\n'; log_info "$1"; }

# 1) Disk space check
ROOT_USE=$(percent_used "/")
append "Disk usage for /: ${ROOT_USE}%"

# 🛡️ Sentinel: Sanitize threshold inputs
DISK_CRIT_VAL="${DISK_CRIT_PCT:-90}"
if ! [[ "$DISK_CRIT_VAL" =~ ^[0-9]+$ ]]; then
    log_warn "Invalid DISK_CRIT_PCT: '$DISK_CRIT_VAL'. Using default 90."
    DISK_CRIT_VAL=90
fi

DISK_WARN_VAL="${DISK_WARN_PCT:-80}"
if ! [[ "$DISK_WARN_VAL" =~ ^[0-9]+$ ]]; then
    log_warn "Invalid DISK_WARN_PCT: '$DISK_WARN_VAL'. Using default 80."
    DISK_WARN_VAL=80
fi

if (( ROOT_USE >= DISK_CRIT_VAL )); then
  log_warn "Critical disk usage: ${ROOT_USE}%"
elif (( ROOT_USE >= DISK_WARN_VAL )); then
  log_warn "High disk usage: ${ROOT_USE}%"
fi

# 2) Memory check
if command -v vm_stat >/dev/null 2>&1; then
  FREE_PAGES=$(vm_stat | awk '/Pages free:/ {print $3}' | tr -d '.' || echo "0")
  PAGE_SIZE=$(vm_stat | awk '/page size of/ {print $8}' || echo "4096")
  FREE_MB=$(( (FREE_PAGES * PAGE_SIZE) / 1024 / 1024 ))
  append "Free memory: ${FREE_MB} MB"
  
  # Warn if very low memory
  if (( FREE_MB < 100 )); then
    log_warn "Very low free memory: ${FREE_MB} MB"
  fi
fi

# 3) System load
LOAD_AVG=$(uptime | awk -F'load averages:' '{print $2}' | sed -E 's/^[[:space:]]+//' | sed -E 's/[[:space:]]+/ /g' | tr -d "
" || echo "unknown")
append "System load averages: ${LOAD_AVG}"

# Extract 1-minute load for comparison
LOAD_1MIN=$(echo "$LOAD_AVG" | awk '{print $1}' | tr -d "," || echo "0")
CPU_COUNT=$(sysctl -n hw.ncpu 2>/dev/null || echo "1")

# Warn if load is very high (more than 2x CPU count)
if command -v bc >/dev/null 2>&1; then
  HIGH_LOAD_THRESHOLD=$(echo "$CPU_COUNT * 2" | bc 2>/dev/null || echo "9999")
  if (( $(echo "$LOAD_1MIN > $HIGH_LOAD_THRESHOLD" | bc -l 2>/dev/null || echo 0) )); then
    log_warn "High system load: ${LOAD_1MIN} (CPUs: ${CPU_COUNT})"
  fi
fi

# 4) Enhanced kernel panic detection with TIMEOUT to prevent hanging
HOURS="${HEALTH_LOG_LOOKBACK_HOURS:-24}"

# 🛡️ Sentinel: Sanitize input to prevent command injection
if ! [[ "$HOURS" =~ ^[0-9]+$ ]]; then
    log_warn "Invalid HEALTH_LOG_LOOKBACK_HOURS value: '$HOURS'. Using default 24."
    HOURS=24
fi

PANIC_DETAILS=""
MOST_RECENT_PANIC=""

log_info "Checking for kernel panics (with 10s timeout)..."

# Check for actual panic reports first (fast - just file search)
PANIC_DIR="/Library/Logs/DiagnosticReports"
if [[ -d "$PANIC_DIR" ]]; then
  PANIC_REPORTS=$(find "$PANIC_DIR" -name "*panic*" -mtime -1 2>/dev/null | wc -l | count_clean || echo "0")
  PANIC_REPORTS=$(to_int "$PANIC_REPORTS")
  
  if (( PANIC_REPORTS > 0 )); then
    # Get most recent panic file for detailed info
    MOST_RECENT_PANIC=$(find "$PANIC_DIR" -name "*panic*" -mtime -1 2>/dev/null | head -1)
    if [[ -n "$MOST_RECENT_PANIC" ]]; then
      PANIC_TIMESTAMP=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$MOST_RECENT_PANIC" 2>/dev/null || echo "unknown")
      PANIC_DETAILS="Most recent panic: $(basename "$MOST_RECENT_PANIC") at $PANIC_TIMESTAMP"
      log_warn "Found panic report: $MOST_RECENT_PANIC"
    fi
    
    append "⚠️ Actual kernel panic reports in last ${HOURS}h: ${PANIC_REPORTS}"
    append "$PANIC_DETAILS"
    log_warn "Found ${PANIC_REPORTS} kernel panic reports!"
  else
    # Look for genuine kernel panic messages in system logs
    # IMPORTANT: Use timeout to prevent hanging
    log_info "Searching system logs for panic messages (this may take up to 10 seconds)..."
    
    PANIC_SEARCH_CMD='log show --predicate '"'"'eventMessage CONTAINS "kernel panic" OR eventMessage CONTAINS "panic(cpu"'"'"' --last "'"${HOURS}"'h" 2>/dev/null | wc -l'
    REAL_KPANIC=$(run_with_timeout 10 "$PANIC_SEARCH_CMD" | count_clean || echo "0")
    REAL_KPANIC=$(to_int "$REAL_KPANIC")
    
    if [[ -z "$REAL_KPANIC" ]] || [[ "$REAL_KPANIC" == "0" ]]; then
      log_info "Log search completed (or timed out) - no panic messages found"
      REAL_KPANIC=0
    fi
    
    if (( REAL_KPANIC > 0 )); then
      # Try to get panic details with timeout
      PANIC_LOG_CMD='log show --predicate '"'"'eventMessage CONTAINS "kernel panic"'"'"' --last "'"${HOURS}"'h" --style compact 2>/dev/null | head -5'
      PANIC_LOG_SAMPLE=$(run_with_timeout 5 "$PANIC_LOG_CMD" || echo "")
      
      if [[ -n "$PANIC_LOG_SAMPLE" ]]; then
        PANIC_TIMESTAMP=$(echo "$PANIC_LOG_SAMPLE" | head -1 | awk '{print $1, $2}' || echo "unknown")
        PANIC_DETAILS="Panic messages in logs (timestamp: $PANIC_TIMESTAMP)"
      fi
      
      append "⚠️ Potential kernel panics in last ${HOURS}h: ${REAL_KPANIC}"
      append "$PANIC_DETAILS"
      log_warn "Found ${REAL_KPANIC} potential kernel panic messages"
    else
      append "Kernel panics in last ${HOURS}h: 0 (system stable)"
    fi
  fi
else
  append "Kernel panic directory not accessible: $PANIC_DIR"
fi

log_info "Panic detection completed"

# 5) Check for failed launch agents
FAILED_JOBS=$(launchctl list 2>/dev/null | awk '$3 ~ /^[1-9][0-9]*$/ {print $3":"$1}' || true)
if [[ -n "${FAILED_JOBS}" ]]; then
  append "Launch agents with non-zero exit codes: ${FAILED_JOBS}"
  log_warn "Found failed launch agents: ${FAILED_JOBS}"
else
  append "Launch agents: All running normally"
fi

# 6) Homebrew check
if command -v brew >/dev/null 2>&1; then
  BREW_DOC=$(brew doctor 2>&1 | head -10 || true)
  
  # Use rg if available for faster searching
  HAS_ISSUES=0
  if command -v rg >/dev/null 2>&1; then
    if ! echo "${BREW_DOC}" | rg -q "Your system is ready to brew"; then
      HAS_ISSUES=1
    fi
  else
    if ! echo "${BREW_DOC}" | grep -q "Your system is ready to brew"; then
      HAS_ISSUES=1
    fi
  fi

  if [[ "$HAS_ISSUES" -eq 1 ]]; then
    append "brew doctor issues detected:"
    append "${BREW_DOC}"
    log_warn "Homebrew doctor found issues"
  else
    append "brew doctor: System ready to brew"
  fi
  
fi

# 7) Software updates check (skip if running automated to avoid password prompts)
if [[ "${AUTOMATED_RUN:-0}" == "1" ]] || [[ -n "${SUDO_USER}" ]] || [[ "$EUID" -ne 0 ]]; then
  # Skip software update check during automated runs to avoid password prompts
  append "Software updates: Skipped (automated run)"
  log_info "Software update check skipped to avoid password prompts"
else
  SWU=$(/usr/sbin/softwareupdate -l 2>&1 || true)
  if echo "$SWU" | grep -qi "No new software available"; then
    append "Software updates: None available"
  elif echo "$SWU" | grep -qi "restart.*required\|reboot.*required"; then
    append "Software updates: RESTART REQUIRED"
    log_warn "Software updates require restart"
  else
    UPDATE_COUNT=$(echo "$SWU" | grep -c "recommended" || echo "0")
    append "Software updates: ${UPDATE_COUNT} available"
  fi
fi

# 8) Network connectivity check
if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
  append "Network connectivity: OK"
else
  append "Network connectivity: ISSUES DETECTED"
  log_warn "Network connectivity problems detected"
fi

# 9) Check for crash logs and diagnostic reports
CRASH_LOGS=$(find "${HOME}/Library/Logs/DiagnosticReports" -name "*.crash" -mtime -1 2>/dev/null | wc -l | count_clean || echo "0")
CRASH_LOGS=$(to_int "$CRASH_LOGS")
DIAGNOSTIC_REPORTS=$(find "${HOME}/Library/Logs/DiagnosticReports" -name "*.ips" -mtime -1 2>/dev/null | wc -l | count_clean || echo "0")
DIAGNOSTIC_REPORTS=$(to_int "$DIAGNOSTIC_REPORTS")
append "Recent crash logs (last 24h): ${CRASH_LOGS}"
append "Recent diagnostic reports (last 24h): ${DIAGNOSTIC_REPORTS}"

if (( CRASH_LOGS > 0 )); then
  log_warn "Found ${CRASH_LOGS} recent crash logs"
fi
if (( DIAGNOSTIC_REPORTS > 5 )); then
  log_warn "Found ${DIAGNOSTIC_REPORTS} recent diagnostic reports (threshold: 5)"
fi

# 10) Background service monitoring
WIDGET_COUNT=$(ps aux | grep -E "\.appex/Contents/MacOS" | grep -v grep | wc -l | count_clean || echo "0")
WIDGET_COUNT=$(to_int "$WIDGET_COUNT")
append "Widget extensions running: ${WIDGET_COUNT}"
if (( WIDGET_COUNT > 60 )); then
  log_warn "High widget count: ${WIDGET_COUNT} (threshold: 60)"
fi

# 11) Battery status (for MacBooks)
if command -v pmset >/dev/null 2>&1; then
  BATTERY_INFO=$(pmset -g batt 2>/dev/null | grep -v "Battery Power" | tail -1 || true)
  if [[ -n "${BATTERY_INFO}" ]]; then
    append "Battery status: ${BATTERY_INFO}"
    
    # Extract battery percentage
    BATTERY_PCT=$(echo "$BATTERY_INFO" | grep -o '[0-9]*%' | tr -d '%' || echo "100")
    if (( BATTERY_PCT < 10 )); then
      log_warn "Low battery: ${BATTERY_PCT}%"
    fi
  fi
fi

# Save report
REPORT_FILE="${LOG_DIR}/health_report-$(date +%Y%m%d-%H%M).txt"
printf "%s\n" "${REPORT}" > "${REPORT_FILE}"
log_info "Health report saved to ${REPORT_FILE}"

# Determine overall health status
HEALTH_ISSUES=0
ISSUE_REASONS=()

if [[ "${ROOT_USE:-0}" -ge "${DISK_WARN_VAL:-80}" ]]; then
  ((HEALTH_ISSUES++))
  ISSUE_REASONS+=("Disk ${ROOT_USE:-?}%")
fi

PANIC_REPORTS_INT=${PANIC_REPORTS:-0}
REAL_KPANIC_INT=${REAL_KPANIC:-0}
PANIC_COUNT=$((PANIC_REPORTS_INT + REAL_KPANIC_INT))

if (( PANIC_COUNT > 0 )); then
  ((HEALTH_ISSUES++))
  ISSUE_REASONS+=("Panics ${PANIC_COUNT}")
fi

if [[ "${CRASH_LOGS:-0}" -gt 0 ]]; then
  ((HEALTH_ISSUES++))
  ISSUE_REASONS+=("Crash logs ${CRASH_LOGS}")
fi

if [[ "${DIAGNOSTIC_REPORTS:-0}" -gt 5 ]]; then
  ((HEALTH_ISSUES++))
  ISSUE_REASONS+=("Diagnostic reports ${DIAGNOSTIC_REPORTS}")
fi

if [[ -n "${FAILED_JOBS}" ]]; then
  ((HEALTH_ISSUES++))
  ISSUE_REASONS+=("Launch agents failed")
fi

if [[ "${WIDGET_COUNT:-0}" -gt 60 ]]; then
  ((HEALTH_ISSUES++))
  ISSUE_REASONS+=("Widgets ${WIDGET_COUNT}")
fi

if (( HEALTH_ISSUES > 0 )); then
  HEALTH_STATUS="⚠️ Issues detected (${HEALTH_ISSUES})"
  log_warn "Health check found ${HEALTH_ISSUES} potential issues"
else
  HEALTH_STATUS="✅ System healthy"
fi

# Build a concise reasons string
REASONS_STR=""
if [[ ${#ISSUE_REASONS[@]} -gt 0 ]]; then
  REASONS_STR=$(IFS=", "; echo "${ISSUE_REASONS[*]}")
fi

# Enhanced notification with panic details
if command -v terminal-notifier >/dev/null 2>&1; then
  if (( HEALTH_ISSUES > 0 )); then
    # Build detailed notification message
    NOTIFICATION_MSG="Disk: ${ROOT_USE:-?}% | ${REASONS_STR}"

    if (( PANIC_COUNT > 0 )); then
      # Add best available detail line (panic file or timestamp)
      if [[ -n "$PANIC_DETAILS" ]]; then
        NOTIFICATION_MSG+="\n${PANIC_DETAILS}"
      fi

      # Provide actionable report (panic analyzer writes a report + opens when interactive)
      terminal-notifier -title "Health Check" \
        -subtitle "${HEALTH_ISSUES} issue(s): ${REASONS_STR}" \
        -message "$NOTIFICATION_MSG" \
        -group "maintenance" \
        -execute "$SCRIPT_DIR/panic_analyzer.sh" 2>/dev/null || true
    else
      terminal-notifier -title "Health Check" \
        -subtitle "${HEALTH_ISSUES} issue(s): ${REASONS_STR}" \
        -message "$NOTIFICATION_MSG" \
        -group "maintenance" \
        -execute "$HOME/Library/Maintenance/bin/view_logs.sh health_check" 2>/dev/null || true
    fi
  else
    terminal-notifier -title "Health Check" \
      -subtitle "System healthy" \
      -message "Disk: ${ROOT_USE:-?}% | No issues detected" \
      -group "maintenance" 2>/dev/null || true
  fi
elif command -v osascript >/dev/null 2>&1; then
  NOTIFICATION_TEXT="${HEALTH_STATUS} | Disk: ${ROOT_USE:-?}%"
  if [[ -n "$REASONS_STR" ]]; then
    NOTIFICATION_TEXT+="\n${REASONS_STR}"
  fi
  if (( PANIC_COUNT > 0 )) && [[ -n "$PANIC_DETAILS" ]]; then
    NOTIFICATION_TEXT+="\n${PANIC_DETAILS}"
  fi
  osascript -e "display notification \"${NOTIFICATION_TEXT}\" with title \"Health Check\"" 2>/dev/null || true
fi

log_info "Health check complete: ${HEALTH_STATUS}"
echo "Health check completed successfully!"
