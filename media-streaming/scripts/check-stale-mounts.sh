#!/bin/bash
#
# check-stale-mounts.sh - Monitor for stale fuse mounts
#
# This script checks for stale rclone/fuse mounts that may have left
# directory entries behind, causing false disk usage reporting.
#
# Usage:
#   bash check-stale-mounts.sh          # Check all common mount points
#   bash check-stale-mounts.sh /path    # Check specific mount point
#   bash check-stale-mounts.sh --fix    # Attempt to fix issues found
#
set -euo pipefail

FIX_MODE=false
MOUNT_POINTS=()

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

notify() {
	local title="$1"
	local message="$2"
	if command -v terminal-notifier &>/dev/null; then
		terminal-notifier -title "$title" -message "$message" -sound default
	elif command -v osascript &>/dev/null; then
		osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title (item 2 of argv)' -e 'end run' -- "$message" "$title" 2>/dev/null || true
	fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
	case "$1" in
	--fix)
		FIX_MODE=true
		shift
		;;
	--help | -h)
		echo "Usage: $0 [--fix] [mount_point1 mount_point2 ...]"
		echo "  --fix    Attempt to clean up stale mounts"
		echo "  Without args: Checks common mount points"
		exit 0
		;;
	-*)
		echo "Unknown option: $1"
		exit 1
		;;
	*)
		MOUNT_POINTS+=("$1")
		shift
		;;
	esac
done

# Default mount points to check
if [[ ${#MOUNT_POINTS[@]} -eq 0 ]]; then
	MOUNT_POINTS=(
		"$HOME/CloudMedia/mounted"
		"$HOME/CloudMedia/test_mount"
		"$HOME/mnt/media"
		"$HOME/mnt/gdrive"
		"$HOME/mnt/rclone"
	)
fi

check_mount_point() {
	local mount_point="$1"

	# Check if directory exists
	if [[ ! -d $mount_point ]]; then
		log "✅ $mount_point: Does not exist (clean)"
		return 0
	fi

	# Check if it's a valid mount point
	if mount | grep -Fq " on $mount_point ("; then
		log "✅ $mount_point: Active mount (valid)"
		return 0
	fi

	# Check if directory has content (potential stale mount)
	if [[ -n "$(ls -A "$mount_point" 2>/dev/null)" ]]; then
		local file_count
		file_count=$(find "$mount_point" -maxdepth 1 -mindepth 1 2>/dev/null | wc -l)
		log "⚠️  $mount_point: Directory exists with $file_count entries but is NOT mounted"

		if [[ $FIX_MODE == "true" ]]; then
			log "   🛠️  Attempting cleanup..."
			if cleanup_stale_mount "$mount_point"; then
				log "   ✅ Cleanup successful"
			else
				log "   ❌ Cleanup failed - manual intervention required"
				log "      Run: rm -rf \"$mount_point\""
			fi
		else
			log "   💡 Run with --fix to attempt cleanup"
		fi
	else
		log "✅ $mount_point: Empty directory (safe)"
	fi

	return 0
}

cleanup_stale_mount() {
	local mount_point="$1"
	local max_retries=3
	local retry_delay=2

	for ((retry = 0; retry < max_retries; retry++)); do
		if rm -rf "$mount_point" 2>/dev/null; then
			mkdir -p "$mount_point"
			return 0
		else
			log "   ⚠️  Attempt $((retry + 1))/$max_retries: Could not remove (files may be busy)"
			sleep $retry_delay
		fi
	done

	return 1
}

# Main execution
log "=== Stale Mount Check Started ==="
log "Fix mode: $FIX_MODE"
log ""

issues_found=0
for mount_point in "${MOUNT_POINTS[@]}"; do
	if ! check_mount_point "$mount_point"; then
		issues_found=$((issues_found + 1))
	fi
done

log ""
if [[ $issues_found -eq 0 ]]; then
	log "✅ No stale mounts detected"
	notify "Stale Mount Check" "No issues found - all mounts clean"
else
	log "⚠️  Found $issues_found potential stale mount(s)"
	notify "Stale Mount Check" "Found $issues_found potential stale mount(s)"
fi

log "=== Stale Mount Check Complete ==="

exit $issues_found
