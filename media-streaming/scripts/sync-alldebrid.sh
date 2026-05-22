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
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"

# Log file location
LOG_FILE="${HOME}/Library/Logs/alldebrid-sync.log"

# === Configuration ===
ALLDEBRID_REMOTE="alldebrid:links"
DOWNLOAD_DIR="$HOME/CloudMedia/downloads"
APPROVAL_DIR="$HOME/CloudMedia/approval_needed"

# Alldebrid-optimized rclone flags
RCLONE_FLAGS="--multi-thread-streams=4 --buffer-size=32M"

DRY_RUN=false
LOCK_FILE="$HOME/.media_upload.lock"
MIN_SPACE_GB=20
TEMP_DOWNLOAD_DIR="${APPROVAL_DIR}/.downloading"

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
	elif command -v osascript &>/dev/null; then
		osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title (item 2 of argv)' -e 'end run' "$message" "$title" 2>/dev/null || true
	fi
}

check_lock() {
	if [[ -f $LOCK_FILE ]]; then
		# Check if lock is stale (older than 120 mins)
		if [[ "$(uname)" == "Darwin" ]]; then
			# macOS stat
			local lock_age_secs=$(($(date +%s) - $(stat -f %m "$LOCK_FILE")))
		else
			# Linux stat
			local lock_age_secs=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE")))
		fi

		if ((lock_age_secs > 7200)); then
			log "⚠️  Stale lock detected (${lock_age_secs}s old). Removing..."
			rm -f "$LOCK_FILE"
			return 1 # Lock removed, proceed
		fi

		log "⏸️  Upload in progress (Lock active for ${lock_age_secs}s). Pausing downloads..."
		return 0 # True, lock exists
	fi
	return 1 # False, no lock
}

check_disk_space() {
	local free_space
	free_space=$(df -g / | awk 'NR==2 {print $4}') # Available in GB
	if ((free_space < MIN_SPACE_GB)); then
		log "⚠️  Low Disk Space: ${free_space}GB free (Min: ${MIN_SPACE_GB}GB). Stopping downloads."
		notify "Download Paused" "Low disk space (${free_space}GB)"
		exit 0
	fi
}

# === Main ===
mkdir -p "$DOWNLOAD_DIR" "$APPROVAL_DIR" "$TEMP_DOWNLOAD_DIR" "$(dirname "$LOG_FILE")"

log "=== Alldebrid Sync Started ==="
log "Source: $ALLDEBRID_REMOTE"
log "Destination: $APPROVAL_DIR (Approval Folder)"
log "Dry run: $DRY_RUN"

# Check for existing pending approvals (ignore hidden files like .DS_Store or .downloading)
# Use null-delimited output to handle filenames with newlines
pending_files=$(find "$APPROVAL_DIR" -maxdepth 1 -type f ! -name ".*" -print0 | grep -cz .)
if ((pending_files > 0)); then
	log "⏸️  A video is waiting for approval in $APPROVAL_DIR. Skipping download."
	exit 0
fi

# Check if alldebrid remote exists
if ! rclone listremotes | grep -q "^alldebrid:$"; then
	log "ERROR: 'alldebrid' remote not configured"
	exit 1
fi

# List files
log "Scanning Alldebrid for video files..."
files_list=$(rclone lsf "$ALLDEBRID_REMOTE" "$RCLONE_FLAGS" --files-only 2>/dev/null | grep -iE '\.(mp4|mkv|avi|m4v|mov)$' || true)

# Filter out historically failed deletions to prevent infinite loops
IGNORE_FILE="$APPROVAL_DIR/.alldebrid_ignore"
if [[ -s $IGNORE_FILE ]]; then
	files_list=$(printf "%s\n" "$files_list" | grep -v -F -f <(awk 'NF' "$IGNORE_FILE") || true)
fi

if [[ -z $files_list ]]; then
	log "No video files found in Alldebrid"
	exit 0
fi

# Count files robustly (handles filenames with spaces but assumes no newlines from rclone lsf)
file_count=$(printf "%s\n" "$files_list" | grep -c .)
log "Found $file_count video file(s)"

if [[ $DRY_RUN == "true" ]]; then
	echo "$files_list"
	echo "Dry run complete."
	exit 0
fi

# Fetch ONLY the first file
file=$(printf "%s\n" "$files_list" | sort | head -n 1)

if [[ -z $file ]]; then
	log "ERROR: Parsed file name is empty. Skipping."
	exit 0
fi

if [[ $file == */ ]]; then
	log "ERROR: Parsed file name is a directory. Skipping."
	exit 0
fi

log "----------------------------------------"
log "Downloading: $file"

# Check constraints
check_disk_space

while check_lock; do
	sleep 60
done

# Atomic Download Strategy:
# 1. Download to .downloading/filename
# 2. Move to approval_needed/filename

rclone copy "$ALLDEBRID_REMOTE/$file" "$TEMP_DOWNLOAD_DIR/" "$RCLONE_FLAGS" --progress 2>&1 | tee -a "$LOG_FILE"
if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
	log "✓ Downloaded to temp: $file"

	# Ensure it is a file before attempting to move
	if [[ -f "$TEMP_DOWNLOAD_DIR/$file" ]]; then
		# Atomic move to Approval Folder
		if mv "$TEMP_DOWNLOAD_DIR/$file" "$APPROVAL_DIR/"; then
			log "➜ Moved to Approval Folder: $file"

			# Delete from Alldebrid to prevent re-downloads and clear the queue
			log "🗑️  Deleting from Alldebrid remote to prevent duplicates..."
			if ! rclone deletefile "$ALLDEBRID_REMOTE/$file" --retries 3; then
				log "⚠️ Failed to delete from remote! Logging to ignore list to prevent loops."
				echo "$file" >>"$IGNORE_FILE"
				tail -n 100 "$IGNORE_FILE" >"$IGNORE_FILE.tmp" && mv "$IGNORE_FILE.tmp" "$IGNORE_FILE"
			fi

			notify "Video Needs Approval" "Review $file in CloudMedia/approval_needed"
		else
			log "✗ ERROR: Failed to move $file to Approval Folder! Remote file preserved."
			exit 1
		fi
	else
		log "✗ Error: Downloaded item is not a file: $file"
	fi
else
	log "✗ Download failed due to network or rclone error: $file"
fi

log "=== Alldebrid Sync Complete ==="
