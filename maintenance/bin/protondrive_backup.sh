#!/usr/bin/env bash
set -euo pipefail

# One-way incremental backup from $HOME into ProtonDrive using rsync.
# Defaults to --dry-run for safety.

PROTON_ROOT_DEFAULT="$HOME/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder"
DEST_DEFAULT="$PROTON_ROOT_DEFAULT/HomeBackup"

if [[ -n "${MAINTENANCE_HOME:-}" ]]; then
  EXCLUDES_FILE_DEFAULT="$MAINTENANCE_HOME/conf/protondrive_backup.exclude"
else
  EXCLUDES_FILE_DEFAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/protondrive_backup.exclude"
fi

usage() {
  cat <<'EOF'
Usage:
  protondrive_backup.sh [--run] [--dry-run] [--no-delete] [--dest PATH] [--proton-root PATH] [--excludes FILE]

Notes:
  - Default mode is --dry-run (shows what WOULD be backed up).
  - --run performs the actual sync (USE WITH CAUTION).
  - --no-delete disables mirror deletions (safer, but destination can accumulate).
  
Examples:
  # Preview what will be backed up (safe)
  ./protondrive_backup.sh
  
  # Actually perform the backup
  ./protondrive_backup.sh --run
  
  # Backup without deleting files from destination
  ./protondrive_backup.sh --run --no-delete
EOF
}

DRY_RUN=1
DELETE=1
PROTON_ROOT="$PROTON_ROOT_DEFAULT"
DEST="$DEST_DEFAULT"
EXCLUDES_FILE="$EXCLUDES_FILE_DEFAULT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run) DRY_RUN=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-delete) DELETE=0; shift ;;
    --proton-root) PROTON_ROOT="$2"; shift 2 ;;
    --dest) DEST="$2"; shift 2 ;;
    --excludes) EXCLUDES_FILE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ ! -d "$PROTON_ROOT" ]]; then
  echo "ERROR: ProtonDrive root not found: $PROTON_ROOT" >&2
  echo "Make sure Proton Drive is mounted and syncing." >&2
  exit 1
fi

if [[ ! -f "$EXCLUDES_FILE" ]]; then
  echo "WARNING: Excludes file not found: $EXCLUDES_FILE" >&2
  echo "Proceeding without exclusions (not recommended)." >&2
  echo "Consider creating an exclude file to skip cache/tmp directories." >&2
fi

mkdir -p "$DEST"

# macOS ships an older rsync, so stick to widely supported flags.
# -a: archive mode (recursive, preserve permissions, times, etc.)
# -E: preserve extended attributes (important for macOS)
# --delete-after: delete extraneous files from dest dirs AFTER transfer
# --ignore-errors: keep going even if some files fail
# --partial: keep partially transferred files
# --human-readable: output numbers in human-readable format
# --stats: print transfer statistics
RSYNC=(/usr/bin/rsync -aE --ignore-errors --partial --human-readable --stats)

# Add exclude file if it exists
if [[ -f "$EXCLUDES_FILE" ]]; then
  RSYNC+=(--exclude-from="$EXCLUDES_FILE")
fi

# Add delete option if enabled
if [[ $DELETE -eq 1 ]]; then
  RSYNC+=(--delete-after)
fi

# Add dry-run if enabled
if [[ $DRY_RUN -eq 1 ]]; then
  RSYNC+=(--dry-run)
  echo "=========================================="
  echo "DRY RUN MODE - No changes will be made"
  echo "Run with --run to actually perform backup"
  echo "=========================================="
  echo ""
fi

require_path() {
  local p="$1"
  if [[ ! -e "$p" ]]; then
    echo "Skipping missing path: $p" >&2
    return 1
  fi
  return 0
}

CORE=(
  "$HOME/Documents"
  "$HOME/Desktop"
  "$HOME/Downloads"
  "$HOME/Pictures"
  "$HOME/Movies"
  "$HOME/Public"
  "$HOME/Applications"
  "$HOME/CloudMedia"
  "$HOME/FontBase"
  "$HOME/Backups"
)

DOTFILES=(
  "$HOME/.bashrc"
  "$HOME/.gitconfig"
  "$HOME/.zshrc"
  "$HOME/.aws"
  "$HOME/.cargo"
  "$HOME/.config"
  "$HOME/.filebot"
  "$HOME/.gemini"
  "$HOME/.jules"
  "$HOME/.local"
  "$HOME/.vscode-R"
  "$HOME/.warp"
)

run_rsync_relative() {
  local label="$1"; shift
  local -a items=("$@")

  echo ""
  echo "==> Backing up: $label"
  echo ""

  local -a existing=()
  for p in "${items[@]}"; do
    if require_path "$p"; then
      existing+=("$p")
    fi
  done

  if [[ ${#existing[@]} -eq 0 ]]; then
    echo "No paths exist for $label; skipping." >&2
    return 0
  fi

  # Run rsync and capture exit code
  set +e
  "${RSYNC[@]}" --relative "${existing[@]}" "$DEST/"
  local rc=$?
  set -e

  # rsync exit codes:
  # 0 = success
  # 23 = "Partial transfer due to error" (common with ._* files)
  # 24 = "Partial transfer due to vanished source files" (common on macOS)
  if [[ $rc -eq 0 ]]; then
    echo "✅ $label backup completed successfully"
  elif [[ $rc -eq 23 ]]; then
    echo "⚠️  $label backup completed with some file errors (exit code 23)"
    echo "This is usually caused by macOS resource fork (._*) files and can be safely ignored."
  elif [[ $rc -eq 24 ]]; then
    echo "⚠️  $label backup completed with some vanished files (exit code 24)"
    echo "This is normal - some files were deleted/moved during backup."
  else
    echo "❌ $label backup failed with exit code: $rc" >&2
    return $rc
  fi

  return 0
}

# Track overall success
BACKUP_ERRORS=0

# Run backups
run_rsync_relative "core directories" "${CORE[@]}" || ((BACKUP_ERRORS++))
run_rsync_relative "dotfiles/config" "${DOTFILES[@]}" || ((BACKUP_ERRORS++))

echo ""
echo "=========================================="
echo "Backup Summary"
echo "=========================================="
echo "Destination: $DEST"
echo "Delete enabled: $([[ $DELETE -eq 1 ]] && echo "Yes" || echo "No")"

if [[ $DRY_RUN -eq 1 ]]; then
  echo ""
  echo "⚠️  DRY RUN MODE - No changes were made"
  echo "Re-run with --run to actually perform backup:"
  echo "  $0 --run"
else
  echo ""
  if [[ $BACKUP_ERRORS -eq 0 ]]; then
    echo "✅ Backup completed successfully!"
  else
    echo "⚠️  Backup completed with $BACKUP_ERRORS errors"
    echo "Check the output above for details."
  fi
fi
echo "=========================================="
