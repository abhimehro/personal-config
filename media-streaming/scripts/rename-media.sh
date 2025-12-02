#!/bin/bash
#
# Media Renaming & Upload Pipeline
# Watches staging folder, renames using FileBot, uploads to cloud
#
# Usage:
#   ./rename-media.sh              # Process all files in staging
#   ./rename-media.sh /path/to/file.mp4  # Process specific file
#   ./rename-media.sh --watch      # Watch mode (continuous)
#
set -euo pipefail

# === Configuration ===
STAGING_DIR="$HOME/CloudMedia/staging"
PROCESSED_DIR="$HOME/CloudMedia/processed"
FAILED_DIR="$HOME/CloudMedia/failed"
LOG_FILE="$HOME/Library/Logs/media-renamer.log"

# Local Google Drive path (synced by Google Drive desktop app)
GDRIVE_LOCAL="$HOME/Library/CloudStorage/GoogleDrive-abhimhrtr@gmail.com/My Drive/Media"
GDRIVE_MOVIES="$GDRIVE_LOCAL/Movies"
GDRIVE_TV="$GDRIVE_LOCAL/TV Shows"

# FileBot settings
FILEBOT_DB="TheMovieDB"  # or TheTVDB for TV shows
FILEBOT_FORMAT="{n} ({y})"  # Output: "Movie Name (2024).ext"
FILEBOT_TV_FORMAT="{n} - {s00e00} - {t}"  # Output: "Show - S01E01 - Title.ext"

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

rename_file() {
    local file="$1"
    local filename=$(basename "$file")
    
    log "Processing: $filename"
    
    # Skip if not a video file
    if [[ ! "$file" =~ \.(mp4|mkv|avi|mov|m4v)$ ]]; then
        log "Skipping non-video file: $filename"
        return 0
    fi
    
    # Ensure Google Drive directories exist
    mkdir -p "$GDRIVE_MOVIES" "$GDRIVE_TV"
    
    # FileBot renames AND moves directly to processed folder
    local fb_output
    fb_output=$(filebot -rename "$file" \
        --db "$FILEBOT_DB" \
        --format "$PROCESSED_DIR/$FILEBOT_FORMAT" \
        -non-strict \
        --action move \
        --log fine 2>&1) || true
    
    echo "$fb_output" | tee -a "$LOG_FILE"
    
    # Parse FileBot output to get the actual renamed file path
    # FileBot outputs: [MOVE] from [...] to [/path/to/new/file.mp4]
    local renamed_file
    renamed_file=$(echo "$fb_output" | grep -oE '\[MOVE\] from .* to \[.*\]' | sed 's/.*to \[\(.*\)\]/\1/' | head -1)
    
    # Handle "Skipped" case (file already correctly named)
    if [[ -z "$renamed_file" ]] && echo "$fb_output" | grep -q "Skipped"; then
        log "File already correctly named, moving directly..."
        renamed_file="$file"
    fi
    
    # Process the renamed file
    if [[ -n "$renamed_file" && -f "$renamed_file" ]]; then
        local new_name=$(basename "$renamed_file")
        log "✓ Renamed to: $new_name"
        
        # Move to local Google Drive folder (native sync handles upload)
        log "Moving to Google Drive (sync will handle upload)..."
        if mv "$renamed_file" "$GDRIVE_MOVIES/"; then
            log "✓ Moved to Google Drive: $GDRIVE_MOVIES/$new_name"
            notify "Media Queued" "$new_name → Google Drive sync"
        else
            log "✗ Failed to move to Google Drive"
            notify "Media Warning" "$new_name in processed (GDrive move failed)"
        fi
    else
        log "✗ FileBot couldn't identify: $filename"
        # Move original to failed for manual handling
        [[ -f "$file" ]] && mv "$file" "$FAILED_DIR/"
        notify "Media Failed" "Couldn't identify: $filename"
    fi
}

process_staging() {
    log "=== Processing staging folder ==="
    
    local count=0
    while IFS= read -r -d '' file; do
        rename_file "$file"
        ((count++)) || true
    done < <(find "$STAGING_DIR" -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.m4v" \) -print0)
    
    log "Processed $count files"
}

watch_mode() {
    log "=== Watch mode started ==="
    log "Watching: $STAGING_DIR"
    
    # Check if fswatch is installed
    if ! command -v fswatch &>/dev/null; then
        log "Installing fswatch..."
        brew install fswatch
    fi
    
    # Watch for new files
    fswatch -0 --event Created --event MovedTo "$STAGING_DIR" | while IFS= read -r -d '' file; do
        # Wait for file to finish writing
        sleep 2
        if [[ -f "$file" ]]; then
            rename_file "$file"
        fi
    done
}

# === Main ===
mkdir -p "$STAGING_DIR" "$PROCESSED_DIR" "$FAILED_DIR" "$(dirname "$LOG_FILE")"

case "${1:-}" in
    --watch)
        watch_mode
        ;;
    "")
        process_staging
        ;;
    *)
        if [[ -f "$1" ]]; then
            rename_file "$1"
        else
            echo "File not found: $1"
            exit 1
        fi
        ;;
esac
