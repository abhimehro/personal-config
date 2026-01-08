#!/usr/bin/env bash
#
# Compare Shell Configs - Audit tool for Fish/Zsh/Bash divergence
# Identifies differences between local configs and repository versions
# Extracts portable enhancements for cross-shell porting
#
# Usage: ./scripts/compare_shell_configs.sh [--extract-enhancements]

set -Eeuo pipefail

# Repository root (absolute path)
REPO_ROOT="${REPO_ROOT:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log()      { printf '%b\n' "${BLUE}[INFO]${NC} $*"; }
success()  { printf '%b\n' "${GREEN}[OK]${NC} $*"; }
warn()     { printf '%b\n' "${YELLOW}[WARN]${NC} $*"; }
error()    { printf '%b\n' "${RED}[ERROR]${NC} $*" >&2; }
header()   { printf '%b\n' "${CYAN}=== $* ===${NC}"; }

EXTRACT_ENHANCEMENTS=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --extract-enhancements|-e)
            EXTRACT_ENHANCEMENTS=1
            shift
            ;;
        -h|--help)
            cat <<'EOF'
Usage: compare_shell_configs.sh [OPTIONS]

Compare local shell configurations against repository versions.

Options:
  -e, --extract-enhancements  Extract portable patterns for Fish porting
  -h, --help                  Show this help message

Examples:
  ./scripts/compare_shell_configs.sh
  ./scripts/compare_shell_configs.sh --extract-enhancements
EOF
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo ""
header "Shell Configuration Audit"
echo ""
log "Repository: $REPO_ROOT"
log "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Track overall status
has_differences=0

# =============================================================================
# Fish Shell Comparison
# =============================================================================
header "Fish Shell Configuration"

REPO_FISH_CONFIG="$REPO_ROOT/configs/.config/fish/config.fish"
LOCAL_FISH_CONFIG="$HOME/.config/fish/config.fish"

if [[ -f "$REPO_FISH_CONFIG" ]]; then
    success "Repository Fish config exists: $REPO_FISH_CONFIG"
else
    warn "Repository Fish config not found: $REPO_FISH_CONFIG"
fi

if [[ -f "$LOCAL_FISH_CONFIG" ]]; then
    success "Local Fish config exists: $LOCAL_FISH_CONFIG"
    
    # Check if it's a symlink to repo
    if [[ -L "$LOCAL_FISH_CONFIG" ]]; then
        link_target=$(readlink "$LOCAL_FISH_CONFIG")
        if [[ "$link_target" == "$REPO_FISH_CONFIG" ]]; then
            success "Local Fish config is symlinked to repository (in sync)"
        else
            warn "Local Fish config is symlinked but to different location: $link_target"
            has_differences=1
        fi
    else
        # Compare contents
        if [[ -f "$REPO_FISH_CONFIG" ]]; then
            if diff -q "$REPO_FISH_CONFIG" "$LOCAL_FISH_CONFIG" >/dev/null 2>&1; then
                success "Fish configs are identical (but not symlinked)"
            else
                warn "Fish configs differ - showing diff:"
                echo ""
                diff -u "$REPO_FISH_CONFIG" "$LOCAL_FISH_CONFIG" || true
                echo ""
                has_differences=1
            fi
        fi
    fi
else
    warn "Local Fish config not found: $LOCAL_FISH_CONFIG"
fi

echo ""

# =============================================================================
# Zsh Shell Comparison
# =============================================================================
header "Zsh Shell Configuration"

REPO_ZSHRC="$REPO_ROOT/configs/.zshrc"
LOCAL_ZSHRC="$HOME/.zshrc"

if [[ -f "$REPO_ZSHRC" ]]; then
    success "Repository Zsh config exists: $REPO_ZSHRC"
else
    log "Repository Zsh config not found (not yet tracked): $REPO_ZSHRC"
fi

if [[ -f "$LOCAL_ZSHRC" ]]; then
    success "Local Zsh config exists: $LOCAL_ZSHRC"
    
    # Show contents summary
    line_count=$(wc -l < "$LOCAL_ZSHRC" | tr -d ' ')
    log "Local .zshrc has $line_count lines"
    
    # Check if it's a symlink
    if [[ -L "$LOCAL_ZSHRC" ]]; then
        link_target=$(readlink "$LOCAL_ZSHRC")
        log "Local .zshrc is symlinked to: $link_target"
    fi
    
    # Compare if repo version exists
    if [[ -f "$REPO_ZSHRC" ]]; then
        if diff -q "$REPO_ZSHRC" "$LOCAL_ZSHRC" >/dev/null 2>&1; then
            success "Zsh configs are identical"
        else
            warn "Zsh configs differ - showing diff:"
            echo ""
            diff -u "$REPO_ZSHRC" "$LOCAL_ZSHRC" || true
            echo ""
            has_differences=1
        fi
    else
        log "No repo version to compare - local is source of truth"
        echo ""
        log "Current local .zshrc contents:"
        echo "---"
        cat "$LOCAL_ZSHRC"
        echo "---"
    fi
