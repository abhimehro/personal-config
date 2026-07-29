#!/bin/bash
#
# Media Server - Foreground Runner for LaunchAgent
# Keeps rclone running in foreground so LaunchAgent can monitor it
#
set -euo pipefail

# Set PATH
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Logging function
log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Timeout helper (pure bash)
run_with_timeout() {
	local timeout_secs="$1"
	shift
	"$@" &
	local pid=$!
	(
		sleep "$timeout_secs"
		kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
	) &
	local watcher_pid=$!
	wait "$pid" 2>/dev/null
	local exit_code=$?
	kill "$watcher_pid" 2>/dev/null || true
	wait "$watcher_pid" 2>/dev/null || true
	return $exit_code
}

log "🔧 Media Server - Starting..."

# Kill any existing rclone WebDAV servers
pkill -f "rclone serve webdav" 2>/dev/null || true
sleep 2

# Get network info
PRIMARY_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "unknown")

log "Network: LAN=$PRIMARY_IP, Public=$PUBLIC_IP"

# WebDAV must use a stable internal port for Windscribe forwarding.
# Default mapping: External 8088 -> Internal 8080/TCP.
# The LaunchAgent already killed any previous rclone WebDAV process above; if
# port 8080 is still occupied by another service, fail loudly instead of
# silently moving to 8081-8083 and breaking remote access.
MEDIA_WEBDAV_PORT="${MEDIA_WEBDAV_PORT:-8080}"
AVAILABLE_PORT="$MEDIA_WEBDAV_PORT"

if lsof -nP -iTCP:"$MEDIA_WEBDAV_PORT" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; then
	log "ERROR: Required WebDAV port $MEDIA_WEBDAV_PORT is already in use."
	log "Windscribe forwarding expects a stable internal port: $MEDIA_WEBDAV_PORT/TCP."
	log "Free port $MEDIA_WEBDAV_PORT and restart com.speedybee.media.server."
	lsof -nP -iTCP:"$MEDIA_WEBDAV_PORT" -sTCP:LISTEN 2>/dev/null || true
	exit 1
fi

log "Using stable WebDAV internal port: $AVAILABLE_PORT"

# Check rclone remote
if ! rclone listremotes 2>/dev/null | grep -q "media:"; then
	log "ERROR: 'media:' remote not found"
	exit 1
fi

# Get credentials
WEB_USER=""
WEB_PASS=""

CRED_FILE="$HOME/.config/media-server/credentials"
if [[ -f $CRED_FILE ]]; then
	log "Loading credentials from fallback file $CRED_FILE..."
	parse_value() {
		local val="$1"
		if [[ $val == \'*\' ]]; then
			val="${val#\'}"
			val="${val%\'}"
		elif [[ $val == '"'*'"' ]]; then
			val="${val#\"}"
			val="${val%\"}"
		fi
		echo "$val"
	}

	while IFS= read -r line || [[ -n $line ]]; do
		[[ $line =~ ^[[:space:]]*# ]] && continue
		[[ -z ${line//[[:space:]]/} ]] && continue

		if [[ $line =~ ^(MEDIA_WEBDAV_USER|MEDIA_USER)= ]]; then
			raw_val=$(echo "$line" | cut -d'=' -f2-)
			WEB_USER=$(parse_value "$raw_val")
		elif [[ $line =~ ^(MEDIA_WEBDAV_PASS|MEDIA_PASS)= ]]; then
			raw_val=$(echo "$line" | cut -d'=' -f2-)
			WEB_PASS=$(parse_value "$raw_val")
		fi
	done <"$CRED_FILE"
fi

if [[ -z $WEB_USER || -z $WEB_PASS ]]; then
	log "Loading credentials from 1Password..."
	if command -v op &>/dev/null; then
		WEB_USER=$(op read "op://Personal/MediaServer/username" 2>/dev/null) || WEB_USER=""
		WEB_PASS=$(op read "op://Personal/MediaServer/password" 2>/dev/null) || WEB_PASS=""
	else
		log "WARNING: 1Password CLI not found"
	fi
fi

if [[ -z $WEB_USER || -z $WEB_PASS ]]; then
	log "ERROR: Could not retrieve credentials from file or 1Password."
	log "Please configure credentials in ~/.config/media-server/credentials or install 1Password CLI."
	exit 1
fi

log "✅ Credentials loaded"
log "🚀 Starting rclone WebDAV server on 0.0.0.0:$AVAILABLE_PORT"
log "   User: $WEB_USER"
log "   LAN Address: $PRIMARY_IP:$AVAILABLE_PORT"

# Start rclone in FOREGROUND (no nohup, no &)
# This keeps the script running so LaunchAgent can monitor it
# 🛡️ Sentinel: Use env vars for credentials to hide them from process list (ps aux)
export RCLONE_USER="$WEB_USER"
export RCLONE_PASS="$WEB_PASS"

# Use a dedicated VFS cache directory so the WebDAV daemon doesn't share
# state with the NFS daemon (both serve the same `media:` remote and would
# otherwise collide on rclone's default cache path).
WEBDAV_CACHE_DIR="$HOME/Library/Caches/rclone-media-webdav"
mkdir -p "$WEBDAV_CACHE_DIR"

exec rclone serve webdav "media:" \
	--addr "0.0.0.0:$AVAILABLE_PORT" \
	--cache-dir "$WEBDAV_CACHE_DIR" \
	--vfs-cache-mode full \
	--vfs-cache-max-size 10G \
	--vfs-cache-max-age 24h \
	--vfs-read-chunk-size 32M \
	--vfs-read-chunk-size-limit 1G \
	--transfers 8 \
	--checkers 16 \
	--read-only \
	--no-modtime \
	--timeout 1m \
	--contimeout 15s \
	--low-level-retries 10 \
	--dir-cache-time 1000h \
	--poll-interval 1m \
	--vfs-read-ahead 128M
