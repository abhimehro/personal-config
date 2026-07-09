#!/usr/bin/env bash
# setup-jellyfin-native.sh — install/configure native Jellyfin for CloudMedia mount
#
# Phase 1 host path (preferred over Colima). Idempotent.
# SECURITY: does not create admin users, open firewall, or touch Windscribe.
# ASSUMES: rclone mount agent keeps ~/CloudMedia/mounted healthy.
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

REPO_ROOT="${REPO_ROOT:-$HOME/dev/personal-config}"
LAUNCHD_SRC="$REPO_ROOT/media-streaming/launchd/com.speedybee.jellyfin.plist"
LAUNCHD_DST="$HOME/Library/LaunchAgents/com.speedybee.jellyfin.plist"
MOUNT_POINT="${JELLYFIN_MEDIA_ROOT:-$HOME/CloudMedia/mounted}"
LOG_DIR="$HOME/Library/Logs"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

require_mount() {
	if [[ ! -d $MOUNT_POINT ]]; then
		log "ERROR: mount point missing: $MOUNT_POINT"
		log "Start com.speedybee.media.mount first (media-restart / sync-launchagents)."
		exit 1
	fi
	if ! mount | grep -Fq " on $MOUNT_POINT ("; then
		log "WARN: $MOUNT_POINT exists but is not listed in mount(8)."
		log "       Continuing — empty dir would yield an empty Jellyfin library."
	fi
	local sample
	sample="$(find "$MOUNT_POINT" -maxdepth 2 -type d 2>/dev/null | head -5 || true)"
	if [[ -z $sample ]]; then
		log "WARN: no directories visible under $MOUNT_POINT — library scan will be empty."
	else
		log "Mount sample paths:"
		echo "$sample" | sed 's/^/  /'
	fi
}

find_jellyfin_bin() {
	if command -v jellyfin >/dev/null 2>&1; then
		command -v jellyfin
		return 0
	fi
	local candidates=(
		"/Applications/Jellyfin.app/Contents/MacOS/jellyfin"
		"$HOME/Applications/Jellyfin.app/Contents/MacOS/jellyfin"
		"/opt/homebrew/opt/jellyfin/bin/jellyfin"
		"/usr/local/opt/jellyfin/bin/jellyfin"
	)
	local c
	for c in "${candidates[@]}"; do
		if [[ -x $c ]]; then
			echo "$c"
			return 0
		fi
	done
	return 1
}

install_hint() {
	cat <<'EOF'

Jellyfin binary not found.

Install one of:
  1) Official macOS app (recommended):
       https://jellyfin.org/downloads/server
       Drag Jellyfin.app → /Applications, then re-run this script.
  2) Homebrew (if formula/cask available on your arch):
       brew install jellyfin
       # or: brew install --cask jellyfin

This script will not download packages automatically (network + Gatekeeper HITL).
EOF
}

install_launchagent() {
	if [[ ! -f $LAUNCHD_SRC ]]; then
		log "ERROR: missing plist source $LAUNCHD_SRC"
		exit 1
	fi
	mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
	# Copy (not symlink) — same rationale as sync-launchagents.sh
	cp "$LAUNCHD_SRC" "$LAUNCHD_DST"
	local uid
	uid="$(id -u)"
	launchctl bootout "gui/$uid" "$LAUNCHD_DST" 2>/dev/null || true
	launchctl bootstrap "gui/$uid" "$LAUNCHD_DST"
	launchctl enable "gui/$uid/com.speedybee.jellyfin" 2>/dev/null || true
	launchctl kickstart -k "gui/$uid/com.speedybee.jellyfin" 2>/dev/null || true
	log "LaunchAgent installed: com.speedybee.jellyfin"
}

write_library_hint() {
	local hint="$HOME/Library/Application Support/jellyfin/library-paths.txt"
	mkdir -p "$(dirname "$hint")"
	cat >"$hint" <<EOF
# Add these as Jellyfin media libraries (Dashboard → Libraries):
Movies=$MOUNT_POINT/Movies
Shows=$MOUNT_POINT/TV Shows
# Optional extras if present on the union remote:
# Documentaries=$MOUNT_POINT/Documentaries
# Kids=$MOUNT_POINT/Kids
# Music=$MOUNT_POINT/Music
EOF
	log "Wrote library path hint: $hint"
}

main() {
	log "Jellyfin native setup starting..."
	require_mount

	local bin=""
	if bin="$(find_jellyfin_bin)"; then
		log "Found Jellyfin: $bin"
	else
		install_hint
		write_library_hint
		log "Partial prep complete. Install Jellyfin, then re-run this script."
		exit 2
	fi

	# Patch ProgramArguments path into a user-local override if binary != default
	# Keep repo plist generic; runtime wrapper resolves path.
	install_launchagent
	write_library_hint

	log "Next (HITL): open http://127.0.0.1:8096 and complete the admin wizard."
	log "Then add libraries from $HOME/Library/Application Support/jellyfin/library-paths.txt"
	log "Validate with: bash $REPO_ROOT/media-streaming/scripts/validate-jellyfin.sh"
}

main "$@"
