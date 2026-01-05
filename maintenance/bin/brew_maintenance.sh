#!/usr/bin/env bash

# Self-contained Homebrew maintenance script with comprehensive cask updates
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

# Basic logging
log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [brew_maintenance] $*" | tee -a "$LOG_DIR/brew_maintenance.log"
}

log_warn() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [WARNING] [brew_maintenance] $*" | tee -a "$LOG_DIR/brew_maintenance.log"
}

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE" 2>/dev/null || true
fi

log_info "Homebrew maintenance started"

# Check if Homebrew is installed
if ! command -v brew >/dev/null 2>&1; then
    log_warn "Homebrew not found, skipping maintenance"
    exit 0
fi

UPDATED_PACKAGES=0
UPDATED_CASKS=0

# Update Homebrew
log_info "Updating Homebrew..."
if brew update 2>&1 | tee -a "$LOG_DIR/brew_maintenance.log"; then
    log_info "Homebrew updated successfully"
else
    log_warn "Homebrew update had issues, continuing anyway"
fi

# Check system health
log_info "Running brew doctor..."
BREW_DOCTOR_OUTPUT=$(brew doctor 2>&1 || true)
if echo "${BREW_DOCTOR_OUTPUT}" | grep -q "Your system is ready to brew"; then
    log_info "brew doctor: System ready to brew"
else
    log_warn "brew doctor reported issues:"
    log_warn "${BREW_DOCTOR_OUTPUT}"
fi

# Optimization: Pre-fetch all outdated info if jq is available
# This consolidates 3 slow calls (outdated, outdated --greedy, outdated --greedy-latest) into 1
OPTI_FETCH_DONE=0
OUTDATED_PACKAGES_LIST=""
OUTDATED_CASKS_LIST=""
LATEST_CASKS_LIST=""

if command -v jq >/dev/null 2>&1; then
    log_info "Checking for outdated packages and casks (optimized)..."
    # --greedy includes both auto_updates and latest casks
    ALL_OUTDATED_JSON=$(brew outdated --json=v2 --greedy 2>/dev/null || true)

    if [[ -n "$ALL_OUTDATED_JSON" ]]; then
        # Parse formulae (packages)
        OUTDATED_PACKAGES_LIST=$(echo "$ALL_OUTDATED_JSON" | jq -r '.formulae[].name' 2>/dev/null || true)

        # Parse all outdated casks (equivalent to --greedy)
        OUTDATED_CASKS_LIST=$(echo "$ALL_OUTDATED_JSON" | jq -r '.casks[].name' 2>/dev/null || true)

        # Parse casks that are outdated because they are :latest version
        # We assume they have current_version == "latest"
        LATEST_CASKS_LIST=$(echo "$ALL_OUTDATED_JSON" | jq -r '.casks[] | select(.current_version == "latest") | .name' 2>/dev/null || true)

        OPTI_FETCH_DONE=1
        log_info "Optimized fetch complete."
    fi
fi

# Check what's outdated (packages)
# Optimization: Capture output once to avoid double execution of slow 'brew outdated'
if [[ "$OPTI_FETCH_DONE" -eq 0 ]]; then
    log_info "Checking for outdated packages..."
    OUTDATED_PACKAGES_LIST=$(brew outdated 2>/dev/null || true)
fi

if [[ -n "$OUTDATED_PACKAGES_LIST" ]]; then
    OUTDATED_PACKAGES=$(echo "$OUTDATED_PACKAGES_LIST" | wc -l | tr -d ' ')
else
    OUTDATED_PACKAGES=0
fi

if (( OUTDATED_PACKAGES > 0 )); then
    log_info "Found ${OUTDATED_PACKAGES} outdated packages"
    echo "$OUTDATED_PACKAGES_LIST" | tee -a "$LOG_DIR/brew_maintenance.log"
    
    # Upgrade packages
    log_info "Upgrading packages..."
    if brew upgrade 2>&1 | tee -a "$LOG_DIR/brew_maintenance.log"; then
        UPDATED_PACKAGES=$OUTDATED_PACKAGES
        log_info "Successfully upgraded ${UPDATED_PACKAGES} packages"
    else
        log_warn "Package upgrade encountered issues"
    fi
else
    log_info "All packages are up to date"
fi

# Check what's outdated (casks) - including auto-updating apps
if [[ "$OPTI_FETCH_DONE" -eq 0 ]]; then
    log_info "Checking for outdated casks (including auto-updating apps)..."
    OUTDATED_CASKS_LIST=$(brew outdated --cask --greedy 2>/dev/null || true)
fi

if [[ -n "$OUTDATED_CASKS_LIST" ]]; then
    OUTDATED_CASKS=$(echo "$OUTDATED_CASKS_LIST" | wc -l | tr -d ' ')
else
    OUTDATED_CASKS=0
fi

