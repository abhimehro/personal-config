#!/usr/bin/env bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/common.sh"
with_lock "node_maintenance"

log_info "Node.js maintenance started"

# Verify Node.js and npm are available
require_cmd node
require_cmd npm

# Log versions
NODE_VERSION=$(node --version)
NPM_VERSION=$(npm --version)
log_info "Node.js version: $NODE_VERSION"
log_info "npm version: $NPM_VERSION"

# Update npm itself first
if [[ "${UPDATE_NODE_GLOBAL:-1}" == "1" ]]; then
    log_info "Updating npm to latest version..."
    retry 3 10 npm install -g npm@latest || log_warn "npm self-update failed"
fi

# Check for outdated global packages
log_info "Checking for outdated global packages..."
if OUTDATED=$(npm -g outdated 2>/dev/null) && [[ -n "$OUTDATED" ]]; then
    log_info "Found outdated global packages:"
    echo "$OUTDATED" | log_info
    
    if [[ "${UPDATE_NODE_GLOBAL:-1}" == "1" ]]; then
        log_info "Updating global packages..."
        retry 3 15 npm -g update || log_warn "Global package update failed"
    fi
else
    log_info "All global packages are up to date"
fi

# Verify and clean npm cache
log_info "Verifying npm cache..."
if npm cache verify 2>/dev/null; then
    log_info "npm cache is clean"
else
    log_warn "npm cache issues detected, cleaning..."
    npm cache clean --force 2>/dev/null || log_warn "Cache cleanup failed"
fi

# Optional: Clean up old node_modules in development projects
if [[ "${REPO_SEARCH_PATHS:-}" ]] && [[ "${NODE_MODULES_MAX_GB:-0}" -gt 0 ]]; then
    log_info "Scanning for large node_modules directories..."
    
    IFS=' ' read -ra SEARCH_PATHS <<< "$REPO_SEARCH_PATHS"
    for search_path in "${SEARCH_PATHS[@]}"; do
        if [[ -d "$search_path" ]]; then
            log_info "Scanning $search_path for node_modules..."
            
            while IFS= read -r -d '' node_modules_dir; do
                if [[ -d "$node_modules_dir" ]]; then
                    # Get directory size in GB
                    size_kb=$(du -sk "$node_modules_dir" 2>/dev/null | cut -f1)
                    size_gb=$((size_kb / 1024 / 1024))
                    
                    # Get last modified time in days
                    if [[ -f "$node_modules_dir/../package.json" ]]; then
                        days_old=$(find "$node_modules_dir" -maxdepth 1 -type d -mtime +${NODE_MODULES_MAX_AGE_DAYS:-90} | wc -l | tr -d ' ')
                        
                        if [[ $size_gb -gt ${NODE_MODULES_MAX_GB:-5} ]] && [[ $days_old -gt 0 ]]; then
                            project_dir=$(dirname "$node_modules_dir")
                            log_warn "Large old node_modules found: $project_dir (${size_gb}GB, ${NODE_MODULES_MAX_AGE_DAYS:-90}+ days old)"
                            
                            if [[ "${DRY_RUN:-0}" == "0" ]]; then
                                log_info "Removing old node_modules: $node_modules_dir"
                                rm -rf "$node_modules_dir" || log_warn "Failed to remove $node_modules_dir"
                            else
                                log_info "[DRY RUN] Would remove: $node_modules_dir"
                            fi
                        fi
                    fi
                fi
            done < <(find "$search_path" -name "node_modules" -type d -print0 2>/dev/null)
        fi
    done
fi

# Set up package manager toolchains if corepack is available
if command -v corepack >/dev/null 2>&1; then
    log_info "Setting up package manager toolchains with corepack..."
    
    if corepack enable 2>/dev/null; then
        log_info "Corepack enabled successfully"
        
        # Prepare yarn and pnpm
        corepack prepare yarn@stable --activate 2>/dev/null || log_warn "Failed to prepare yarn"
        corepack prepare pnpm@latest --activate 2>/dev/null || log_warn "Failed to prepare pnpm"
        
        log_info "Package manager versions:"
        yarn --version 2>/dev/null && log_info "Yarn: $(yarn --version)" || log_info "Yarn: not available"
        pnpm --version 2>/dev/null && log_info "pnpm: $(pnpm --version)" || log_info "pnpm: not available"
    else
        log_warn "Failed to enable corepack"
    fi
else
    log_info "Corepack not available (Node.js 16+ required)"
fi

# Security audit
log_info "Running npm security audit..."
if npm audit --audit-level=moderate 2>/dev/null; then
    log_info "No security vulnerabilities found"
else
    log_warn "Security vulnerabilities detected. Run 'npm audit fix' in affected projects."
fi

# Doctor check for npm configuration
log_info "Running npm doctor..."
if npm doctor 2>/dev/null; then
    log_info "npm configuration is healthy"
else
    log_warn "npm doctor found configuration issues"
fi

log_info "Node.js maintenance complete"
notify "Node.js Maintenance" "Completed - Node: $NODE_VERSION, npm: $(npm --version)"
after_success