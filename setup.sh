#!/usr/bin/env bash
#
# macOS bootstrap for personal-config
# - Idempotent: safe to run repeatedly; backs up before linking
# - Secure: expects secrets from 1Password CLI or local untracked files
# - Scope: dotfile symlinks, maintenance launchd, DNS/VPN helpers, media services
#

set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${BLUE}ℹ️  [INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}✅ [OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}⚠️  [WARN]${NC}  $*"; }
err()   { echo -e "${RED}❌ [ERR]${NC}   $*" >&2; }

check_requirements() {
  local missing=()
  # Shellcheck-safe associative array requires declare -A (bash 4+),
  # but macOS ships bash 3.2 by default. using simple if/elif logic for hints
  # to maintain compatibility with stock macOS bash.

  info "Checking prerequisites..."
  echo ""

  # Define requirements (git is not required as repo is already cloned)
  local reqs="brew op rclone"

  for cmd in $reqs; do
    if command -v "$cmd" >/dev/null 2>&1; then
      ok "Found $cmd"
    else
      missing+=("$cmd")
      # Don't print error yet, collect all missing
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo ""
    err "Missing ${#missing[@]} required tool(s):"

    for cmd in "${missing[@]}"; do
      echo "   - $cmd"
    done

    echo ""
    info "Installation instructions (install Homebrew first):"

    # Sort missing so brew appears first if present
    local sorted_missing=()
    for cmd in "${missing[@]}"; do
      if [[ "$cmd" == "brew" ]]; then
        sorted_missing=("brew" "${sorted_missing[@]}")
      else
        sorted_missing+=("$cmd")
      fi
    done

    for cmd in "${sorted_missing[@]}"; do
      local hint=""
      case "$cmd" in
        "brew") hint='/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"' ;;
        "op")   hint='brew install --cask 1password/tap/1password-cli' ;;
        "rclone") hint='brew install rclone' ;;
        *)      hint="brew install $cmd" ;;
      esac

      if [[ "$cmd" == "brew" ]]; then
        echo "   👉 1. Install Homebrew (Required for others):"
        echo "         $hint"
      else
        echo "   👉 To install $cmd: $hint"
      fi
    done
    echo ""
    exit 1
  fi
}

ensure_macos() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    err "This bootstrap is macOS-only."
    exit 1
  fi
}

sync_configs() {
  info "Syncing configuration symlinks..."
  bash "$REPO_ROOT/scripts/sync_all_configs.sh"
  bash "$REPO_ROOT/scripts/verify_all_configs.sh"
  ok "Dotfiles linked and verified."
}

install_maintenance() {
  info "Installing maintenance system (launchd agents + scripts)..."
  bash "$REPO_ROOT/maintenance/install.sh"
  ok "Maintenance system installed."
}

remove_legacy_agents() {
  local legacy="$HOME/Library/LaunchAgents/com.user.maintenance.weekly.plist"
  if [[ -f "$legacy" ]]; then
    info "Removing legacy maintenance LaunchAgent (com.user.maintenance.weekly)..."
    launchctl bootout "gui/$(id -u)" "$legacy" 2>/dev/null || true
    rm -f "$legacy"
    ok "Legacy LaunchAgent removed."
  fi
}

prepare_network_tools() {
  info "Ensuring network helpers are executable..."
  chmod +x "$REPO_ROOT/scripts/network-mode-manager.sh" \
            "$REPO_ROOT/scripts/network-mode-verify.sh" \
            "$REPO_ROOT/scripts/network-mode-regression.sh" \
            "$REPO_ROOT/scripts/macos/ipv6-manager.sh" || true
  ok "Network scripts ready."
}

stage_rclone_config() {
  local rclone_dir="$HOME/.config/rclone"
  local rclone_cfg="$rclone_dir/rclone.conf"
  local template="$REPO_ROOT/media-streaming/configs/rclone.conf.template"

  mkdir -p "$rclone_dir"

  if [[ -f "$rclone_cfg" ]]; then
    ok "rclone config already present at $rclone_cfg (left untouched)."
    return
  fi

  if [[ -f "$template" ]]; then
    info "Seeding rclone config from template (remember to inject secrets via 1Password)..."
    cp "$template" "$rclone_cfg"
    chmod 600 "$rclone_cfg"
    warn "Edit or replace $rclone_cfg with 'op inject' before starting media services."
  else
    warn "No rclone template found; create $rclone_cfg manually."
  fi
}

stage_media_scripts() {
  local media_bin="$HOME/Library/Media/bin"
  mkdir -p "$media_bin"
  info "Linking media helper scripts to $media_bin..."

  for s in start-media-server.sh start-media-server-vpn-fix.sh start-alldebrid.sh stop-alldebrid.sh test-infuse-connection.sh; do
    local src="$REPO_ROOT/media-streaming/scripts/$s"
    if [[ -f "$src" ]]; then
      ln -sf "$src" "$media_bin/$s"
      chmod +x "$src"
    else
      warn "Missing media script: $src"
    fi
  done

  mkdir -p "$HOME/.config/media-server" "$HOME/Library/Application Support/MediaCache" "$HOME/Library/Logs/media"
  ok "Media scripts staged."
}

install_media_launchd() {
  local launch_src="$REPO_ROOT/media-streaming/launchd"
  local launch_dst="$HOME/Library/LaunchAgents"
  mkdir -p "$launch_dst"

  if [[ ! -d "$launch_src" ]]; then
    warn "No media launchd definitions found at $launch_src; skipping."
    return
  fi

  info "Installing media LaunchAgents..."
  for plist in "$launch_src"/*.plist; do
    [[ -e "$plist" ]] || continue
    local base
    base="$(basename "$plist")"
    cp "$plist" "$launch_dst/$base"
    launchctl bootout "gui/$(id -u)" "$launch_dst/$base" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$launch_dst/$base" 2>/dev/null && ok "Loaded $base" || warn "Failed to load $base (check logs)."
  done
}

main() {
  ensure_macos
  info "Starting bootstrap from $REPO_ROOT"

  check_requirements

  sync_configs
  install_maintenance
  remove_legacy_agents
  prepare_network_tools
  stage_rclone_config
  stage_media_scripts
  install_media_launchd

  cat <<'SUMMARY'

Bootstrap complete ✅
- Dotfiles linked and verified
- Maintenance launchd installed
- Network helpers prepared
- rclone config seeded (fill secrets via 1Password)
- Media scripts staged and launchd agents (if present) loaded

Next steps:
1) Populate ~/.config/rclone/rclone.conf with real credentials (use `op inject`).
2) If needed, set MEDIA_WEBDAV_USER/PASS in ~/.config/media-server/credentials (untracked).
3) Verify services:
   - launchctl list | grep maintenance
   - launchctl list | grep media
   - rclone listremotes
4) Run ./scripts/network-mode-verify.sh controld browsing
SUMMARY
}

main "$@"
