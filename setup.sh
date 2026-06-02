#!/usr/bin/env bash
#
# macOS bootstrap for personal-config
# - Idempotent: safe to run repeatedly; backs up before linking
# - Secure: expects secrets from 1Password CLI or local untracked files
# - Scope: dotfile symlinks, maintenance launchd, DNS/VPN helpers, media services
#

set -Eeuo pipefail

trap 'printf "\n\033[0;31m👋 Setup cancelled by user. Goodbye!\033[0m\n"; exit 130' SIGINT

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BOLD='\033[1m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { printf "%bℹ️  [INFO]%b  %s\n" "${BLUE}" "${NC}" "$*"; }
log_ok() { printf "%b✅ [OK]%b    %s\n" "${GREEN}" "${NC}" "$*"; }
log_warn() { printf "%b⚠️  [WARN]%b  %s\n" "${YELLOW}" "${NC}" "$*"; }
log_err() { printf "%b❌ [ERR]%b   %s\n" "${RED}" "${NC}" "$*" >&2; }

hr() { printf "%b────────────────────────────────────────────────────────────%b\n" "${BLUE}" "${NC}"; }
header() {
	echo
	printf "%b🔷 %s%b\n" "${BOLD}${BLUE}" "$*" "${NC}"
	hr
}

require_cmd() {
	local cmd="$1"
	local install_hint="${2-}" # Optional: defaults to empty string
	if ! command -v "$cmd" >/dev/null 2>&1; then
		log_err "Missing required command: $cmd"
		if [[ -n $install_hint ]]; then
			log_info "To install: $install_hint"
		elif [[ $cmd == "brew" ]]; then
			log_info "To install: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
		elif [[ $cmd == "op" ]]; then
			log_info "To install: brew install --cask 1password/tap/1password-cli"
		fi
		return 1
	fi
	log_ok "Found $cmd"
}

ensure_macos() {
	if [[ "$(uname -s)" != "Darwin" ]]; then
		log_err "This bootstrap is macOS-only."
		exit 1
	fi
	log_info "Running on macOS $(sw_vers -productVersion)"
}

check_requirements() {
	header "Environment Check"
	ensure_macos
	require_cmd brew
	require_cmd op
}

sync_configs() {
	header "Configuration Sync"
	log_info "Syncing configuration symlinks..."
	bash "$REPO_ROOT/scripts/sync_all_configs.sh"
	bash "$REPO_ROOT/scripts/verify_all_configs.sh"
	log_ok "Dotfiles linked and verified."
}

install_maintenance() {
	header "System Maintenance"
	log_info "Installing maintenance system (launchd agents + scripts)..."
	bash "$REPO_ROOT/maintenance/install.sh"
	log_ok "Maintenance system installed."
}

remove_legacy_agents() {
	local legacy="$HOME/Library/LaunchAgents/com.user.maintenance.weekly.plist"
	if [[ -f $legacy ]]; then
		log_info "Removing legacy maintenance LaunchAgent (com.user.maintenance.weekly)..."
		launchctl bootout "gui/$(id -u)" "$legacy" 2>/dev/null || true
		rm -f "$legacy"
		log_ok "Legacy LaunchAgent removed."
	fi
}

prepare_network_tools() {
	header "Network Tools"
	log_info "Ensuring network helpers are executable..."
	chmod +x "$REPO_ROOT/scripts/network-mode-manager.sh" \
		"$REPO_ROOT/scripts/network-mode-verify.sh" \
		"$REPO_ROOT/scripts/network-mode-regression.sh" \
		"$REPO_ROOT/scripts/macos/ipv6-manager.sh" || true
	log_ok "Network scripts ready."
}

stage_rclone_config() {
	header "Media Services"
	local rclone_dir="$HOME/.config/rclone"
	local rclone_cfg="$rclone_dir/rclone.conf"
	local template="$REPO_ROOT/media-streaming/configs/rclone.conf.template"

	mkdir -p "$rclone_dir"

	if [[ -f $rclone_cfg ]]; then
		log_ok "rclone config already present at $rclone_cfg (left untouched)."
		return
	fi

	if [[ -f $template ]]; then
		log_info "Seeding rclone config from template (remember to inject secrets via 1Password)..."
		cp "$template" "$rclone_cfg"
		chmod 600 "$rclone_cfg"
		log_warn "Edit or replace $rclone_cfg with 'op inject' before starting media services."
	else
		log_warn "No rclone template found; create $rclone_cfg manually."
	fi
}

