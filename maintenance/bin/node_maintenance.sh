#!/usr/bin/env bash

# Self-contained Node.js maintenance script
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

# Basic logging
log_info() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [INFO] [node_maintenance] $*" | tee -a "$LOG_DIR/node_maintenance.log"
}

log_warn() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [WARNING] [node_maintenance] $*" | tee -a "$LOG_DIR/node_maintenance.log"
}

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE" 2>/dev/null || true
fi

log_info "Node.js maintenance started"

# Check if Node.js and npm are available
if ! command -v node >/dev/null 2>&1; then
    log_warn "Node.js not found, skipping Node.js maintenance"
    exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
    log_warn "npm not found, skipping Node.js maintenance"
    exit 0
fi

UPDATES_MADE=0

# Log versions
NODE_VERSION=$(node --version 2>/dev/null || echo "unknown")
NPM_VERSION=$(npm --version 2>/dev/null || echo "unknown")
log_info "Node.js version: $NODE_VERSION"
log_info "npm version: $NPM_VERSION"

# Update npm itself first
if [[ "${UPDATE_NODE_GLOBAL:-1}" == "1" ]]; then
    log_info "Updating npm to latest version..."
    
    CURRENT_NPM=$(npm --version 2>/dev/null)
    if npm install -g npm@latest 2>&1 | tee -a "$LOG_DIR/node_maintenance.log"; then
        NEW_NPM=$(npm --version 2>/dev/null)
        if [[ "$CURRENT_NPM" != "$NEW_NPM" ]]; then
            log_info "npm updated from $CURRENT_NPM to $NEW_NPM"
            UPDATES_MADE=1
        else
            log_info "npm already at latest version: $CURRENT_NPM"
        fi
    else
        log_warn "npm self-update failed"
    fi
fi

# Check for outdated global packages
log_info "Checking for outdated global packages..."
OUTDATED_OUTPUT=$(npm -g outdated --parseable 2>/dev/null || true)
if [[ -n "$OUTDATED_OUTPUT" ]]; then
    OUTDATED_COUNT=$(echo "$OUTDATED_OUTPUT" | wc -l | tr -d ' ')
    log_info "Found ${OUTDATED_COUNT} outdated global packages"
    
    # Show the outdated packages
    if npm -g outdated 2>/dev/null | tee -a "$LOG_DIR/node_maintenance.log"; then
        log_info "Outdated packages listed above"
    fi
    
    if [[ "${UPDATE_NODE_GLOBAL:-1}" == "1" ]]; then
        log_info "Updating global packages..."
        if npm -g update 2>&1 | tee -a "$LOG_DIR/node_maintenance.log"; then
            log_info "Successfully updated ${OUTDATED_COUNT} global packages"
            UPDATES_MADE=1
        else
            log_warn "Global package update encountered issues"
        fi
    else
        log_info "Global package updates disabled (UPDATE_NODE_GLOBAL=0)"
    fi
else
    log_info "All global packages are up to date"
fi

# Verify and clean npm cache
log_info "Verifying npm cache..."
if npm cache verify 2>&1 | tee -a "$LOG_DIR/node_maintenance.log"; then
    log_info "npm cache is clean"
else
    log_warn "npm cache issues detected, cleaning..."
    if npm cache clean --force 2>&1 | tee -a "$LOG_DIR/node_maintenance.log"; then
        log_info "npm cache cleaned successfully"
    else
        log_warn "Cache cleanup failed"
    fi
fi

