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

# Find available port
AVAILABLE_PORT=8080
for port in 8080 8081 8082 8083; do
	if ! lsof -nP -i:$port 2>/dev/null | grep -q LISTEN; then
		AVAILABLE_PORT=$port
		break
	fi
done

log "Using port: $AVAILABLE_PORT"

# Check rclone remote
if ! rclone listremotes 2>/dev/null | grep -q "media:"; then
	log "ERROR: 'media:' remote not found"
	exit 1
fi

# Get credentials (try 1Password first with 3s timeout)
log "Loading credentials from 1Password..."
WEB_USER=""
WEB_PASS=""
if command -v op &>/dev/null; then
	WEB_USER=$(run_with_timeout 3 op read "op://Personal/MediaServer/username" 2>/dev/null) || WEB_USER=""
	WEB_PASS=$(run_with_timeout 3 op read "op://Personal/MediaServer/password" 2>/dev/null) || WEB_PASS=""
fi

if [[ -z $WEB_USER || -z $WEB_PASS ]]; then
	log "⚠️  1Password locked or unavailable, using secure local fallback"
	WEB_USER="infuse"
	WEB_PASS="MALARIA7bunch!katarina"
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
	--timeout 10s \
	--contimeout 5s \
	--low-level-retries 2
