#!/usr/bin/env bash
#
# Verify All Configs - Symlink Verification Script
# Verifies all configuration symlinks are correctly established
#
# Usage: ./scripts/verify_all_configs.sh

set -Eeuo pipefail

# Repository root (absolute path)
REPO_ROOT="${REPO_ROOT:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}"

# Colors for output
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log()      { printf '%b\n' "${BLUE}ℹ️  [INFO]${NC}  $*"; }
success()  { printf '%b\n' "${GREEN}✅ [OK]${NC}    $*"; }
warn()     { printf '%b\n' "${YELLOW}⚠️  [WARN]${NC}  $*"; }
error()    { printf '%b\n' "${RED}❌ [ERR]${NC}   $*" >&2; }
hr()       { printf '%b\n' "${BLUE}────────────────────────────────────────────────────────────${NC}"; }
header()   { printf '\n%b\n' "${BOLD}${BLUE}🔷 $*${NC}"; hr; }

fail=0

# Performance Optimization: Detect stat command format once
# Avoids forking a failing process on every check for cross-platform support
if stat -f %Mp%Lp . >/dev/null 2>&1; then
    # BSD/macOS stat
    get_perms() {
        stat -f %Mp%Lp "$1" 2>/dev/null || echo ""
    }
else
    # GNU/Linux stat
    get_perms() {
        stat -c %a "$1" 2>/dev/null || echo ""
    }
fi

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

    local actual_target
    actual_target="$(readlink "$link")"
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
        actual_perms=$(get_perms "$expected_target")

        # Optimize: Handle empty/missing permissions safely
        if [[ -z "$actual_perms" ]]; then
             warn "$name target file permissions could not be determined"
             return 0
        fi

        # Normalize permissions (remove leading zeros for comparison)
        # Handle empty output case to prevent arithmetic error
        if [[ -z "$actual_perms" ]]; then
            actual_perms="0"
        fi
        actual_perms_normalized=$((10#$actual_perms))
        expected_perms_normalized=$((10#$expected_perms))

        if [[ "$actual_perms_normalized" != "$expected_perms_normalized" ]]; then
            warn "$name target file permissions are $actual_perms (expected $expected_perms)"
            # Try to fix permissions
            log "Attempting to fix permissions on target file..."
            # shellcheck disable=SC2015
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

    local actual_target
    actual_target="$(readlink "$link")"
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

header "Verifying Configuration Symlinks"

# 1. SSH Configuration
header "SSH Configuration"
verify_file_link "$HOME/.ssh/config" "$REPO_ROOT/configs/ssh/config" "$HOME/.ssh/config" "600"
verify_file_link "$HOME/.ssh/agent.toml" "$REPO_ROOT/configs/ssh/agent.toml" "$HOME/.ssh/agent.toml" "600"

# Check SSH control directory
if [[ -d "$HOME/.ssh/control" ]]; then
    perms=$(get_perms "$HOME/.ssh/control")

    if [[ -n "$perms" ]]; then
        perms_normalized=$((10#$perms))
        if [[ "$perms_normalized" -eq 700 ]]; then
            success "$HOME/.ssh/control exists with correct permissions (700)"
        else
            warn "$HOME/.ssh/control permissions are $perms (expected 700)"
        fi
    else
        warn "$HOME/.ssh/control permissions could not be determined"
    fi
else
    warn "$HOME/.ssh/control directory does not exist"
fi

# 2. Fish Shell Configuration
header "Fish Shell Configuration"
verify_dir_link "$HOME/.config/fish" "$REPO_ROOT/configs/.config/fish" "$HOME/.config/fish"

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

    # Check Hydro prompt is listed (installed/updated via Fisher using fish_plugins)
    hydro_listed=0
    if [[ -f "$HOME/.config/fish/fish_plugins" ]]; then
        if grep -q "^jorgebucaran/hydro$" "$HOME/.config/fish/fish_plugins" 2>/dev/null; then
            success "Hydro prompt listed in fish_plugins"
            hydro_listed=1
        else
            warn "Hydro prompt not listed in fish_plugins (expected jorgebucaran/hydro)"
        fi
    fi

    # Prompt conflict checks:
    # - Hydro installs its own `fish_prompt.fish`, so the file existing is expected when Hydro is installed.
    # - We only warn if `fish_prompt.fish` exists and does NOT look like Hydro's implementation.
    if [[ -f "$HOME/.config/fish/functions/fish_prompt.fish" ]]; then
        if grep -Eq '^[[:space:]]*function[[:space:]]+fish_prompt([[:space:]]|$).*--description[[:space:]]+Hydro([[:space:]]|$)' \
            "$HOME/.config/fish/functions/fish_prompt.fish" 2>/dev/null; then
            success "Hydro fish_prompt.fish detected"
        else
            warn "Non-Hydro fish_prompt.fish detected (will override Hydro). Consider renaming to fish_prompt.fish.backup"
        fi
    else
        if [[ "$hydro_listed" -eq 1 ]]; then
            warn "Hydro is listed but not installed yet. Run: ./scripts/bootstrap_fish_plugins.sh (or: fish -lc 'fisher update')"
        fi
    fi

    # Hydro doesn't ship a right prompt file by default; a `fish_right_prompt.fish` is likely user-defined.
    if [[ -f "$HOME/.config/fish/functions/fish_right_prompt.fish" ]]; then
        log "Custom fish_right_prompt.fish detected (right-side prompt). If undesired, consider renaming to fish_right_prompt.fish.backup"
    fi
fi

# 3. Cursor Configuration
header "Cursor IDE Configuration"
verify_dir_link "$HOME/.cursor" "$REPO_ROOT/.cursor" "$HOME/.cursor"

# 4. VS Code Configuration
header "VS Code Configuration"
verify_dir_link "$HOME/.vscode" "$REPO_ROOT/.vscode" "$HOME/.vscode"

# 5. Git Configuration (if exists)
header "Git Configuration"
if [[ -f "$REPO_ROOT/configs/.gitconfig" ]]; then
    verify_file_link "$HOME/.gitconfig" "$REPO_ROOT/configs/.gitconfig" "$HOME/.gitconfig"
else
    log "No .gitconfig in repository (skipping)"
fi

# 6. Local Configuration (if exists)
header "Local Configuration"
if [[ -d "$REPO_ROOT/configs/.local" ]]; then
    verify_dir_link "$HOME/.local" "$REPO_ROOT/configs/.local" "$HOME/.local"
else
    log "No .local directory in repository (skipping)"
fi

echo
if [[ $fail -eq 0 ]]; then
    success "All configuration symlinks verified successfully!"
    hr
    exit 0
else
    error "Some configuration symlinks failed verification"
    hr
    printf '\n%b\n' "${BOLD}👉 To fix issues, run:${NC}"
    printf '%b\n' "   ${CYAN}./scripts/sync_all_configs.sh${NC}"
    exit 1
fi
