#!/usr/bin/env bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")"/../lib && pwd)/common.sh"
with_lock "health_check"

log_info "Health check started"

REPORT=""
append() { REPORT+="$1"$'\n'; log_info "$1"; }

# 1) Disk space check
ROOT_USE=$(percent_used "/")
append "Disk usage for /: ${ROOT_USE}%"
if (( ROOT_USE >= ${DISK_CRIT_PCT:-90} )); then
  log_warn "Critical disk usage: ${ROOT_USE}%"
  if should_auto_remediate; then
    log_info "Running auto-cleanup due to critical disk usage"
    "$MNT_ROOT/bin/system_cleanup.sh" || log_warn "Auto-cleanup failed"
    ROOT_USE=$(percent_used "/")
    append "Post-cleanup disk usage for /: ${ROOT_USE}%"
  fi
elif (( ROOT_USE >= ${DISK_WARN_PCT:-80} )); then
  log_warn "High disk usage: ${ROOT_USE}%"
fi

# 2) Memory pressure check
if command -v memory_pressure >/dev/null 2>&1; then
  MP_SUM=$(memory_pressure -Q 2>/dev/null | awk -F'=' '/systemwide/ {print $2+0}' || echo "unknown")
  append "Memory pressure: ${MP_SUM}%"
  if [[ -n "${MP_SUM:-}" && "${MP_SUM}" != "unknown" && "${MP_SUM}" -ge "${MEMORY_PRESSURE_WARN:-80}" ]]; then
    log_warn "Elevated memory pressure detected: ${MP_SUM}%"
  fi
fi

# 3) Recent kernel panics and shutdown causes
HOURS="${HEALTH_LOG_LOOKBACK_HOURS:-24}"
KPANIC=$(log show --predicate 'eventMessage CONTAINS[c] "panic"' --last "${HOURS}h" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
append "Kernel panic-like log entries in last ${HOURS}h: ${KPANIC}"

SHUT_CAUSES=$(log show --predicate 'eventMessage CONTAINS[c] "Previous shutdown cause"' --last "${HOURS}h" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
append "Previous shutdown cause entries in last ${HOURS}h: ${SHUT_CAUSES}"

# 4) Check for crashed processes and failed launch agents
FAILED_JOBS=$(launchctl list 2>/dev/null | awk '$3 ~ /^[1-9][0-9]*$/ {print $3":"$1}' || true)
if [[ -n "${FAILED_JOBS}" ]]; then
  append "Launch agents with non-zero exit codes: ${FAILED_JOBS}"
  log_warn "Found failed launch agents: ${FAILED_JOBS}"
fi

# 5) System load average
LOAD_AVG=$(uptime | awk -F'load averages:' '{print $2}' | tr -d ' ' || echo "unknown")
append "System load averages: ${LOAD_AVG}"

# 6) Available memory
if command -v vm_stat >/dev/null 2>&1; then
  FREE_PAGES=$(vm_stat | awk '/Pages free:/ {print $3}' | tr -d '.' || echo "0")
  PAGE_SIZE=$(vm_stat | awk '/page size of/ {print $8}' || echo "4096")
  FREE_MB=$(( (FREE_PAGES * PAGE_SIZE) / 1024 / 1024 ))
  append "Free memory: ${FREE_MB} MB"
fi

# 7) Temperature check (if available)
if command -v pmset >/dev/null 2>&1; then
  TEMP_INFO=$(pmset -g therm 2>/dev/null | grep -i "CPU_Speed_Limit\|GPU_Speed_Limit" || true)
  if [[ -n "${TEMP_INFO}" ]]; then
    append "Thermal throttling info: ${TEMP_INFO}"
  fi
fi

# 8) Homebrew doctor check
if command -v brew >/dev/null 2>&1; then
  BREW_DOC=$(brew doctor 2>&1 | head -20 || true)
  if echo "${BREW_DOC}" | grep -v "Your system is ready to brew" >/dev/null; then
    append "brew doctor issues detected:"
    append "${BREW_DOC}"
    log_warn "Homebrew doctor found issues"
  else
    append "brew doctor: System ready to brew"
  fi
fi

# 9) Software updates check
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

# 10) Disk verification (quick check)
if command -v diskutil >/dev/null 2>&1; then
  DISKROOT=$(diskutil info / 2>/dev/null | awk '/Device Identifier:/ {print $3}' | head -1 || echo "")
  if [[ -n "${DISKROOT}" ]]; then
    DISK_STATUS=$(diskutil verifyVolume / 2>&1 | tail -1 || echo "unknown")
    append "Disk verification: ${DISK_STATUS}"
    if ! echo "${DISK_STATUS}" | grep -qi "appears to be ok\|volume appears to be ok"; then
      log_warn "Disk verification found potential issues: ${DISK_STATUS}"
    fi
  fi
fi

# 11) Check for core dumps or crash logs
CRASH_LOGS=$(find "${HOME}/Library/Logs/DiagnosticReports" -name "*.crash" -mtime -1 2>/dev/null | wc -l | tr -d ' ' || echo "0")
append "Recent crash logs (last 24h): ${CRASH_LOGS}"
if (( CRASH_LOGS > 0 )); then
  log_warn "Found ${CRASH_LOGS} recent crash logs"
fi

# 12) Network connectivity check
if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
  append "Network connectivity: OK"
else
  append "Network connectivity: ISSUES DETECTED"
  log_warn "Network connectivity problems detected"
fi

# 13) Check for runaway processes (high CPU usage)
TOP_PROCS=$(top -l 1 -n 5 -stats pid,cpu,command | tail -n +12 | head -5 || true)
if [[ -n "${TOP_PROCS}" ]]; then
  append "Top CPU processes:"
  append "${TOP_PROCS}"
fi

# 14) Battery status (for MacBooks)
if command -v pmset >/dev/null 2>&1; then
  BATTERY_INFO=$(pmset -g batt 2>/dev/null | grep -v "Battery Power" | tail -1 || true)
  if [[ -n "${BATTERY_INFO}" ]]; then
    append "Battery status: ${BATTERY_INFO}"
  fi
fi

# 15) Check system integrity (SIP status)
if command -v csrutil >/dev/null 2>&1; then
  SIP_STATUS=$(csrutil status 2>&1 || echo "unknown")
  append "System Integrity Protection: ${SIP_STATUS}"
fi

# Save comprehensive health report
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

prune_logs
log_info "Health check complete"
notify "Health Check" "${HEALTH_STATUS} | Disk: ${ROOT_USE:-?}% | Panics: ${KPANIC:-0}"
