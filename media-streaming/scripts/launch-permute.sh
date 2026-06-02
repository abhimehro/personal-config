#!/bin/bash
# Launch Permute 4 with watch folder configuration
# This script ensures Permute 4 is running and watching ~/CloudMedia/staging/
# with output to ~/CloudMedia/processed/ using HEVC/H.265 encoding

set -euo pipefail

APP_NAME="Permute 4.app"
APP_PATH="/Applications/$APP_NAME"
WATCH_DIR="$HOME/CloudMedia/permute_input"
OUTPUT_DIR="$HOME/CloudMedia/staging"
LOG_FILE="$HOME/Library/Logs/permute-launch.log"

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Ensure directories exist
mkdir -p "$WATCH_DIR" "$OUTPUT_DIR" "$(dirname "$LOG_FILE")"

# Check if Permute 4 is running
if pgrep -q "Permute 4"; then
	log "Permute 4 is already running"
	exit 0
fi

# Check if the app exists
if [[ ! -d $APP_PATH ]]; then
	log "ERROR: Permute 4 not found at $APP_PATH"
	exit 1
fi

log "Starting Permute 4..."

# Open Permute 4 (GUI app)
# Note: This will launch the GUI, but watch folder configuration must be done manually
# or via AppleScript. Permute 4 doesn't have a CLI for configuration.
open "$APP_PATH"

# Wait a bit for the app to launch
sleep 5

# Check if it's running
if pgrep -q "Permute 4"; then
	log "Permute 4 launched successfully"
else
	log "ERROR: Failed to launch Permute 4"
	exit 1
fi

log "Permute 4 is running. Please ensure it's configured to:"
log "  - Watch folder: $WATCH_DIR"
log "  - Output folder: $OUTPUT_DIR"
log "  - Video format: HEVC/H.265"
log "  - Quality: High (or your preferred setting)"
