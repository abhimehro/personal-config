#!/usr/bin/env bash
#
# Verify All Configs - Symlink Verification Script
# Verifies all configuration symlinks are correctly established
#
# Usage: ./scripts/verify_all_configs.sh

set -Eeuo pipefail

# Repository root (absolute path)
REPO_ROOT="$HOME/Documents/dev/personal-config"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log()      { echo -e "${BLUE}[INFO]${NC} $@"; }
success()  { echo -e "${GREEN}[OK]${NC} $@"; }
warn()     { echo -e "${YELLOW}[WARN]${NC} $@"; }
error()    { echo -e "${RED}[ERROR]${NC} $@" >&2; }

fail=0

# Verify a file symlink
verify_file_link() {
    local link="$1"
    local expected_target="$2"
    local name="$3"
    local expected_perms="${4:-}"  # Optional expected permissions

    if [[ ! -L "$link" ]]; then
        if [[ -e "$link" ]]; then
            error "$name exists but is not a symlink (it's a regular file/directory)"
            fail=1
        else
            error "$name does not exist"
            fail=1
        fi
        return 1
    fi

    local actual_target=$(readlink "$link")
    if [[ "$actual_target" != "$expected_target" ]]; then
        error "$name points to wrong location:"
        error "  Expected: $expected_target"
        error "  Actual:   $actual_target"
        fail=1
        return 1
    fi

    if [[ ! -e "$expected_target" ]]; then
        error "$name points to non-existent target: $expected_target"
        fail=1
        return 1
    fi

    # Check permissions if specified
    # For symlinks, check the target file permissions (what actually matters)
    if [[ -n "$expected_perms" ]]; then
        # Check target file permissions (not symlink permissions)
        actual_perms=$(stat -f %Mp%Lp "$expected_target" 2>/dev/null || stat -c %a "$expected_target" 2>/dev/null || echo "")
        # Normalize permissions (remove leading zeros for comparison)
        actual_perms_normalized=$((10#$actual_perms))
        expected_perms_normalized=$((10#$expected_perms))

        if [[ "$actual_perms_normalized" != "$expected_perms_normalized" ]]; then
            warn "$name target file permissions are $actual_perms (expected $expected_perms)"
            # Try to fix permissions
            log "Attempting to fix permissions on target file..."
            chmod "$expected_perms" "$expected_target" 2>/dev/null && success "Fixed permissions" || warn "Could not fix permissions (may need manual intervention)"
        else
            success "$name permissions are correct ($expected_perms)"
        fi
    fi

    success "$name -> $expected_target"
    return 0
}

# Verify a directory symlink
verify_dir_link() {
    local link="$1"
    local expected_target="$2"
    local name="$3"

    if [[ ! -L "$link" ]]; then
        if [[ -e "$link" ]]; then
            error "$name exists but is not a symlink (it's a regular file/directory)"
            fail=1
        else
            error "$name does not exist"
            fail=1
        fi
        return 1
    fi

    local actual_target=$(readlink "$link")
    if [[ "$actual_target" != "$expected_target" ]]; then
        error "$name points to wrong location:"
        error "  Expected: $expected_target"
        error "  Actual:   $actual_target"
        fail=1
        return 1
    fi

    if [[ ! -d "$expected_target" ]]; then
        error "$name points to non-existent directory: $expected_target"
        fail=1
        return 1
    fi

    success "$name -> $expected_target"
    return 0
}

echo "=========================================="
echo "Verifying Configuration Symlinks"
echo "=========================================="
echo ""

# 1. SSH Configuration
echo "== SSH Configuration =="
verify_file_link "$HOME/.ssh/config" "$REPO_ROOT/configs/ssh/config" "~/.ssh/config" "600"
verify_file_link "$HOME/.ssh/agent.toml" "$REPO_ROOT/configs/ssh/agent.toml" "~/.ssh/agent.toml" "600"

# Check SSH control directory
if [[ -d "$HOME/.ssh/control" ]]; then
    perms=$(stat -f %Mp%Lp "$HOME/.ssh/control" 2>/dev/null || stat -c %a "$HOME/.ssh/control" 2>/dev/null || echo "")
    perms_normalized=$((10#$perms))
    if [[ "$perms_normalized" -eq 700 ]]; then
        success "~/.ssh/control exists with correct permissions (700)"
    else
        warn "~/.ssh/control permissions are $perms (expected 700)"
    fi
else
    warn "~/.ssh/control directory does not exist"
fi

# 2. Fish Shell Configuration
echo ""
echo "== Fish Shell Configuration =="
verify_dir_link "$HOME/.config/fish" "$REPO_ROOT/configs/.config/fish" "~/.config/fish"

# Check if NM_ROOT is set in fish config
if [[ -f "$HOME/.config/fish/config.fish" ]]; then
    if grep -q "NM_ROOT" "$HOME/.config/fish/config.fish" 2>/dev/null; then
        success "NM_ROOT environment variable found in fish config"
    else
        warn "NM_ROOT environment variable not found in fish config"
    fi
fi

# Check if Control D functions exist
if [[ -d "$HOME/.config/fish/functions" ]]; then
    function_count=0
    for func in nm-browse nm-privacy nm-gaming nm-vpn nm-status nm-regress nm-cd-status; do
        if [[ -f "$HOME/.config/fish/functions/$func.fish" ]]; then
            ((function_count++))
        fi
    done
    if [[ $function_count -eq 7 ]]; then
        success "All Control D fish functions found ($function_count/7)"
    else
        warn "Some Control D fish functions missing ($function_count/7 found)"
    fi

    # Check for greeting function
    if [[ -f "$HOME/.config/fish/functions/fish_greeting.fish" ]]; then
        success "Custom greeting function found"
    else
        log "No custom greeting function (using default)"
    fi
fi

# 3. Cursor Configuration
echo ""
echo "== Cursor IDE Configuration =="
verify_dir_link "$HOME/.cursor" "$REPO_ROOT/.cursor" "~/.cursor"

# 4. VS Code Configuration
echo ""
echo "== VS Code Configuration =="
verify_dir_link "$HOME/.vscode" "$REPO_ROOT/.vscode" "~/.vscode"

# 5. Git Configuration (if exists)
echo ""
echo "== Git Configuration =="
if [[ -f "$REPO_ROOT/configs/.gitconfig" ]]; then
    verify_file_link "$HOME/.gitconfig" "$REPO_ROOT/configs/.gitconfig" "~/.gitconfig"
else
    log "No .gitconfig in repository (skipping)"
fi

# 6. Local Configuration (if exists)
echo ""
echo "== Local Configuration =="
if [[ -d "$REPO_ROOT/configs/.local" ]]; then
    verify_dir_link "$HOME/.local" "$REPO_ROOT/configs/.local" "~/.local"
else
    log "No .local directory in repository (skipping)"
fi

echo ""
echo "=========================================="
if [[ $fail -eq 0 ]]; then
    success "All configuration symlinks verified successfully!"
    echo "=========================================="
    exit 0
else
    error "Some configuration symlinks failed verification"
    echo "=========================================="
    echo ""
    echo "To fix issues, run: ./scripts/sync_all_configs.sh"
    exit 1
fi
