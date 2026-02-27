#!/bin/bash
#
# File Common Library
# Secure filesystem helpers: symlink detection, safe directory creation,
# and atomic file writes.
#
# Usage: source "scripts/lib/file-common.sh"

# Source Guard
if [[ "${_FILE_COMMON_SH_:-}" == "true" ]]; then
    return
fi
_FILE_COMMON_SH_="true"

# Source common.sh when available (provides make_temp_file / is_regular_file etc.)
_FILE_COMMON_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$_FILE_COMMON_LIB_DIR/common.sh" ]]; then
    # shellcheck source=scripts/lib/common.sh
    source "$_FILE_COMMON_LIB_DIR/common.sh"
fi
unset _FILE_COMMON_LIB_DIR

# --- Symlink Safety ---

# Return 1 (and print an error) if <path> is a symlink.
# Designed for pre-flight security checks before reading or writing a path.
# Usage: assert_not_symlink <path> [label]
assert_not_symlink() {
    local path="$1"
    local label="${2:-$path}"
    if [[ -L "$path" ]]; then
        echo "Security Alert: $label ($path) is a symlink! Refusing to proceed." >&2
        return 1
    fi
    return 0
}

# Check that none of the supplied paths are symlinks.
# Returns 1 (and prints per-path errors) if any path is a symlink.
# Usage: assert_none_are_symlinks <path1> [path2 ...]
assert_none_are_symlinks() {
    local failed=0
    local path
    for path in "$@"; do
        if [[ -L "$path" ]]; then
            echo "Security Alert: $path is a symlink! Refusing to proceed." >&2
            failed=1
        fi
    done
    return "$failed"
}

# --- Secure Directory Creation ---

# Create <path> as a directory with <mode> permissions (default 755).
# Refuses to proceed if <path> is already a symlink or a non-directory file.
# Uses 'install -d' for atomic creation with the requested permissions.
# Usage: secure_mkdir <path> [mode]
secure_mkdir() {
    local path="$1"
    local mode="${2:-755}"
    # 🛡️ Sentinel: Refuse to proceed if path is a symlink
    if [[ -L "$path" ]]; then
        echo "Security Alert: $path is a symlink! Refusing to create directory." >&2
        return 1
    fi
    # Refuse to overwrite an existing non-directory
    if [[ -e "$path" && ! -d "$path" ]]; then
        echo "Security Alert: $path exists but is not a directory." >&2
        return 1
    fi
    if [[ ! -d "$path" ]]; then
        # 'install -d' creates the directory atomically with the requested mode,
        # avoiding the TOCTOU race between mkdir and chmod.
        install -d -m "$mode" "$path"
    fi
    return 0
}

# --- Atomic File Writes ---

# Write <content> to <dest> atomically via a temp file + rename.
# Prevents partial reads and avoids following an existing symlink at <dest>.
# Usage: atomic_write <dest> <content>
atomic_write() {
    local dest="$1"
    local content="$2"
    # 🛡️ Sentinel: Refuse to write if dest is already a symlink to prevent
    # an attacker from redirecting the write to an arbitrary location.
    if [[ -L "$dest" ]]; then
        echo "Security Alert: $dest is a symlink! Refusing atomic_write." >&2
        return 1
    fi
    local dir
    dir=$(dirname "$dest")
    local tmp
    # Write to a sibling temp file then rename atomically
    tmp=$(mktemp "$dir/.atomic_write.XXXXXX")
    printf '%s' "$content" > "$tmp"
    mv "$tmp" "$dest"
}
