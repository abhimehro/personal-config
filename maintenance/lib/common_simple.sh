#!/usr/bin/env bash
# Simplified and robust common.sh library for maintenance scripts

# Use less strict error handling to avoid exit on minor issues
set -eo pipefail

# Architecture and OS detection
ARCH="$(uname -m)"
OS_VER="$(sw_vers -productVersion)"

# Simple PATH setup for Apple Silicon
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Repository-aware paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MNT_ROOT="$REPO_ROOT/maintenance"

# Logging setup
LOG_DIR="${LOG_DIR:-$HOME/Library/Logs/maintenance}"
mkdir -p "$LOG_DIR" "$MNT_ROOT/tmp"

# Load config if it exists
CONFIG_FILE="$MNT_ROOT/conf/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    set -a
    source "$CONFIG_FILE" 2>/dev/null || true
    set +a
fi

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

log() {
    local level="${1:-INFO}"
    shift
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    local script_name="$(basename "${BASH_SOURCE[2]:-${BASH_SOURCE[1]:-common}}" .sh)"
    local line="$ts [$level] [$script_name] $*"
    
    echo "$line" | tee -a "$LOG_DIR/${script_name}.log" 2>/dev/null || echo "$line"
}

log_debug() { [[ "${DEBUG:-0}" == "1" ]] && log "DEBUG" "$@"; }
log_info()  { log "INFO" "$@"; }
log_warn()  { log "WARNING" "$@"; }
log_error() { log "ERROR" "$@"; }

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Simple locking using mkdir
with_lock() {
    local name="${1:-$(basename "${BASH_SOURCE[1]}" .sh)}"
    local lock_dir="$MNT_ROOT/tmp/${name}.lock"
    
    if mkdir "$lock_dir" 2>/dev/null; then
        trap "rm -rf '$lock_dir' 2>/dev/null || true" EXIT INT TERM
        log_debug "Lock acquired: $lock_dir"
    else
        log_warn "Another instance is running (lock: $lock_dir); exiting."
        exit 0
    fi
}

# Get disk usage percentage
percent_used() {
    local path="${1:-/}"
    df -P "$path" | awk 'NR==2 {print $5}' | tr -d '%'
}

# Check if auto-remediation is enabled
should_auto_remediate() {
    [[ "${HEALTHCHECK_AUTO_REMEDIATE:-0}" == "1" ]]
}

# Simple notification
notify() {
    local title="${1:-Maintenance}"
    local message="${2:-Completed}"
    
    # macOS notification
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"$message\" with title \"$title\"" 2>/dev/null || true
    fi
}

# Prune old log files
prune_logs() {
    local days="${LOG_RETENTION_DAYS:-60}"
    if [[ -d "$LOG_DIR" ]]; then
        find "$LOG_DIR" -type f -name "*.log" -mtime +$days -delete 2>/dev/null || true
    fi
}

# Retry function
retry() {
    local cmd="$1"
    local max_attempts="${2:-3}"
    local delay="${3:-5}"
    local attempt=1
    
    until eval "$cmd"; do
        local rc=$?
        if [[ $attempt -ge $max_attempts ]]; then
            log_error "Command failed after $max_attempts attempts: $cmd"
            return $rc
        fi
        
        log_warn "Attempt $attempt/$max_attempts failed; retrying in ${delay}s"
        sleep "$delay"
        ((attempt++))
    done
}

# Legacy compatibility
require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_error "Missing required command: $cmd"
        return 1
    fi
}

script_basename() { 
    basename "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}" .sh
}

acquire_lock() { with_lock "$@"; }

# Log successful load
log_debug "Common library loaded - Arch: $ARCH, macOS: $OS_VER"