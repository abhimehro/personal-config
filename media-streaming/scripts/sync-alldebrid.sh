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
MAX_FILE_SIZE_GB=15
# Track retry counts per file identity
REQUIRE_WINDSCRIBE=true
VPN_INTERFACE_PREFIX="utun"
TEMP_DOWNLOAD_DIR="${APPROVAL_DIR}/.downloading"

# Pre-download approval system
PENDING_DIR="${APPROVAL_DIR}/.pending"
APPROVED_DIR="${APPROVAL_DIR}/.approved"
AUTO_APPROVE_UNDER_GB=2
THRESHOLD_GATE_ENABLED=true

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

# Check if file exceeds maximum size limit (bash 3.2 compatible)
check_file_size() {
	local file="$1"
	local file_size_gb
	file_size_gb=$(rclone size "$ALLDEBRID_REMOTE/$file" --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['bytes']/1024/1024/1024)" 2>/dev/null || echo "0")

	# Use awk for floating point comparison (bash 3.2 compatible)
	if awk -v fs="$file_size_gb" -v max="$MAX_FILE_SIZE_GB" 'BEGIN { exit (fs > max) ? 0 : 1 }'; then
		log "⏸️  File too large (${file_size_gb:.2f}GB > ${MAX_FILE_SIZE_GB}GB): $file. Skipping to avoid system stress."
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

# Human-readable bytes
bytes_to_human() {
	local bytes=$1
	awk -v b="$bytes" 'BEGIN { printf "%.2f GB", b/1024/1024/1024 }'
}

# Create candidate metadata file with atomic write
create_candidate() {
	local file="$1"
	local file_size_gb="$2"

	# Get file size in bytes
	local file_size_bytes
	file_size_bytes=$(rclone size "$ALLDEBRID_REMOTE/$file" --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['bytes'])" 2>/dev/null || echo "0")

	local size_human
	size_human=$(bytes_to_human "$file_size_bytes")
	local queued_at
	queued_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
	local safe_filename
	safe_filename="${file//\//_}" # Replace slashes for filename
	local candidate_id="${safe_filename}.candidate.json"
	local candidate_file="$PENDING_DIR/$candidate_id"
	local tmp_file="$PENDING_DIR/${candidate_id}.tmp"

	# Create metadata JSON
	cat >"$tmp_file" <<EOF
{
  "filename": "$file",
  "size_bytes": $file_size_bytes,
  "size_human": "$size_human",
  "size_gb": $file_size_gb,
  "alldebrid_path": "$ALLDEBRID_REMOTE/$file",
  "queued_at": "$queued_at",
  "status": "pending"
}
EOF

	# Atomic write: tmp -> final
	mv "$tmp_file" "$candidate_file"

	log "✓ Candidate created: $candidate_file"
	return 0
}

# Process approved candidates (download files that have been approved)
process_approved_candidates() {
	local downloaded_count=0

	# Check for approved candidates
	for approved_file in "$APPROVED_DIR"/*.candidate.json; do
		[[ -f $approved_file ]] || continue

		local filename
		filename=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['filename'])" "$approved_file" 2>/dev/null)
		local alldebrid_path
		alldebrid_path=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['alldebrid_path'])" "$approved_file" 2>/dev/null)
		local candidate_id
		candidate_id="${approved_file##*/}"

		log "----------------------------------------"
		log "Processing approved candidate: $filename"

		# Re-check constraints before downloading
		check_vpn
		check_disk_space
		check_containment

		# Extract just the filename from the full path
		local basename="${filename##*/}"

		while check_lock; do
			sleep 60
		done

		# Download the file
		if rclone copy "$alldebrid_path" "$TEMP_DOWNLOAD_DIR/" "${RCLONE_FLAGS[@]}" --progress 2>&1 | tee -a "$LOG_FILE"; then
			log "✓ Downloaded to temp: $basename"

			# Ensure it is a file before attempting to move
			if [[ -f "$TEMP_DOWNLOAD_DIR/$basename" ]]; then
				if mv "$TEMP_DOWNLOAD_DIR/$basename" "$APPROVAL_DIR/"; then
					log "➜ Moved to Approval Folder: $basename"

					# Clean up approved candidate file
					rm -f "$approved_file"
					log "✓ Removed approved candidate: $candidate_id"

					# Persist to ledger
					PENDING_SELECTION="$APPROVAL_DIR/.alldebrid_candidate_pending.tsv"
					SELECTED_LEDGER="$APPROVAL_DIR/.alldebrid_selected.tsv"
					if [[ -s $PENDING_SELECTION ]]; then
						if [[ ! -s $SELECTED_LEDGER ]]; then
							head -n 1 "$PENDING_SELECTION" >"$SELECTED_LEDGER"
						fi
						if tail -n +2 "$PENDING_SELECTION" >>"$SELECTED_LEDGER"; then
							rm -f "$PENDING_SELECTION"
							log "✓ Persisted selected identity to ledger"
						else
							log "✗ ERROR: Failed to append to ledger. PENDING_SELECTION preserved."
						fi
					fi

					downloaded_count=$((downloaded_count + 1))
				else
					log "✗ ERROR: Failed to move $basename to Approval Folder!"
					exit 1
				fi
			else
				log "✗ Error: Downloaded item is not a file: $basename"
			fi
		else
			log "✗ Download failed: $basename"
			# Clean up approved candidate file even on failure
			rm -f "$approved_file"
		fi
	done

	log "Processed $downloaded_count approved candidate(s)"
	return 0
}

