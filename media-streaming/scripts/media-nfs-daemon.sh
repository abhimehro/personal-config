#!/bin/bash
#
# Media NFS Server - Foreground Runner for LaunchAgent
# Provides high-performance NFS access specifically for Plex on macOS
#
set -euo pipefail

# Set PATH
export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Logging function
log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "📡 Media NFS Server - Starting..."

# Kill any existing rclone NFS servers
pkill -f "rclone serve nfs" 2>/dev/null || true
sleep 2

# Check rclone remote
if ! rclone listremotes 2>/dev/null | grep -q "media:"; then
	log "ERROR: 'media:' remote not found"
	exit 1
fi

# Configuration
NFS_PORT=12049
BIND_ADDR="localhost"

log "🚀 Starting rclone NFS server on $BIND_ADDR:$NFS_PORT"

# Start rclone in FOREGROUND
# Note: NFS in rclone currently doesn't require/support user/pass auth
# We bind to localhost to keep it secure.
# Use a dedicated VFS cache directory so the NFS daemon doesn't share state
# with the WebDAV daemon (both serve the same `media:` remote and would
# otherwise collide on rclone's default cache path).
NFS_CACHE_DIR="$HOME/Library/Caches/rclone-media-nfs"
mkdir -p "$NFS_CACHE_DIR"

exec rclone serve nfs "media:" \
	--addr "$BIND_ADDR:$NFS_PORT" \
	--cache-dir "$NFS_CACHE_DIR" \
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
