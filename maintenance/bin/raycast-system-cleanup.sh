#!/usr/bin/env bash
# @raycast.schemaVersion 1
# @raycast.title System Cleanup
# @raycast.mode fullOutput
# @raycast.packageName Maintenance
# @raycast.icon 🧹
# @raycast.description Clean caches/temp/logs via personal-config

set -euo pipefail

TARGET="${TARGET_CLEANUP_SCRIPT:-$HOME/Library/Maintenance/bin/system_cleanup.sh}"
if [[ ! -x "$TARGET" ]]; then
  echo "❌ system_cleanup.sh not found at $TARGET"
  exit 1
fi

bash "$TARGET"
