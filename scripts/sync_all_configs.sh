#!/usr/bin/env bash
#
# Sync All Configs - Master Symlink Management Script
# Creates symlinks from repository configuration files to home directory
# Ensures repository updates automatically reflect in home directory
#
# Usage: ./scripts/sync_all_configs.sh

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
log() { printf '%b\n' "${BLUE}[INFO]${NC} $*"; }
success() { printf '%b\n' "${GREEN}[OK]${NC} $*"; }
warn() { printf '%b\n' "${YELLOW}[WARN]${NC} $*"; }
error() { printf '%b\n' "${RED}[ERROR]${NC} $*" >&2; }

# Ensure we're in the repo root
if [[ ! -d $REPO_ROOT ]]; then
	error "Repository root not found: $REPO_ROOT"
	exit 1
fi

cd "$REPO_ROOT"

# Ensure symlink for a file
ensure_file_link() {
	local link="$1"
	local target="$2"
	local name="$3"
	local perms="${4-}" # Optional permissions (e.g., "600" for SSH files)

	# Check if target exists in repo
	if [[ ! -e $target ]]; then
		warn "Target not found: $target (skipping $name)"
		return 0
	fi

	# Check if symlink already exists and is correct
	if [[ -L $link ]] && [[ "$(readlink "$link")" == "$target" ]]; then
		success "$name symlink is intact"
		return 0
	fi

	# Backup existing file/directory if it exists and is not a symlink
	if [[ -e $link ]] && [[ ! -L $link ]]; then
		local backup
		backup="${link}.backup.$(date +%Y%m%d_%H%M%S)"
		log "Backing up existing $name to $backup"
		mv -v "$link" "$backup"
	fi

	# Remove existing symlink if it points to wrong location
	if [[ -L $link ]]; then
		rm -f "$link"
	fi

	# Create parent directory if needed
	mkdir -p "$(dirname "$link")"

	# Create symlink
	log "Creating symlink: $name -> $target"
	ln -s "$target" "$link"

	# Set permissions if specified
	# Note: chmod on symlink affects the target file on macOS
	if [[ -n $perms ]]; then
		# Ensure target file has correct permissions
		chmod "$perms" "$target" 2>/dev/null || true
		# Also set on symlink (affects target on macOS)
		chmod "$perms" "$link" 2>/dev/null || true
	fi

	success "Created $name symlink"
}

# Ensure symlink for a directory
ensure_dir_link() {
	local link="$1"
	local target="$2"
	local name="$3"

	# Check if target exists in repo
	if [[ ! -d $target ]]; then
		warn "Target directory not found: $target (skipping $name)"
		return 0
	fi

	# Check if symlink already exists and is correct
	if [[ -L $link ]] && [[ "$(readlink "$link")" == "$target" ]]; then
		success "$name symlink is intact"
		return 0
	fi

	# Backup existing directory if it exists and is not a symlink
	if [[ -e $link ]] && [[ ! -L $link ]]; then
		local backup
		backup="${link}.backup.$(date +%Y%m%d_%H%M%S)"
		log "Backing up existing $name directory to $backup"
		mv -v "$link" "$backup"
	fi

	# Remove existing symlink if it points to wrong location
	if [[ -L $link ]]; then
		rm -f "$link"
	fi

	# Create parent directory if needed
	mkdir -p "$(dirname "$link")"

	# Create symlink
	log "Creating directory symlink: $name -> $target"
	ln -s "$target" "$link"

	success "Created $name directory symlink"
}

echo "=========================================="
echo "Syncing Configuration Files to Home Directory"
echo "=========================================="
echo ""

# 1. SSH Configuration (files)
log "Setting up SSH configuration..."

# Ensure SSH directory and control directory exist with correct permissions first
mkdir -p "$HOME/.ssh/control"
chmod 700 "$HOME/.ssh" 2>/dev/null || true
chmod 700 "$HOME/.ssh/control" 2>/dev/null || true

# Ensure target files have correct permissions before creating symlinks
chmod 600 "$REPO_ROOT/configs/ssh/config" 2>/dev/null || true
chmod 600 "$REPO_ROOT/configs/ssh/agent.toml" 2>/dev/null || true

ensure_file_link "$HOME/.ssh/config" "$REPO_ROOT/configs/ssh/config" "$HOME/.ssh/config" "600"
ensure_file_link "$HOME/.ssh/agent.toml" "$REPO_ROOT/configs/ssh/agent.toml" "$HOME/.ssh/agent.toml" "600"

# 2. Fish Shell Configuration (directory)
log "Setting up Fish shell configuration..."
ensure_dir_link "$HOME/.config/fish" "$REPO_ROOT/configs/.config/fish" "$HOME/.config/fish"

# 3. Cursor Configuration (directory)
log "Setting up Cursor IDE configuration..."
ensure_dir_link "$HOME/.cursor" "$REPO_ROOT/.cursor" "$HOME/.cursor"

# 4. VS Code Configuration (directory)
log "Setting up VS Code configuration..."
ensure_dir_link "$HOME/.vscode" "$REPO_ROOT/.vscode" "$HOME/.vscode"

# 5. Git Configuration (file, if exists)
if [[ -f "$REPO_ROOT/configs/.gitconfig" ]]; then
	log "Setting up Git configuration..."
	ensure_file_link "$HOME/.gitconfig" "$REPO_ROOT/configs/.gitconfig" "$HOME/.gitconfig"

	# Ensure Git commit template from this repo is available at the configured path
	# ASSUMES: configs/.gitconfig uses ~/.config/git/commit-template.personal-config.txt
	# as the commit.template location (expanded to $HOME/.config/git/commit-template.personal-config.txt).
	# This prevents "could not read template" errors on fresh installs.
	log "Ensuring Git commit template is configured..."
	mkdir -p "${HOME/.config/git"
	ensure_file_link \
		"$HOME/.config/git/commit-template.personal-config.txt" \
		"$REPO_ROOT/.gitmessage" \
		"$HOME/.config/git/commit-template.personal-config.txt"
else
	warn "No .gitconfig found in repo (skipping)"
fi

# 6. Local Configuration (directory, if exists)
if [[ -d "$REPO_ROOT/configs/.local" ]]; then
	log "Setting up local configuration..."
	ensure_dir_link "$HOME/.local" "$REPO_ROOT/configs/.local" "$HOME/.local"
else
	warn "No .local directory found in repo (skipping)"
fi

# 7. GitHub Configuration (directory, if exists)
if [[ -d "$REPO_ROOT/.github" ]]; then
	log "Setting up GitHub configuration..."
	# Note: .github in home is less common, but we'll create it if requested
	# Most users don't need this, so we'll skip it by default
	# Uncomment if needed:
	# ensure_dir_link "$HOME/.github" "$REPO_ROOT/.github" "~/.github"
	log "Skipping ~/.github (typically not needed in home directory)"
fi

echo ""
echo "=========================================="
success "Configuration sync completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify symlinks: ./scripts/verify_all_configs.sh"
echo "2. Reload fish shell: exec fish"
echo "3. Install/update Fish plugins (Hydro, etc): ./scripts/bootstrap_fish_plugins.sh"
echo "   (fallback if Fisher already installed: fish -lc 'fisher update')"
echo "4. Test Control D functions: nm-status"
echo ""
