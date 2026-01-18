#!/usr/bin/env bash

# Google Drive monitoring and health check script
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

# Basic logging
log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [google_drive_monitor] $*" | tee -a "$LOG_DIR/google_drive_monitor.log"
}

log_warn() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [WARNING] [google_drive_monitor] $*" | tee -a "$LOG_DIR/google_drive_monitor.log"
}

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE" 2>/dev/null || true
fi

log_info "Google Drive monitoring started"

# Check if Google Drive is running
GDRIVE_STATUS="Not detected"
SYNC_STATUS="Unknown"

# Check for Google Drive process
if pgrep -f "Google Drive" >/dev/null 2>&1; then
    GDRIVE_STATUS="Running"
    log_info "Google Drive process is running"
    
    # Check Google Drive directory
    GDRIVE_DIR="${GDRIVE_ROOT:-$HOME/Library/CloudStorage}"
    # If GDRIVE_ROOT is a parent directory, try to find GoogleDrive-* subdir
    if [[ -d "$GDRIVE_DIR" ]] && [[ "$GDRIVE_DIR" == *"/CloudStorage" ]]; then
        GDRIVE_DIR=$(ls -1d "$HOME/Library/CloudStorage/GoogleDrive-"* 2>/dev/null | head -1 || true)
    fi
    if [[ -d "$GDRIVE_DIR" ]]; then
        log_info "Google Drive directory found: $GDRIVE_DIR"
        
        # Check recent sync activity (files modified in last 48 hours)
        SYNC_CHECK_HOURS="${GDRIVE_SYNC_CHECK_HOURS:-48}"
        RECENT_FILES=$(find "$GDRIVE_DIR" -type f -mtime -2 2>/dev/null | wc -l | tr -d ' ')
        
        if [[ $RECENT_FILES -gt 0 ]]; then
            SYNC_STATUS="Active (${RECENT_FILES} files modified in last ${SYNC_CHECK_HOURS}h)"
            log_info "Google Drive sync appears active: ${RECENT_FILES} files modified recently"
        else
            SYNC_STATUS="No recent activity"
            log_warn "No Google Drive file activity detected in last ${SYNC_CHECK_HOURS} hours"
        fi
        
        # Check Google Drive directory size
        GDRIVE_SIZE=$(du -sh "$GDRIVE_DIR" 2>/dev/null | cut -f1 || echo "unknown")
        log_info "Google Drive directory size: $GDRIVE_SIZE"
        
        # Check for sync errors in logs
        SYNC_ERRORS=0
        if [[ -d "$HOME/Library/Application Support/Google/DriveFS/Logs" ]]; then
            # Look for error patterns in recent logs
            RECENT_LOGS=$(find "$HOME/Library/Application Support/Google/DriveFS/Logs" -name "*.log" -mtime -1 2>/dev/null)
            if [[ -n "$RECENT_LOGS" ]]; then
                SYNC_ERRORS=$(grep -i "error\|failed\|cannot sync" $RECENT_LOGS 2>/dev/null | wc -l | tr -d "[:space:]" || echo "0")
                SYNC_ERRORS=$(printf "%s" "${SYNC_ERRORS}" | tr -cd "0-9")
                SYNC_ERRORS=${SYNC_ERRORS:-0}
                if [[ $SYNC_ERRORS -gt 5 ]]; then
                    log_warn "Google Drive sync errors detected: ${SYNC_ERRORS} error messages in recent logs"
                    SYNC_STATUS="${SYNC_STATUS} (${SYNC_ERRORS} errors)"
                fi
            fi
        fi
        
    else
        log_warn "Google Drive directory not found at $GDRIVE_DIR"
        SYNC_STATUS="Directory not found"
    fi
    
else
    log_warn "Google Drive process not found"
    GDRIVE_STATUS="Not running"
fi

