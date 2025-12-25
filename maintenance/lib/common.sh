#!/usr/bin/env bash
# Working maintenance common library

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

# Fast timestamp generation
if [[ ${BASH_VERSINFO[0]} -ge 4 ]]; then
    get_timestamp() {
        printf -v "$1" "%(%Y-%m-%d %H:%M:%S)T" -1
    }
else
    get_timestamp() {
        local val
        val="$(date '+%Y-%m-%d %H:%M:%S')"
        eval "$1='$val'"
    }
fi

log() {
    local level="${1:-INFO}"
    shift

    local ts
    get_timestamp ts

    # Avoid basename subshell
    local source="${BASH_SOURCE[2]:-${BASH_SOURCE[1]:-common}}"
    local script_name="${source##*/}"
    script_name="${script_name%.sh}"

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
    local source="${BASH_SOURCE[1]}"
    local name_base="${source##*/}"
    local name="${1:-${name_base%.sh}}"
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

# Legacy compatibility functions
require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_error "Missing required command: $cmd"
        return 1
    fi
}

script_basename() { 
    local source="${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}"
    local name="${source##*/}"
    echo "${name%.sh}"
}

acquire_lock() { with_lock "$@"; }

log_file_init() {
    local base="${1:-$(script_basename)}"
    local ts
    # If we are in bash 4+, use printf, otherwise date
    if [[ ${BASH_VERSINFO[0]} -ge 4 ]]; then
        printf -v ts "%(%Y%m%d)T" -1
    else
        ts="$(date +%Y%m%d)"
    fi
    LOG_FILE="$LOG_DIR/${base}-${ts}.log"
    touch "$LOG_FILE" || true
}

with_retry() {
    local attempts="$1"; shift
    local delay="$1"; shift
    retry "$*" "$attempts" "$delay"
}

after_success() {
    local hook="$REPO_ROOT/.cursor/scripts/backup-configs.sh"
    if [[ -x "$hook" ]]; then
        "$hook" --reason "$(basename "$0")" 2>/dev/null || true
    fi
}

cleanup_and_exit() {
    local exit_code="${1:-0}"
    prune_logs
    exit "$exit_code"
}

# Log successful load
log_debug "Common library loaded - Arch: $ARCH, macOS: $OS_VER"