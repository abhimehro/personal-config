#!/bin/bash
#
# Bulk Rename Existing Cloud Media
# Downloads, renames with FileBot, re-uploads with proper names
#
# Usage:
#   ./bulk-rename-cloud.sh           # Interactive mode
#   ./bulk-rename-cloud.sh --dry-run # Preview only
#
set -euo pipefail

WORK_DIR="$HOME/CloudMedia/bulk-rename-temp"
LOG_FILE="$HOME/Library/Logs/bulk-rename.log"
CLOUD_SOURCE="gdrive:Media/Movies"
CLOUD_DEST="gdrive:Media/Movies"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

mkdir -p "$WORK_DIR" "$(dirname "$LOG_FILE")"

log "=== Bulk Rename Started ==="
log "Source: $CLOUD_SOURCE"
log "Dry run: $DRY_RUN"

# List files that need renaming (hash-like or numeric names)
echo ""
echo "📋 Scanning for poorly-named files..."
echo ""

# Pattern: files starting with numbers/hashes, containing "HEVC", etc.
rclone lsf "$CLOUD_SOURCE" --files-only 2>/dev/null | while read -r file; do
    # Check if filename looks like it needs renaming
    if [[ "$file" =~ ^[0-9a-f]{20,}.*\.mp4$ ]] || \
       [[ "$file" =~ ^[0-9]+_(shd|hd|h).*\.mp4$ ]] || \
       [[ "$file" =~ ^master\.m3u8.*\.mp4$ ]] || \
       [[ "$file" =~ ^[0-9]+_[0-9]+p.*\.mp4$ ]]; then
        echo "  ⚠️  $file"
    fi
done

echo ""
echo "These files have non-descriptive names that Infuse can't match to metadata."
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    echo "Dry run complete. Run without --dry-run to process files."
    exit 0
fi

read -p "Do you want to attempt automatic renaming? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "User cancelled"
    exit 0
fi

echo ""
echo "📥 Downloading files for renaming..."
echo "(This may take a while depending on file sizes)"
echo ""

# Download files one at a time to conserve space
rclone lsf "$CLOUD_SOURCE" --files-only 2>/dev/null | while read -r file; do
    # Only process poorly-named files
    if [[ "$file" =~ ^[0-9a-f]{20,}.*\.mp4$ ]] || \
       [[ "$file" =~ ^[0-9]+_(shd|hd|h).*\.mp4$ ]] || \
       [[ "$file" =~ ^master\.m3u8.*\.mp4$ ]]; then
        
        log "Processing: $file"
        
        # Download
        rclone copy "$CLOUD_SOURCE/$file" "$WORK_DIR/" --progress
        
        local_file="$WORK_DIR/$file"
        
        if [[ -f "$local_file" ]]; then
            # Try FileBot rename
            temp_out=$(mktemp -d)
            
            if filebot -rename "$local_file" \
                --db TheMovieDB \
                --format "{n} ({y})" \
                --output "$temp_out" \
                -non-strict \
                --action copy 2>&1 | tee -a "$LOG_FILE"; then
                
                renamed=$(find "$temp_out" -type f -name "*.mp4" | head -1)
                
                if [[ -n "$renamed" && -f "$renamed" ]]; then
                    new_name=$(basename "$renamed")
                    log "✓ Identified as: $new_name"
                    
                    # Upload renamed file
                    rclone copy "$renamed" "$CLOUD_DEST/" --progress
                    
                    # Delete original from cloud
                    rclone delete "$CLOUD_SOURCE/$file"
                    
                    log "✓ Replaced on cloud"
                else
                    log "✗ FileBot couldn't identify: $file"
                fi
            fi
            
            # Cleanup
            rm -rf "$temp_out"
            rm -f "$local_file"
        fi
    fi
done

log "=== Bulk Rename Complete ==="
echo ""
echo "✅ Done! Check ~/Library/Logs/bulk-rename.log for details."
echo "💡 Files that couldn't be identified are still in cloud with original names."