if (( OUTDATED_CASKS > 0 )); then
    log_info "Found ${OUTDATED_CASKS} outdated casks"
    echo "$OUTDATED_CASKS_LIST" | tee -a "$LOG_DIR/brew_maintenance.log"
    
    # Upgrade casks with comprehensive flags
    log_info "Upgrading casks (including auto-updating apps)..."
    
    # First, try upgrading with --greedy-auto-updates (like you used manually)
    if brew upgrade --cask --greedy-auto-updates 2>&1 | tee -a "$LOG_DIR/brew_maintenance.log"; then
        log_info "Successfully upgraded casks with auto-updates"
        UPDATED_CASKS=$OUTDATED_CASKS
    else
        log_warn "Cask upgrade with --greedy-auto-updates had issues, trying basic --greedy"
        
        # Fallback to basic greedy upgrade
        if brew upgrade --cask --greedy 2>&1 | tee -a "$LOG_DIR/brew_maintenance.log"; then
            log_info "Successfully upgraded casks with basic --greedy"
            UPDATED_CASKS=$OUTDATED_CASKS
            # FLAG: We used full greedy, so no need to check latest again.
            FULL_GREEDY_USED=1
        else
            log_warn "Cask upgrade encountered issues"
        fi
    fi
else
    log_info "All casks are up to date"
fi

# Check for casks that need --greedy-latest flag
# Performance Optimization: Skip this check if:
# 1. No casks were outdated even with --greedy (superset of --greedy-latest)
# 2. We already performed a full --greedy upgrade (which includes :latest)
if (( OUTDATED_CASKS == 0 )); then
    log_info "Skipping :latest check (no outdated casks found with --greedy)"
    LATEST_CASKS=0
elif [[ "${FULL_GREEDY_USED:-0}" == "1" ]]; then
    log_info "Skipping :latest check (already upgraded via full --greedy)"
    LATEST_CASKS=0
else
    if [[ "$OPTI_FETCH_DONE" -eq 0 ]]; then
        log_info "Checking for casks with version :latest..."
        LATEST_CASKS_LIST=$(brew outdated --cask --greedy-latest 2>/dev/null || true)
    fi

    if [[ -n "$LATEST_CASKS_LIST" ]]; then
        LATEST_CASKS=$(echo "$LATEST_CASKS_LIST" | wc -l | tr -d ' ')
    else
        LATEST_CASKS=0
    fi
fi

if (( LATEST_CASKS > 0 )); then
    log_info "Found ${LATEST_CASKS} casks with version :latest that can be upgraded"
    echo "$LATEST_CASKS_LIST" | tee -a "$LOG_DIR/brew_maintenance.log"
    
    # Optionally upgrade these (they may be more frequent updates)
    if [[ "${UPDATE_GREEDY_LATEST:-0}" == "1" ]]; then
        log_info "Upgrading casks with version :latest..."
        if brew upgrade --cask --greedy-latest 2>&1 | tee -a "$LOG_DIR/brew_maintenance.log"; then
            log_info "Successfully upgraded casks with version :latest"
            UPDATED_CASKS=$((UPDATED_CASKS + LATEST_CASKS))
        else
            log_warn "Greedy-latest cask upgrade had issues"
        fi
    else
        log_info "Skipping :latest casks (set UPDATE_GREEDY_LATEST=1 to enable)"
    fi
fi

# Cleanup
log_info "Cleaning up Homebrew cache and old versions..."
if brew autoremove 2>&1 | tee -a "$LOG_DIR/brew_maintenance.log"; then
    log_info "Successfully removed unused dependencies"
else
    log_warn "Autoremove had issues"
fi

if brew cleanup --prune=${BREW_CLEAN_PRUNE_DAYS:-30} 2>&1 | tee -a "$LOG_DIR/brew_maintenance.log"; then
    log_info "Successfully cleaned up old versions (older than ${BREW_CLEAN_PRUNE_DAYS:-30} days)"
else
    log_warn "Cleanup had issues"
fi

# Check for failed brew services and restart them
log_info "Checking Homebrew services..."
if brew services list >/dev/null 2>&1; then
    FAILED_SERVICES=$(brew services list 2>/dev/null | awk 'NR>1 && $2!="started" && $2!="none" {print $1" "$2}' || true)
    if [[ -n "${FAILED_SERVICES}" ]]; then
        log_warn "Found failed brew services:"
        echo "${FAILED_SERVICES}" | tee -a "$LOG_DIR/brew_maintenance.log"
        
        echo "${FAILED_SERVICES}" | while IFS= read -r line; do
            svc_name=$(echo "$line" | awk '{print $1}')
            log_info "Attempting to restart service: $svc_name"
            if brew services restart "$svc_name" 2>&1 | tee -a "$LOG_DIR/brew_maintenance.log"; then
                log_info "Successfully restarted $svc_name"
            else
                log_warn "Failed to restart $svc_name"
            fi
        done
    else
        log_info "All Homebrew services are running normally"
    fi
fi

# Final status
TOTAL_UPDATES=$((UPDATED_PACKAGES + UPDATED_CASKS))
if (( TOTAL_UPDATES > 0 )); then
    STATUS_MSG="Updated ${UPDATED_PACKAGES} packages, ${UPDATED_CASKS} casks"
else
    STATUS_MSG="All packages and casks up to date"
fi

# Notification
if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"${STATUS_MSG}\" with title \"Homebrew Maintenance\"" 2>/dev/null || true
fi

log_info "Homebrew maintenance complete: ${STATUS_MSG}"
echo "Homebrew maintenance completed successfully!"