# === Main ===
mkdir -p "$DOWNLOAD_DIR" "$APPROVAL_DIR" "$TEMP_DOWNLOAD_DIR" "$PENDING_DIR" "$APPROVED_DIR" "$(dirname "$LOG_FILE")"

log "=== Alldebrid Sync Started ==="
log "Source: $ALLDEBRID_REMOTE"
log "Destination: $APPROVAL_DIR (Approval Folder)"
log "Dry run: $DRY_RUN"

# Hard safety gates. These prevent runaway downloads from a large Alldebrid backlog.
check_vpn
check_disk_space
check_containment

# Check if alldebrid remote exists
if ! rclone listremotes | grep -q "^alldebrid:"; then
	log "ERROR: 'alldebrid' remote not configured"
	exit 1
fi

# ============================================================================
# PHASE 1: Process any already-approved candidates (download them)
# ============================================================================
log "Checking for approved candidates..."
process_approved_candidates

# ============================================================================
# PHASE 2: If we have pending candidates, don't queue more
# ============================================================================
if [[ -n "$(ls -A "$PENDING_DIR"/*.candidate.json 2>/dev/null)" ]]; then
	log "Pending candidates already exist. Not queuing new ones until approval."
	log "   Run 'approve-download --list' to see pending candidates."
	log "=== Alldebrid Sync Complete (Pending Approval) ==="
	exit 0
fi

# ============================================================================
# PHASE 3: Select and queue new candidates for approval
# ============================================================================
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

# Get file size for threshold gate and size check
file_size_gb=$(rclone size "$ALLDEBRID_REMOTE/$file" --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['bytes']/1024/1024/1024)" 2>/dev/null || echo "0")

log "----------------------------------------"
log "Candidate selected: $file (${file_size_gb:.2f} GB)"

# Threshold gate: auto-approve small files (under AUTO_APPROVE_UNDER_GB)
if [[ $THRESHOLD_GATE_ENABLED == "true" ]] &&
	awk -v fs="$file_size_gb" -v max="$AUTO_APPROVE_UNDER_GB" 'BEGIN { exit (fs <= max) ? 0 : 1 }' 2>/dev/null; then
	log "Auto-approved (under ${AUTO_APPROVE_UNDER_GB}GB threshold): $file"

	# Create and immediately approve
	create_candidate "$file" "$file_size_gb"

	# Move to approved (atomic)
	candidate_id="${file////_}.candidate.json"
	mv "$PENDING_DIR/$candidate_id" "$APPROVED_DIR/$candidate_id"

	log "Candidate auto-approved and queued for download"
	log "=== Alldebrid Sync Complete (Auto-Approved) ==="
	exit 0
fi

# Check file size limit (user requested approval for large files)
if ! check_file_size "$file"; then
	# File was too large, already logged and added to ignore
	log "=== Alldebrid Sync Complete (File Too Large) ==="
	exit 0
fi

# Create candidate metadata file (atomic write)
create_candidate "$file" "$file_size_gb"

# Notify user that a download is pending approval
notify "Download Pending Approval" "New candidate: ${file} (${file_size_gb:.2f} GB). Run 'approve-download --list' or move file to .approved/"

log "Candidate queued for approval: $file"
log "   Size: ${file_size_gb:.2f} GB"
log "   To approve: approve-download ${file////_} or move $PENDING_DIR/${file////_}.candidate.json to $APPROVED_DIR/"

log "=== Alldebrid Sync Complete (Approval Required) ==="