else
    log "Local Zsh config not found: $LOCAL_ZSHRC"
fi

echo ""

# =============================================================================
# Bash Shell Comparison
# =============================================================================
header "Bash Shell Configuration"

REPO_BASHRC="$REPO_ROOT/configs/.bashrc"
LOCAL_BASHRC="$HOME/.bashrc"

if [[ -f "$REPO_BASHRC" ]]; then
    success "Repository Bash config exists: $REPO_BASHRC"
else
    log "Repository Bash config not found (not tracked): $REPO_BASHRC"
fi

if [[ -f "$LOCAL_BASHRC" ]]; then
    success "Local Bash config exists: $LOCAL_BASHRC"
    line_count=$(wc -l < "$LOCAL_BASHRC" | tr -d ' ')
    log "Local .bashrc has $line_count lines"
else
    log "Local Bash config not found: $LOCAL_BASHRC"
fi

echo ""

# =============================================================================
# Enhancement Extraction (Optional)
# =============================================================================
if [[ $EXTRACT_ENHANCEMENTS -eq 1 ]]; then
    header "Portable Enhancement Extraction"
    
    # Securely create temporary file
    ENHANCEMENTS_FILE=$(mktemp "${TMPDIR:-/tmp}/shell-enhancements.XXXXXX")
    
    log "Extracting portable patterns from local shell configs..."
    echo ""
    
    {
        echo "# Shell Enhancement Candidates for Fish Porting"
        echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "# Source: Local shell configurations"
        echo ""
        
        # Extract from Zsh
        if [[ -f "$LOCAL_ZSHRC" ]]; then
            echo "## From ~/.zshrc"
            echo ""
            
            # PATH modifications
            echo "### PATH Modifications"
            grep -E '^export PATH=|^PATH=' "$LOCAL_ZSHRC" 2>/dev/null || echo "# (none found)"
            echo ""
            
            # Environment variables
            echo "### Environment Variables"
            grep -E '^export [A-Z_]+=' "$LOCAL_ZSHRC" 2>/dev/null | grep -v '^export PATH' || echo "# (none found)"
            echo ""
            
            # Tool initializations (brew, conda, pyenv, rbenv, nvm, etc.)
            echo "### Tool Initializations"
            grep -E '(brew|conda|pyenv|rbenv|nvm|chruby|eval|source)' "$LOCAL_ZSHRC" 2>/dev/null || echo "# (none found)"
            echo ""
            
            # Aliases
            echo "### Aliases"
            grep -E '^alias ' "$LOCAL_ZSHRC" 2>/dev/null || echo "# (none found)"
            echo ""
        fi
        
        # Extract from Bash
        if [[ -f "$LOCAL_BASHRC" ]]; then
            echo "## From ~/.bashrc"
            echo ""
            
            # PATH modifications
            echo "### PATH Modifications"
            grep -E '^export PATH=|^PATH=' "$LOCAL_BASHRC" 2>/dev/null || echo "# (none found)"
            echo ""
            
            # Environment variables
            echo "### Environment Variables"
            grep -E '^export [A-Z_]+=' "$LOCAL_BASHRC" 2>/dev/null | grep -v '^export PATH' || echo "# (none found)"
            echo ""
            
            # Tool initializations
            echo "### Tool Initializations"
            grep -E '(brew|conda|pyenv|rbenv|nvm|chruby|eval|source)' "$LOCAL_BASHRC" 2>/dev/null || echo "# (none found)"
            echo ""
        fi
        
        echo ""
        echo "# Fish Porting Reference"
        echo "# ======================"
        echo "#"
        echo "# Zsh/Bash Pattern          | Fish Equivalent"
        echo "# --------------------------|----------------------------------"
        echo "# export PATH=\"\$PATH:dir\"   | fish_add_path --global --append dir"
        echo "# export VAR=value          | set -gx VAR value"
        echo "# alias foo='bar'           | alias foo='bar' (same)"
        echo "# eval \"\$(tool init)\"       | tool init fish | source"
        echo "# source file               | source file (same)"
        echo "# if [ condition ]; then    | if test condition"
        echo "#"
        
    } > "$ENHANCEMENTS_FILE"
    
    success "Enhancements extracted to: $ENHANCEMENTS_FILE"
    echo ""
    log "Contents:"
    echo ""
    cat "$ENHANCEMENTS_FILE"
fi

echo ""

# =============================================================================
# Summary
# =============================================================================
header "Summary"

if [[ $has_differences -eq 0 ]]; then
    success "All shell configurations are in sync!"
else
    warn "Some configurations have differences - review above"
fi

echo ""
log "Recommendations:"
echo "  1. Run ./setup.sh to sync repo configs to home directory"
echo "  2. Use ./scripts/sync_zsh_config.sh to track local Zsh changes"
echo "  3. Use --extract-enhancements to identify portable patterns"
echo ""
