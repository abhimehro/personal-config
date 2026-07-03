#!/usr/bin/env bash
#
# Shared Logging and Error Handling Library
# 
# This library provides consistent logging, error handling, and utility functions
# for all shell scripts in the personal-config repository.
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/../scripts/lib/logging.sh"
#
# Features:
#   - Color-coded logging (INFO, OK, WARN, ERROR)
#   - Standard error handling with line numbers
#   - Signal trapping for graceful exits
#   - Common utility functions
#   - Configuration validation
#

set -Eeuo pipefail

# =============================================================================
# GLOBAL CONFIGURATION
# =============================================================================

# Enable strict mode for all scripts that source this library
# set -Eeuo pipefail is already set above, but we can re-enforce it

# =============================================================================
# COLOR DEFINITIONS
# =============================================================================

# Check if colors are supported (not running in CI or piped)
if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
    # Colors are supported
    readonly BOLD='\033[1m'
    readonly DIM='\033[2m'
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly BLUE='\033[0;34m'
    readonly MAGENTA='\033[0;35m'
    readonly CYAN='\033[0;36m'
    readonly WHITE='\033[1;37m'
    readonly NC='\033[0m' # No Color
else
    # No colors
    readonly BOLD=''
    readonly DIM=''
    readonly RED=''
    readonly GREEN=''
    readonly YELLOW=''
    readonly BLUE=''
    readonly MAGENTA=''
    readonly CYAN=''
    readonly WHITE=''
    readonly NC=''
fi

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

# Log an informational message
# Usage: log_info "message"
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

# Log a success message
# Usage: log_ok "message"
log_ok() {
    echo -e "${GREEN}[OK]${NC} $*"
}

# Log a warning message
# Usage: log_warn "message"
log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

# Log an error message
# Usage: log_err "message"
log_err() {
    echo -e "${RED}[ERR]${NC} $*" >&2
}

# Log a debug message (only if DEBUG is set)
# Usage: log_debug "message"
log_debug() {
    if [[ -n "${DEBUG:-}" ]]; then
        echo -e "${CYAN}[DEBUG]${NC} $*"
    fi
}

# Log a header/section title
# Usage: log_header "Section Title"
log_header() {
    echo -e "\n${BOLD}${BLUE}=== $* ===${NC}"
}

# Log a horizontal rule
# Usage: log_hr
log_hr() {
    echo -e "${BLUE}────────────────────────────────────────────────────────────────${NC}"
}

# =============================================================================
# ERROR HANDLING
# =============================================================================

# Global error handler - called on any error
# This provides consistent error messages with line numbers
handle_error() {
    local exit_code
    exit_code=$1
    local line_number
    line_number=$2
    local command
    command=$3
    
    log_err "Error at line ${line_number}: ${command}"
    log_err "Exit code: ${exit_code}"
    
    # Print stack trace if available
    if [[ -n "${BASH_COMMAND:-}" ]]; then
        log_debug "Failed command: ${BASH_COMMAND}"
    fi
    
    exit ${exit_code}
}

# Global cleanup handler - called on script exit
handle_cleanup() {
    local exit_code
    exit_code=$1
    
    # Add any cleanup logic here
    # For example: remove temp files, stop services, etc.
    
    if [[ ${exit_code} -ne 0 ]]; then
        log_err "Script exited with errors (code: ${exit_code})"
    fi
    
    exit ${exit_code}
}

# Setup error trapping
setup_error_handling() {
    # Trap errors and provide line numbers
    trap 'handle_error $? $LINENO "$BASH_COMMAND"' ERR
    
    # Trap exit for cleanup
    trap 'handle_cleanup $?' EXIT
    
    # Trap interrupts (Ctrl+C)
    trap 'log_warn "Interrupted by user (Ctrl+C)"; exit 130' SIGINT
    
    # Trap termination signals
    trap 'log_warn "Terminated by signal"; exit 143' SIGTERM
}

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

# Check if a command exists
# Usage: require_cmd "command_name" ["install_hint"]
# Returns: 0 if command exists, 1 otherwise
require_cmd() {
    local cmd
    cmd="$1"
    local install_hint
    install_hint="${2:-}"
    
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_err "Required command not found: ${cmd}"
        if [[ -n "$install_hint" ]]; then
            log_info "Installation hint: $install_hint"
        fi
        return 1
    fi
    
    log_debug "Found command: ${cmd}"
    return 0
}

