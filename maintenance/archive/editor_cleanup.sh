#!/usr/bin/env bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/common.sh"
with_lock "editor_cleanup"

log_info "Editor cache cleanup started"

total_freed=0

# Function to clean cache directory
clean_cache_dir() {
    local cache_dir="$1"
    local editor_name="$2"
    
    if [[ ! -d "$cache_dir" ]]; then
        log_info "$editor_name cache directory not found: $cache_dir"
        return 0
    fi
    
    # Get size before cleanup
    local size_before
    size_before=$(du -sk "$cache_dir" 2>/dev/null | cut -f1)
    local size_before_mb=$((size_before / 1024))
    
    log_info "$editor_name cache directory: $cache_dir (${size_before_mb}MB)"
    
    # Check if cache is larger than threshold
    local max_size_kb=$((${EDITOR_CACHE_MAX_GB:-2} * 1024 * 1024))
    local age_days=${EDITOR_CACHE_AGE_DAYS:-14}
    
    if [[ $size_before -gt $max_size_kb ]]; then
        log_warn "$editor_name cache is large (${size_before_mb}MB > ${EDITOR_CACHE_MAX_GB:-2}GB threshold)"
        
        if [[ "${DRY_RUN:-0}" == "0" ]]; then
            log_info "Cleaning $editor_name cache older than $age_days days..."
            
            # Clean files older than specified days
            find "$cache_dir" -type f -mtime +$age_days -delete 2>/dev/null || true
            
            # Remove empty directories
            find "$cache_dir" -type d -empty -delete 2>/dev/null || true
            
            # Get size after cleanup
            local size_after
            size_after=$(du -sk "$cache_dir" 2>/dev/null | cut -f1)
            local size_after_mb=$((size_after / 1024))
            local freed_kb=$((size_before - size_after))
            local freed_mb=$((freed_kb / 1024))
            
            if [[ $freed_kb -gt 0 ]]; then
                log_info "$editor_name cache cleanup freed ${freed_mb}MB (${size_before_mb}MB -> ${size_after_mb}MB)"
                total_freed=$((total_freed + freed_kb))
            else
                log_info "$editor_name cache was already clean"
            fi
        else
            log_info "[DRY RUN] Would clean $editor_name cache: $cache_dir"
        fi
    else
        log_info "$editor_name cache size is within limits (${size_before_mb}MB)"
    fi
}

# Cursor cache directories
log_info "Cleaning Cursor caches..."
clean_cache_dir "$HOME/Library/Application Support/Cursor/Cache" "Cursor"
clean_cache_dir "$HOME/Library/Application Support/Cursor/Code Cache" "Cursor Code"
clean_cache_dir "$HOME/Library/Application Support/Cursor/GPUCache" "Cursor GPU"
clean_cache_dir "$HOME/Library/Caches/Cursor" "Cursor System"

# Cursor logs cleanup
cursor_logs_dir="$HOME/Library/Application Support/Cursor/logs"
if [[ -d "$cursor_logs_dir" ]]; then
    log_info "Cleaning old Cursor logs..."
    if [[ "${DRY_RUN:-0}" == "0" ]]; then
        find "$cursor_logs_dir" -name "*.log" -mtime +7 -delete 2>/dev/null || true
        log_info "Cleaned old Cursor logs (>7 days)"
    else
        log_info "[DRY RUN] Would clean old Cursor logs"
    fi
fi

# Zed cleanup (in case it still exists from before)
zed_dirs=(
    "$HOME/Library/Application Support/Zed/Cache"
    "$HOME/Library/Application Support/Zed/Code Cache"
    "$HOME/Library/Caches/dev.zed.Zed"
)

zed_found=false
for zed_dir in "${zed_dirs[@]}"; do
    if [[ -d "$zed_dir" ]]; then
        zed_found=true
        clean_cache_dir "$zed_dir" "Zed"
    fi
done

if [[ "$zed_found" == "false" ]]; then
    log_info "No Zed cache directories found (already removed)"
fi

# VS Code cleanup (if present)
vscode_dirs=(
    "$HOME/Library/Application Support/Code/Cache"
    "$HOME/Library/Application Support/Code/CachedData"
    "$HOME/Library/Caches/com.microsoft.VSCode"
)

vscode_found=false
for vscode_dir in "${vscode_dirs[@]}"; do
    if [[ -d "$vscode_dir" ]]; then
        vscode_found=true
        clean_cache_dir "$vscode_dir" "VS Code"
    fi
done

if [[ "$vscode_found" == "true" ]]; then
    log_info "VS Code caches also cleaned"
fi

# Summary
total_freed_mb=$((total_freed / 1024))
if [[ $total_freed_mb -gt 0 ]]; then
    log_info "Editor cache cleanup freed ${total_freed_mb}MB total"
    notify "Editor Cleanup" "Completed - Freed ${total_freed_mb}MB"
else
    log_info "Editor caches were already clean"
    notify "Editor Cleanup" "Completed - Caches already clean"
fi

log_info "Editor cache cleanup complete"
after_success