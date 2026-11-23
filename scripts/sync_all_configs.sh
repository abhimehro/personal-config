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

# 2b. Starship Prompt Configuration (file)
# The Dracula palette lives here. Kaku shell integration and the zsh/fish
# prompt both read ~/.config/starship.toml, so it must be a real path in $HOME.
log "Setting up Starship prompt configuration..."
ensure_file_link \
	"$HOME/.config/starship.toml" \
	"$REPO_ROOT/configs/.config/starship.toml" \
	"$HOME/.config/starship.toml"

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
	mkdir -p "${HOME}/.config/git"
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

# 8. Antigravity Proactive Skills and Safety Hook (if exists)
if [[ -d "$REPO_ROOT/configs/antigravity/skills" ]]; then
	log "Setting up Antigravity proactive skills and safety hook..."
	mkdir -p "$HOME/.gemini/config/skills" "$HOME/.gemini/antigravity/proactive-reports" "$HOME/.gemini/antigravity/worktrees"
	chmod 700 "$HOME/.gemini/antigravity/proactive-reports" "$HOME/.gemini/antigravity/worktrees" 2>/dev/null || true
	for agy_skill_dir in "$REPO_ROOT"/configs/antigravity/skills/*; do
		[[ -d $agy_skill_dir ]] || continue
		agy_skill_name="${agy_skill_dir##*/}"
		ensure_dir_link \
			"$HOME/.gemini/config/skills/$agy_skill_name" \
			"$agy_skill_dir" \
			"$HOME/.gemini/config/skills/$agy_skill_name"
	done
	if [[ -f "$REPO_ROOT/configs/antigravity/hooks.json" ]]; then
		ensure_file_link \
			"$HOME/.gemini/config/hooks.json" \
			"$REPO_ROOT/configs/antigravity/hooks.json" \
			"$HOME/.gemini/config/hooks.json"
	fi
fi

# 9. Mole user config (files copied rather than symlinked)
# Mole rewrites these files from its interactive editors (e.g. `mole clean
# --whitelist`), and it writes atomically via a temp file plus rename. A
# symlink would be replaced by a regular file on the first such write,
# silently breaking the link, so the repo copies are deployed by copy.
# All three files the installed Mole reads from ~/.config/mole/ are synced:
#   whitelist          - protected paths enforced by safe_clean
#   purge_paths        - paths Mole may purge
#   whitelist_optimize - checks skipped during optimization runs
# Without this sync, repo whitelist fixes (e.g. the 2026-11-22 ~/.sonar
# protection) never reach the installed Mole that actually runs.
mole_sync_one() {
	local name="$1"
	local src="$REPO_ROOT/configs/.config/mole/$name"
	local dst="$HOME/.config/mole/$name"
	if [[ ! -f $src ]]; then
		warn "No Mole $name found in repo (skipping)"
		return 0
	fi
	mkdir -p "$(dirname "$dst")"
	if [[ -f $dst ]] && cmp -s "$src" "$dst"; then
		success "Mole $name is up to date"
		return 0
	fi
	if [[ -f $dst ]]; then
		local local_backup
		local_backup="${dst}.backup.$(date +%Y%m%d_%H%M%S)"
		log "Backing up existing Mole $name to $local_backup"
		cp "$dst" "$local_backup"
	fi
	cp "$src" "$dst"
	success "Deployed Mole $name from repo"
}

log "Setting up Mole user config..."
mole_sync_one whitelist
mole_sync_one purge_paths
mole_sync_one whitelist_optimize

# 10. CleanMyMac ignore list (applied through the vendor CLI)
# The ignore list lives in an encrypted binary store, so the repo tracks a
# declarative path list and reconciles it with the CLI.
CMM_APPLY="$REPO_ROOT/scripts/apply_cleanmymac_ignores.sh"
if [[ -x $CMM_APPLY ]]; then
	log "Reconciling CleanMyMac ignore list..."
	if "$CMM_APPLY" >/dev/null 2>&1; then
		success "CleanMyMac ignore list reconciled"
	else
		warn "CleanMyMac ignore list not reconciled (run $CMM_APPLY to see why)"
	fi
fi

# 11. Maintenance deploy drift check (advisory only)
# ~/Library/Maintenance is a real directory populated by copy, so live scripts
# no longer track the checked-out branch. That is deliberate: a symlink into the
# repo let a `git checkout` silently rewrite production behaviour.
#
# This is a WARNING, never a deploy. Running a deploy from here would copy
# whatever branch happens to be checked out into the live tree, which is exactly
# the cross-branch contamination this decoupling removed. Deploys stay manual:
#   ./scripts/deploy_maintenance.sh
DEPLOY_SCRIPT="$REPO_ROOT/scripts/deploy_maintenance.sh"
if [[ -x $DEPLOY_SCRIPT ]]; then
	if "$DEPLOY_SCRIPT" --check >/dev/null 2>&1; then
		success "Live maintenance tree matches the repo"
	else
		warn "Live maintenance tree has drifted from the repo"
		warn "Review with: ./scripts/deploy_maintenance.sh --dry-run"
		warn "Apply with:  ./scripts/deploy_maintenance.sh"
	fi
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
