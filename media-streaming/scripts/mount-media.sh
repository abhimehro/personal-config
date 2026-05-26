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
STATE_DIR="$HOME/.local/state/media-mount"
LAST_NOTIFY_FILE="$STATE_DIR/last-notify"
NOTIFY_COOLDOWN_SECONDS=1800

log() {
	# Note: stdout is redirected to $LOG_FILE by the LaunchAgent plist, so plain
	# echo is sufficient there. When run interactively, callers can tee manually.
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
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

mkdir -p "$(dirname "$LOG_FILE")" "$STATE_DIR"

mount_is_registered() {
	mount | grep -Fq " on $MOUNT_POINT ("
}

nfs_server_is_listening() {
	nc -z "$NFS_HOST" "$NFS_PORT" 2>/dev/null
}

notify_mount_success() {
	local now last=0
	now=$(date +%s)
	[[ -f $LAST_NOTIFY_FILE ]] && last=$(cat "$LAST_NOTIFY_FILE" 2>/dev/null || echo 0)

	# Avoid repeated user notifications when launchd checks the mount frequently.
	if ((now - last < NOTIFY_COOLDOWN_SECONDS)); then
		return 0
	fi

	echo "$now" >"$LAST_NOTIFY_FILE"
	notify "Media Library Mounted" "Cloud media is now available at $MOUNT_POINT"
}

# --- Timeout Helper ---
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

# --- Health Check ---
# A mount is considered healthy if it is registered AND a timeout-protected
# `ls` check returns without error. We use a relaxed 15-second timeout to prevent
# false-positives on cold-starts, while still allowing recovery from stale mounts.
if mount_is_registered; then
	if run_with_timeout 15 ls "$MOUNT_POINT" &>/dev/null; then
		exit 0
	else
		log "⚠️  Stale mount detected (unresponsive). Unmounting..."
		diskutil unmount force "$MOUNT_POINT" 2>/dev/null || true
		sleep 2
	fi
fi

# --- Dependency Check ---
# Wait up to 30 seconds for the NFS server to be ready (handles boot delays)
MAX_RETRIES=6
RETRY_COUNT=0
while ! nc -z "$NFS_HOST" "$NFS_PORT" 2>/dev/null; do
	if ((RETRY_COUNT >= MAX_RETRIES)); then
		log "ERROR: NFS server not available on port $NFS_PORT after 30s. Aborting."
		exit 1
	fi
	log "Waiting for NFS server..."
	sleep 5
	# Guard against set -e: ((var++)) returns the pre-increment value, which is
	# 0 (falsy) on the first iteration and would abort the script.
	((RETRY_COUNT++)) || true
done

# --- Mount ---
mkdir -p "$MOUNT_POINT"

log "Mounting NFS → $MOUNT_POINT"
# Options:
# - nolock: Required because rclone NFS doesn't support NLM
# - locallocks: Enable local file locking on macOS
# - resvport: Usually needed for macOS NFS, but localhost works without it if rclone allows
# - tcp: Ensure TCP is used
# - port/mountport: Direct both to rclone's unified NFS port
# - soft,intr: Allow interruption on network drops
# - timeo/retrans: Fail fast if server goes unresponsive (avoid system hangs)
# - deadtimeout: Force-unmount dead connections fast to dismiss macOS system alerts
if mount_nfs -o "port=$NFS_PORT,mountport=$NFS_PORT,nolock,locallocks,tcp,soft,intr,timeo=150,retrans=3,deadtimeout=300" "$NFS_HOST:/" "$MOUNT_POINT" 2>&1; then
	sleep 2
	if mount_is_registered; then
		log "✅ Mount successful"
		notify_mount_success
	else
		log "ERROR: mount_nfs returned 0 but drive is not in mount list"
		exit 1
	fi
else
	log "ERROR: mount_nfs failed"
	exit 1
fi
