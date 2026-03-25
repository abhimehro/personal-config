#!/usr/bin/env bash
#
# Control D DNS Configuration Enforcement Script (Separation Strategy aware)
# Ensures that when Control D mode is active, the network state remains
# consistent. This script now delegates to the unified network-mode-manager
# rather than directly forcing DNS/IPv4/IPv6, to avoid fighting Windscribe.
#
# Usage: bash controld-ensure.sh
# Auto-runs via LaunchAgent at login
#
# Last Updated: Phase 1 Separation Strategy

set -euo pipefail

LOG_FILE="$HOME/Library/Logs/controld-ensure.log"
MANAGER_SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/scripts/network-mode-manager.sh"
VERIFY_SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/scripts/network-mode-verify.sh"

log() {
	# Capture timestamp once so each log entry is consistent
	local ts
	ts="$(date '+%Y-%m-%d %H:%M:%S')"

	{
		# Print timestamp prefix
		printf '[%s] ' "$ts"

		# Safely print all arguments on a single line, preserving boundaries.
		# We avoid `$*` because it joins arguments using IFS and can mangle
		# arguments with spaces or empty strings.
		if [ "$#" -gt 0 ]; then
			printf '%s' "$1"
			shift
			for arg in "$@"; do
				printf ' %s' "$arg"
			done
		fi
		printf '\n'
	} | tee -a "$LOG_FILE"
}

main() {
	log "🚀 Starting Control D DNS enforcement (Separation Strategy)..."

	if [[ $EUID -eq 0 ]]; then
		log "❌ Do not run this script as root. It will prompt for sudo when needed."
		exit 1
	fi

	if [[ ! -x $MANAGER_SCRIPT ]]; then
		log "❌ network-mode-manager.sh not found or not executable at \"$MANAGER_SCRIPT\""
		exit 1
	fi

	if [[ ! -x $VERIFY_SCRIPT ]]; then
		log "❌ network-mode-verify.sh not found or not executable at \"$VERIFY_SCRIPT\""
		exit 1
	fi

	# Give the system a moment to stabilize at login
	sleep 2

	# Ensure Control D DNS mode is active using the default browsing profile
	log "🔧 Ensuring Control D DNS mode is active (browsing profile)..."
	"$MANAGER_SCRIPT" controld browsing || log "⚠️  Manager reported issues switching to Control D mode."

	# Run verification for CONTROL D ACTIVE state
	log "🧪 Running Control D verification..."
	if "$VERIFY_SCRIPT" controld; then
		log "🎉 Control D DNS configuration verified successfully."
		log "📊 You can also verify via: https://verify.controld.com"
		exit 0
	else
		log "❌ Control D DNS verification failed. Manual troubleshooting may be required."
		exit 1
	fi
}

main "$@"
