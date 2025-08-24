#!/usr/bin/env bash
# ActiveDock/uBar Cleanup Script - Optimized Version
# Safely removes ActiveDock 2, uBar, and related applications with comprehensive cleanup

set -euo pipefail

# Configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly BACKUP_DIR="$HOME/Desktop/Dock_Cleanup_Backup_$(date +%Y%m%d_%H%M%S)"
readonly LOG_FILE="$BACKUP_DIR/cleanup.log"

# Application identifiers and names
readonly -a APP_DOMAINS=(
    "com.sergey-gerasimenko.ActiveDock-2"
    "ca.brawer.uBar"
    "ca.brawer.uBar4"
    "com.brawer.uBar"
    "com.sergey-gerasimenko.Command-Tab-Plus-2"
)

readonly -a APP_NAMES=(
    "ActiveDock 2"
    "uBar"
    "Command Tab Plus 2"
)

# Logging function
log() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

# Error handling
cleanup_on_error() {
    log "ERROR: Script failed at line $1"
    log "Partial cleanup may have occurred. Check log file: $LOG_FILE"
    exit 1
}

trap 'cleanup_on_error $LINENO' ERR

# Check if running as root (not recommended)
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log "WARNING: Running as root. This may cause permission issues."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Aborted by user"
            exit 1
        fi
    fi
}

# Create backup directory
setup_backup() {
    echo "Creating backup directory: $BACKUP_DIR"
    if ! mkdir -p "$BACKUP_DIR"; then
        echo "ERROR: Failed to create backup directory"
        exit 1
    fi
    
    # Initialize log file
    touch "$LOG_FILE"
    log "Starting cleanup process with $SCRIPT_NAME"
    log "Backup directory: $BACKUP_DIR"
}

# Backup preferences with better error handling
backup_preferences() {
    log "== Backing up preferences =="
    local backed_up=0
    
    for dom in "${APP_DOMAINS[@]}"; do
        if /usr/bin/defaults read "$dom" >/dev/null 2>&1; then
            log "Backing up preferences for: $dom"
            if /usr/bin/defaults export "$dom" "$BACKUP_DIR/$dom.plist" 2>/dev/null; then
                log "✓ Successfully backed up: $dom"
                ((backed_up++))
            else
                log "⚠ Failed to backup: $dom (but preferences exist)"
            fi
        else
            log "• No preferences found for: $dom"
        fi
    done
    
    log "Backed up $backed_up preference file(s)"
}

# Terminate processes with timeout and verification
terminate_processes() {
    log "== Terminating running processes =="
    
    # Function to wait for process termination
    wait_for_termination() {
        local process_name="$1"
        local max_attempts=10
        local attempt=0
        
        while pgrep -x "$process_name" >/dev/null 2>&1 && [[ $attempt -lt $max_attempts ]]; do
            sleep 1
            ((attempt++))
        done
        
        if pgrep -x "$process_name" >/dev/null 2>&1; then
            log "⚠ Force killing: $process_name"
            pkill -9 -x "$process_name" >/dev/null 2>&1 || true
            sleep 2
        fi
    }
    
    # Gracefully quit applications via AppleScript
    for app in "${APP_NAMES[@]}"; do
        if pgrep -x "$app" >/dev/null 2>&1; then
            log "Attempting to quit: $app"
            /usr/bin/osascript -e "tell application \"$app\" to quit" >/dev/null 2>&1 || true
            wait_for_termination "$app"
            
            if ! pgrep -x "$app" >/dev/null 2>&1; then
                log "✓ Successfully terminated: $app"
            else
                log "⚠ Failed to terminate: $app"
            fi
        else
            log "• $app not running"
        fi
    done
}