# Check if a file exists and is readable
# Usage: require_file "path/to/file" ["description"]
# Returns: 0 if file exists and is readable, 1 otherwise
require_file() {
    local file_path
    file_path="$1"
    local description
    description="${2:-file}"
    
    if [[ ! -f "$file_path" ]]; then
        log_err "Required ${description} not found: ${file_path}"
        return 1
    fi
    
    if [[ ! -r "$file_path" ]]; then
        log_err "Cannot read ${description}: ${file_path}"
        return 1
    fi
    
    log_debug "Found ${description}: ${file_path}"
    return 0
}

# Check if a directory exists
# Usage: require_dir "path/to/dir" ["description"]
# Returns: 0 if directory exists, 1 otherwise
require_dir() {
    local dir_path
    dir_path="$1"
    local description
    description="${2:-directory}"
    
    if [[ ! -d "$dir_path" ]]; then
        log_err "Required ${description} not found: ${dir_path}"
        return 1
    fi
    
    log_debug "Found ${description}: ${dir_path}"
    return 0
}

# Validate that a variable is set and not empty
# Usage: require_var "VAR_NAME" ["description"]
# Returns: 0 if variable is set and not empty, 1 otherwise
require_var() {
    local var_name
    var_name="$1"
    local description
    description="${2:-variable}"
    local var_value
    var_value="${!var_name:-}"
    
    if [[ -z "$var_value" ]]; then
        log_err "Required ${description} is not set: ${var_name}"
        return 1
    fi
    
    log_debug "${description} is set: ${var_name}"
    return 0
}

# Check if running on macOS
# Usage: ensure_macos ["message"]
# Returns: 0 if on macOS, 1 otherwise
ensure_macos() {
    local message
    message="${1:-This script requires macOS}"
    
    if [[ "$(uname -s)" != "Darwin" ]]; then
        log_err "${message}"
        return 1
    fi
    
    log_debug "Running on macOS $(sw_vers -productVersion)"
    return 0
}

