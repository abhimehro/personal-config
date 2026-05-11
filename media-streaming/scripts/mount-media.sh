#!/bin/bash
#
# Mount Media — Native macOS NFS Mount
# Bridges the rclone NFS server to ~/CloudMedia/mounted/
#
# This is the "Zero-Copy" bridge for Plex and FileBot.
#
set -euo pipefail

export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

MOUNT_POINT="$HOME/CloudMedia/mounted"
NFS_HOST="localhost"
NFS_PORT=12049
LOG_FILE="$HOME/Library/Logs/media-mount.log"

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

notify() {
	local title="$1"
	local message="$2"
	if command -v terminal-notifier &>/dev/null; then
		terminal-notifier -title "$title" -message "$message" -sound default
	elif command -v osascript &>/dev/null; then
		local esc_title="${title//\"/\\\"}"
		local esc_message="${message//\"/\\\"}"
		osascript -e "display notification \"$esc_message\" with title \"$esc_title\"" 2>/dev/null || true
	fi
}

mkdir -p "$(dirname "$LOG_FILE")"

# --- Health Check ---
if mount | grep -q "$MOUNT_POINT"; then
	if ls "$MOUNT_POINT" &>/dev/null && [[ -n "$(ls -A "$MOUNT_POINT" 2>/dev/null)" ]]; then
		# Already mounted and healthy
		exit 0
	else
		log "⚠️  Stale mount detected. Unmounting..."
		diskutil unmount force "$MOUNT_POINT" 2>/dev/null || true
		sleep 2
	fi
fi

# --- Dependency Check ---
# Wait up to 30 seconds for the NFS server to be ready (handles boot delays)
MAX_RETRIES=6
RETRY_COUNT=0
while ! nc -z "$NFS_HOST" "$NFS_PORT" 2>/dev/null; do
	if (( RETRY_COUNT >= MAX_RETRIES )); then
		log "ERROR: NFS server not available on port $NFS_PORT after 30s. Aborting."
		exit 1
	fi
	log "Waiting for NFS server..."
	sleep 5
	((RETRY_COUNT++))
done

# --- Mount ---
mkdir -p "$MOUNT_POINT"

log "Mounting NFS → $MOUNT_POINT"
# Options:
# - nolock: Required because rclone NFS doesn't support NLM
# - resvport: Usually needed for macOS NFS, but localhost works without it if rclone allows
# - tcp: Ensure TCP is used
# - port/mountport: Direct both to rclone's unified NFS port
if sudo mount_nfs -o "port=$NFS_PORT,mountport=$NFS_PORT,nolock,tcp,soft,intr" "$NFS_HOST:/" "$MOUNT_POINT"; then
	sleep 2
	if mount | grep -q "$MOUNT_POINT"; then
		log "✅ Mount successful"
		notify "Media Library Mounted" "Cloud media is now available at $MOUNT_POINT"
	else
		log "ERROR: mount_nfs returned 0 but drive is not in mount list"
		exit 1
	fi
else
	log "ERROR: mount_nfs failed"
	exit 1
fi
