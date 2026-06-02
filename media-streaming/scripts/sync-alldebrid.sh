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

# Set PATH for launchd compatibility. Prefer the official rclone binary in
# /usr/local/bin because the Homebrew build does not support macOS mounts.
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

# Log file location
LOG_FILE="${HOME}/Library/Logs/alldebrid-sync.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# === Configuration ===
ALLDEBRID_REMOTE="alldebrid:links"
DOWNLOAD_DIR="$HOME/CloudMedia/downloads"
APPROVAL_DIR="$HOME/CloudMedia/approval_needed"

# Alldebrid-optimized rclone flags
# Keep these as an array. Passing them as one quoted string makes rclone treat
# the whole value as a positional argument, which caused scans to silently
# return no files when stderr was redirected.
RCLONE_FLAGS=(--multi-thread-streams=4 --buffer-size=32M)

DRY_RUN=false
LOCK_FILE="$HOME/.media_upload.lock"
MIN_SPACE_GB=20
MAX_APPROVAL_FILES=1
MAX_DOWNLOADING_FILES=1
# Prevent system stress from large files: skip files > 15GB
MAX_FILE_SIZE_GB=15
# Max retries per file before skipping to next
MAX_RETRY_COUNT=3
# Track retry counts per file identity
declare -A RETRY_COUNT
REQUIRE_WINDSCRIBE=true
VPN_INTERFACE_PREFIX="utun"
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

count_visible_files() {
	local dir="$1"
	find "$dir" -maxdepth 1 -type f ! -name ".*" -print0 | grep -cz . || true
}

# Check if file exceeds maximum size limit
check_file_size() {
	local file="$1"
	# Use rclone to get file size without downloading
	local file_size_gb
	file_size_gb=$(rclone size "$ALLDEBRID_REMOTE/$file" --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['total']/1024/1024/1024)" 2>/dev/null || echo "0")

	if (($(echo "$file_size_gb > $MAX_FILE_SIZE_GB" | bc -l))); then
		log "⏸️  File too large (${file_size_gb:.2f}GB > ${MAX_FILE_SIZE_GB}GB): $file. Skipping to avoid system stress."
		# Add to ignore list to prevent retries
		echo "$file" >>"$IGNORE_FILE"
		return 1
	fi
	return 0
}

check_vpn() {
	if [[ $REQUIRE_WINDSCRIBE != "true" ]]; then
		return 0
	fi

	if pgrep -ix "Windscribe" >/dev/null 2>&1 && ifconfig | grep -q "^${VPN_INTERFACE_PREFIX}"; then
		return 0
	fi

	log "⏸️  Windscribe/VPN guard is not satisfied. Refusing to download."
	notify "Alldebrid Download Paused" "Windscribe/VPN does not appear connected"
	exit 0
}

check_containment() {
	local approval_count downloading_count
	approval_count=$(count_visible_files "$APPROVAL_DIR")
	downloading_count=$(count_visible_files "$TEMP_DOWNLOAD_DIR")

	if ((approval_count >= MAX_APPROVAL_FILES)); then
		log "⏸️  Approval gate active: $approval_count file(s) already waiting in $APPROVAL_DIR."
		exit 0
	fi

	if ((downloading_count >= MAX_DOWNLOADING_FILES)); then
		log "⏸️  Download gate active: $downloading_count file(s) already in $TEMP_DOWNLOAD_DIR."
		exit 0
	fi
}

# === Main ===
mkdir -p "$DOWNLOAD_DIR" "$APPROVAL_DIR" "$TEMP_DOWNLOAD_DIR" "$(dirname "$LOG_FILE")"

log "=== Alldebrid Sync Started ==="
log "Source: $ALLDEBRID_REMOTE"
log "Destination: $APPROVAL_DIR (Approval Folder)"
log "Dry run: $DRY_RUN"

# Hard safety gates. These prevent runaway downloads from a large Alldebrid backlog.
check_vpn
check_disk_space
check_containment

# Check if alldebrid remote exists
if ! rclone listremotes | grep -q "^alldebrid:$"; then
	log "ERROR: 'alldebrid' remote not configured"
	exit 1
fi

# List files
log "Scanning Alldebrid for video files..."
files_list=$(rclone lsf "$ALLDEBRID_REMOTE" --files-only "${RCLONE_FLAGS[@]}" 2>/dev/null | grep -iE '\.(mp4|mkv|avi|m4v|mov)$' || true)

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

# Fetch ONLY the best conservative candidate for this sync run.
selection_log=$(mktemp)
trap 'rm -f "$selection_log"' EXIT
file=$(printf "%s\n" "$files_list" | APPROVAL_DIR="$APPROVAL_DIR" python3 "$SCRIPT_DIR/select-best-alldebrid-candidate.py" 2>"$selection_log")
while IFS= read -r line; do
	log "$line"
done <"$selection_log"
rm -f "$selection_log"

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

# Re-check constraints immediately before transferring bytes.
check_vpn
check_disk_space
check_containment
check_file_size "$file"

while check_lock; do
	sleep 60
done

# Atomic Download Strategy:
# 1. Download to .downloading/filename
# 2. Move to approval_needed/filename

rclone copy "$ALLDEBRID_REMOTE/$file" "$TEMP_DOWNLOAD_DIR/" "${RCLONE_FLAGS[@]}" --progress 2>&1 | tee -a "$LOG_FILE"
if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
	log "✓ Downloaded to temp: $file"

	# Ensure it is a file before attempting to move
	if [[ -f "$TEMP_DOWNLOAD_DIR/$file" ]]; then
		# Atomic move to Approval Folder
		if mv "$TEMP_DOWNLOAD_DIR/$file" "$APPROVAL_DIR/"; then
			log "➜ Moved to Approval Folder: $file"

			# Persist the selected canonical identity only after the file safely lands
			# in approval_needed. This avoids marking failed downloads as processed.
			PENDING_SELECTION="$APPROVAL_DIR/.alldebrid_candidate_pending.tsv"
			SELECTED_LEDGER="$APPROVAL_DIR/.alldebrid_selected.tsv"
			if [[ -s $PENDING_SELECTION ]]; then
				if [[ ! -s $SELECTED_LEDGER ]]; then
					head -n 1 "$PENDING_SELECTION" >"$SELECTED_LEDGER"
				fi
				if tail -n +2 "$PENDING_SELECTION" >>"$SELECTED_LEDGER"; then
					rm -f "$PENDING_SELECTION"
					log "✓ Persisted selected identity to ledger: $SELECTED_LEDGER"
				else
					log "✗ ERROR: Failed to append to ledger $SELECTED_LEDGER. PENDING_SELECTION preserved."
				fi
			fi

			# Do not delete from Alldebrid automatically. The local ledger prevents
			# repeat processing while keeping the remote library non-destructive.
			log "ℹ️  Remote file preserved in Alldebrid; local ledger prevents duplicate processing."

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
