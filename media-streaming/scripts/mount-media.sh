#!/bin/bash
#
# Mount Media — Native macOS FSKit Mount
# Mounts the rclone unified "media:" remote directly to ~/CloudMedia/mounted
# leveraging the macOS native FSKit kernel-less architecture.
#
set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

MOUNT_POINT="$HOME/CloudMedia/mounted"
LOG_FILE="$HOME/Library/Logs/media-mount.log"
CACHE_DIR="$HOME/Library/Caches/rclone-media-mount"

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "🔌 Starting Native FSKit Mount..."

# Create necessary directories
mkdir -p "$MOUNT_POINT"
mkdir -p "$CACHE_DIR"

# Check rclone remote
if ! rclone listremotes 2>/dev/null | grep -q "media:"; then
	log "ERROR: 'media:' remote not found in rclone configuration"
	exit 1
fi

# Ensure any existing mount points are unmounted before we begin
if mount | grep -Fq " on $MOUNT_POINT ("; then
	log "⚠️  Existing mount detected at $MOUNT_POINT. Unmounting cleanly..."
	diskutil unmount force "$MOUNT_POINT" 2>/dev/null || true
	sleep 2
fi

log "🚀 Launching native FSKit rclone mount for 'media:' at $MOUNT_POINT"
log "   VFS Cache: 10GB Bounded in $CACHE_DIR"

# Mount in FOREGROUND. The launchd agent is KeepAlive and will track this process.
# FSKit mount uses the backend specified in fuse-t.ini (backend=fskit)
exec rclone mount "media:" "$MOUNT_POINT" \
	--cache-dir "$CACHE_DIR" \
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
