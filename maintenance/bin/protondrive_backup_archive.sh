#!/usr/bin/env bash
set -euo pipefail

# Archive-based cloud backup helper (bash 3.2 compatible)
#
# Goal:
#   Create ONE archive locally and copy ONE file to a cloud folder.
#   This avoids overwhelming macOS File Provider based sync engines.
#
# IMPORTANT:
#   macOS /usr/bin/tar is bsdtar (libarchive). It does NOT support GNU tar's
#   --absolute-names. To keep paths sensible, we run tar with -C / and pass
#   paths relative to /. The archive will contain entries like:
#     Users/speedybee/Documents/...

CLOUD_ROOT_DEFAULT="$HOME/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder"
DEST_DIR_DEFAULT="$CLOUD_ROOT_DEFAULT/HomeBackup/Archives"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAINTENANCE_HOME_DEFAULT="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

STAGING_DEFAULT="$HOME/Library/Logs/maintenance/tmp/archive_backup"
EXCLUDES_FILE_DEFAULT="$MAINTENANCE_HOME_DEFAULT/conf/protondrive_backup.exclude"

usage() {
  cat <<'EOF'
Usage:
  protondrive_backup_archive.sh [--run] [--dry-run]
                              [--dest-dir PATH]
                              [--proton-root PATH]
                              [--cloud-root PATH]
                              [--staging PATH]
                              [--excludes FILE]
                              [--retention N]
                              [--label NAME]
                              [--profile light|full]

Profiles:
  light: Documents + Desktop + dotfiles/config (fast, ideal for daily)
  full:  light + larger folders (Pictures/Movies/Downloads/etc.)

Notes:
  - Default mode is --dry-run.
  - Creates ONE .tar.gz archive locally then copies it to dest-dir.
EOF
}

DRY_RUN=1
CLOUD_ROOT="$CLOUD_ROOT_DEFAULT"
DEST_DIR="$DEST_DIR_DEFAULT"
STAGING_DIR="$STAGING_DEFAULT"
EXCLUDES_FILE="$EXCLUDES_FILE_DEFAULT"
RETENTION=21
LABEL="HomeBackup"
PROFILE="light"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run) DRY_RUN=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --proton-root|--cloud-root) CLOUD_ROOT="$2"; shift 2 ;;
    --dest-dir) DEST_DIR="$2"; shift 2 ;;
    --staging) STAGING_DIR="$2"; shift 2 ;;
    --excludes) EXCLUDES_FILE="$2"; shift 2 ;;
    --retention) RETENTION="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

log() {
  local level="$1"; shift
  printf '%s [%s] [archive_backup] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$*" | tee -a "$LOG_DIR/protondrive_backup_archive.log"
}

log INFO "Starting archive backup (dry-run=$DRY_RUN, profile=$PROFILE)"
log INFO "Cloud root: $CLOUD_ROOT"
log INFO "Dest dir:   $DEST_DIR"

if [[ ! -d "$CLOUD_ROOT" ]]; then
  log WARN "Cloud root not found: $CLOUD_ROOT"
  log WARN "Ensure the provider app is running and signed in (CloudStorage mount present)."
  exit 1
fi

mkdir -p "$STAGING_DIR"
mkdir -p "$DEST_DIR"

# Build include sets
CORE_LIGHT=(
  "$HOME/Documents"
  "$HOME/Desktop"
)

CORE_FULL=(
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

CORE=()
case "$PROFILE" in
  light)
    CORE=("${CORE_LIGHT[@]}")
    ;;
  full)
    CORE=("${CORE_LIGHT[@]}" "${CORE_FULL[@]}")
    ;;
  *)
    log WARN "Unknown profile: $PROFILE (expected 'light' or 'full')"
    exit 2
    ;;
 esac

EXISTING_ABS=()
for p in "${CORE[@]}" "${DOTFILES[@]}"; do
  if [[ -e "$p" ]]; then
    EXISTING_ABS+=("$p")
  else
    log INFO "Skipping missing path: $p"
  fi
done

if [[ ${#EXISTING_ABS[@]} -eq 0 ]]; then
  log WARN "No source paths exist; nothing to back up."
  exit 0
fi

# Build archive name
TS="$(date +%Y%m%d-%H%M%S)"
ARCHIVE_NAME="${LABEL}-${PROFILE}-${TS}.tar.gz"
ARCHIVE_PATH="$STAGING_DIR/$ARCHIVE_NAME"

# Ensure tar doesn't generate AppleDouble files
export COPYFILE_DISABLE=1

# Convert absolute paths to paths relative to /
EXISTING_REL=()
for p in "${EXISTING_ABS[@]}"; do
  EXISTING_REL+=("${p#/}")
done

# Build tar args
# -C / makes entries relative to root, without requiring GNU --absolute-names
TAR=(/usr/bin/tar -czf "$ARCHIVE_PATH" -C /)

# Excludes: AppleDouble files, rsync temp, Finder metadata
TAR+=(--exclude '._*' --exclude '*.sync' --exclude '.DS_Store')

if [[ -f "$EXCLUDES_FILE" ]]; then
  TAR+=(--exclude-from "$EXCLUDES_FILE")
else
  log WARN "Exclude file not found: $EXCLUDES_FILE (continuing without it)"
fi

if [[ $DRY_RUN -eq 1 ]]; then
  log INFO "DRY RUN: would create archive at: $ARCHIVE_PATH"
  log INFO "DRY RUN: would copy archive to: $DEST_DIR/$ARCHIVE_NAME"
  log INFO "DRY RUN: would retain last $RETENTION archives"
  exit 0
fi

log INFO "Creating archive: $ARCHIVE_PATH"

set +e
"${TAR[@]}" "${EXISTING_REL[@]}" 2>&1 | tee -a "$LOG_DIR/protondrive_backup_archive.log"
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  log WARN "tar returned non-zero exit code: $RC"
  log WARN "Archive may be incomplete: $ARCHIVE_PATH"
fi

if [[ ! -f "$ARCHIVE_PATH" ]]; then
  log WARN "Archive was not created: $ARCHIVE_PATH"
  exit 1
fi

SIZE=$(ls -lh "$ARCHIVE_PATH" | awk '{print $5}' || echo "?")
log INFO "Archive created (size: $SIZE)"

# Copy into cloud folder
log INFO "Copying to cloud: $DEST_DIR/$ARCHIVE_NAME"
cp -f "$ARCHIVE_PATH" "$DEST_DIR/$ARCHIVE_NAME"
log INFO "Copy complete"

# Retention pruning (keep newest N)
if [[ "$RETENTION" =~ ^[0-9]+$ ]] && (( RETENTION > 0 )); then
  log INFO "Pruning archives (keep newest $RETENTION)"
  ls -1t "$DEST_DIR"/*.tar.gz 2>/dev/null | tail -n +$((RETENTION+1)) | while read -r old; do
    log INFO "Removing old archive: $old"
    rm -f "$old" 2>/dev/null || true
  done
fi

log INFO "Done. Archive stored at: $DEST_DIR/$ARCHIVE_NAME"
