#!/bin/bash
#
# Alldebrid → CloudMedia Integration
# Downloads links from Alldebrid to the Downie/Permute watch folder.
# This integrates Alldebrid downloads into the main media processing pipeline:
# Download -> Convert (Permute) -> Stage -> Rename (Filebot) -> Upload
#
# Usage:
#   ./sync-alldebrid.sh              # Sync all files from alldebrid:links
#   ./sync-alldebrid.sh --dry-run    # Preview only
#
set -euo pipefail

# Set PATH to include Homebrew/local binaries for launchd compatibility
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Log file location
LOG_FILE="${HOME}/Library/Logs/alldebrid-sync.log"

# === Configuration ===
ALLDEBRID_REMOTE="alldebrid:links"
DOWNLOAD_DIR="$HOME/CloudMedia/downloads"

# Alldebrid-optimized rclone flags
# --ignore-existing ensures we don't re-download if the file is still sitting in downloads
RCLONE_FLAGS="--multi-thread-streams=4 --buffer-size=32M --ignore-existing"

DRY_RUN=false
LOCK_FILE="$HOME/.media_upload.lock"
MIN_SPACE_GB=20
TEMP_DOWNLOAD_DIR="${DOWNLOAD_DIR}/.downloading"

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
    esac
done

# === Functions ===
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

notify() {
    local title="$1"
    local message="$2"
    if command -v terminal-notifier &>/dev/null; then
        terminal-notifier -title "$title" -message "$message" -sound default
    fi
}

check_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        log "⏸️  Upload in progress (Lock file found). Pausing downloads..."
        return 0 # True, lock exists
    fi
    return 1 # False, no lock
}

check_disk_space() {
    local free_space
    free_space=$(df -g / | awk 'NR==2 {print $4}') # Available in GB
    if (( free_space < MIN_SPACE_GB )); then
        log "⚠️  Low Disk Space: ${free_space}GB free (Min: ${MIN_SPACE_GB}GB). Stopping downloads."
        notify "Download Paused" "Low disk space (${free_space}GB)"
        exit 0
    fi
}

# === Main ===
mkdir -p "$DOWNLOAD_DIR" "$TEMP_DOWNLOAD_DIR" "$(dirname "$LOG_FILE")"

log "=== Alldebrid Sync Started ==="
log "Source: $ALLDEBRID_REMOTE"
log "Destination: $DOWNLOAD_DIR (Permute Watch Folder)"
log "Dry run: $DRY_RUN"

# Check if alldebrid remote exists
if ! rclone listremotes | grep -q "^alldebrid:$"; then
    log "ERROR: 'alldebrid' remote not configured"
    exit 1
fi

# List files
log "Scanning Alldebrid for video files..."
files_list=$(rclone lsf "$ALLDEBRID_REMOTE" $RCLONE_FLAGS --files-only 2>/dev/null | grep -iE '\.(mp4|mkv|avi|m4v|mov)$' || true)

if [[ -z "$files_list" ]]; then
    log "No video files found in Alldebrid"
    exit 0
fi

file_count=$(echo "$files_list" | wc -l | tr -d ' ')
log "Found $file_count video file(s)"

if [[ "$DRY_RUN" == "true" ]]; then
    echo "$files_list"
    echo "Dry run complete."
    exit 0
fi

# Download Process
success_count=0
fail_count=0

echo "$files_list" | while read -r file; do
    log "----------------------------------------"
    log "Downloading: $file"

    # We use 'move' locally to simulate consuming the link, OR 'copy' if we want to keep it on cloud.
    # Given the workflow "Download -> ...", usually we want to bring it local.
    # However, 'rclone move' on some remotes might be slow or unsupported.
    # We'll use 'copy' here. To prevent infinite re-downloads, users usually clear their debrid links manually
    # or we could keep a history file.
    # For now, 'copy --ignore-existing' lets it sit there until the user removes it from Alldebrid.

    # Check constraints before EACH file
    check_disk_space

    while check_lock; do
        sleep 60
    done

    # Atomic Download Strategy:
    # 1. Download to .downloading/filename
    # 2. Move to downloads/filename
    # This prevents Permute from picking up partial files.

    if rclone copy "$ALLDEBRID_REMOTE/$file" "$TEMP_DOWNLOAD_DIR/" $RCLONE_FLAGS --progress 2>&1 | tee -a "$LOG_FILE"; then
        log "✓ Downloaded to temp: $file"

        # Atomic move to Watch Folder
        mv "$TEMP_DOWNLOAD_DIR/$file" "$DOWNLOAD_DIR/"

        log "➜ Moved to Watch Folder: $file"
        notify "Media Downloaded" "$file sent to Permute pipeline"
        ((success_count++)) || true

        # Optional: Delete from remote after successful download?
        # rclone delete "$ALLDEBRID_REMOTE/$file"
    else
        log "✗ Download failed: $file"
        ((fail_count++)) || true
    fi
done

log "=== Alldebrid Sync Complete ==="
log "Success: $success_count, Failed: $fail_count"
notify "Alldebrid Sync Complete" "$success_count files queued for processing"
