#!/usr/bin/env bash
#
# Sync Zsh Config - Track local Zsh configuration in the repository
# Creates backup, copies to repo, and establishes symlink
#
# Usage: ./scripts/sync_zsh_config.sh [--no-symlink] [--extract-only]

set -Eeuo pipefail

# Repository root (absolute path)
REPO_ROOT="${REPO_ROOT:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log()      { printf '%b\n' "${BLUE}[INFO]${NC} $*"; }
success()  { printf '%b\n' "${GREEN}[OK]${NC} $*"; }
warn()     { printf '%b\n' "${YELLOW}[WARN]${NC} $*"; }
error()    { printf '%b\n' "${RED}[ERROR]${NC} $*" >&2; }

# Paths
LOCAL_ZSHRC="$HOME/.zshrc"
REPO_ZSHRC="$REPO_ROOT/configs/.zshrc"
ENHANCEMENTS_FILE="$REPO_ROOT/configs/.zshrc.enhancements.md"

# Options
CREATE_SYMLINK=1
EXTRACT_ONLY=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-symlink)
            CREATE_SYMLINK=0
            shift
            ;;
        --extract-only)
            EXTRACT_ONLY=1
            shift
            ;;
        -h|--help)
            cat <<'EOF'
Usage: sync_zsh_config.sh [OPTIONS]

Track local Zsh configuration in the repository.

Options:
  --no-symlink     Copy config without creating symlink
  --extract-only   Only extract enhancements, don't modify files
  -h, --help       Show this help message

Operations:
  1. Backs up existing repo .zshrc (if any)
  2. Copies ~/.zshrc to configs/.zshrc
  3. Creates symlink ~/.zshrc -> configs/.zshrc (unless --no-symlink)
  4. Extracts portable enhancements for Fish review

Examples:
  ./scripts/sync_zsh_config.sh              # Full sync with symlink
  ./scripts/sync_zsh_config.sh --no-symlink # Copy only, no symlink
  ./scripts/sync_zsh_config.sh --extract-only # Just extract enhancements
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
echo "=========================================="
echo "Syncing Zsh Configuration to Repository"
echo "=========================================="
echo ""

# Check if local .zshrc exists
if [[ ! -f "$LOCAL_ZSHRC" ]] && [[ ! -L "$LOCAL_ZSHRC" ]]; then
    error "Local .zshrc not found: $LOCAL_ZSHRC"
    exit 1
fi

# If it's already a symlink to repo, check if it's correct
ALREADY_SYNCED=0
if [[ -L "$LOCAL_ZSHRC" ]]; then
    link_target=$(readlink "$LOCAL_ZSHRC")
    if [[ "$link_target" == "$REPO_ZSHRC" ]]; then
        success "Local .zshrc is already symlinked to repository"
        ALREADY_SYNCED=1
        if [[ $EXTRACT_ONLY -eq 0 ]]; then
            log "Nothing to do - configs are in sync"
        fi
    else
        warn "Local .zshrc is symlinked to different location: $link_target"
        log "Will update to point to repository"
    fi
fi

# =============================================================================
# Step 1: Backup existing repo .zshrc (if exists)
# =============================================================================
if [[ -f "$REPO_ZSHRC" ]] && [[ $EXTRACT_ONLY -eq 0 ]] && [[ $ALREADY_SYNCED -eq 0 ]]; then
    backup_path="${REPO_ZSHRC}.backup.$(date +%Y%m%d_%H%M%S)"
    log "Backing up existing repo .zshrc to: $backup_path"
    cp "$REPO_ZSHRC" "$backup_path"
    success "Backup created"
fi

# =============================================================================
# Step 2: Copy local .zshrc to repository
# =============================================================================
if [[ $EXTRACT_ONLY -eq 0 ]] && [[ $ALREADY_SYNCED -eq 0 ]]; then
    # Copy local .zshrc to repository (use -L to follow symlinks on macOS)
    if [[ -L "$LOCAL_ZSHRC" ]]; then
        log "Following symlink and copying content to repository"
    else
        log "Copying local .zshrc to repository"
    fi
    # -L dereferences symlinks (portable across BSD/GNU)
    cp -L "$LOCAL_ZSHRC" "$REPO_ZSHRC"
    success "Copied to: $REPO_ZSHRC"
fi

# =============================================================================
# Step 3: Create symlink (unless --no-symlink or --extract-only)
# =============================================================================
if [[ $CREATE_SYMLINK -eq 1 ]] && [[ $EXTRACT_ONLY -eq 0 ]] && [[ $ALREADY_SYNCED -eq 0 ]]; then
    # Remove existing file/symlink
    if [[ -e "$LOCAL_ZSHRC" ]] || [[ -L "$LOCAL_ZSHRC" ]]; then
        # Only backup if it's a regular file (not already a symlink)
        if [[ ! -L "$LOCAL_ZSHRC" ]]; then
            backup_path="${LOCAL_ZSHRC}.backup.$(date +%Y%m%d_%H%M%S)"
            log "Backing up local .zshrc to: $backup_path"
            mv "$LOCAL_ZSHRC" "$backup_path"
        else
            rm "$LOCAL_ZSHRC"
        fi
    fi
    
    log "Creating symlink: $LOCAL_ZSHRC -> $REPO_ZSHRC"
    ln -s "$REPO_ZSHRC" "$LOCAL_ZSHRC"
    success "Symlink created"
fi

