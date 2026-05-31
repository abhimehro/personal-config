#!/usr/bin/env bash
# ==============================================================================
# SecOps Autopilot — installer / loader
# ==============================================================================
# Installs (symlinks) the three LaunchAgents and (re)loads them via launchctl.
# Idempotent: safe to run repeatedly. Run from anywhere.
#
#   bash ~/secops/install.sh            # install + load
#   bash ~/secops/install.sh --uninstall  # bootout + remove symlinks
# ==============================================================================
set -euo pipefail

REPO_SECOPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" # resolves through ~/secops symlink
LA_DIR="$HOME/Library/LaunchAgents"
REPO_PLIST_DIR="$REPO_SECOPS/../launch-agents"
LABELS=(com.speedybee.secops.phase1 com.speedybee.secops.phase2 com.speedybee.secops.phase3)
UID_NUM="$(id -u)"

mkdir -p "$HOME/Library/Logs/maintenance"

uninstall() {
	for label in "${LABELS[@]}"; do
		launchctl bootout "gui/$UID_NUM/$label" 2>/dev/null || true
		rm -f "$LA_DIR/$label.plist"
		echo "removed $label"
	done
	echo "SecOps Autopilot uninstalled."
}

install() {
	for label in "${LABELS[@]}"; do
		src="$REPO_PLIST_DIR/$label.plist"
		dst="$LA_DIR/$label.plist"
		if [ ! -f "$src" ]; then
			echo "WARN: missing $src, skipping"
			continue
		fi
		# Keep a real copy in ~/Library/LaunchAgents (launchd does not follow some symlinks reliably).
		cp -f "$src" "$dst"
		launchctl bootout "gui/$UID_NUM/$label" 2>/dev/null || true
		launchctl bootstrap "gui/$UID_NUM" "$dst" 2>/dev/null || true
		echo "loaded $label"
	done
	echo
	echo "Installed. Current status:"
	launchctl list | grep secops || true
}

case "${1-}" in
--uninstall) uninstall ;;
*) install ;;
esac
