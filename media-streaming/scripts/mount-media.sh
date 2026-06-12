#!/bin/bash
#
# Mount Media — Native macOS FSKit Mount
# Mounts the rclone unified "media:" remote directly to ~/CloudMedia/mounted
# leveraging the macOS native FSKit kernel-less architecture.
#
# SAFEGUARDS:
# - Validates mount point is empty before mounting
# - Cleans up stale directory entries from previous mounts
# - Verifies successful unmount before proceeding
# - Uses unique cache directory per mount session
# - Logs all operations for debugging
#
set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

MOUNT_POINT="$HOME/CloudMedia/mounted"
CACHE_DIR="$HOME/Library/Caches/rclone-media-mount"
MAX_RETRIES=3
RETRY_DELAY=2

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

notify() {
	local title="$1"
	local message="$2"
	if command -v terminal-notifier &>/dev/null; then
		terminal-notifier -title "$title" -message "$message" -sound default
	elif command -v osascript &>/dev/null; then
		osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title (item 2 of argv)' -e 'end run' "$message" "$title" 2>/dev/null || true
	fi
}

# Safeguard: Clean up stale mount directory entries
# This removes any leftover files/directories from previous failed mounts
cleanup_stale_mount() {
	local mount_dir="$1"

	# Check if directory exists but is not a valid mount point
	if [[ -d $mount_dir ]]; then
		# Verify it's actually a mount point
		if ! mount | grep -Fq " on $mount_dir ("; then
			log "🧹 Cleaning up stale mount directory: $mount_dir"

			# Try to remove the directory and its contents
			# Use retry logic in case files are busy
			local retry
			retry=0
			while [[ $retry -lt $MAX_RETRIES ]]; do
				if rm -rf "$mount_dir" 2>/dev/null; then
					log "✅ Successfully cleaned up stale mount directory"
					mkdir -p "$mount_dir"
					return 0
				else
					retry=$((retry + 1))
					log "⚠️  Attempt $retry/$MAX_RETRIES: Could not remove $mount_dir (may be busy)"
					sleep $RETRY_DELAY
				fi
			done

			log "❌ Failed to clean up stale mount directory after $MAX_RETRIES attempts"
			log "   Manual cleanup required: rm -rf \"$mount_dir\""
			notify "Mount Error" "Failed to clean stale mount at $mount_dir. Manual cleanup needed."
			return 1
		fi
	fi
}

log "🔌 Starting Native FSKit Mount..."

# SAFEGUARD 1: Clean up any stale mount directory before starting
log "🛡️  Safeguard: Checking for stale mount directory..."
cleanup_stale_mount "$MOUNT_POINT" || exit 1

# Create necessary directories
mkdir -p "$MOUNT_POINT"
mkdir -p "$CACHE_DIR"

# Check rclone remote
if ! rclone listremotes 2>/dev/null | grep -q "media:"; then
	log "ERROR: 'media:' remote not found in rclone configuration"
	exit 1
fi

# SAFEGUARD 2: Verify mount point is empty before mounting
log "🛡️  Safeguard: Verifying mount point is empty..."
if [[ -n "$(ls -A "$MOUNT_POINT" 2>/dev/null)" ]]; then
	log "ERROR: Mount point $MOUNT_POINT is not empty. Contents:"
	find "$MOUNT_POINT" -maxdepth 1 -mindepth 1 2>/dev/null | head -20
	log "ERROR: Refusing to mount over non-empty directory"
	exit 1
fi

# SAFEGUARD 3: Ensure any existing mount points are properly unmounted
if mount | grep -Fq " on $MOUNT_POINT ("; then
	log "⚠️  Existing mount detected at $MOUNT_POINT. Unmounting cleanly..."

	retry=0
	while [[ $retry -lt $MAX_RETRIES ]]; do
		if diskutil unmount force "$MOUNT_POINT" 2>/dev/null; then
			log "✅ Successfully unmounted existing mount"

			# SAFEGUARD 4: Verify unmount was successful
			if ! mount | grep -Fq " on $MOUNT_POINT ("; then
				log "✅ Verified: Mount point is no longer active"
				sleep 2
				break
			else
				log "⚠️  Mount still appears active, retrying..."
				retry=$((retry + 1))
				sleep $RETRY_DELAY
				continue
			fi
		else
			retry=$((retry + 1))
			log "⚠️  Attempt $retry/$MAX_RETRIES: Unmount failed"
			sleep $RETRY_DELAY
		fi
	done

	if [[ $retry -ge $MAX_RETRIES ]]; then
		log "❌ Failed to unmount existing mount after $MAX_RETRIES attempts"
		log "   Manual intervention required"
		notify "Mount Error" "Failed to unmount $MOUNT_POINT. Check logs."
		exit 1
	fi
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