# =============================================================================
# Step 4: Extract portable enhancements for Fish review
# =============================================================================
log "Extracting portable enhancements for Fish porting..."

# Read the config content (from repo if available, otherwise local)
if [[ -f "$REPO_ZSHRC" ]]; then
    config_source="$REPO_ZSHRC"
else
    config_source="$LOCAL_ZSHRC"
fi

{
    cat <<'HEADER'
# Zsh Configuration Enhancements - Fish Porting Guide

This file documents portable patterns from `.zshrc` that can be ported to Fish shell.

## Source Configuration

HEADER
    echo "- **Source**: \`$config_source\`"
    echo "- **Generated**: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    cat <<'INTRO'
## Porting Reference

| Zsh/Bash Pattern | Fish Equivalent |
|------------------|-----------------|
| `export PATH="$PATH:dir"` | `fish_add_path --global --append dir` |
| `export VAR=value` | `set -gx VAR value` |
| `alias foo='bar'` | `alias foo='bar'` |
| `eval "$(tool init bash)"` | `tool init fish \| source` |
| `source file` | `source file` |
| `if [ -f file ]; then` | `if test -f file` |

---

## Extracted Patterns

INTRO

    echo "### PATH Modifications"
    echo '```bash'
    grep -E '^export PATH=|^PATH=|\$PATH' "$config_source" 2>/dev/null || echo "# (none found)"
    echo '```'
    echo ""
    
    echo "**Fish equivalent:**"
    echo '```fish'
    # Parse and convert PATH additions
    while IFS= read -r line; do
        # Extract path additions like $PATH:dir or dir:$PATH
        if [[ "$line" =~ \$HOME/([^:\"\']+) ]]; then
            dir="${BASH_REMATCH[1]}"
            echo "fish_add_path --global \$HOME/$dir"
        elif [[ "$line" =~ /([^:\"\']+) ]] && [[ ! "$line" =~ \$PATH ]]; then
            echo "# Check: $line"
        fi
    done < <(grep -E 'PATH=' "$config_source" 2>/dev/null || true)
    echo '```'
    echo ""
    
    echo "### Environment Variables"
    echo '```bash'
    grep -E '^export [A-Z_]+=' "$config_source" 2>/dev/null | grep -v '^export PATH' || echo "# (none found)"
    echo '```'
    echo ""
    
    echo "### Tool Initializations"
    echo '```bash'
    grep -E '(chruby|rbenv|pyenv|nvm|conda|brew|eval|source.*/opt)' "$config_source" 2>/dev/null || echo "# (none found)"
    echo '```'
    echo ""
    
    # Specific tool conversion suggestions
    if grep -q 'chruby' "$config_source" 2>/dev/null; then
        cat <<'CHRUBY'
**Fish equivalent for chruby:**
```fish
# Add to config.fish or create functions/chruby.fish
if test -f /opt/homebrew/opt/chruby-fish/share/chruby/chruby.fish
    source /opt/homebrew/opt/chruby-fish/share/chruby/chruby.fish
end

if test -f /opt/homebrew/opt/chruby-fish/share/chruby/auto.fish
    source /opt/homebrew/opt/chruby-fish/share/chruby/auto.fish
end

# Set default Ruby version
chruby ruby-3.4.7
```

> **Note**: Install chruby-fish via `brew install chruby-fish`

CHRUBY
    fi
    
    if grep -q 'pyenv' "$config_source" 2>/dev/null; then
        cat <<'PYENV'
**Fish equivalent for pyenv:**
```fish
if type -q pyenv
    pyenv init - | source
end
```

PYENV
    fi
    
    if grep -q 'nvm' "$config_source" 2>/dev/null; then
        cat <<'NVM'
**Fish equivalent for nvm:**
```fish
# Consider using nvm.fish or fnm instead
# Install: fisher install jorgebucaran/nvm.fish
# Or: brew install fnm && fnm env --use-on-cd | source
```

NVM
    fi
    
    echo "### Aliases"
    echo '```bash'
    grep -E '^alias ' "$config_source" 2>/dev/null || echo "# (none found)"
    echo '```'
    echo ""
    
    cat <<'FOOTER'
---

## Next Steps

1. Review the patterns above
2. Add relevant Fish equivalents to `configs/.config/fish/config.fish`
3. Test with `source ~/.config/fish/config.fish` or `exec fish`
4. Commit changes to the repository

FOOTER
} > "$ENHANCEMENTS_FILE"

success "Enhancements documented in: $ENHANCEMENTS_FILE"

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""

if [[ $EXTRACT_ONLY -eq 1 ]]; then
    log "Extraction complete (no files modified)"
elif [[ $ALREADY_SYNCED -eq 1 ]]; then
    success "Zsh configuration already in sync (no changes needed)"
else
    success "Zsh configuration synced to repository"
    if [[ $CREATE_SYMLINK -eq 1 ]]; then
        success "Symlink created: ~/.zshrc -> configs/.zshrc"
    else
        log "No symlink created (--no-symlink specified)"
    fi
fi

echo ""
log "Files:"
echo "  - Repository config: $REPO_ZSHRC"
echo "  - Enhancements doc:  $ENHANCEMENTS_FILE"
echo ""
log "Next steps:"
echo "  1. Review $ENHANCEMENTS_FILE for Fish porting candidates"
echo "  2. Add useful patterns to configs/.config/fish/config.fish"
echo "  3. Commit changes: git add configs/.zshrc configs/.zshrc.enhancements.md"
echo ""
