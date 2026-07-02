#!/usr/bin/env bash
#
# Shared Utility Functions Library
# 
# This library provides common utility functions for file operations,
# string manipulation, and system interactions.
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/../scripts/lib/utils.sh"
#
# Dependencies: logging.sh (should be sourced first)
#

# Ensure logging library is loaded
if ! declare -f log_info >/dev/null 2>&1; then
    # Try to source logging.sh from the same directory
    if [[ -f "$(dirname "${BASH_SOURCE[0]}")/logging.sh" ]]; then
        # shellcheck disable=SC1090
        source "$(dirname "${BASH_SOURCE[0]}")/logging.sh"
    else
        echo "Error: logging.sh not found. Please source logging.sh first." >&2
        return 1
    fi
fi

# =============================================================================
# FILE AND DIRECTORY OPERATIONS
# =============================================================================

# Find files by pattern and return as array
# Usage: find_files "pattern" ["directory"]
# Example: files=($(find_files "*.sh" "scripts/"))
find_files() {
    local pattern
    pattern="$1"
    local directory
    directory="${2:-.}"
    
    find "$directory" -name "$pattern" -type f 2>/dev/null | sort
}

# Find all shell scripts in a directory
# Usage: find_shell_scripts ["directory"]
find_shell_scripts() {
    local directory
    directory="${1:-.}"
    find_files "*.sh" "$directory"
}

# Find all Python files in a directory
# Usage: find_python_files ["directory"]
find_python_files() {
    local directory
    directory="${1:-.}"
    find_files "*.py" "$directory"
}

