#!/usr/bin/env bash

# Self-contained quick cleanup script
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

# Basic logging
log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [quick_cleanup] $*" | tee -a "$LOG_DIR/quick_cleanup.log"
}

log_warn() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [WARNING] [quick_cleanup] $*" | tee -a "$LOG_DIR/quick_cleanup.log"
}

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE" 2>/dev/null || true
fi

log_info "Quick cleanup started"

CLEANED=0

# 1) Clear user caches
log_info "Cleaning user caches..."
if [[ -d "$HOME/Library/Caches" ]]; then
    # Clean application caches (but preserve important ones)
    for cache_dir in "$HOME/Library/Caches"/*; do
        if [[ -d "$cache_dir" ]]; then
            # Skip system-critical caches
            case "$(basename "$cache_dir")" in
                com.apple.*|CloudKit|CrashReporter|SkyLight) continue ;;
            esac
            
            # Clean cache if older than configured days
            if find "$cache_dir" -type f -mtime +${CLEANUP_CACHE_DAYS:-30} -print -quit | grep -q .; then
                find "$cache_dir" -type f -mtime +${CLEANUP_CACHE_DAYS:-30} -delete 2>/dev/null || true
                ((CLEANED++))
            fi
        fi
    done
fi

# 2) Clean Downloads folder (old files)
log_info "Cleaning old downloads..."
if [[ -d "$HOME/Downloads" ]]; then
    BEFORE_COUNT=$(find "$HOME/Downloads" -type f | wc -l)
    find "$HOME/Downloads" -type f -mtime +${CLEANUP_CACHE_DAYS:-30} -delete 2>/dev/null || true
    AFTER_COUNT=$(find "$HOME/Downloads" -type f | wc -l)
    if (( BEFORE_COUNT > AFTER_COUNT )); then
        log_info "Cleaned $((BEFORE_COUNT - AFTER_COUNT)) old files from Downloads"
        ((CLEANED++))
    fi
fi

# 3) Clean temporary directories
log_info "Cleaning temporary directories..."
for tmp_dir in "/tmp" "$HOME/.tmp" "/var/tmp"; do
    if [[ -d "$tmp_dir" ]]; then
        find "$tmp_dir" -user "$(whoami)" -type f -mtime +${TMP_CLEAN_DAYS:-7} -delete 2>/dev/null || true
        ((CLEANED++))
    fi
done

# 4) Clean trash if very full
log_info "Checking trash..."
TRASH_SIZE=$(du -sk "$HOME/.Trash" 2>/dev/null | awk '{print $1}' || echo 0)
if (( TRASH_SIZE > 1048576 )); then  # > 1GB
    log_warn "Trash is large ($(( TRASH_SIZE / 1024 )) MB), consider emptying"
fi

# 5) Clean browser caches (safe locations only)
log_info "Cleaning browser caches..."
for browser_cache in \
    "$HOME/Library/Caches/com.google.Chrome/Default/Cache" \
    "$HOME/Library/Caches/org.mozilla.firefox" \
    "$HOME/Library/Caches/com.apple.Safari"; do
    
    if [[ -d "$browser_cache" ]]; then
        find "$browser_cache" -type f -mtime +7 -delete 2>/dev/null || true
        ((CLEANED++))
    fi
done

# 6) System log cleanup (user-accessible only)
log_info "Cleaning old logs..."
if [[ -d "$LOG_DIR" ]]; then
    find "$LOG_DIR" -type f -name "*.log" -mtime +${LOG_RETENTION_DAYS:-60} -delete 2>/dev/null || true
fi

# 7) Quick disk space check
DISK_USE=$(df -P / | awk 'NR==2 {print $5}' | tr -d '%')
log_info "Current disk usage: ${DISK_USE}%"

# 8) Clean up package manager caches
if command -v brew >/dev/null 2>&1; then
    log_info "Cleaning Homebrew cache..."
    brew cleanup --prune=7 2>/dev/null || true
    ((CLEANED++))
fi

if command -v npm >/dev/null 2>&1; then
    log_info "Cleaning npm cache..."
    npm cache clean --force 2>/dev/null || true
    ((CLEANED++))
fi

# Notification
if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"Cleaned ${CLEANED} items | Disk: ${DISK_USE}%\" with title \"Quick Cleanup\"" 2>/dev/null || true
fi

log_info "Quick cleanup completed: ${CLEANED} items cleaned"
echo "Quick cleanup completed successfully!"