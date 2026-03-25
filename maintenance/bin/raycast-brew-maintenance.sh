#!/usr/bin/env bash
# @raycast.schemaVersion 1
# @raycast.title Homebrew Maintenance
# @raycast.mode fullOutput
# @raycast.packageName Maintenance
# @raycast.icon 🍺
# @raycast.description Run Homebrew maintenance via personal-config

set -euo pipefail

TARGET="${TARGET_BREW_SCRIPT:-$HOME/Library/Maintenance/bin/brew_maintenance.sh}"
if [[ ! -x $TARGET ]]; then
	echo "❌ brew_maintenance.sh not found at $TARGET"
	exit 1
fi

bash "$TARGET"
