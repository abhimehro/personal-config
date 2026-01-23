#!/bin/bash
#
# Media Renaming & Upload Pipeline
# Watches staging folder, renames using FileBot, uploads to Cloud Union (GDrive + OneDrive)
#
# Usage:
#   ./rename-media.sh              # Process all files in staging
#   ./rename-media.sh --watch      # Watch mode (continuous)
#
set -euo pipefail

# Set PATH to include Homebrew/local binaries for launchd compatibility
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# === Configuration ===
STAGING_DIR="$HOME/CloudMedia/staging"
FAILED_DIR="$HOME/CloudMedia/failed"
LOG_FILE="$HOME/Library/Logs/media-renamer.log"

# Cloud Destination (Union Remote)
CLOUD_REMOTE="media"
MOVIE_DEST="Movies"
TV_DEST="TV Shows"

# FileBot Hardcoded Formats (Source of Truth)
FILEBOT_DB="TheMovieDB"
# User requested: {n.colon(' - ')} ({y}){subt}
FORMAT_MOVIE="{n.colon(' - ')} ({y}){subt}"
# User requested: {n} - {s00e00} - {t}{subt}
FORMAT_TV="{n} - {s00e00} - {t}{subt}"

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

rename_and_upload() {
    local file="$1"
    local filename=$(basename "$file")

    log "Processing: $filename"

    # Skip if not a video file
    if [[ ! "$file" =~ \.(mp4|mkv|avi|mov|m4v)$ ]]; then
        return 0
    fi

    # 1. IDENTIFY & RENAME (locally in place first to verify)
    # We use --action rename to rename the file in STAGING temporarily before upload
    # This ensures we allow FileBot to do its magic locally.

    log "Identifying with FileBot..."

    # Try Movies DB first
    local fb_output
    local match_type="Movie"

    # Attempt rename. We use a custom --format that includes the folder structure if needed,
    # but for rclone uploads, it's easier to just get the filename right and handle the folder mapping manually.
    # However, to support TV/Movie separation, checking the metadata is helpful.

    # We'll use a specific format expression that outputs: "TYPE|NEWFILENAME"
    # This allows us to parse whether it matched a Movie or Episode.
    # We use xattr to get metadata or just try strict mode.

    # SIMPLIFIED APPROACH:
    # We will try to rename using the Movie format. If it fails or looks like a show, we can try logic.
    # But FileBot CLI usually needs to know --db.
    # A robust way is to use the {type} binding or separate logic.

    local rename_cmd=(filebot -rename "$file" --action rename -non-strict --log fine --no-xattr)

    # Heuristic: If it has S01E01 pattern, assume TV
    if [[ "$filename" =~ [Ss][0-9]+[Ee][0-9]+ ]]; then
        match_type="TV"
        rename_cmd+=(--db TheTVDB --format "$FORMAT_TV")
    else
        match_type="Movie"
        rename_cmd+=(--db TheMovieDB --format "$FORMAT_MOVIE")
    fi

    if ! "${rename_cmd[@]}" 2>&1 | tee -a "$LOG_FILE"; then
        log "✗ FileBot matched failed locally"
        mv "$file" "$FAILED_DIR/"
        return 1
    fi

    # File is now renamed in place (in Staging). Find it.
    # Since we don't know the exact new name (FileBot did it), we look for the file that is NOT the old name
    # OR if it was already named correctly, it's the same file.

    # Actually, simpler: capture the output line with [MOVE] or [RENAME]
    # But since we did in-place rename, the 'file' variable might point to a non-existent path now.

    # Better strategy: Output to a temporary 'upload_ready' folder
    # This avoids "losing" the file pointer.

    # Let's retry the strategy: Move -> FileBot(Move) -> Rclone
}

# Improved Strategy for Handling FileBot + Rclone
process_file() {
    local file="$1"
    local filename=$(basename "$file")

    log "---------------------------------------------------"
    log "Processing: $filename"

    # Temporary directory for the final renamed file
    local temp_stage="$HOME/CloudMedia/upload_stage"
    mkdir -p "$temp_stage"

    # Determine DB and Format
    local db="TheMovieDB"
    local fmt="$FORMAT_MOVIE"
    local dest_subfolder="$MOVIE_DEST"

    # Simple regex for TV detection
    if [[ "$filename" =~ [Ss][0-9]+[Ee][0-9]+ ]]; then
        db="TheTVDB"
        fmt="$FORMAT_TV"
        dest_subfolder="$TV_DEST"
    fi

    log "Detected Type: $db ($dest_subfolder)"

    # filebot -rename
    #   --action move : moves from staging into temp_stage with new name
    #   --output : the root for the format.
    #   format needs to be relative to output

    log "Running FileBot..."
    # Note: --no-xattr removed to allow better identification.
    if filebot -rename "$file" \
        --db "$db" \
        --format "$fmt" \
        --output "$temp_stage" \
        --action move \
        -non-strict \
        --log fine >> "$LOG_FILE" 2>&1; then

        # Find the file in temp_stage
        local renamed_file=$(find "$temp_stage" -type f | head -1)

        if [[ -z "$renamed_file" ]]; then
             log "⚠ FileBot said success but file not found in $temp_stage"
             return 1
        fi

        local new_name=$(basename "$renamed_file")
        log "✓ Renamed to: $new_name"

        # Upload to Union Remote
        local cloud_path="$CLOUD_REMOTE:$dest_subfolder"

        log "🚀 Uploading to Cloud ($cloud_path)..."
        # We use 'move' to upload and delete local copy
        if rclone move "$renamed_file" "$cloud_path" --transfers=4 --checkers=8 >> "$LOG_FILE" 2>&1; then
            log "✅ Upload Successful!"
            notify "Media Added" "$new_name added to Library"
        else
            log "❌ Upload Failed"
            mv "$renamed_file" "$FAILED_DIR/"
            notify "Upload Failed" "$new_name"
        fi

        # Cleanup empty dirs in temp_stage
        rmdir "$temp_stage" 2>/dev/null || true

    else
        log "❌ FileBot identification failed"
        mv "$file" "$FAILED_DIR/"
        notify "Identification Failed" "$filename"
    fi
}


process_staging() {
    # Find video files
    find "$STAGING_DIR" -maxdepth 1 -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.m4v" -o -name "*.avi" \) -print0 | while IFS= read -r -d '' file; do
        process_file "$file"
    done
}

watch_mode() {
    log "=== Watch Mode Active ($STAGING_DIR) ==="

    if ! command -v fswatch &>/dev/null; then
        log "Installing fswatch..."
        brew install fswatch
    fi

    fswatch -0 --event Created --event MovedTo "$STAGING_DIR" | while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            # Small delay to ensure write is done
            sleep 2
            process_file "$file"
        fi
    done
}

# === Entry Point ===
mkdir -p "$STAGING_DIR" "$FAILED_DIR" "$(dirname "$LOG_FILE")"

case "${1:-}" in
    --watch)
        watch_mode
        ;;
    "")
        process_staging
        ;;
    *)
        if [[ -f "$1" ]]; then
            process_file "$1"
        else
            echo "File not found: $1"
            exit 1
        fi
        ;;
esac