stage_media_scripts() {
	local media_bin="$HOME/Library/Media/bin"
	mkdir -p "$media_bin"
	log_info "Linking media helper scripts to $media_bin..."

	for s in media-server-daemon.sh mount-media.sh rename-media.sh sync-alldebrid.sh bulk-rename-cloud.sh launch-permute.sh; do
		local src="$REPO_ROOT/media-streaming/scripts/$s"
		if [[ -f $src ]]; then
			ln -sf "$src" "$media_bin/$s"
			chmod +x "$src"
		else
			log_warn "Missing media script: $src"
		fi
	done

	mkdir -p "$HOME/.config/media-server" "$HOME/Library/Application Support/MediaCache" "$HOME/Library/Logs/media"
	log_ok "Media scripts staged."
}

install_media_launchd() {
	local launch_src="$REPO_ROOT/media-streaming/launchd"
	local launch_dst="$HOME/Library/LaunchAgents"
	mkdir -p "$launch_dst"

	if [[ ! -d $launch_src ]]; then
		log_warn "No media launchd definitions found at $launch_src; skipping."
		return
	fi

	log_info "Installing media LaunchAgents..."
	for plist in "$launch_src"/*.plist; do
		[[ -e $plist ]] || continue
		local base
		base="$(basename "$plist")"
		rm -f "$launch_dst/$base" 2>/dev/null || true
		ln -s "$plist" "$launch_dst/$base"
		launchctl bootout "gui/$(id -u)" "$launch_dst/$base" 2>/dev/null || true
		if launchctl bootstrap "gui/$(id -u)" "$launch_dst/$base" 2>/dev/null; then
			log_ok "Loaded $base"
		else
			log_warn "Failed to load $base (check ~/Library/Logs or Console.app)."
		fi
	done
}

main() {
	# Welcome Banner
	printf "%b🎨 Personal Config Bootstrap%b\n" "${BOLD}" "${NC}"
	printf "   Repository: %s\n" "$REPO_ROOT"

	# Check for non-interactive mode or flag
	local interactive=true
	if [[ ${1-} == "-y" ]] || [[ ${1-} == "--yes" ]]; then
		interactive=false
	elif [[ ! -t 0 ]]; then
		interactive=false
		log_warn "Non-interactive shell detected. Proceeding automatically."
	fi

	# Interactive Confirmation
	if [[ $interactive == "true" ]]; then
		echo
		printf "%bPlan of Execution:%b\n" "${BOLD}" "${NC}"
		printf "  1. Check macOS environment and requirements (brew, op)\n"
		printf "  2. Sync and verify configuration symlinks\n"
		printf "  3. Install system maintenance agents\n"
		printf "  4. Setup network tools and media services\n"
		echo
		printf "%b⚠️  This will modify configuration files in your home directory.%b\n" "${YELLOW}" "${NC}"
		echo
		read -r -p "Ready to proceed? (y/N) "
		REPLY=${REPLY:-N}
		if [[ ! $REPLY =~ ^([Yy][Ee][Ss]|[Yy])$ ]]; then
			log_info "Bootstrap cancelled by user."
			exit 0
		fi
	else
		printf "%bRunning in non-interactive mode.%b\n" "${BOLD}" "${NC}"
	fi

	check_requirements
	sync_configs
	install_maintenance
	remove_legacy_agents
	prepare_network_tools
	stage_rclone_config
	stage_media_scripts
	install_media_launchd

	echo
	printf "%b🎉 Bootstrap Complete!%b\n" "${GREEN}" "${NC}"
	hr
	printf "%bSummary of Actions:%b\n" "${BOLD}" "${NC}"
	printf "  ✅ Dotfiles linked and verified\n"
	printf "  ✅ Maintenance launchd installed\n"
	printf "  ✅ Network helpers prepared\n"
	printf "  ✅ Media scripts staged and launchd agents loaded\n"
	hr
	echo
	printf "%b👉 Next Steps:%b\n" "${BOLD}" "${NC}"
	printf "  1. Populate %b~/.config/rclone/rclone.conf%b with real credentials\n" "${BOLD}" "${NC}"
	printf "     (use %bop inject%b if available)\n" "${CYAN}" "${NC}"
	printf "  2. Verify 1Password-backed media credentials resolve correctly; optional fallback file remains %b~/.config/media-server/credentials%b\n" "${BOLD}" "${NC}"
	printf "  3. Verify services:\n"
	printf "     %blaunchctl list | grep maintenance%b\n" "${CYAN}" "${NC}"
	printf "     %blaunchctl list | grep media%b\n" "${CYAN}" "${NC}"
	printf "  4. Run network verification:\n"
	printf "     %b./scripts/network-mode-verify.sh controld browsing%b\n" "${CYAN}" "${NC}"
	echo
}

main "$@"