# Check if a file contains a pattern
# Usage: file_contains "file_path" "pattern"
# Returns: 0 if pattern found, 1 otherwise
file_contains() {
    local file_path
    file_path="$1"
    local pattern
    pattern="$2"
    
    if [[ ! -f "$file_path" ]]; then
        return 1
    fi
    
    if grep -q "$pattern" "$file_path" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# Count lines in a file
# Usage: count_lines "file_path"
count_lines() {
    local file_path
    file_path="$1"
    
    if [[ ! -f "$file_path" ]]; then
        echo 0
        return 1
    fi
    
    wc -l < "$file_path" | tr -d ' '
}

# Get file size in bytes
# Usage: get_file_size "file_path"
get_file_size() {
    local file_path
    file_path="$1"
    
    if [[ ! -f "$file_path" ]]; then
        echo 0
        return 1
    fi
    
    stat -c%s "$file_path" 2>/dev/null || stat -f%z "$file_path" 2>/dev/null || echo 0
}

# Get file extension
# Usage: get_extension "filename"
get_extension() {
    local filename
    filename="$1"
    echo "${filename##*.}"
}

# Get filename without extension
# Usage: get_basename "filename"
get_basename() {
    local filename
    filename="$1"
    echo "${filename%.*}"
}

# =============================================================================
# STRING MANIPULATION
# =============================================================================

# Convert string to lowercase
# Usage: to_lowercase "STRING"
to_lowercase() {
    echo "${1,,}"
}

# Convert string to uppercase
# Usage: to_uppercase "STRING"
to_uppercase() {
    echo "${1^^}"
}

# Trim whitespace from both ends
# Usage: trim "string"
trim() {
    local str
    str="$1"
    echo "${str#"${str%%[![:space:]]*}"}" | awk '{$1=$1};1'
}

# Trim whitespace from left
# Usage: ltrim "string"
ltrim() {
    local str
    str="$1"
    echo "${str#"${str%%[![:space:]]*}"}"
}

# Trim whitespace from right
# Usage: rtrim "string"
rtrim() {
    local str
    str="$1"
    echo "${str%"${str##*[![:space:]]} "}"
}

# Check if string starts with prefix
# Usage: starts_with "string" "prefix"
# Returns: 0 if string starts with prefix, 1 otherwise
starts_with() {
    local string
    string="$1"
    local prefix
    prefix="$2"
    
    [[ "$string" == "$prefix"* ]]
}

# Check if string ends with suffix
# Usage: ends_with "string" "suffix"
# Returns: 0 if string ends with suffix, 1 otherwise
ends_with() {
    local string
    string="$1"
    local suffix
    suffix="$2"
    
    [[ "$string" == *"$suffix" ]]
}

# Check if string contains substring
# Usage: contains "string" "substring"
# Returns: 0 if string contains substring, 1 otherwise
contains() {
    local string
    string="$1"
    local substring
    substring="$2"
    
    [[ "$string" == *"$substring"* ]]
}

# Replace all occurrences of a substring
# Usage: replace_all "string" "old" "new"
replace_all() {
    local string
    string="$1"
    local old
    old="$2"
    local new
    new="$3"
    
    echo "${string//$old/$new}"
}

# Replace first occurrence of a substring
# Usage: replace_first "string" "old" "new"
replace_first() {
    local string
    string="$1"
    local old
    old="$2"
    local new
    new="$3"
    
    echo "${string/$old/$new}"
}

# Split string by delimiter
# Usage: split "string" "delimiter"
# Returns: array of parts
split() {
    local string
    string="$1"
    local delimiter
    delimiter="$2"
    
    IFS="$delimiter" read -ra parts <<< "$string"
    echo "${parts[@]}"
}

# =============================================================================
# ARRAY OPERATIONS
# =============================================================================

# Check if array contains element
# Usage: array_contains "element" "${array[@]}"
# Returns: 0 if element is in array, 1 otherwise
array_contains() {
    local element
    element="$1"
    shift
    
    local item
    for item in "$@"; do
        if [[ "$item" == "$element" ]]; then
            return 0
        fi
    done
    
    return 1
}

# Get array length
# Usage: array_length "${array[@]}"
array_length() {
    echo $#
}

# Join array elements with delimiter
# Usage: array_join "delimiter" "${array[@]}"
array_join() {
    local delimiter
    delimiter="$1"
    shift
    
    local result
    
    result=""
    local first
    first=true
    
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

# =============================================================================
# SYSTEM INFORMATION
# =============================================================================

# Get current user
# Usage: get_current_user
get_current_user() {
    echo "$(whoami)"
}

# Get current hostname
# Usage: get_hostname
get_hostname() {
    hostname
}

# Get OS name
# Usage: get_os
get_os() {
    uname -s
}

# Get OS version
# Usage: get_os_version
get_os_version() {
    uname -r
}

# Check if running in CI environment
# Usage: is_ci
# Returns: 0 if in CI, 1 otherwise
is_ci() {
    [[ -n "${CI:-}" ]] || [[ -n "${GITHUB_ACTIONS:-}" ]] || [[ -n "${GITLAB_CI:-}" ]]
}

# Check if running in Docker container
# Usage: is_docker
# Returns: 0 if in Docker, 1 otherwise
is_docker() {
    [[ -f /.dockerenv ]] || grep -q 'docker' /proc/1/cgroup 2>/dev/null
}

# Get number of CPU cores
# Usage: get_cpu_count
get_cpu_count() {
    if command -v nproc >/dev/null 2>&1; then
        nproc
    elif [[ "$(uname)" == "Darwin" ]]; then
        sysctl -n hw.ncpu
    else
        grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 1
    fi
}

# Get total memory in MB
# Usage: get_total_memory
get_total_memory() {
    if [[ "$(uname)" == "Darwin" ]]; then
        sysctl -n hw.memsize | awk '{print $1/1024/1024}'
    elif command -v free >/dev/null 2>&1; then
        free -m | awk '/^Mem:/ {print $2}'
    else
        echo 0
    fi
}

# =============================================================================
# NETWORK UTILITIES
# =============================================================================

# Check if host is reachable
# Usage: is_reachable "hostname" ["port"] ["timeout"]
is_reachable() {
    local host
    host="$1"
    local port
    port="${2:-80}"
    local timeout
    timeout="${3:-2}"
    
    if command -v nc >/dev/null 2>&1; then
        nc -z -w "$timeout" "$host" "$port" 2>/dev/null
    elif command -v curl >/dev/null 2>&1; then
        curl -s --connect-timeout "$timeout" "http://${host}:${port}" >/dev/null 2>&1
    else
        ping -c 1 -W "$timeout" "$host" >/dev/null 2>&1
    fi
}

# Check if internet is available
# Usage: is_internet_available
# Returns: 0 if internet is available, 1 otherwise
is_internet_available() {
    is_reachable "8.8.8.8" "53" "2"
}

# Get public IP address
# Usage: get_public_ip
get_public_ip() {
    if command -v curl >/dev/null 2>&1; then
        curl -s https://api.ipify.org 2>/dev/null || echo "unknown"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://api.ipify.org 2>/dev/null || echo "unknown"
    else
        echo "unknown"
    fi
}

# =============================================================================
# GIT UTILITIES
# =============================================================================

# Get current branch name
# Usage: get_git_branch
get_git_branch() {
    git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown"
}

# Get current commit hash
# Usage: get_git_commit
get_git_commit() {
    git rev-parse HEAD 2>/dev/null || echo "unknown"
}

# Check if repository is clean
# Usage: is_git_clean
# Returns: 0 if clean, 1 otherwise
is_git_clean() {
    if git status --porcelain 2>/dev/null | grep -q .; then
        return 1
    fi
    return 0
}

# Get git root directory
# Usage: get_git_root
get_git_root() {
    git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)"
}

# Check if current directory is a git repository
# Usage: is_git_repo
# Returns: 0 if git repo, 1 otherwise
is_git_repo() {
    git rev-parse --is-inside-work-tree >/dev/null 2>&1
}

# =============================================================================
# PROCESS MANAGEMENT
# =============================================================================

# Check if a process is running
# Usage: is_process_running "process_name"
# Returns: 0 if running, 1 otherwise
is_process_running() {
    local process_name
    process_name="$1"
    
    if command -v pgrep >/dev/null 2>&1; then
        pgrep -f "$process_name" >/dev/null 2>&1
    elif [[ "$(uname)" == "Darwin" ]]; then
        ps aux | grep -v grep | grep -q "$process_name"
    else
        ps aux | grep -v grep | grep -q "$process_name"
    fi
}

# Get process ID by name
# Usage: get_pid "process_name"
# Returns: PID or empty string
get_pid() {
    local process_name
    process_name="$1"
    
    if command -v pgrep >/dev/null 2>&1; then
        pgrep -f "$process_name" | head -1
    elif [[ "$(uname)" == "Darwin" ]]; then
        ps aux | grep -v grep | grep "$process_name" | awk '{print $2}' | head -1
    else
        ps aux | grep -v grep | grep "$process_name" | awk '{print $2}' | head -1
    fi
}

# Kill process by name
# Usage: kill_process "process_name" ["signal"]
kill_process() {
    local process_name
    process_name="$1"
    local signal
    signal="${2:-TERM}"
    
    local pid
    pid=$(get_pid "$process_name")
    
    if [[ -n "$pid" ]]; then
        kill -"$signal" "$pid" 2>/dev/null
        log_info "Sent ${signal} signal to process ${pid} (${process_name})"
        return 0
    fi
    
    log_warn "Process not found: ${process_name}"
    return 1
}

# =============================================================================
# TIME AND DATE UTILITIES
# =============================================================================

# Get current timestamp in various formats

# ISO 8601 timestamp
# Usage: timestamp_iso
timestamp_iso() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Human-readable timestamp
# Usage: timestamp_human
timestamp_human() {
    date +"%Y-%m-%d %H:%M:%S"
}

# Timestamp for filenames (no spaces or colons)
# Usage: timestamp_filename
timestamp_filename() {
    date +"%Y%m%d_%H%M%S"
}

# Get epoch time
# Usage: timestamp_epoch
timestamp_epoch() {
    date +%s
}

# Convert epoch to human-readable
# Usage: epoch_to_human "epoch"
epoch_to_human() {
    local epoch
    epoch="$1"
    date -d "@$epoch" +"%Y-%m-%d %H:%M:%S" 2>/dev/null || date -r "$epoch" +"%Y-%m-%d %H:%M:%S" 2>/dev/null
}

# =============================================================================
# FILE PERMISSION UTILITIES
# =============================================================================

# Check if file is executable
# Usage: is_executable "file_path"
# Returns: 0 if executable, 1 otherwise
is_executable() {
    local file_path
    file_path="$1"
    [[ -x "$file_path" ]]
}

# Check if file is readable
# Usage: is_readable "file_path"
# Returns: 0 if readable, 1 otherwise
is_readable() {
    local file_path
    file_path="$1"
    [[ -r "$file_path" ]]
}

# Check if file is writable
# Usage: is_writable "file_path"
# Returns: 0 if writable, 1 otherwise
is_writable() {
    local file_path
    file_path="$1"
    [[ -w "$file_path" ]]
}

# Set file permissions
# Usage: set_permissions "file_path" "permissions"
# Example: set_permissions "/path/to/file" "755"
set_permissions() {
    local file_path
    file_path="$1"
    local permissions
    permissions="$2"
    
    if [[ -f "$file_path" ]] || [[ -d "$file_path" ]]; then
        chmod "$permissions" "$file_path"
        log_debug "Set permissions ${permissions} on ${file_path}"
    else
        log_warn "File not found: ${file_path}"
        return 1
    fi
}

# =============================================================================
# SYMLINK MANAGEMENT
# =============================================================================

# Create a symlink with backup
# Usage: create_symlink "source" "target"
# Returns: 0 on success, 1 on failure
create_symlink() {
    local source
    source="$1"
    local target
    target="$2"
    
    # Check if source exists
    if [[ ! -e "$source" ]]; then
        log_err "Source does not exist: ${source}"
        return 1
    fi
    
    # Get absolute paths
    local abs_source
    abs_source=$(get_abs_path "$source")
    local abs_target
    abs_target=$(get_abs_path "$target")
    
    # Check if target already exists
    if [[ -e "$abs_target" ]]; then
        if [[ -L "$abs_target" ]]; then
            # Target is a symlink, check if it points to the same source
            local current_target
            current_target=$(readlink "$abs_target")
            if [[ "$current_target" == "$abs_source" ]]; then
                log_debug "Symlink already exists and is correct: ${abs_target} -> ${abs_source}"
                return 0
            else
                # Backup existing symlink
                local backup
                backup=$(backup_file "$abs_target")
                log_info "Backing up existing symlink: ${abs_target} -> ${backup}"
            fi
        else
            # Target is a regular file or directory, backup it
            local backup
            backup=$(backup_file "$abs_target")
            log_info "Backing up existing file: ${abs_target} -> ${backup}"
        fi
    fi
    
    # Create parent directories if they don't exist
    local target_dir
    target_dir=$(dirname "$abs_target")
    ensure_dir "$target_dir"
    
    # Create the symlink
    ln -sf "$abs_source" "$abs_target"
    log_info "Created symlink: ${abs_target} -> ${abs_source}"
    
    return 0
}

# Verify a symlink
# Usage: verify_symlink "target" "expected_source"
# Returns: 0 if symlink is correct, 1 otherwise
verify_symlink() {
    local target
    target="$1"
    local expected_source
    expected_source="$2"
    
    if [[ ! -L "$target" ]]; then
        log_err "Not a symlink: ${target}"
        return 1
    fi
    
    local actual_source
    actual_source=$(readlink "$target")
    local expected_abs
    expected_abs=$(get_abs_path "$expected_source")
    local actual_abs
    actual_abs=$(get_abs_path "$actual_source")
    
    if [[ "$actual_abs" == "$expected_abs" ]]; then
        log_debug "Symlink verified: ${target} -> ${actual_source}"
        return 0
    else
        log_err "Symlink mismatch: ${target} -> ${actual_source} (expected: ${expected_source})"
        return 1
    fi
}

# =============================================================================
# INITIALIZATION
# =============================================================================

# Ensure the library is properly initialized
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    # Library is being sourced, so we're good
    log_debug "Utils library loaded successfully"
else
    # Library is being executed directly
    echo "This file should be sourced, not executed directly." >&2
    echo "Usage: source \"\$(dirname \"\${BASH_SOURCE[0]}\")/utils.sh\""
    exit 1
fi