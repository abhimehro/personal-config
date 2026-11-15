#!/bin/bash
# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Play/Pause Kaset
# @raycast.mode silent
# Optional parameters:
# @raycast.packageName Kaset
# @raycast.description Toggle play/pause in the Kaset YouTube Music player
# @raycast.author Abhi Mehrotra

set -euo pipefail

if ! pgrep -qx "Kaset" && ! pgrep -qf "/Applications/Kaset.app/Contents/MacOS/Kaset"; then
	open -a "Kaset"
	sleep 1
fi

osascript -e 'tell application "Kaset" to playpause'
