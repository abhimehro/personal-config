#!/usr/bin/env bash
#
# macOS bootstrap for personal-config
# - Idempotent: safe to run repeatedly; backs up before linking
# - Secure: expects secrets from 1Password CLI or local untracked files
# - Scope: dotfile symlinks, maintenance launchd, DNS/VPN helpers, media services
#

set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BOLD='\033[1m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()   { echo -e "${BLUE}ℹ️  [INFO]${NC}  $*"; }
ok()     { echo -e "${GREEN}✅ [OK]${NC}    $*"; }
warn()   { echo -e "${YELLOW}⚠️  [WARN]${NC}  $*"; }
err()    { echo -e "${RED}❌ [ERR]${NC}   $*" >&2; }

hr()     { echo -e "${BLUE}────────────────────────────────────────────────────────────${NC}"; }
header() { echo; echo -e "${BOLD}${BLUE}🔷 $*${NC}"; hr; }

require_cmd() {
  local cmd="$1"
  local install_hint="${2:-}"  # Optional: defaults to empty string
  if ! command -v "$cmd" >/dev/null 2>&1; then
    err "Missing required command: $cmd"
    if [[ -n "$install_hint" ]]; then
      info "To install: $install_hint"
    elif [[ "$cmd" == "brew" ]]; then
      info "To install: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    elif [[ "$cmd" == "op" ]]; then
      info "To install: brew install --cask 1password/tap/1password-cli"
    fi
    return 1
  fi
}

ensure_macos() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    err "This bootstrap is macOS-only."
    exit 1
  fi
  info "Running on macOS $(sw_vers -productVersion)"
}

check_requirements() {
  header "Environment Check"
  ensure_macos
  require_cmd brew
  require_cmd op
}

sync_configs() {
  header "Configuration Sync"
  info "Syncing configuration symlinks..."
  bash "$REPO_ROOT/scripts/sync_all_configs.sh"
  bash "$REPO_ROOT/scripts/verify_all_configs.sh"
  ok "Dotfiles linked and verified."
}

install_maintenance() {
  header "System Maintenance"
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
  header "Network Tools"
  info "Ensuring network helpers are executable..."
  chmod +x "$REPO_ROOT/scripts/network-mode-manager.sh" \
            "$REPO_ROOT/scripts/network-mode-verify.sh" \
            "$REPO_ROOT/scripts/network-mode-regression.sh" \
            "$REPO_ROOT/scripts/macos/ipv6-manager.sh" || true
  ok "Network scripts ready."
}

stage_rclone_config() {
  header "Media Services"
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
  # Welcome Banner
  echo -e "${BOLD}🎨 Personal Config Bootstrap${NC}"
  echo -e "   Repository: $REPO_ROOT"

  check_requirements
  sync_configs
  install_maintenance
  remove_legacy_agents
  prepare_network_tools
  stage_rclone_config
  stage_media_scripts
  install_media_launchd

  echo
  echo -e "${GREEN}🎉 Bootstrap Complete!${NC}"
  hr
  echo -e "${BOLD}Summary of Actions:${NC}"
  echo -e "  ✅ Dotfiles linked and verified"
  echo -e "  ✅ Maintenance launchd installed"
  echo -e "  ✅ Network helpers prepared"
  echo -e "  ✅ Media scripts staged and launchd agents loaded"
  hr
  echo
  echo -e "${BOLD}👉 Next Steps:${NC}"
  echo -e "  1. Populate ${BOLD}~/.config/rclone/rclone.conf${NC} with real credentials"
  echo -e "     (use ${CYAN}op inject${NC} if available)"
  echo -e "  2. If needed, set credentials in ${BOLD}~/.config/media-server/credentials${NC}"
  echo -e "  3. Verify services:"
  echo -e "     ${CYAN}launchctl list | grep maintenance${NC}"
  echo -e "     ${CYAN}launchctl list | grep media${NC}"
  echo -e "  4. Run network verification:"
  echo -e "     ${CYAN}./scripts/network-mode-verify.sh controld browsing${NC}"
  echo
}

main "$@"
