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
pkill -f "rclone serve nfs media:" 2>/dev/null || true
sleep 2

# Check rclone remote
if ! rclone listremotes 2>/dev/null | grep -qx "media:"; then
	log "ERROR: 'media:' remote not found"
	exit 1
fi

# Configuration
NFS_PORT=12049
BIND_ADDR="localhost"

log "🚀 Starting rclone NFS server on $BIND_ADDR:$NFS_PORT"

# Start rclone in FOREGROUND.
# Note: NFS in rclone currently doesn't require/support user/pass auth;
# we bind to localhost to keep it secure. The cache is isolated from the
# WebDAV daemon to avoid two rclone processes contending over the same
# cache directory for the shared `media:` remote.
exec rclone serve nfs "media:" \
	--addr "$BIND_ADDR:$NFS_PORT" \
	--cache-dir "$HOME/Library/Caches/rclone-vfs/nfs" \
	--vfs-cache-mode full \
	--vfs-cache-max-size 10G \
	--vfs-cache-max-age 24h \
	--vfs-read-chunk-size 32M \
	--vfs-read-chunk-size-limit 1G \
	--transfers 8 \
	--checkers 16 \
	--read-only \
	--no-modtime
