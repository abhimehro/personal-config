#!/usr/bin/env bash

# Self-contained OneDrive monitoring script
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

# Basic logging
log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [onedrive_monitor] $*" | tee -a "$LOG_DIR/onedrive_monitor.log"
}

log_warn() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [WARNING] [onedrive_monitor] $*" | tee -a "$LOG_DIR/onedrive_monitor.log"
}

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE" 2>/dev/null || true
fi

log_info "OneDrive monitoring started"

# Check if OneDrive is running
ONEDRIVE_STATUS="Not detected"
SYNC_STATUS="Unknown"

# Check for OneDrive process
if pgrep -f "OneDrive" >/dev/null 2>&1; then
    ONEDRIVE_STATUS="Running"
    log_info "OneDrive process is running"
    
    # Check OneDrive directory
    ONEDRIVE_DIR="$HOME/OneDrive"
    if [[ -d "$ONEDRIVE_DIR" ]]; then
        log_info "OneDrive directory found: $ONEDRIVE_DIR"
        
        # Check recent sync activity (files modified in last 48 hours)
        SYNC_CHECK_HOURS="${ONEDRIVE_SYNC_CHECK_HOURS:-48}"
        RECENT_FILES=$(find "$ONEDRIVE_DIR" -type f -mtime -2 2>/dev/null | wc -l | tr -d ' ')
        
        if [[ $RECENT_FILES -gt 0 ]]; then
            SYNC_STATUS="Active (${RECENT_FILES} files modified in last ${SYNC_CHECK_HOURS}h)"
            log_info "OneDrive sync appears active: ${RECENT_FILES} files modified recently"
        else
            SYNC_STATUS="No recent activity"
            log_warn "No OneDrive file activity detected in last ${SYNC_CHECK_HOURS} hours"
        fi
        
        # Check OneDrive directory size
        ONEDRIVE_SIZE=$(du -sh "$ONEDRIVE_DIR" 2>/dev/null | cut -f1 || echo "unknown")
        log_info "OneDrive directory size: $ONEDRIVE_SIZE"
        
    else
        log_warn "OneDrive directory not found at $ONEDRIVE_DIR"
        SYNC_STATUS="Directory not found"
    fi
    
else
    log_warn "OneDrive process not found"
    ONEDRIVE_STATUS="Not running"
fi

# Check for OneDrive in Applications
ONEDRIVE_APP="/Applications/Microsoft OneDrive.app"
if [[ -d "$ONEDRIVE_APP" ]]; then
    ONEDRIVE_VERSION=$(defaults read "$ONEDRIVE_APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null || echo "unknown")
    log_info "OneDrive app version: $ONEDRIVE_VERSION"
else
    log_warn "OneDrive app not found in Applications"
fi

# Check system login items for OneDrive
if osascript -e 'tell application "System Events" to get the name of every login item' 2>/dev/null | grep -qi onedrive; then
    log_info "OneDrive is in login items (will start automatically)"
else
    log_warn "OneDrive not found in login items"
fi

# Simple connectivity test
log_info "Testing internet connectivity for OneDrive sync..."
if ping -c 1 graph.microsoft.com >/dev/null 2>&1; then
    log_info "Microsoft Graph connectivity: OK"
elif ping -c 1 1.1.1.1 >/dev/null 2>&1; then
    log_info "Internet connectivity: OK (but Microsoft Graph unreachable)"
else
    log_warn "Internet connectivity: Issues detected"
fi

# Summary status
STATUS_MSG="OneDrive: $ONEDRIVE_STATUS | Sync: $SYNC_STATUS"

# Notification
if command -v terminal-notifier >/dev/null 2>&1; then
    if [[ "$ONEDRIVE_STATUS" != "Running" ]] || [[ "$SYNC_STATUS" == *"No recent activity"* ]]; then
        # Issues detected - provide actionable notification
        terminal-notifier -title "OneDrive Monitor" \
          -subtitle "Issues detected" \
          -message "Status: $ONEDRIVE_STATUS | Sync: $SYNC_STATUS | Click for details" \
          -group "maintenance" \
          -execute "/Users/speedybee/Library/Maintenance/bin/view_logs.sh onedrive_monitor" 2>/dev/null || true
        log_warn "OneDrive monitoring detected potential issues"
    else
        # Normal operation - simple notification
        terminal-notifier -title "OneDrive Monitor" \
          -subtitle "Working normally" \
          -message "$STATUS_MSG" \
          -group "maintenance" 2>/dev/null || true
        log_info "OneDrive appears to be working normally"
    fi
elif command -v osascript >/dev/null 2>&1; then
    # Fallback to osascript
    if [[ "$ONEDRIVE_STATUS" != "Running" ]] || [[ "$SYNC_STATUS" == *"No recent activity"* ]]; then
        osascript -e "display notification \"$STATUS_MSG\" with title \"OneDrive Monitor - Issues Detected\"" 2>/dev/null || true
        log_warn "OneDrive monitoring detected potential issues"
    else
        log_info "OneDrive appears to be working normally"
    fi
fi

log_info "OneDrive monitoring complete: $STATUS_MSG"
echo "OneDrive monitoring completed successfully!"