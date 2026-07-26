#!/usr/bin/env bash
#
# Install and register LaunchAgents for Weekly Repository Health Reviews
# Plists installed:
#   com.speedybee.repo-health.research.plist (Tuesdays 09:00)
#   com.speedybee.repo-health.general.plist  (Thursdays 09:00)

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/maintenance"

mkdir -p "$LAUNCH_AGENTS_DIR" "$LOG_DIR"

PLISTS=(
	"com.speedybee.repo-health.research.plist"
	"com.speedybee.repo-health.general.plist"
)

echo "=========================================="
echo "Installing Weekly Repo Health LaunchAgents"
echo "=========================================="

for plist in "${PLISTS[@]}"; do
	src="$REPO_ROOT/launch-agents/$plist"
	dest="$LAUNCH_AGENTS_DIR/$plist"
	label="${plist%.plist}"

	if [[ ! -f $src ]]; then
		echo "[ERROR] Source plist missing: $src" >&2
		exit 1
	fi

	echo "[INFO] Copying $plist -> $dest"
	cp -f "$src" "$dest"
	chmod 644 "$dest"

	# Unload previous version if running
	launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || launchctl unload "$dest" 2>/dev/null || true

	# Load new version
	echo "[INFO] Loading $label via launchctl..."
	launchctl bootstrap "gui/$(id -u)" "$dest" 2>/dev/null || launchctl load "$dest" 2>/dev/null
done

echo ""
echo "[OK] Installed. Verifying launchctl status:"
launchctl list | grep repo-health || true
echo "=========================================="
