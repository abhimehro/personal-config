#!/bin/bash
#
# Common Utility Library
# Cross-platform helpers for shell scripts (filesystem, process management, etc.)
#
# Usage: source "scripts/lib/common.sh"

# Source Guard
if [[ "${_COMMON_SH_:-}" == "true" ]]; then
    return
fi
_COMMON_SH_="true"

# --- Cross-platform temporary file/directory creation ---

# Create a temporary file in TMPDIR (or /tmp as fallback)
make_temp_file() {
    local template="${1:-script_temp.XXXXXX}"
    mktemp "${TMPDIR:-/tmp}/${template}"
}

# Create a temporary directory in TMPDIR (or /tmp as fallback)
make_temp_dir() {
    local template="${1:-script_temp.XXXXXX}"
    mktemp -d "${TMPDIR:-/tmp}/${template}"
}

# --- Symlink-safe filesystem checks ---

# Return 0 if the path is a regular file (not a symlink or special file)
is_regular_file() {
    local file="$1"
    [[ -f "$file" && ! -L "$file" ]]
}

# Return 0 if the path is a real directory (not a symlink)
is_real_dir() {
    local dir="$1"
    [[ -d "$dir" && ! -L "$dir" ]]
}

# --- Process management ---

# Wait for a process to stop, polling every 0.1s up to max_retries * 0.1s
# Usage: wait_for_process_stop <process_name> [max_retries]
wait_for_process_stop() {
    local process_name="$1"
    local max_retries="${2:-20}"
    local retry=0
    while pgrep -x "$process_name" >/dev/null 2>&1 && [[ $retry -lt $max_retries ]]; do
        sleep 0.1
        retry=$((retry + 1))
    done
}
