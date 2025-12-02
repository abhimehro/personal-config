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
CLOUD_DEST="gdrive:Media/Movies"  # Change to onedrive:Media/Movies if preferred

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
    
    # Create temp directory for FileBot output
    local temp_dir=$(mktemp -d)
    
    # Try FileBot rename (in-place with --action move)
    local original_dir=$(dirname "$file")
    
    if filebot -rename "$file" \
        --db "$FILEBOT_DB" \
        --format "$FILEBOT_FORMAT" \
        -non-strict \
        --action move \
        --log fine 2>&1 | tee -a "$LOG_FILE"; then
        
        # Find the renamed file (FileBot renames in-place)
        local renamed_file=$(find "$original_dir" -maxdepth 1 -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.m4v" \) -newer "$LOG_FILE" 2>/dev/null | head -1)
        
        # If not found by timestamp, look for any movie-named file
        if [[ -z "$renamed_file" ]]; then
            renamed_file=$(find "$original_dir" -maxdepth 1 -type f -name "* (*).mp4" -o -name "* (*).mkv" -o -name "* (*).m4v" 2>/dev/null | head -1)
        fi
        
        if [[ -n "$renamed_file" && -f "$renamed_file" ]]; then
            local new_name=$(basename "$renamed_file")
            log "✓ Renamed to: $new_name"
            
            # Upload to cloud
            log "Uploading to $CLOUD_DEST..."
            if rclone copy "$renamed_file" "$CLOUD_DEST" --progress 2>&1 | tee -a "$LOG_FILE"; then
                log "✓ Uploaded successfully"
                
                # Move renamed file to processed
                mv "$renamed_file" "$PROCESSED_DIR/"
                notify "Media Processed" "$new_name uploaded to cloud"
            else
                log "✗ Upload failed"
                mv "$renamed_file" "$FAILED_DIR/"
            fi
        else
            log "✗ FileBot couldn't identify: $filename"
            # Move to failed for manual handling
            [[ -f "$file" ]] && mv "$file" "$FAILED_DIR/"
            notify "Media Failed" "Couldn't identify: $filename"
        fi
    else
        log "✗ FileBot error for: $filename"
        [[ -f "$file" ]] && mv "$file" "$FAILED_DIR/"
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
