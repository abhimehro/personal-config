#!/usr/bin/env bash

# Self-contained system cleanup script - DAILY VERSION
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

# Basic logging
log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [system_cleanup] $*" | tee -a "$LOG_DIR/system_cleanup.log"
}

log_warn() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [WARNING] [system_cleanup] $*" | tee -a "$LOG_DIR/system_cleanup.log"
}

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE" 2>/dev/null || true
fi

# Get disk usage percentage
percent_used() {
    local path="${1:-/}"
    df -P "$path" | awk 'NR==2 {print $5}' | tr -d '%'
}

log_info "System cleanup started"

DISK_BEFORE=$(percent_used "/")
log_info "Disk usage before cleanup: ${DISK_BEFORE}%"

CLEANED_ITEMS=0

# 1) Prune user caches older than CLEANUP_CACHE_DAYS
CACHE_DIR="${HOME}/Library/Caches"
if [[ -d "${CACHE_DIR}" ]]; then
    log_info "Pruning caches older than ${CLEANUP_CACHE_DAYS:-30} days in ${CACHE_DIR}"
    
    # Clean cache files (excluding critical system caches)
    for cache_subdir in "${CACHE_DIR}"/*; do
        if [[ -d "$cache_subdir" ]]; then
            case "$(basename "$cache_subdir")" in
                # Skip critical system caches
                com.apple.*|CloudKit|CrashReporter|SkyLight) continue ;;
                *)
                    FILES_CLEANED=$(find "$cache_subdir" -type f -mtime +${CLEANUP_CACHE_DAYS:-30} -print -delete 2>/dev/null | wc -l | tr -d ' ')
                    if [[ $FILES_CLEANED -gt 0 ]]; then
                        log_info "Cleaned $FILES_CLEANED cache files from $(basename "$cache_subdir")"
                        CLEANED_ITEMS=$((CLEANED_ITEMS + FILES_CLEANED))
                    fi
                    ;;
            esac
        fi
    done
    
    # Remove empty directories
    find "${CACHE_DIR}" -type d -empty -delete 2>/dev/null || true
fi

# 2) Clean TMPDIR and /tmp files older than TMP_CLEAN_DAYS
for TDIR in "${TMPDIR:-/tmp}" "/tmp"; do
    if [[ -d "$TDIR" ]]; then
        log_info "Cleaning temporary files older than ${TMP_CLEAN_DAYS:-7} days in $TDIR"
        TEMP_FILES_CLEANED=$(find "$TDIR" -type f -mtime +${TMP_CLEAN_DAYS:-7} -user "${USER}" -print -delete 2>/dev/null | wc -l | tr -d ' ')
        if [[ $TEMP_FILES_CLEANED -gt 0 ]]; then
            log_info "Cleaned $TEMP_FILES_CLEANED temporary files from $TDIR"
            CLEANED_ITEMS=$((CLEANED_ITEMS + TEMP_FILES_CLEANED))
        fi
    fi
done

# 3) Xcode DerivedData cleanup (if present)
DDIR="${HOME}/Library/Developer/Xcode/DerivedData"
if [[ -d "${DDIR}" ]]; then
    log_info "Pruning Xcode DerivedData older than ${XCODE_DERIVEDDATA_KEEP_DAYS:-30} days"
    # Note: -delete implies -depth, but for directories we often need rm -rf if they are not empty.
    # standard find -delete works on directories only if they are empty.
    # So we keep the double find here for safety with rm -rf, or we can use -exec rm -rf {} +
    # Let's keep it safe for directories unless we are sure they are empty.
    # Actually, we can just list them and then xargs rm -rf.
    # But let's stick to the double find for directories requiring recursive delete to avoid complexity and risks,
    # focusing optimization on file deletion which is high volume.
    XCODE_CLEANED=$(find "${DDIR}" -mindepth 1 -maxdepth 1 -mtime +${XCODE_DERIVEDDATA_KEEP_DAYS:-30} -print 2>/dev/null | wc -l | tr -d ' ')
    if [[ $XCODE_CLEANED -gt 0 ]]; then
        find "${DDIR}" -mindepth 1 -maxdepth 1 -mtime +${XCODE_DERIVEDDATA_KEEP_DAYS:-30} -print0 2>/dev/null | xargs -0 rm -rf 2>/dev/null || true
        log_info "Cleaned $XCODE_CLEANED Xcode DerivedData directories"
        CLEANED_ITEMS=$((CLEANED_ITEMS + XCODE_CLEANED))
    fi
fi

# 4) iOS Simulator cleanup (if present)
IOS_SIM_DIR="${HOME}/Library/Developer/CoreSimulator/Caches/dyld"
if [[ -d "${IOS_SIM_DIR}" ]]; then
    log_info "Cleaning iOS Simulator caches"
    IOS_FILES_CLEANED=$(find "${IOS_SIM_DIR}" -type f -mtime +7 -print -delete 2>/dev/null | wc -l | tr -d ' ')
    if [[ $IOS_FILES_CLEANED -gt 0 ]]; then
        log_info "Cleaned $IOS_FILES_CLEANED iOS Simulator cache files"
        CLEANED_ITEMS=$((CLEANED_ITEMS + IOS_FILES_CLEANED))
    fi
fi

# 5) Homebrew cleanup
if command -v brew >/dev/null 2>&1; then
    log_info "Running Homebrew cleanup"
    if brew cleanup --prune=${BREW_CLEAN_PRUNE_DAYS:-30} 2>&1 | tee -a "$LOG_DIR/system_cleanup.log"; then
        log_info "Homebrew cleanup completed successfully"
        CLEANED_ITEMS=$((CLEANED_ITEMS + 1))
    fi
    
    if brew autoremove 2>&1 | tee -a "$LOG_DIR/system_cleanup.log"; then
        log_info "Homebrew autoremove completed successfully"
    fi
fi

# 6) Language/tool caches (safe cleanup)
if command -v npm >/dev/null 2>&1; then
    log_info "Verifying npm cache"
    if npm cache verify 2>&1 | tee -a "$LOG_DIR/system_cleanup.log"; then
        log_info "npm cache verified successfully"
    fi
fi

if command -v pip3 >/dev/null 2>&1; then
    log_info "Purging pip cache"
    if pip3 cache purge 2>&1 | tee -a "$LOG_DIR/system_cleanup.log"; then
        log_info "pip cache purged successfully"
        CLEANED_ITEMS=$((CLEANED_ITEMS + 1))
    fi
fi

if command -v gem >/dev/null 2>&1; then
    log_info "Cleaning gem cache"
    if gem cleanup 2>&1 | tee -a "$LOG_DIR/system_cleanup.log"; then
        log_info "gem cleanup completed successfully"
        CLEANED_ITEMS=$((CLEANED_ITEMS + 1))
    fi
fi

# 7) macOS system cleanup
log_info "Cleaning system logs and temporary files"

# Clean user logs older than 30 days
USER_LOGS_DIR="${HOME}/Library/Logs"
if [[ -d "${USER_LOGS_DIR}" ]]; then
    LOG_FILES_CLEANED=$(find "${USER_LOGS_DIR}" -name "*.log" -mtime +30 -print -delete 2>/dev/null | wc -l | tr -d ' ')
    if [[ $LOG_FILES_CLEANED -gt 0 ]]; then
        log_info "Cleaned $LOG_FILES_CLEANED old log files"
        CLEANED_ITEMS=$((CLEANED_ITEMS + LOG_FILES_CLEANED))
    fi
fi

# Clean downloads folder of files older than 90 days (be conservative)
DOWNLOADS_DIR="${HOME}/Downloads"
if [[ -d "${DOWNLOADS_DIR}" ]]; then
    log_info "Cleaning old downloads (90+ days)"
    OLD_DOWNLOADS=$(find "${DOWNLOADS_DIR}" -type f -mtime +90 -print -delete 2>/dev/null | wc -l | tr -d ' ')
    if [[ $OLD_DOWNLOADS -gt 0 ]]; then
        log_info "Cleaned $OLD_DOWNLOADS old download files"
        CLEANED_ITEMS=$((CLEANED_ITEMS + OLD_DOWNLOADS))
    fi
fi

# 8) Browser cache cleanup (optional - only very old caches)
for browser_cache in \
    "${HOME}/Library/Caches/com.google.Chrome" \
    "${HOME}/Library/Caches/com.apple.Safari" \
    "${HOME}/Library/Caches/org.mozilla.firefox"; do
    
    if [[ -d "$browser_cache" ]]; then
        BROWSER_NAME=$(basename "$browser_cache" | sed 's/com\..*\.//')
        log_info "Cleaning old browser cache: $BROWSER_NAME"
        BROWSER_FILES_CLEANED=$(find "$browser_cache" -type f -mtime +14 -print -delete 2>/dev/null | wc -l | tr -d ' ')
        if [[ $BROWSER_FILES_CLEANED -gt 0 ]]; then
            log_info "Cleaned $BROWSER_FILES_CLEANED cache files from $BROWSER_NAME"
            CLEANED_ITEMS=$((CLEANED_ITEMS + BROWSER_FILES_CLEANED))
        fi
    fi
done

# 9) Clean old maintenance logs
MAINT_LOGS_CLEANED=$(find "$LOG_DIR" -type f -name "*.log" -mtime +${LOG_RETENTION_DAYS:-60} -print -delete 2>/dev/null | wc -l | tr -d ' ')
if [[ $MAINT_LOGS_CLEANED -gt 0 ]]; then
    log_info "Cleaned $MAINT_LOGS_CLEANED old maintenance logs"
    CLEANED_ITEMS=$((CLEANED_ITEMS + MAINT_LOGS_CLEANED))
fi

# 10) Report disk space after cleanup
DISK_AFTER=$(percent_used "/")
DISK_SAVED=$((DISK_BEFORE - DISK_AFTER))
log_info "Disk usage after cleanup: ${DISK_AFTER}% (saved: ${DISK_SAVED}%)"

# Final status
STATUS_MSG="Cleaned ${CLEANED_ITEMS} items, saved ${DISK_SAVED}% disk space"

# Notification
if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"${STATUS_MSG}\" with title \"System Cleanup\"" 2>/dev/null || true
fi

log_info "System cleanup complete: ${STATUS_MSG}"
echo "System cleanup completed successfully!"