#!/usr/bin/env bash
# @raycast.schemaVersion 1
# @raycast.title Dev Maintenance
# @raycast.mode fullOutput
# @raycast.packageName Maintenance
# @raycast.icon 🛠️
# @raycast.description Update dev toolchains (npm/yarn/pip/gem/rust) and clean caches

set -euo pipefail

TARGET="${TARGET_DEV_MAINT_SCRIPT:-$HOME/Library/Maintenance/bin/dev_maintenance.sh}"
if [[ ! -x $TARGET ]]; then
	echo "❌ dev_maintenance.sh not found at $TARGET"
	exit 1
fi

bash "$TARGET"