# Check for large/old node_modules directories
if [[ -n "${REPO_SEARCH_PATHS:-}" ]] && [[ "${NODE_MODULES_MAX_GB:-0}" -gt 0 ]]; then
    log_info "Scanning for large node_modules directories..."
    
    IFS=' ' read -ra SEARCH_PATHS <<< "$REPO_SEARCH_PATHS"
    CLEANED_DIRS=0
    
    for search_path in "${SEARCH_PATHS[@]}"; do
        if [[ -d "$search_path" ]]; then
            log_info "Scanning $search_path for node_modules..."
            
            find "$search_path" -name "node_modules" -type d -print0 2>/dev/null | while IFS= read -r -d '' node_modules_dir; do
                if [[ -d "$node_modules_dir" ]] && [[ -f "$node_modules_dir/../package.json" ]]; then
                    # Get directory size in GB
                    size_kb=$(du -sk "$node_modules_dir" 2>/dev/null | cut -f1 || echo "0")
                    size_gb=$((size_kb / 1024 / 1024))
                    
                    # Check if directory is old
                    days_old=$(find "$node_modules_dir" -maxdepth 0 -type d -mtime +${NODE_MODULES_MAX_AGE_DAYS:-90} 2>/dev/null | wc -l | tr -d ' ')
                    
                    if [[ $size_gb -gt ${NODE_MODULES_MAX_GB:-5} ]] && [[ $days_old -gt 0 ]]; then
                        project_dir=$(dirname "$node_modules_dir")
                        project_name=$(basename "$project_dir")
                        
                        log_warn "Large old node_modules: $project_name (${size_gb}GB, ${NODE_MODULES_MAX_AGE_DAYS:-90}+ days old)"
                        
                        if [[ "${DRY_RUN:-0}" == "0" ]]; then
                            log_info "Removing old node_modules: $node_modules_dir"
                            if rm -rf "$node_modules_dir" 2>/dev/null; then
                                echo "$((CLEANED_DIRS + 1))" > /tmp/cleaned_dirs_$$ 2>/dev/null || true
                                log_info "Successfully removed node_modules for $project_name"
                            else
                                log_warn "Failed to remove $node_modules_dir"
                            fi
                        else
                            log_info "[DRY RUN] Would remove: $node_modules_dir"
                        fi
                    fi
                fi
            done
            
            # Get cleaned count (limited by shell scope)
            if [[ -f "/tmp/cleaned_dirs_$$" ]]; then
                CLEANED_DIRS=$(cat "/tmp/cleaned_dirs_$$" 2>/dev/null || echo "0")
                rm -f "/tmp/cleaned_dirs_$$" 2>/dev/null || true
            fi
        fi
    done
    
    if [[ $CLEANED_DIRS -gt 0 ]]; then
        log_info "Cleaned up $CLEANED_DIRS large/old node_modules directories"
    fi
fi

# Set up package manager toolchains if corepack is available
if command -v corepack >/dev/null 2>&1; then
    log_info "Checking package manager toolchains with corepack..."
    
    # Use timeout to prevent hanging
    if timeout 30 corepack enable 2>/dev/null; then
        log_info "Corepack enabled successfully"
        
        # Log available package manager versions with timeout
        if command -v yarn >/dev/null 2>&1; then
            YARN_VER=$(timeout 10 yarn --version 2>/dev/null || echo "not available")
            log_info "Yarn: $YARN_VER"
        fi
        
        if command -v pnpm >/dev/null 2>&1; then
            PNPM_VER=$(timeout 10 pnpm --version 2>/dev/null || echo "not available")
            log_info "pnpm: $PNPM_VER"
        fi
    else
        log_info "Corepack not available or timed out"
    fi
else
    log_info "Corepack not available (Node.js 16+ required)"
fi

# Security audit (non-blocking, with timeout)
log_info "Running npm security audit..."
if timeout 60 npm audit --audit-level=moderate 2>/dev/null >/dev/null; then
    log_info "No moderate+ security vulnerabilities found"
else
    log_warn "Security audit found issues or timed out. Consider running 'npm audit' manually if needed."
fi

# Final status
if [[ $UPDATES_MADE -gt 0 ]]; then
    STATUS_MSG="Updates applied - Node: $NODE_VERSION, npm: $(npm --version 2>/dev/null)"
else
    STATUS_MSG="All up to date - Node: $NODE_VERSION, npm: $(npm --version 2>/dev/null)"
fi

# Notification
if command -v terminal-notifier >/dev/null 2>&1; then
    if [[ $UPDATES_MADE -gt 0 ]]; then
        # Updates applied - provide actionable notification
        terminal-notifier -title "Node.js Maintenance" \
          -subtitle "$UPDATES_MADE update(s) applied" \
          -message "Node: $NODE_VERSION | Click for details" \
          -group "maintenance" \
          -execute "/Users/abhimehrotra/Library/Maintenance/bin/view_logs.sh node_maintenance" 2>/dev/null || true
    else
        # No updates - simple notification
        terminal-notifier -title "Node.js Maintenance" \
          -subtitle "All up to date" \
          -message "Node: $NODE_VERSION" \
          -group "maintenance" 2>/dev/null || true
    fi
elif command -v osascript >/dev/null 2>&1; then
    # Fallback to osascript
    osascript -e "display notification \"$STATUS_MSG\" with title \"Node.js Maintenance\"" 2>/dev/null || true
fi

log_info "Node.js maintenance complete: $STATUS_MSG"
echo "Node.js maintenance completed successfully!"