# Check if running as root
# Usage: ensure_not_root ["message"]
# Returns: 0 if not root, 1 if root
ensure_not_root() {
    local message
    message="${1:-This script should not be run as root}"
    
    if [[ $EUID -eq 0 ]]; then
        log_err "${message}"
        return 1
    fi
    
    log_debug "Running as non-root user: $(whoami)"
    return 0
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Print a formatted list
# Usage: print_list "item1" "item2" "item3"
print_list() {
    for item in "$@"; do
        echo "  - ${item}"
    done
}

# Print a key-value pair
# Usage: print_kv "Key" "Value"
print_kv() {
    printf "  %-20s %s\n" "$1:" "$2"
}

# Check if a string is in a list
# Usage: string_in_list "needle" "haystack1" "haystack2" "haystack3"
# Returns: 0 if needle is in list, 1 otherwise
string_in_list() {
    local needle
    needle="$1"
    shift
    
    for item in "$@"; do
        if [[ "$item" == "$needle" ]]; then
            return 0
        fi
    done
    
    return 1
}

# Join array elements with a delimiter
# Usage: join_array "delimiter" "${array[@]}"
join_array() {
    local delimiter
    delimiter="$1"
    shift
    
    local first
    
    first=true
    local result
    result=""
    
    for item in "$@"; do
        if [[ "$first" == true ]]; then
            result="$item"
            first=false
        else
            result="${result}${delimiter}${item}"
        fi
    done
    
    echo "$result"
}

# Get the absolute path of a file or directory
# Usage: get_abs_path "path/to/file"
get_abs_path() {
    local path
    path="$1"
    
    if [[ -d "$path" ]]; then
        (cd "$path" && pwd)
    else
        echo "$(cd "$(dirname "$path")" && pwd)/$(basename "$path")"
    fi
}

# Get the directory of the current script
# Usage: get_script_dir
get_script_dir() {
    echo "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
}

# Get the root directory of the repository
# Usage: get_repo_root
get_repo_root() {
    local script_dir
    script_dir=$(get_script_dir)
    
    # Navigate up to find the repository root
    while [[ ! -f "$script_dir/setup.sh" ]] && [[ "$script_dir" != "/" ]]; do
        script_dir=$(dirname "$script_dir")
    done
    
    if [[ "$script_dir" == "/" ]]; then
        log_err "Could not find repository root"
        exit 1
    fi
    
    echo "$script_dir"
}

# =============================================================================
# TIME UTILITY FUNCTIONS
# =============================================================================

# Get current timestamp
# Usage: get_timestamp
get_timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

# Get current timestamp in ISO format
# Usage: get_timestamp_iso
get_timestamp_iso() {
    date +"%Y-%m-%dT%H:%M:%S%z"
}

# Measure execution time of a command
# Usage: time_command "description" "command" [args...]
# Example: time_command "Running tests" make test
time_command() {
    local description
    description="$1"
    shift
    
    local start_time
    start_time=$(date +%s.%N)
    
    log_info "Starting: ${description}"
    
    # Execute the command
    "$@"
    local exit_code
    exit_code=$?
    
    local end_time
    end_time=$(date +%s.%N)
    
    local elapsed
    elapsed=$(echo "$end_time - $start_time" | bc)
    
    if [[ ${exit_code} -eq 0 ]]; then
        log_ok "Completed: ${description} (${elapsed}s)"
    else
        log_err "Failed: ${description} (${elapsed}s)"
    fi
    
    return ${exit_code}
}

# =============================================================================
# FILE SYSTEM UTILITY FUNCTIONS
# =============================================================================

# Create a directory if it doesn't exist
# Usage: ensure_dir "path/to/dir"
ensure_dir() {
    local dir_path
    dir_path="$1"
    
    if [[ ! -d "$dir_path" ]]; then
        mkdir -p "$dir_path"
        log_debug "Created directory: ${dir_path}"
    fi
}

# Create a backup of a file
# Usage: backup_file "path/to/file"
# Returns: path to backup file
backup_file() {
    local file_path
    file_path="$1"
    local backup_path
    backup_path="${file_path}.bak.$(get_timestamp | tr ' :' '_')"
    
    if [[ -f "$file_path" ]]; then
        cp "$file_path" "$backup_path"
        log_info "Backed up ${file_path} to ${backup_path}"
    fi
    
    echo "$backup_path"
}

# Check if a file has changed
# Usage: file_changed "path/to/file" "md5_sum"
# Returns: 0 if file has changed, 1 otherwise
file_changed() {
    local file_path
    file_path="$1"
    local old_md5
    old_md5="$2"
    
    if [[ ! -f "$file_path" ]]; then
        return 1
    fi
    
    local new_md5
    new_md5=$(md5sum "$file_path" | awk '{print $1}')
    
    if [[ "$new_md5" != "$old_md5" ]]; then
        return 0
    fi
    
    return 1
}

# =============================================================================
# INITIALIZATION
# =============================================================================

# Initialize the library - call this at the start of your script
# Usage: init_script "script_name" ["description"]
init_script() {
    local script_name
    script_name="$1"
    local description
    description="${2:-}"
    
    # Setup error handling
    setup_error_handling
    
    # Log script start
    log_header "${script_name}"
    if [[ -n "$description" ]]; then
        log_info "${description}"
    fi
    
    log_debug "Script started at: $(get_timestamp)"
}

# =============================================================================
# MAIN EXECUTION HELPER
# =============================================================================

# Helper to run main function with error handling
# Usage: 
#   main() {
#       # your code here
#   }
#   run_main "$@"
run_main() {
    init_script "${0##*/}" "$*"
    main "$@"
}

# =============================================================================
# AUTOMATIC INITIALIZATION
# =============================================================================

# If this library is sourced (not executed directly), don't run anything
# This prevents the library from executing when sourced
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    # Library is being sourced, so we're good
    :
else
    # Library is being executed directly
    echo "This file should be sourced, not executed directly."
    echo "Usage: source \"\$(dirname \"\${BASH_SOURCE[0]}\")/logging.sh\""
    exit 1
fi