# Check for Google Drive in Applications
GDRIVE_APP="/Applications/Google Drive.app"
if [[ -d "$GDRIVE_APP" ]]; then
    GDRIVE_VERSION=$(defaults read "$GDRIVE_APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null || echo "unknown")
    log_info "Google Drive app version: $GDRIVE_VERSION"
else
    log_warn "Google Drive app not found in Applications"
fi

# Check system login items for Google Drive
if osascript -e 'tell application "System Events" to get the name of every login item' 2>/dev/null | grep -qi "google drive"; then
    log_info "Google Drive is in login items (will start automatically)"
else
    log_warn "Google Drive not found in login items"
fi

# Check disk space for Google Drive location
if [[ -d "$GDRIVE_DIR" ]]; then
    GDRIVE_DISK_USAGE=$(df -h "$GDRIVE_DIR" 2>/dev/null | awk 'NR==2 {print $5}' | tr -d '%' | tr -d "[:space:]" || echo "0")
    GDRIVE_DISK_USAGE=$(printf "%s" "${GDRIVE_DISK_USAGE}" | tr -cd "0-9")
    GDRIVE_DISK_USAGE=${GDRIVE_DISK_USAGE:-0}
    if [[ $GDRIVE_DISK_USAGE -gt 85 ]]; then
        log_warn "Google Drive storage location is ${GDRIVE_DISK_USAGE}% full"
    else
        log_info "Google Drive storage location usage: ${GDRIVE_DISK_USAGE}%"
    fi
fi

# Check internet connectivity for Google Drive sync
log_info "Testing internet connectivity for Google Drive sync..."
if ping -c 1 drive.google.com >/dev/null 2>&1; then
    log_info "Google Drive connectivity: OK"
elif ping -c 1 1.1.1.1 >/dev/null 2>&1; then
    log_info "Internet connectivity: OK (but Google Drive unreachable)"
    SYNC_STATUS="${SYNC_STATUS} (connectivity issues)"
else
    log_warn "Internet connectivity: Issues detected"
    SYNC_STATUS="${SYNC_STATUS} (offline)"
fi

# Check Proton Drive backup status (companion check)
PROTON_STATUS="Unknown"

find_proton_homebackup_dir() {
    # 1) Explicit override
    if [[ -n "${PROTON_BACKUP_DEST:-}" ]] && [[ -d "${PROTON_BACKUP_DEST}" ]]; then
        printf '%s
' "${PROTON_BACKUP_DEST}"
        return 0
    fi

    # 2) Probe common CloudStorage location
    local -a candidates=()
    while IFS= read -r d; do
        [[ -n "$d" ]] && candidates+=("$d")
    done < <(find "$HOME/Library/CloudStorage" -maxdepth 2 -type d -name "HomeBackup" 2>/dev/null)

    if [[ ${#candidates[@]} -gt 0 ]]; then
        printf '%s
' "${candidates[0]}"
        return 0
    fi

    # 3) Fallback shallow search under $HOME (rare)
    while IFS= read -r d; do
        [[ -n "$d" ]] && { printf '%s
' "$d"; return 0; }
    done < <(find "$HOME" -maxdepth 4 -type d -name "HomeBackup" 2>/dev/null | head -20)

    return 1
}

PROTON_DIR=$(find_proton_homebackup_dir 2>/dev/null || true)
if [[ -n "$PROTON_DIR" ]] && [[ -d "$PROTON_DIR" ]]; then
    EXPECT_DAYS="${PROTON_BACKUP_EXPECT_DAYS:-7}"
    LAST_BACKUP=$(find "$PROTON_DIR" -type f -mtime -"$EXPECT_DAYS" 2>/dev/null | wc -l | tr -d '[:space:]')
    LAST_BACKUP=$(printf "%s" "${LAST_BACKUP}" | tr -cd '0-9')
    LAST_BACKUP=${LAST_BACKUP:-0}

    if [[ $LAST_BACKUP -gt 0 ]]; then
        PROTON_STATUS="Recent backup detected (last ${EXPECT_DAYS}d)"
        log_info "Proton Drive: Recent backup activity found"
    else
        PROTON_STATUS="No recent backup in last ${EXPECT_DAYS}d"
        log_warn "Proton Drive: No recent backup detected in last ${EXPECT_DAYS} days (check protondrive_backup.sh)"
    fi
else
    PROTON_STATUS="Backup directory not found"
    log_warn "Proton Drive backup directory not found"
fi

# Summary status
STATUS_MSG="Google Drive: $GDRIVE_STATUS | Sync: $SYNC_STATUS"
BACKUP_MSG="Proton Drive Backup: $PROTON_STATUS"

# Notification
if command -v terminal-notifier >/dev/null 2>&1; then
    if [[ "$GDRIVE_STATUS" != "Running" ]] || [[ "$SYNC_STATUS" == *"No recent activity"* ]] || [[ "$SYNC_STATUS" == *"errors"* ]]; then
        # Issues detected - provide actionable notification
        terminal-notifier -title "Google Drive Monitor" \
          -subtitle "Issues detected" \
          -message "$STATUS_MSG\n$BACKUP_MSG\nClick for details" \
          -group "maintenance" \
          -execute "$HOME/Library/Maintenance/bin/view_logs.sh google_drive_monitor" 2>/dev/null || true
        log_warn "Google Drive monitoring detected potential issues"
    else
        # Normal operation - simple notification
        terminal-notifier -title "Google Drive Monitor" \
          -subtitle "Working normally" \
          -message "$STATUS_MSG\n$BACKUP_MSG" \
          -group "maintenance" 2>/dev/null || true
        log_info "Google Drive appears to be working normally"
    fi
elif command -v osascript >/dev/null 2>&1; then
    # Fallback to osascript
    if [[ "$GDRIVE_STATUS" != "Running" ]] || [[ "$SYNC_STATUS" == *"No recent activity"* ]] || [[ "$SYNC_STATUS" == *"errors"* ]]; then
        osascript -e "display notification \"$STATUS_MSG\n$BACKUP_MSG\" with title \"Google Drive Monitor - Issues Detected\"" 2>/dev/null || true
        log_warn "Google Drive monitoring detected potential issues"
    else
        log_info "Google Drive appears to be working normally"
    fi
fi

log_info "Google Drive monitoring complete: $STATUS_MSG"
log_info "Backup status: $BACKUP_MSG"
echo "Google Drive monitoring completed successfully!"
