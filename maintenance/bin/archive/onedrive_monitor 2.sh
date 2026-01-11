#!/usr/bin/env bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/common.sh"
with_lock "onedrive_monitor"

log_info "OneDrive monitoring started"

# Detect OneDrive root directory
ONEDRIVE_ROOT=$(ls -d "$HOME/Library/CloudStorage/OneDrive"* 2>/dev/null | head -1)

if [[ -z "$ONEDRIVE_ROOT" ]]; then
    log_warn "OneDrive directory not found in CloudStorage"
    notify "OneDrive Monitor" "⚠️ OneDrive directory not found"
    exit 1
fi

log_info "OneDrive root: $ONEDRIVE_ROOT"

# Check if OneDrive process is running
ONEDRIVE_PID=$(pgrep -f "/OneDrive$" 2>/dev/null)
if [[ -n "$ONEDRIVE_PID" ]]; then
    log_info "OneDrive process running (PID: $ONEDRIVE_PID)"
    process_running=true
else
    log_warn "OneDrive process not running"
    process_running=false
fi

# Check recent sync activity
log_info "Checking recent sync activity..."
recent_files=$(find "$ONEDRIVE_ROOT" -type f -mtime -1 -print -quit 2>/dev/null)
if [[ -n "$recent_files" ]]; then
    log_info "Recent sync activity detected (files modified in last 24h)"
    recent_activity=true
else
    log_warn "No recent sync activity detected (no files modified in last 24h)"
    recent_activity=false
fi

# Check OneDrive logs for issues
ONEDRIVE_LOGS="$HOME/Library/Containers/com.microsoft.OneDrive/Data/Library/Logs/OneDrive"
log_issues=""

if [[ -d "$ONEDRIVE_LOGS" ]]; then
    log_info "Checking OneDrive logs for issues..."
    
    # Look for recent error/warning patterns
    if latest_log=$(find "$ONEDRIVE_LOGS" -name "OneDrive*.log" -type f -mtime -7 | head -1); then
        log_issues=$(tail -n 200 "$latest_log" 2>/dev/null | grep -E "error|warning|throttl|auth|offline" -i | tail -5 || true)
        
        if [[ -n "$log_issues" ]]; then
            log_warn "Found recent issues in OneDrive logs:"
            echo "$log_issues" | while IFS= read -r line; do
                log_warn "  $line"
            done
        else
            log_info "No error/warning patterns found in recent logs"
        fi
    else
        log_warn "No recent OneDrive log files found"
    fi
else
    log_warn "OneDrive logs directory not found: $ONEDRIVE_LOGS"
fi

# Network connectivity check for OneDrive
log_info "Checking OneDrive connectivity..."
if ping -c 1 oneclient.sfx.ms >/dev/null 2>&1; then
    log_info "OneDrive network connectivity: OK"
    network_ok=true
else
    log_warn "OneDrive network connectivity: ISSUES DETECTED"
    network_ok=false
fi

# Determine overall status
issues=0
status_messages=()

if [[ "$process_running" == "false" ]]; then
    ((issues++))
    status_messages+=("Process not running")
fi

if [[ "$recent_activity" == "false" ]]; then
    ((issues++))
    status_messages+=("No recent sync activity")
fi

if [[ -n "$log_issues" ]]; then
    ((issues++))
    status_messages+=("Log issues detected")
fi

if [[ "$network_ok" == "false" ]]; then
    ((issues++))
    status_messages+=("Network issues")
fi

# Self-healing actions
needs_restart=false

if [[ "$process_running" == "false" ]] || [[ "$recent_activity" == "false" && "$network_ok" == "true" ]]; then
    if [[ "${DRY_RUN:-0}" == "0" ]]; then
        log_info "Attempting OneDrive self-healing..."
        
        # Kill any existing OneDrive processes
        if [[ -n "$ONEDRIVE_PID" ]]; then
            log_info "Stopping existing OneDrive process..."
            killall OneDrive 2>/dev/null || true
            sleep 3
        fi
        
        # Start OneDrive
        log_info "Starting OneDrive application..."
        if open -a "OneDrive" 2>/dev/null; then
            log_info "OneDrive restart initiated"
            needs_restart=true
            sleep 5
            
            # Verify process started
            if pgrep -f "/OneDrive$" >/dev/null 2>&1; then
                log_info "OneDrive process started successfully"
                process_running=true
                ((issues--)) # Reduce issue count since we fixed process
            else
                log_warn "OneDrive process failed to start"
            fi
        else
            log_error "Failed to start OneDrive application"
        fi
    else
        log_info "[DRY RUN] Would restart OneDrive application"
        needs_restart=true
    fi
fi

# Get OneDrive status via command line (if available)
if command -v "/Applications/OneDrive.app/Contents/MacOS/OneDrive" >/dev/null 2>&1; then
    onedrive_status=$("/Applications/OneDrive.app/Contents/MacOS/OneDrive" /status 2>/dev/null || true)
    if [[ -n "$onedrive_status" ]]; then
        log_info "OneDrive status: $onedrive_status"
    fi
fi

# Final status summary
if [[ $issues -eq 0 ]]; then
    status="✅ OneDrive healthy"
    log_info "$status"
else
    status="⚠️ OneDrive issues (${issues}): ${status_messages[*]}"
    log_warn "$status"
fi

# Send notification
if [[ $issues -gt 0 ]]; then
    if [[ "$needs_restart" == "true" ]]; then
        notify "OneDrive Monitor" "$status - Restart attempted"
    else
        notify "OneDrive Monitor" "$status"
    fi
else
    log_info "OneDrive monitoring complete - no notification needed for healthy status"
fi

log_info "OneDrive monitoring complete"
after_success