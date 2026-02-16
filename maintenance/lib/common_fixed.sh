#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

# =============================================================================
# ENHANCED MAINTENANCE COMMON LIBRARY
# macOS Sequoia + Apple Silicon Compatible - FIXED VERSION
# =============================================================================

# Architecture and OS detection
ARCH="$(uname -m)"
OS_VER="$(sw_vers -productVersion)"

# Robust PATH for Apple Silicon and Intel Macs - FIXED
# Clean up PATH construction to avoid quote issues
BASE_PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
if [[ -n "${PATH:-}" ]]; then
    # Extract only clean path elements
    CLEAN_PATH=$(echo "$PATH" | tr ':' '\n' | grep -E '^/[^"]*$' | sort -u | paste -sd: -)
    export PATH="${BASE_PATH}:${CLEAN_PATH}"
else
    export PATH="${BASE_PATH}"
fi

# Repository-aware paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MNT_ROOT="$REPO_ROOT/maintenance"

# Logging and locks
LOG_DIR="${LOG_DIR:-$HOME/Library/Logs/maintenance}"
mkdir -p "$LOG_DIR"

# Legacy config support
CONFIG_DIR="${HOME}/.config/maintenance"
CONFIG_FILE="${CONFIG_DIR}/config.env"
[[ -f "$CONFIG_FILE" ]] && source "$CONFIG_FILE"

# Load environment configuration
load_env() {
    local env="$MNT_ROOT/conf/config.env"
    if [[ -f "$env" ]]; then
        set -a
        # shellcheck source=/dev/null
        . "$env"
        set +a
    fi
}

# Early env load
load_env

# =============================================================================
# MODERN TOOLING WRAPPERS
# Provides graceful fallbacks for ripgrep (rg), fd, and bat
# =============================================================================

# ripgrep (rg) -> grep
# Usage: smart_grep [options] pattern [path]
smart_grep() {
    if command -v rg >/dev/null 2>&1; then
        rg "$@"
    else
        # Basic grep fallback (most common flags handled by grep)
        grep "$@"
    fi
}

# fd -> find
# Usage: smart_find [pattern]
smart_find() {
    if command -v fd >/dev/null 2>&1; then
        fd "$@"
    else
        # find fallback (basic name search)
        find . -name "$@"
    fi
}

# bat -> cat
# Usage: smart_cat [file]
smart_cat() {
    if command -v bat >/dev/null 2>&1; then
        bat --style=plain --paging=never "$@"
    else
        cat "$@"
    fi
}

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

log() {
    local level="${1:-INFO}"
    shift
    local ts
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    local script_name
    script_name="$(basename "${BASH_SOURCE[2]:-${BASH_SOURCE[1]:-common}}" .sh)"
    local line="$ts [$level] [$script_name] $*"
    
    echo "$line" | tee -a "$LOG_DIR/${script_name}.log"
    
    # Optional cloud logging
    if [[ "${GCLOUD_LOGGING:-0}" == "1" ]] && command -v gcloud >/dev/null 2>&1; then
        gcloud logging write "${GCLOUD_LOG_NAME:-maintenance}" "$line" \
            --severity="$level" --quiet 2>/dev/null || true
    fi
}

log_debug() { [[ "${DEBUG:-0}" == "1" ]] && log "DEBUG" "$@"; }
log_info()  { log "INFO" "$@"; }
log_warn()  { log "WARNING" "$@"; }
log_error() { log "ERROR" "$@"; }

# =============================================================================
# UTILITY FUNCTIONS  
# =============================================================================

# Check for required commands
require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_error "Missing required command: $cmd"
        return 1
    fi
}

# Simple atomic locking using mkdir (macOS compatible)
with_lock() {
    local name="${1:-$(basename "${BASH_SOURCE[1]}" .sh)}"
    local lock_dir="$MNT_ROOT/tmp/${name}.lock"
    
    # Try to create lock directory atomically
    if mkdir "$lock_dir" 2>/dev/null; then
        # Ensure cleanup on exit
        trap "rm -rf '$lock_dir' 2>/dev/null || true" EXIT INT TERM
        log_debug "Lock acquired: $lock_dir"
    else
        log_warn "Another instance is running (lock: $lock_dir); exiting."
        exit 0
    fi
}

