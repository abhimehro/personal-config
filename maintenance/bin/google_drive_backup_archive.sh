#!/usr/bin/env bash
set -euo pipefail

# Google Drive Backup (Archive-based)
# Wrapper around protondrive_backup_archive.sh that targets Google Drive.
#
# IMPORTANT:
#   On macOS, Google Drive exposes multiple roots under CloudStorage.
#   The writable area is typically under "My Drive".

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
ARCHIVER="$SCRIPT_DIR/protondrive_backup_archive.sh"

GDRIVE_ROOT_DEFAULT="$HOME/Library/CloudStorage/GoogleDrive-abhimhrtr@gmail.com"
# Prefer storing in My Drive (writable) rather than the CloudStorage root.
DEST_DIR_DEFAULT="$GDRIVE_ROOT_DEFAULT/My Drive/Backups/MaintenanceArchives"

if [[ ! -x "$ARCHIVER" ]]; then
  echo "Missing archiver: $ARCHIVER" >&2
  exit 1
fi

# Default to the low-impact profile for daily backups.
PROFILE_DEFAULT="light"

exec /bin/bash "$ARCHIVER" \
  --label "HomeBackup" \
  --cloud-root "${GDRIVE_ROOT_DEFAULT}" \
  --dest-dir "${DEST_DIR_DEFAULT}" \
  --profile "${PROFILE_DEFAULT}" \
  "$@"
