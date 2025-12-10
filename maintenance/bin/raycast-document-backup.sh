#!/usr/bin/env bash
# @raycast.schemaVersion 1
# @raycast.title Document Backup
# @raycast.mode fullOutput
# @raycast.packageName Maintenance
# @raycast.icon 💾
# @raycast.description Backup Documents/Desktop/Scripts and key configs

set -euo pipefail

TARGET="${TARGET_DOC_BACKUP_SCRIPT:-$HOME/Library/Maintenance/bin/document_backup.sh}"
if [[ ! -x "$TARGET" ]]; then
  echo "❌ document_backup.sh not found at $TARGET"
  exit 1
fi

bash "$TARGET"