# Comprehensive file cleanup
cleanup_files() {
    log "== Removing application files =="
    local removed_count=0
    
    # Define cleanup paths
    local -a cleanup_paths=(
        # Application Support
        "$HOME/Library/Application Support/ActiveDock 2"
        "$HOME/Library/Application Support/uBar"
        
        # Caches
        "$HOME/Library/Caches/com.sergey-gerasimenko.ActiveDock-2"
        "$HOME/Library/Caches/ca.brawer.uBar"
        "$HOME/Library/Caches/ca.brawer.uBar4"
        "$HOME/Library/Caches/com.brawer.uBar"
        
        # Preferences
        "$HOME/Library/Preferences/com.sergey-gerasimenko.ActiveDock-2.plist"
        "$HOME/Library/Preferences/ca.brawer.uBar.plist"
        "$HOME/Library/Preferences/ca.brawer.uBar4.plist"
        "$HOME/Library/Preferences/com.brawer.uBar.plist"
        "$HOME/Library/Preferences/com.sergey-gerasimenko.Command-Tab-Plus-2.plist"
        
        # Containers
        "$HOME/Library/Containers/com.sergey-gerasimenko.ActiveDock-2"
        "$HOME/Library/Containers/ca.brawer.uBar"
        "$HOME/Library/Containers/ca.brawer.uBar4"
        "$HOME/Library/Containers/com.brawer.uBar"
        
        # Group Containers (modern macOS)
        "$HOME/Library/Group Containers/group.com.sergey-gerasimenko.ActiveDock-2"
        "$HOME/Library/Group Containers/group.ca.brawer.uBar"
        
        # Saved Application State
        "$HOME/Library/Saved Application State/com.sergey-gerasimenko.ActiveDock-2.savedState"
        "$HOME/Library/Saved Application State/ca.brawer.uBar.savedState"
        "$HOME/Library/Saved Application State/ca.brawer.uBar4.savedState"
        
        # LaunchAgents
        "$HOME/Library/LaunchAgents/com.sergey-gerasimenko.ActiveDock-2.plist"
        "$HOME/Library/LaunchAgents/ca.brawer.uBar.plist"
        "$HOME/Library/LaunchAgents/ca.brawer.uBar4.plist"
        
        # Logs
        "$HOME/Library/Logs/ActiveDock 2"
        "$HOME/Library/Logs/uBar"
        
        # Crash Reports
        "$HOME/Library/Logs/DiagnosticReports/ActiveDock*"
        "$HOME/Library/Logs/DiagnosticReports/uBar*"
    )
    
    # Remove files and directories
    for path in "${cleanup_paths[@]}"; do
        if [[ -e "$path" ]]; then
            log "Removing: $path"
            if rm -rf "$path" 2>/dev/null; then
                log "✓ Removed: $path"
                ((removed_count++))
            else
                log "⚠ Failed to remove: $path"
            fi
        fi
    done
    
    # Clean up using wildcards (more comprehensive)
    local -a wildcard_paths=(
        "$HOME/Library/Caches/ca.brawer.uBar"*
        "$HOME/Library/Containers/ca.brawer.uBar"*
        "$HOME/Library/LaunchAgents/ca.brawer.uBar"*
        "$HOME/Library/LaunchAgents/com.sergey-gerasimenko.ActiveDock"*
    )
    
    for pattern in "${wildcard_paths[@]}"; do
        for path in $pattern; do
            if [[ -e "$path" ]]; then
                log "Removing (wildcard): $path"
                if rm -rf "$path" 2>/dev/null; then
                    log "✓ Removed: $path"
                    ((removed_count++))
                else
                    log "⚠ Failed to remove: $path"
                fi
            fi
        done
    done
    
    log "Removed $removed_count file(s)/directory(ies)"
}

# Reset Dock with verification
reset_dock() {
    log "== Resetting Apple Dock =="
    
    # Backup current Dock preferences
    if /usr/bin/defaults read com.apple.dock >/dev/null 2>&1; then
        log "Backing up current Dock preferences"
        /usr/bin/defaults export com.apple.dock "$BACKUP_DIR/com.apple.dock.plist" 2>/dev/null || true
    fi
    
    # Reset Dock preferences
    log "Clearing Dock preferences"
    /usr/bin/defaults delete com.apple.dock >/dev/null 2>&1 || true
    
    # Apply recommended settings
    log "Applying recommended Dock settings"
    /usr/bin/defaults write com.apple.dock show-recents -bool false
    /usr/bin/defaults write com.apple.dock autohide -bool true
    /usr/bin/defaults write com.apple.dock tilesize -int 48
    /usr/bin/defaults write com.apple.dock magnification -bool false
    
    # Restart Dock
    log "Restarting Dock"
    /usr/bin/killall Dock 2>/dev/null || true
    
    # Wait for Dock to restart
    sleep 3
    if pgrep -x "Dock" >/dev/null 2>&1; then
        log "✓ Dock restarted successfully"
    else
        log "⚠ Dock restart verification failed"
    fi
}

# Final cleanup and summary
generate_summary() {
    log "== Cleanup Summary =="
    log "Backup location: $BACKUP_DIR"
    log "Log file: $LOG_FILE"
    
    # Check if any target processes are still running
    local still_running=()
    for app in "${APP_NAMES[@]}"; do
        if pgrep -x "$app" >/dev/null 2>&1; then
            still_running+=("$app")
        fi
    done
    
    if [[ ${#still_running[@]} -gt 0 ]]; then
        log "⚠ WARNING: The following processes are still running:"
        for app in "${still_running[@]}"; do
            log "  - $app"
        done
        log "You may need to restart your Mac for complete cleanup."
    else
        log "✓ All target processes successfully terminated"
    fi
    
    # Display file count in backup
    local backup_files=$(find "$BACKUP_DIR" -name "*.plist" | wc -l | tr -d ' ')
    log "✓ $backup_files preference file(s) backed up"
    
    log "== Cleanup completed successfully =="
    echo
    echo "Summary:"
    echo "• Backup directory created: $BACKUP_DIR"
    echo "• Log file available: $LOG_FILE"
    echo "• Dock has been reset to defaults"
    echo "• You may want to restart your Mac to ensure complete cleanup"
}

# Main execution
main() {
    echo "ActiveDock/uBar Cleanup Script - Optimized Version"
    echo "=================================================="
    echo
    
    check_permissions
    setup_backup
    backup_preferences
    terminate_processes
    cleanup_files
    reset_dock
    generate_summary
}

# Run main function
main "$@"