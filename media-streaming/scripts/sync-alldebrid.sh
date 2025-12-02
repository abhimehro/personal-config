#!/bin/bash
#
# Alldebrid → Cloud Unified Library Sync
# Downloads from Alldebrid, renames with FileBot, uploads to Google Drive
#
# Usage:
#   ./sync-alldebrid.sh              # Sync all files from alldebrid:links
#   ./sync-alldebrid.sh --dry-run    # Preview only
#   ./sync-alldebrid.sh --recent     # Only files from last 24 hours
#
set -euo pipefail

# === Configuration ===
ALLDEBRID_REMOTE="alldebrid:links"
WORK_DIR="$HOME/CloudMedia/alldebrid-sync"
PROCESSED_DIR="$HOME/CloudMedia/processed"
FAILED_DIR="$HOME/CloudMedia/failed"
LOG_FILE="$HOME/Library/Logs/alldebrid-sync.log"
CLOUD_DEST="gdrive:Media/Movies"

# Alldebrid-optimized rclone flags (for copy/sync operations)
RCLONE_FLAGS="--multi-thread-streams=0 --buffer-size=0"

# FileBot settings
FILEBOT_DB="TheMovieDB"
FILEBOT_FORMAT="{n} ({y})"

DRY_RUN=false
RECENT_ONLY=false

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        --recent) RECENT_ONLY=true ;;
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

cleanup() {
    log "Cleaning up work directory..."
    rm -rf "$WORK_DIR"/*
}

# === Main ===
mkdir -p "$WORK_DIR" "$PROCESSED_DIR" "$FAILED_DIR" "$(dirname "$LOG_FILE")"

log "=== Alldebrid Sync Started ==="
log "Source: $ALLDEBRID_REMOTE"
log "Destination: $CLOUD_DEST"
log "Dry run: $DRY_RUN"

# Check if alldebrid remote exists
if ! rclone listremotes | grep -q "^alldebrid:$"; then
    log "ERROR: 'alldebrid' remote not configured"
    echo ""
    echo "Please configure Alldebrid first:"
    echo "  rclone config create alldebrid webdav \\"
    echo "      url=\"https://webdav.debrid.it\" \\"
    echo "      vendor=\"other\" \\"
    echo "      user=\"YOUR_APIKEY\" \\"
    echo "      pass=\"eeeee\""
    exit 1
fi

# List files from Alldebrid
log "Scanning Alldebrid for video files..."
echo ""

# Get list of video files
files_list=$(rclone lsf "$ALLDEBRID_REMOTE" $RCLONE_FLAGS --files-only 2>/dev/null | grep -iE '\.(mp4|mkv|avi|m4v)$' || true)

if [[ -z "$files_list" ]]; then
    log "No video files found in Alldebrid"
    exit 0
fi

file_count=$(echo "$files_list" | wc -l | tr -d ' ')
log "Found $file_count video file(s)"
echo ""

echo "$files_list" | while read -r file; do
    echo "  📁 $file"
done

echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    echo "Dry run complete. Run without --dry-run to process files."
    exit 0
fi

read -p "Do you want to sync these files? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "User cancelled"
    exit 0
fi

# Process each file
success_count=0
fail_count=0

echo "$files_list" | while read -r file; do
    log "----------------------------------------"
    log "Processing: $file"
    
    # Download from Alldebrid
    log "Downloading from Alldebrid..."
    if ! rclone copy "$ALLDEBRID_REMOTE/$file" "$WORK_DIR/" $RCLONE_FLAGS --progress 2>&1 | tee -a "$LOG_FILE"; then
        log "✗ Download failed: $file"
        ((fail_count++)) || true
        continue
    fi
    
    local_file="$WORK_DIR/$file"
    
    if [[ ! -f "$local_file" ]]; then
        log "✗ File not found after download: $file"
        ((fail_count++)) || true
        continue
    fi
    
    # Rename with FileBot
    log "Identifying with FileBot..."
    if filebot -rename "$local_file" \
        --db "$FILEBOT_DB" \
        --format "$FILEBOT_FORMAT" \
        -non-strict \
        --action move \
        --log fine 2>&1 | tee -a "$LOG_FILE"; then
        
        # Find the renamed file
        renamed_file=$(find "$WORK_DIR" -maxdepth 1 -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.m4v" \) | head -1)
        
        if [[ -n "$renamed_file" && -f "$renamed_file" ]]; then
            new_name=$(basename "$renamed_file")
            log "✓ Identified as: $new_name"
            
            # Check if already exists in cloud
            if rclone lsf "$CLOUD_DEST/$new_name" $RCLONE_FLAGS 2>/dev/null | grep -q .; then
                log "⚠ Already exists in cloud, skipping upload"
                rm -f "$renamed_file"
                ((success_count++)) || true
                continue
            fi
            
            # Upload to cloud
            log "Uploading to $CLOUD_DEST..."
            if rclone copy "$renamed_file" "$CLOUD_DEST/" --progress 2>&1 | tee -a "$LOG_FILE"; then
                log "✓ Uploaded successfully: $new_name"
                mv "$renamed_file" "$PROCESSED_DIR/"
                notify "Alldebrid Sync" "$new_name synced to cloud"
                ((success_count++)) || true
            else
                log "✗ Upload failed"
                mv "$renamed_file" "$FAILED_DIR/"
                ((fail_count++)) || true
            fi
        else
            log "✗ FileBot couldn't identify: $file"
            # Keep original name but still upload
            log "Uploading with original name..."
            if rclone copy "$local_file" "$CLOUD_DEST/" --progress 2>&1 | tee -a "$LOG_FILE"; then
                log "✓ Uploaded (unidentified): $file"
                mv "$local_file" "$PROCESSED_DIR/"
                ((success_count++)) || true
            else
                mv "$local_file" "$FAILED_DIR/"
                ((fail_count++)) || true
            fi
        fi
    else
        log "✗ FileBot error for: $file"
        mv "$local_file" "$FAILED_DIR/"
        ((fail_count++)) || true
    fi
done

# Cleanup
cleanup

log "=== Alldebrid Sync Complete ==="
log "Success: $success_count, Failed: $fail_count"
echo ""
echo "✅ Sync complete!"
echo "   Success: $success_count files"
echo "   Failed: $fail_count files"
echo ""
echo "💡 Check logs at: $LOG_FILE"

notify "Alldebrid Sync Complete" "$success_count synced, $fail_count failed"
