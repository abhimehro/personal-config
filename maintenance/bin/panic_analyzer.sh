#!/usr/bin/env bash

# Self-contained kernel panic analysis report.
# Safe to run non-interactively; avoids hanging by using short timeouts where possible.

set -eo pipefail

LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [panic_analyzer] $*" | tee -a "$LOG_DIR/panic_analyzer.log"
}

log_warn() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [WARNING] [panic_analyzer] $*" | tee -a "$LOG_DIR/panic_analyzer.log"
}

# Prefer gtimeout (coreutils) if available, else use a simple kill-based timeout.
run_with_timeout() {
    local timeout_seconds="$1"; shift
    local cmd="$@"

    if command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$timeout_seconds" bash -c "$cmd" 2>/dev/null || true
        return 0
    fi

    local output_file
    output_file=$(mktemp)
    bash -c "$cmd" >"$output_file" 2>/dev/null &
    local pid=$!

    local count=0
    while kill -0 "$pid" 2>/dev/null && [[ $count -lt $timeout_seconds ]]; do
        sleep 1
        count=$((count + 1))
    done

    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
        rm -f "$output_file"
        return 0
    fi

    wait "$pid" 2>/dev/null || true
    cat "$output_file" 2>/dev/null || true
    rm -f "$output_file"
    return 0
}

REPORT_FILE="$LOG_DIR/panic_analysis-$(date +%Y%m%d-%H%M).txt"

{
    echo "=== KERNEL PANIC ANALYSIS REPORT ==="
    echo "Generated: $(date)"
    echo

    echo "=== PANIC REPORT FILES (Last 7 days) ==="
    PANIC_DIR="/Library/Logs/DiagnosticReports"
    if [[ -d "$PANIC_DIR" ]]; then
        find "$PANIC_DIR" -maxdepth 1 -type f -iname "*panic*" -mtime -7 2>/dev/null | sed -n '1,50p'
    else
        echo "Panic directory not accessible: $PANIC_DIR"
    fi
    echo

    echo "=== PANIC-LIKE LOG ENTRIES (Last 24h, sample) ==="
    if command -v log >/dev/null 2>&1; then
        run_with_timeout 8 "log show --predicate 'eventMessage CONTAINS[c] \"kernel panic\" OR eventMessage CONTAINS[c] \"panic(cpu\"' --last 24h --style compact | head -50"
    else
        echo "log command not available"
    fi
    echo

    echo "=== SHUTDOWN/RESTART CAUSES (Last 48h, sample) ==="
    if command -v log >/dev/null 2>&1; then
        run_with_timeout 8 "log show --predicate 'eventMessage CONTAINS[c] \"shutdown cause\" OR eventMessage CONTAINS[c] \"Previous shutdown\"' --last 48h --style compact | head -80"
    else
        echo "log command not available"
    fi
    echo

    echo "=== NON-APPLE KERNEL EXTENSIONS (if any) ==="
    if command -v kextstat >/dev/null 2>&1; then
        kextstat 2>/dev/null | grep -v "com.apple" | sed -n '1,60p' || true
    else
        echo "kextstat not available (expected on Apple Silicon / newer macOS)"
    fi
    echo

    echo "=== RECENT DIAGNOSTIC REPORTS (Last 7 days) ==="
    USER_DIAG="$HOME/Library/Logs/DiagnosticReports"
    if [[ -d "$USER_DIAG" ]]; then
        find "$USER_DIAG" -maxdepth 1 -type f \( -name "*.panic" -o -name "*.ips" -o -name "*.crash" \) -mtime -7 2>/dev/null | sed -n '1,50p'
    else
        echo "User diagnostic dir not accessible: $USER_DIAG"
    fi
    echo

    echo "=== LATEST PANIC FILE (head) ==="
    if [[ -d "$PANIC_DIR" ]]; then
        LATEST=$(ls -t "$PANIC_DIR"/*panic* 2>/dev/null | head -1 || true)
        if [[ -n "$LATEST" ]] && [[ -f "$LATEST" ]]; then
            echo "File: $LATEST"
            echo
            head -120 "$LATEST" 2>/dev/null || true
        else
            echo "No panic files found in $PANIC_DIR"
        fi
    fi
    echo

    echo "=== SYSTEM CONTEXT ==="
    echo "macOS: $(sw_vers -productVersion 2>/dev/null || true) ($(sw_vers -buildVersion 2>/dev/null || true))"
    echo "Uptime: $(uptime 2>/dev/null || true)"
    echo "Hardware:"
    system_profiler SPHardwareDataType 2>/dev/null | grep -E "Model Name|Model Identifier|Chip|Processor|Memory" || true
    echo

    echo "=== CURRENT TOP PROCESSES (CPU/mem, sample) ==="
    top -l 1 -n 10 -stats pid,cpu,rsize,command 2>/dev/null | sed -n '1,35p' || true
    echo

    echo "=== RECOMMENDATIONS ==="
    echo "* If panics are frequent, check the LATEST PANIC FILE section for implicated kexts/drivers or subsystems."
    echo "* Disconnect recently-added USB/Thunderbolt devices and observe if panics stop."
    echo "* If you use third-party kernel/system extensions (VPNs, AV, drivers), update or uninstall to test."
    echo "* Run Apple Diagnostics (hold D at boot) if panics persist."
} | tee "$REPORT_FILE" >/dev/null

log_info "Panic analysis saved to: $REPORT_FILE"

# Open the report when run interactively.
if [[ -t 1 ]] && command -v open >/dev/null 2>&1; then
    open -a TextEdit "$REPORT_FILE" 2>/dev/null || true
fi

echo "$REPORT_FILE"
