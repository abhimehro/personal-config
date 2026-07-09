#!/usr/bin/env bash
# jellyfin-daemon.sh — foreground runner for LaunchAgent (native Jellyfin)
#
# Resolves the Jellyfin binary on PATH or common macOS install locations,
# then execs it so launchd KeepAlive tracks the real process.
# SECURITY: binds default Jellyfin listen (LAN). No public exposure here.
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

resolve_bin() {
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
		[[ -x $c ]] && {
			echo "$c"
			return 0
		}
	done
	return 1
}

resolve_ffmpeg() {
	if command -v ffmpeg >/dev/null 2>&1; then
		command -v ffmpeg
		return 0
	fi
	local c
	for c in /opt/homebrew/bin/ffmpeg /usr/local/bin/ffmpeg; do
		[[ -x $c ]] && {
			echo "$c"
			return 0
		}
	done
	return 1
}

bin="$(resolve_bin)" || {
	log "ERROR: jellyfin binary not found. Run setup-jellyfin-native.sh after installing the app."
	exit 1
}

# Official macOS .app ships web UI under Contents/Resources/jellyfin-web, but the
# server binary defaults to Contents/MacOS/jellyfin-web (missing) → crash loop.
resolve_webdir() {
	local app_root web
	app_root="$(cd "$(dirname "$bin")/../.." && pwd)"
	web="$app_root/Contents/Resources/jellyfin-web"
	if [[ -f $web/index.html ]]; then
		echo "$web"
		return 0
	fi
	web="$(dirname "$bin")/jellyfin-web"
	if [[ -f $web/index.html ]]; then
		echo "$web"
		return 0
	fi
	return 1
}

args=(--service)
if webdir="$(resolve_webdir)"; then
	args+=(--webdir "$webdir")
	log "Using webdir: $webdir"
else
	log "ERROR: jellyfin-web not found next to $bin (expected Contents/Resources/jellyfin-web)."
	exit 1
fi

if ff="$(resolve_ffmpeg)"; then
	args+=(--ffmpeg "$ff")
	log "Using ffmpeg: $ff"
else
	# Prefer Homebrew ffmpeg; fall back to the binary bundled inside the .app.
	bundled="$(dirname "$bin")/ffmpeg"
	if [[ -x $bundled ]]; then
		args+=(--ffmpeg "$bundled")
		log "Using bundled ffmpeg: $bundled"
	else
		log "WARN: ffmpeg not on PATH — Jellyfin will use its bundled ffmpeg if present"
	fi
fi

log "Starting Jellyfin: $bin ${args[*]-}"
# NOTE: Jellyfin stores config under ~/Library/Application Support/jellyfin by default on macOS.
exec "$bin" "${args[@]}"
