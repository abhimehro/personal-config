#!/usr/bin/env bash
source "${HOME}/Scripts/maintenance/common.sh"
log_file_init "panic_analyzer"

log_info "Kernel panic analysis started"

REPORT_FILE="${LOG_DIR}/panic_analysis-$(date +%Y%m%d-%H%M).txt"
REPORT=""
append() { REPORT+="$1"$'\n'; echo "$1"; }

append "=== KERNEL PANIC ANALYSIS REPORT ==="
append "Generated: $(date)"
append ""

# 1) Recent panic logs with details
append "=== RECENT PANIC ENTRIES (Last 24h) ==="
PANIC_ENTRIES=$(log show --predicate 'eventMessage CONTAINS[c] "panic"' --last "24h" --style compact 2>/dev/null || echo "Unable to retrieve panic logs")
if [[ -n "${PANIC_ENTRIES}" ]]; then
    append "${PANIC_ENTRIES}"
else
    append "No panic entries found or unable to access logs"
fi
append ""

# 2) System shutdown/restart causes
append "=== SHUTDOWN/RESTART CAUSES (Last 48h) ==="
SHUTDOWN_LOGS=$(log show --predicate 'eventMessage CONTAINS[c] "shutdown cause" OR eventMessage CONTAINS[c] "Previous shutdown"' --last "48h" --style compact 2>/dev/null || echo "Unable to retrieve shutdown logs")
if [[ -n "${SHUTDOWN_LOGS}" ]]; then
    append "${SHUTDOWN_LOGS}"
else
    append "No shutdown cause entries found"
fi
append ""

# 3) Check for kernel extensions
append "=== LOADED KERNEL EXTENSIONS ==="
KEXTS=$(kextstat 2>/dev/null | grep -v "com.apple" | head -20 || echo "Unable to list kernel extensions")
append "Non-Apple kernel extensions:"
append "${KEXTS}"
append ""

# 4) Hardware-related logs
append "=== HARDWARE ISSUES (Last 24h) ==="
HW_LOGS=$(log show --predicate 'eventMessage CONTAINS[c] "thermal" OR eventMessage CONTAINS[c] "overheat" OR eventMessage CONTAINS[c] "temperature" OR eventMessage CONTAINS[c] "hardware error"' --last "24h" 2>/dev/null | head -50 || echo "No hardware issues found")
append "${HW_LOGS}"
append ""

# 5) Memory pressure events
append "=== MEMORY PRESSURE EVENTS (Last 24h) ==="
MEM_LOGS=$(log show --predicate 'eventMessage CONTAINS[c] "memory pressure" OR eventMessage CONTAINS[c] "low memory"' --last "24h" 2>/dev/null | head -20 || echo "No memory pressure events found")
append "${MEM_LOGS}"
append ""

# 6) Check crash reports directory
append "=== RECENT CRASH REPORTS ==="
CRASH_DIR="${HOME}/Library/Logs/DiagnosticReports"
if [[ -d "${CRASH_DIR}" ]]; then
    RECENT_CRASHES=$(find "${CRASH_DIR}" -name "*.crash" -o -name "*.panic" -mtime -7 2>/dev/null | head -10)
    if [[ -n "${RECENT_CRASHES}" ]]; then
        append "Recent crash/panic files (last 7 days):"
        append "${RECENT_CRASHES}"
        
        # Show summary of most recent crash
        LATEST_CRASH=$(find "${CRASH_DIR}" -name "*.crash" -mtime -1 2>/dev/null | head -1)
        if [[ -n "${LATEST_CRASH}" ]]; then
            append ""
            append "=== LATEST CRASH SUMMARY ==="
            append "File: ${LATEST_CRASH}"
            head -30 "${LATEST_CRASH}" 2>/dev/null | while read -r line; do
                append "$line"
            done
        fi
    else
        append "No recent crash reports found"
    fi
else
    append "Crash reports directory not accessible"
fi
append ""

# 7) System configuration that might cause issues
append "=== SYSTEM CONFIGURATION ==="
append "macOS Version: $(sw_vers -productVersion)"
append "Build: $(sw_vers -buildVersion)"
append "Hardware: $(system_profiler SPHardwareDataType | grep -E "(Model Name|Model Identifier|Processor|Memory)" 2>/dev/null || echo "Hardware info unavailable")"
append ""

# 8) Check for problematic processes
append "=== PROCESSES WITH HIGH CPU/MEMORY (Current) ==="
TOP_PROCESSES=$(top -l 1 -n 10 -stats pid,cpu,rsize,command | tail -n +13 || echo "Unable to get process info")
append "${TOP_PROCESSES}"
append ""

# 9) Disk and filesystem status
append "=== DISK STATUS ==="
DISK_STATUS=$(diskutil list 2>/dev/null || echo "Unable to get disk status")
append "${DISK_STATUS}"
append ""

# 10) USB/Thunderbolt devices (potential sources of kernel panics)
append "=== CONNECTED DEVICES ==="
USB_DEVICES=$(system_profiler SPUSBDataType 2>/dev/null | grep -E "(Product ID|Vendor ID|Serial Number)" | head -20 || echo "Unable to get USB device info")
append "USB Devices:"
append "${USB_DEVICES}"
append ""

# 11) Look for specific panic patterns
append "=== PANIC PATTERN ANALYSIS ==="
if command -v log >/dev/null 2>&1; then
    # Common panic causes
    WATCHDOG_PANICS=$(log show --predicate 'eventMessage CONTAINS[c] "watchdog timeout"' --last "7d" 2>/dev/null | wc -l | tr -d ' ')
    GPU_PANICS=$(log show --predicate 'eventMessage CONTAINS[c] "GPU" AND eventMessage CONTAINS[c] "panic"' --last "7d" 2>/dev/null | wc -l | tr -d ' ')
    DRIVER_PANICS=$(log show --predicate 'eventMessage CONTAINS[c] "driver" AND eventMessage CONTAINS[c] "panic"' --last "7d" 2>/dev/null | wc -l | tr -d ' ')
    
    append "Panic pattern counts (last 7 days):"
    append "- Watchdog timeouts: ${WATCHDOG_PANICS}"
    append "- GPU-related panics: ${GPU_PANICS}"
    append "- Driver-related panics: ${DRIVER_PANICS}"
fi

append ""
append "=== RECOMMENDATIONS ==="
if (( ${KEXTS} > 5 )); then
    append "⚠️  High number of non-Apple kernel extensions detected. Consider:"
    append "   - Uninstalling unnecessary drivers/extensions"
    append "   - Checking if extensions are compatible with your macOS version"
fi

append "📋 Next steps for diagnosis:"
append "1. Review crash reports in ~/Library/Logs/DiagnosticReports/"
append "2. Check Console.app for detailed system logs"
append "3. Run Apple Diagnostics: Hold D while starting up"
append "4. Consider safe mode boot to isolate third-party software"
append "5. If using beta macOS, file feedback with Apple"

# Save comprehensive report
printf "%s\n" "${REPORT}" > "${REPORT_FILE}"
log_info "Panic analysis saved to ${REPORT_FILE}"

echo ""
echo "🔍 Panic analysis complete! Report saved to:"
echo "   ${REPORT_FILE}"
echo ""
echo "📋 Quick Actions:"
echo "   • Review the report above for patterns"
echo "   • Check ${HOME}/Library/Logs/DiagnosticReports/ for detailed crash logs"
echo "   • Run: sudo dmesg | grep -i panic (for recent kernel messages)"
echo "   • Consider: Apple Menu > About This Mac > System Report for hardware details"
