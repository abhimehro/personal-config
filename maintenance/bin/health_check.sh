#!/usr/bin/env bash

# Self-contained health check script with inline functions
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

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
if (( ROOT_USE >= ${DISK_CRIT_PCT:-90} )); then
  log_warn "Critical disk usage: ${ROOT_USE}%"
elif (( ROOT_USE >= ${DISK_WARN_PCT:-80} )); then
  log_warn "High disk usage: ${ROOT_USE}%"
fi

# 2) Memory check
if command -v vm_stat >/dev/null 2>&1; then
  FREE_PAGES=$(vm_stat | awk '/Pages free:/ {print $3}' | tr -d '.' || echo "0")
  PAGE_SIZE=$(vm_stat | awk '/page size of/ {print $8}' || echo "4096")
  FREE_MB=$(( (FREE_PAGES * PAGE_SIZE) / 1024 / 1024 ))
  append "Free memory: ${FREE_MB} MB"
fi

# 3) System load
LOAD_AVG=$(uptime | awk -F'load averages:' '{print $2}' | tr -d ' ' || echo "unknown")
append "System load averages: ${LOAD_AVG}"

# 4) Recent kernel panics
HOURS="${HEALTH_LOG_LOOKBACK_HOURS:-24}"
KPANIC=$(log show --predicate 'eventMessage CONTAINS[c] "panic"' --last "${HOURS}h" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
append "Kernel panic-like log entries in last ${HOURS}h: ${KPANIC}"

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
  if echo "${BREW_DOC}" | grep -v "Your system is ready to brew" >/dev/null; then
    append "brew doctor issues detected:"
    append "${BREW_DOC}"
    log_warn "Homebrew doctor found issues"
  else
    append "brew doctor: System ready to brew"
  fi
  
  # Check for outdated packages
  BREW_OUTDATED=$(brew outdated 2>/dev/null | wc -l | tr -d ' ')
  append "Outdated Homebrew packages: ${BREW_OUTDATED}"
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

# 9) Check for crash logs
CRASH_LOGS=$(find "${HOME}/Library/Logs/DiagnosticReports" -name "*.crash" -mtime -1 2>/dev/null | wc -l | tr -d ' ' || echo "0")
append "Recent crash logs (last 24h): ${CRASH_LOGS}"
if (( CRASH_LOGS > 0 )); then
  log_warn "Found ${CRASH_LOGS} recent crash logs"
fi

# 10) Battery status (for MacBooks)
if command -v pmset >/dev/null 2>&1; then
  BATTERY_INFO=$(pmset -g batt 2>/dev/null | grep -v "Battery Power" | tail -1 || true)
  if [[ -n "${BATTERY_INFO}" ]]; then
    append "Battery status: ${BATTERY_INFO}"
  fi
fi

# Save report
REPORT_FILE="${LOG_DIR}/health_report-$(date +%Y%m%d-%H%M).txt"
printf "%s\n" "${REPORT}" > "${REPORT_FILE}"
log_info "Health report saved to ${REPORT_FILE}"

# Determine overall health status
HEALTH_ISSUES=0
[[ "${ROOT_USE:-0}" -ge "${DISK_WARN_PCT:-80}" ]] && ((HEALTH_ISSUES++))
[[ "${KPANIC:-0}" -gt 0 ]] && ((HEALTH_ISSUES++))
[[ "${CRASH_LOGS:-0}" -gt 0 ]] && ((HEALTH_ISSUES++))
[[ -n "${FAILED_JOBS}" ]] && ((HEALTH_ISSUES++))

if (( HEALTH_ISSUES > 0 )); then
  HEALTH_STATUS="⚠️ Issues detected (${HEALTH_ISSUES})"
  log_warn "Health check found ${HEALTH_ISSUES} potential issues"
else
  HEALTH_STATUS="✅ System healthy"
fi

# Notification
if command -v osascript >/dev/null 2>&1; then
  osascript -e "display notification \"${HEALTH_STATUS} | Disk: ${ROOT_USE:-?}% | Panics: ${KPANIC:-0}\" with title \"Health Check\"" 2>/dev/null || true
fi

log_info "Health check complete: ${HEALTH_STATUS}"
echo "Health check completed successfully!"