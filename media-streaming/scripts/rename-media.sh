#!/bin/bash
set -euo pipefail
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"
STAGING_DIR="$HOME/CloudMedia/staging"
PROCESSED_DIR="$HOME/CloudMedia/processed"
FAILED_DIR="$HOME/CloudMedia/failed"
REVIEW_DIR="$HOME/CloudMedia/upload_stage"
LOG_FILE="$HOME/Library/Logs/media-rename.log"
LOCK_FILE="$HOME/.media_upload.lock"
CLOUD_REMOTE="media"
MOUNT_DIR="$HOME/CloudMedia/mounted"
MOVIE_DEST="Movies"
TV_DEST="TV Shows"
FILEBOT_MOVIE_DB="TheMovieDB"
FILEBOT_TV_DB="TheTVDB"
FORMAT_MOVIE="{n.colon(' - ')} ({y}){subt}"
FORMAT_TV="{n} - {s00e00} - {t}{subt}"
AUTO_UPLOAD=0
WATCH_MODE=0
# Prevent uploading files > 15GB to avoid system stress
MAX_UPLOAD_SIZE_GB=15
ACTION="process"
APPROVE_TARGET=""
DIRECT_FILE=""
cleanup() { rm -f "$LOCK_FILE" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
notify() {
	local t="$1"
	local m="$2"
	if command -v terminal-notifier >/dev/null 2>&1; then
		terminal-notifier -title "$t" -message "$m" -sound default
	elif command -v osascript >/dev/null 2>&1; then
		osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title (item 2 of argv)' -e 'end run' -- "$m" "$t" 2>/dev/null || true
	fi
}
ensure_dirs() { mkdir -p "$STAGING_DIR" "$PROCESSED_DIR" "$FAILED_DIR" "$REVIEW_DIR" "$(dirname "$LOG_FILE")"; }
is_video_file() { [[ $1 =~ \.(mp4|mkv|avi|mov|m4v)$ ]]; }

# Bash-compatible timeout function (macOS doesn't have GNU timeout)
# Usage: run_with_timeout <timeout_seconds> <log_file> <command> [args...]
# Example: run_with_timeout 1800 "$LOG_FILE" rclone move "file.mp4" "remote:"
run_with_timeout() {
	local timeout_secs=$1
	local log_file=$2
	shift 2

	# Run command in background with all args preserved (handles spaces in filenames)
	"$@" >>"$log_file" 2>&1 &
	local cmd_pid=$!

	# Wait for command or timeout
	local start_time
	start_time=$(date +%s)
	while kill -0 $cmd_pid 2>/dev/null; do
		local current_time
		current_time=$(date +%s)
		local elapsed=$((current_time - start_time))
		if ((elapsed >= timeout_secs)); then
			kill -TERM $cmd_pid 2>/dev/null
			wait $cmd_pid 2>/dev/null
			return 1
		fi
		sleep 1
	done

	# Get exit status of the command
	wait $cmd_pid 2>/dev/null
	return $?
}
detect_type() {
	local f="$1"
	if [[ $f =~ [Ss][0-9]+[Ee][0-9]+ ]]; then echo tv; else echo movie; fi
}
check_remote_duplicate() {
	local r="$1"
	local n="$2"
	rclone lsf "$r" --files-only 2>/dev/null | grep -Fxq "$n"
}
has_base_name_match() {
	local dir="$1"
	local base="$2"
	[[ -d $dir ]] || return 1
	local f file_name file_base
	for f in "$dir"/*; do
		[[ -f $f ]] || continue
		file_name="${f##*/}"
		file_base="${file_name%.*}"
		if [[ $file_base == "$base" ]]; then
			return 0
		fi
	done
	return 1
}
write_sidecar() {
	local sidecar_path="$1" original_path="$2" proposed_path="$3" media_type="$4" target_remote="$5" db="$6" fmt="$7" duplicate_flag="$8"
	local created_at proposal_id
	created_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	proposal_id="$(printf %s "$original_path|$created_at" | shasum | awk '{print substr($1,1,12)}')"
	cat >"$sidecar_path" <<EOF
{
  "proposal_id": "$proposal_id",
  "original_path": "$original_path",
  "original_name": "${original_path##*/}",
  "proposed_path": "$proposed_path",
  "proposed_name": "${proposed_path##*/}",
  "media_type": "$media_type",
  "target_remote": "$target_remote",
  "filebot_db": "$db",
  "filebot_format": "$fmt",
  "created_at": "$created_at",
  "status": "pending",
  "duplicate_remote_match": $duplicate_flag,
  "notes": []
}
EOF
}
list_pending() {
	python3 - <<'PY'
import json
from pathlib import Path
sidecars = sorted((Path.home()/"CloudMedia"/"upload_stage").rglob("*.proposal.json"))
if not sidecars:
    print("No pending proposals.")
    raise SystemExit(0)
for s in sidecars:
    d = json.loads(s.read_text())
    print("----------------------------------------")
    print("proposal_id:  ", d.get("proposal_id"))
    print("created_at:   ", d.get("created_at"))
    print("original:     ", d.get("original_name"))
    print("proposed:     ", d.get("proposed_name"))
    print("media_type:   ", d.get("media_type"))
    print("target_remote:", d.get("target_remote"))
    print("duplicate:    ", "yes" if d.get("duplicate_remote_match") else "no")
    print("sidecar:      ", s)
PY
}
approve_candidate() {
	local sidecar="$1"
	[[ -f $sidecar ]] || {
		log "Sidecar not found: $sidecar"
		return 1
	}
	local proposed_path target_remote dup proposed_name sidecar_name failed_target
	local parsed
	parsed="$(
		python3 - "$sidecar" <<'PY'
import json, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text())
print(d["proposed_path"] + "|" + d["target_remote"] + "|" + ("true" if d.get("duplicate_remote_match") else "false"))
PY
	)"
	IFS="|" read -r proposed_path target_remote dup <<<"$parsed"
	proposed_name="${proposed_path##*/}"
	sidecar_name="${sidecar##*/}"
	[[ -f $proposed_path ]] || {
		log "Missing proposed file: $proposed_path"
		return 1
	}
	if [[ $dup == "true" ]]; then
		log "Skipping duplicate candidate pending manual review: $proposed_path"
		notify "Duplicate Pending" "Manual review needed for $proposed_name"
		return 2
	fi
	# Check file size before upload to prevent system stress
	local file_size_mb
	file_size_mb=$(stat -f "%z" "$proposed_path" 2>/dev/null | awk '{print $1/1024/1024}') || file_size_mb=0
	if (($(echo "$file_size_mb > $MAX_UPLOAD_SIZE_GB * 1024" | bc -l))); then
		local file_size_gb
		file_size_gb=$(echo "scale=2; $file_size_mb / 1024" | bc)
		log "⏸️  File too large for upload (${file_size_gb}GB > ${MAX_UPLOAD_SIZE_GB}GB): $proposed_name. Moved to failed queue."
		mv "$proposed_path" "$FAILED_DIR/" 2>/dev/null || true
		mv "$sidecar" "$FAILED_DIR/$sidecar_name" 2>/dev/null || true
		notify "Upload Skipped" "$proposed_name too large (${file_size_gb}GB)"
		rm -f "$LOCK_FILE" || true
		return 1
	fi

	touch "$LOCK_FILE"
	log "Uploading approved file: $proposed_name -> $target_remote"
	if run_with_timeout 1800 "$LOG_FILE" rclone move "$proposed_path" "$target_remote" --transfers=4 --checkers=8; then
		rm -f "$sidecar"
		log "Upload successful: $target_remote"
		notify "Media Uploaded" "$proposed_name"
		rm -f "$LOCK_FILE" || true
	else
		failed_target="$FAILED_DIR/$proposed_name"
		mv "$proposed_path" "$failed_target" 2>/dev/null || true
		mv "$sidecar" "$FAILED_DIR/$sidecar_name" 2>/dev/null || true
		log "Upload failed; moved candidate to failed queue"
		notify "Upload Failed" "$proposed_name"
		rm -f "$LOCK_FILE" || true
		return 1
	fi
}
approve_ready() {
	if [[ -n $APPROVE_TARGET ]]; then
		local target="$APPROVE_TARGET"
		if [[ -f $target && $target == *.proposal.json ]]; then
			approve_candidate "$target"
			return
		fi
		if [[ -f "$target.proposal.json" ]]; then
			approve_candidate "$target.proposal.json"
			return
		fi
		log "No matching proposal for target: $target"
		return 1
	fi
	local found=0
	while IFS= read -r sidecar; do
		found=1
		approve_candidate "$sidecar" || true
	done < <(find "$REVIEW_DIR" -type f -name "*.proposal.json" | sort)
	if [[ $found -eq 0 ]]; then log "No pending proposals to approve."; fi
}
process_file() {
	local file="$1" filename media_type db fmt dest_subfolder temp_output renamed_file final_dir final_path target_remote duplicate sidecar
	local final_name base_name ext counter
	filename="${file##*/}"
	log "---------------------------------------------------"
	log "Processing: $filename"
	if ! is_video_file "$file"; then
		log "Skipping non-video file: $filename"
		return 0
	fi
	media_type="$(detect_type "$filename")"
	if [[ $media_type == "tv" ]]; then
		db="$FILEBOT_TV_DB"
		fmt="$FORMAT_TV"
		dest_subfolder="$TV_DEST"
	else
		db="$FILEBOT_MOVIE_DB"
		fmt="$FORMAT_MOVIE"
		dest_subfolder="$MOVIE_DEST"
	fi
	temp_output="$(mktemp -d "$REVIEW_DIR/.incoming.XXXXXX")"
	log "Running FileBot using $db -> $dest_subfolder"
	if filebot -rename "$file" --db "$db" --format "$fmt" --output "$temp_output" --action move -non-strict --log fine >>"$LOG_FILE" 2>&1; then
		renamed_file="$(find "$temp_output" -type f | head -1)"
		if [[ -z $renamed_file || ! -f $renamed_file ]]; then
			log "FileBot reported success but no output file was found."
			rmdir "$temp_output" 2>/dev/null || true
			return 1
		fi
		final_dir="$REVIEW_DIR/$dest_subfolder"
		mkdir -p "$final_dir"

		final_name="${renamed_file##*/}"
		base_name="${final_name%.*}"
		ext="${final_name##*.}"
		counter=1

		# Mimic FileBot's conflict resolution by checking BOTH the live mount
		# (already-uploaded files) AND the local upload queue (in-flight files
		# that haven't been pushed to the remote yet). Skipping the queue check
		# would allow two same-named renames to overwrite each other in
		# $REVIEW_DIR before either is uploaded.
		# Check for base name matches to handle cases where extensions differ (e.g. .mp4 vs .mkv).
		local current_base="$base_name"
		while has_base_name_match "$MOUNT_DIR/$dest_subfolder" "$current_base" ||
			has_base_name_match "$final_dir" "$current_base"; do
			log "Duplicate detected for base name '$current_base'. Appending index."
			current_base="${base_name} (${counter})"
			((counter++)) || true
		done
		final_name="${current_base}.${ext}"

		final_path="$final_dir/$final_name"
		mv "$renamed_file" "$final_path"
		rmdir "$temp_output" 2>/dev/null || true
		target_remote="$CLOUD_REMOTE:$dest_subfolder"

		# Check whether the resolved name still collides on the remote (the
		# mount may be slightly stale vs. what rclone sees directly).
		duplicate=false
		if check_remote_duplicate "$target_remote" "${final_path##*/}"; then
			duplicate=true
			log "Duplicate found in remote: ${final_path##*/}"
		fi

		# Review queue is used ONLY for two exception cases:
		#   1. A remote duplicate exists and needs manual disambiguation.
		#   2. AUTO_UPLOAD is explicitly off (manual/test invocation).
		# Every other successfully renamed file is uploaded immediately.
		if [[ $duplicate == "true" ]]; then
			sidecar="$final_path.proposal.json"
			write_sidecar "$sidecar" "$file" "$final_path" "$media_type" "$target_remote" "$db" "$fmt" "true"
			log "Queued for review (remote duplicate): $final_path"
			notify "Duplicate Review Required" "${final_path##*/} already exists on server — manual review needed"
		elif [[ $AUTO_UPLOAD -eq 0 ]]; then
			sidecar="$final_path.proposal.json"
			write_sidecar "$sidecar" "$file" "$final_path" "$media_type" "$target_remote" "$db" "$fmt" "false"
			log "Queued for review (AUTO_UPLOAD off): $final_path"
			notify "Rename Review Ready" "${final_path##*/} queued for approval"
		else
			# Check file size before upload to prevent system stress
			local file_size_mb
			file_size_mb=$(stat -f "%z" "$final_path" 2>/dev/null | awk '{print $1/1024/1024}') || file_size_mb=0
			if (($(echo "$file_size_mb > $MAX_UPLOAD_SIZE_GB * 1024" | bc -l))); then
				local file_size_gb
				file_size_gb=$(echo "scale=2; $file_size_mb / 1024" | bc)
				log "⏸️  File too large for upload (${file_size_gb}GB > ${MAX_UPLOAD_SIZE_GB}GB): ${final_path##*/}. Moved to failed queue."
				mv "$final_path" "$FAILED_DIR/" 2>/dev/null || true
				notify "Upload Skipped" "${final_path##*/} too large (${file_size_gb}GB)"
				return 1
			fi

			# Happy path: clean rename, upload immediately with timeout.
			touch "$LOCK_FILE"
			log "Uploading: ${final_path##*/} -> $target_remote"
			if run_with_timeout 1800 "$LOG_FILE" rclone move "$final_path" "$target_remote" --transfers=4 --checkers=8; then
				log "Upload successful: ${final_path##*/}"
				notify "Media Uploaded" "${final_path##*/}"
				rm -f "$LOCK_FILE" || true
			else
				local failed_target="$FAILED_DIR/${final_path##*/}"
				mv "$final_path" "$failed_target" 2>/dev/null || true
				log "Upload failed; moved to failed queue: ${final_path##*/}"
				notify "Upload Failed" "${final_path##*/}"
				rm -f "$LOCK_FILE" || true
			fi
		fi
	else
		log "FileBot identification failed for $filename — queued for manual review"
		mkdir -p "$REVIEW_DIR/unidentified"
		mv "$file" "$REVIEW_DIR/unidentified/" 2>/dev/null || true
		notify "Identification Failed — Review Required" "$filename could not be matched by FileBot"
		rmdir "$temp_output" 2>/dev/null || true
	fi
}
process_staging() {
	# 1. Process video files that are fully written in STAGING_DIR.
	#    Filtering by extension here (instead of `! -name ".*"`) prevents
	#    non-video sidecars/junk from being moved into PROCESSED_DIR where
	#    they would be stranded (the FileBot step below only picks up videos).
	find "$STAGING_DIR" -maxdepth 1 -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.m4v" -o -name "*.avi" -o -name "*.mov" \) -print0 | while IFS= read -r -d "" file; do
		# Check if file is currently open by any process (e.g., Permute)
		if ! lsof "$file" >/dev/null 2>&1; then
			# SECURITY: Re-check existence because the file may have been moved or deleted
			# between find and lsof; treating every lsof failure as "safe to move" is racy.
			if [[ -f $file ]]; then
				log "File completely written, moving to processed: ${file##*/}"
				if ! mv "$file" "$PROCESSED_DIR/"; then
					# NOTE: A transient race should not terminate the watchdog loop under set -e.
					log "Failed to move file to processed, skipping: ${file##*/}"
				fi
			else
				log "File disappeared before move, skipping: ${file##*/}"
			fi
		else
			log "File still being written by Permute, waiting: ${file##*/}"
		fi
	done

	# 2. Run FileBot on files in PROCESSED_DIR
	find "$PROCESSED_DIR" -maxdepth 1 -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.m4v" -o -name "*.avi" -o -name "*.mov" \) -print0 | while IFS= read -r -d "" file; do
		process_file "$file"
	done
}
watch_mode() {
	log "Watch mode active (Polling $STAGING_DIR & $PROCESSED_DIR)"
	# A simple polling loop is much more robust for the 'wait until closed' logic
	# than fswatch since it naturally checks state every few seconds.
	while true; do
		process_staging
		sleep 10
	done
}
usage() { echo "Usage: rename-media.sh [--watch] [--auto-upload] | --list-pending | --approve-ready [proposal-or-media-file] | <file>"; }
ensure_dirs
while [[ $# -gt 0 ]]; do
	case "$1" in
	--watch) WATCH_MODE=1 ;;
	--auto-upload) AUTO_UPLOAD=1 ;;
	--list-pending) ACTION="list" ;;
	--approve-ready)
		ACTION="approve"
		shift
		APPROVE_TARGET="${1-}"
		if [[ -z $APPROVE_TARGET ]]; then
			set --
			break
		fi
		;;
	-h | --help)
		usage
		exit 0
		;;
	*) if [[ -f $1 ]]; then DIRECT_FILE="$1"; else
		echo "File not found: $1"
		exit 1
	fi ;;
	esac
	shift || break
done
case "$ACTION" in
list) list_pending ;;
approve) approve_ready ;;
process) if [[ -n $DIRECT_FILE ]]; then process_file "$DIRECT_FILE"; elif [[ $WATCH_MODE -eq 1 ]]; then watch_mode; else process_staging; fi ;;
esac
