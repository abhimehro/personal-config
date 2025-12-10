#!/usr/bin/env bash
# @raycast.schemaVersion 1
# @raycast.title Package Updates
# @raycast.mode fullOutput
# @raycast.packageName Maintenance
# @raycast.icon 📦
# @raycast.description Update package managers (npm/pip/gem/cargo/mas)

set -euo pipefail

TARGET="${TARGET_PACKAGE_UPDATES_SCRIPT:-$HOME/Library/Maintenance/bin/package_updates.sh}"
if [[ ! -x "$TARGET" ]]; then
  echo "❌ package_updates.sh not found at $TARGET"
  exit 1
fi

bash "$TARGET"
