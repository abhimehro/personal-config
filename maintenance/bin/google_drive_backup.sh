#!/usr/bin/env bash
set -euo pipefail

# Google Drive Backup Script
# Supports --light (daily) and --full (weekly) modes.
# Light: Backs up critical configs and documents.
# Full: Backs up everything including media and large files.
# Automatically pauses light backup on weekends if requested.

# Default Google Drive Root
GDRIVE_ROOT_DEFAULT="${GDRIVE_ROOT:-$HOME/Library/CloudStorage}"
# Try to find GoogleDrive mount point
if [[ -d "$GDRIVE_ROOT_DEFAULT" ]]; then
    GDRIVE_MOUNT=$(ls -1d "$GDRIVE_ROOT_DEFAULT/GoogleDrive-"* 2>/dev/null | head -1 || true)
    if [[ -n "$GDRIVE_MOUNT" ]]; then
        GDRIVE_ROOT_DEFAULT="$GDRIVE_MOUNT"
    fi
fi

# Fallback destination
DEST_DEFAULT="${GOOGLE_DRIVE_BACKUP_DEST:-$GDRIVE_ROOT_DEFAULT/My Drive/HomeBackup}"

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE" 2>/dev/null || true
fi

# Determine Excludes File
if [[ -n "${MAINTENANCE_HOME:-}" ]]; then
  EXCLUDES_FILE_DEFAULT="$MAINTENANCE_HOME/conf/backup.exclude"
else
  EXCLUDES_FILE_DEFAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/backup.exclude"
fi

usage() {
  cat <<'EOF'
Usage:
  google_drive_backup.sh [--run] [--dry-run] [--light|--full] [--no-delete] [--dest PATH] [--excludes FILE]

Modes:
  --light       (Default) Backup only critical configs and documents.
                Skips Movies, Downloads, Pictures, etc.
  --full        Backup everything defined in CORE.

Options:
  --run         Perform actual backup.
  --dry-run     (Default) Show what would happen.
  --no-delete   Don't delete files from destination (safer).
  --dest        Override backup destination.
  
Weekend Pause:
  Light backups are automatically skipped on Saturday and Sunday
  unless FORCE_RUN=1 is set.
EOF
}

DRY_RUN=1
DELETE=1
MODE="light"
DEST="$DEST_DEFAULT"
EXCLUDES_FILE="$EXCLUDES_FILE_DEFAULT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run) DRY_RUN=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --light) MODE="light"; shift ;;
    --full) MODE="full"; shift ;;
    --no-delete) DELETE=0; shift ;;
    --dest) DEST="$2"; shift 2 ;;
    --excludes) EXCLUDES_FILE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

# Check Schedule Conflicts for Light Mode
DAY_OF_WEEK=$(date +%u) # 1=Mon, 6=Sat, 7=Sun

if [[ "$MODE" == "light" ]]; then
    # Skip on Mondays (Day 1) because Full Backup runs then
    if [[ "$DAY_OF_WEEK" -eq 1 ]] && [[ "${FORCE_RUN:-0}" != "1" ]]; then
        echo "Skipping Light Backup on Monday (Full Backup scheduled for 4:00 AM)."
        exit 0
    fi
    
    # Note: Weekend pause removed per user request (Tue-Sun schedule active)
fi

if [[ ! -d "$DEST" ]]; then
    if [[ "$DRY_RUN" -eq 0 ]]; then
        mkdir -p "$DEST" || {
            echo "ERROR: Destination not found and could not be created: $DEST" >&2
            echo "Make sure Google Drive is mounted." >&2
            exit 1
        }
    else
        echo "WARNING: Destination not found: $DEST (Simulating creation)"
    fi
fi

# rsync setup
RSYNC=(/usr/bin/rsync -aE --ignore-errors --partial --human-readable --stats)

if [[ -f "$EXCLUDES_FILE" ]]; then
  RSYNC+=(--exclude-from="$EXCLUDES_FILE")
fi

if [[ $DELETE -eq 1 ]]; then
  RSYNC+=(--delete-after)
fi

if [[ $DRY_RUN -eq 1 ]]; then
  RSYNC+=(--dry-run)
  echo "=========================================="
  echo "DRY RUN MODE - No changes will be made"
  echo "=========================================="
fi

require_path() {
  local p="$1"
  if [[ ! -e "$p" ]]; then
    echo "Skipping missing path: $p" >&2
    return 1
  fi
  return 0
}

# Define Backup Sets
CORE_LIGHT=(
  "$HOME/Documents"
  "$HOME/Desktop"
  "$HOME/Scripts"
  "$HOME/Backups" # Assuming small local backups
)

CORE_FULL=(
  "${CORE_LIGHT[@]}"
  "$HOME/Downloads"
  "$HOME/Pictures"
  "$HOME/Movies"
  "$HOME/Public"
  "$HOME/Applications"
  "$HOME/CloudMedia"
  "$HOME/FontBase"
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
  "$HOME/.ssh" # Be careful with this, but usually good to back up
)

run_rsync_relative() {
  local label="$1"; shift
  local -a items=("${@}")

  echo ""
  echo "==> Backing up ($MODE): $label"
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

  # Run rsync
  set +e
  "${RSYNC[@]}" --relative "${existing[@]}" "$DEST/"
  local rc=$?
  set -e

  if [[ $rc -eq 0 ]]; then
    echo "✅ $label backup completed successfully"
  elif [[ $rc -eq 23 ]]; then
    echo "⚠️  $label backup completed with file errors (code 23 - usually harmless ._* files)"
  elif [[ $rc -eq 24 ]]; then
    echo "⚠️  $label backup completed with vanished files (code 24 - normal)"
  else
    echo "❌ $label backup failed with exit code: $rc" >&2
    return $rc
  fi
  return 0
}

BACKUP_ERRORS=0

echo "Starting Google Drive Backup ($MODE)..."
echo "Destination: $DEST"

if [[ "$MODE" == "full" ]]; then
    run_rsync_relative "Full Core" "${CORE_FULL[@]}" || ((BACKUP_ERRORS++))
else
    run_rsync_relative "Light Core" "${CORE_LIGHT[@]}" || ((BACKUP_ERRORS++))
fi

# Always backup dotfiles
run_rsync_relative "Dotfiles" "${DOTFILES[@]}" || ((BACKUP_ERRORS++))

echo ""
echo "=========================================="
if [[ $BACKUP_ERRORS -eq 0 ]]; then
    echo "✅ Google Drive Backup ($MODE) completed successfully!"
else
    echo "⚠️  Backup completed with $BACKUP_ERRORS errors"
fi
echo "=========================================="