# Retry function with exponential backoff
retry() {
    local max_attempts="${1:-3}"
    local delay="${2:-5}"
    shift 2
    local cmd=("${@}")
    local attempt=1
    
    until "${cmd[@]}"; do
        local rc=$?
        if [[ $attempt -ge $max_attempts ]]; then
            log_error "Command failed after $max_attempts attempts: ${cmd[*]} (exit code: $rc)"
            return $rc
        fi
        
        log_warn "Attempt $attempt/$max_attempts failed (exit code: $rc); retrying in ${delay}s: ${cmd[*]}"
        sleep "$delay"
        ((attempt++))
        delay=$((delay * 2))  # Exponential backoff
    done
}

# Notifications
notify() {
    local title="${1:-Maintenance}"
    local message="${2:-Completed}"
    local mode="${NOTIFY_MODE:-auto}"
    
    [[ "$mode" == "none" ]] && return 0
    
    # Slack webhook if configured
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        (
            curl -s -X POST -H 'Content-type: application/json' \
                --data "$(printf '{"text":"%s: %s"}' "$title" "$message")" \
                "$SLACK_WEBHOOK_URL" >/dev/null
        ) || true
    fi
    
    # macOS notification
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"$message\" with title \"$title\"" 2>/dev/null || true
    fi
}

# =============================================================================
# SYSTEM UTILITIES
# =============================================================================

# Get disk usage percentage
percent_used() {
    local path="${1:-/}"
    df -P "$path" | awk 'NR==2 {print $5}' | tr -d '%'
}

# Check if auto-remediation is enabled
should_auto_remediate() {
    [[ "${HEALTHCHECK_AUTO_REMEDIATE:-0}" == "1" ]]
}

# Prune old log files
prune_logs() {
    local days="${LOG_RETENTION_DAYS:-60}"
    if [[ -d "$LOG_DIR" ]]; then
        find "$LOG_DIR" -type f -name "*.log" -mtime +$days -delete 2>/dev/null || true
        
        # Simple log rotation for large files
        find "$LOG_DIR" -type f -name "*.log" -size +10M -print0 2>/dev/null | while IFS= read -r -d '' log_file; do
            local base
            base="$(basename "$log_file" .log)"
            mv "$log_file" "$LOG_DIR/${base}-$(date +%Y%m%d).log" || true
            touch "$log_file" || true
        done
    fi
}

# Clean exit handler
cleanup_and_exit() {
    local exit_code="${1:-0}"
    prune_logs
    exit "$exit_code"
}

# Get script basename helper
script_basename() { 
    basename "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}" .sh
}

# Legacy compatibility - keep old function names
log_file_init() {
    local base="${1:-$(script_basename)}"
    LOG_FILE="$LOG_DIR/${base}-$(date +%Y%m%d).log"
    touch "$LOG_FILE" || true
}

acquire_lock() {
    with_lock "$@"
}

with_retry() {
    local attempts="$1"; shift
    local delay="$1"; shift
    retry "$attempts" "$delay" "$@"
}

# =============================================================================
# BACKUP INTEGRATION HOOK
# =============================================================================

after_success() {
    local hook="$REPO_ROOT/.cursor/scripts/backup-configs.sh"
    if [[ -x "$hook" ]]; then
        "$hook" --reason "$(basename "$0")" 2>/dev/null || true
    fi
}

# =============================================================================
# INITIALIZATION
# =============================================================================

# Ensure required directories exist
mkdir -p "$LOG_DIR" "$MNT_ROOT/tmp"

# Log startup info
log_debug "Common library loaded - Arch: $ARCH, macOS: $OS_VER, Repo: $REPO_ROOT"
