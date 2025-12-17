#!/usr/bin/env bash
set -euo pipefail

# One-way incremental backup from $HOME into ProtonDrive using rsync.
# Defaults to --dry-run for safety.

PROTON_ROOT_DEFAULT="$HOME/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder"
DEST_DEFAULT="$PROTON_ROOT_DEFAULT/HomeBackup"
EXCLUDES_FILE_DEFAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/protondrive_backup.exclude"

usage() {
  cat <<'EOF'
Usage:
  protondrive_backup.sh [--run] [--dry-run] [--no-delete] [--dest PATH] [--proton-root PATH] [--excludes FILE]

Notes:
  - Default mode is --dry-run.
  - --run performs the actual sync.
  - --no-delete disables mirror deletions (safer, but destination can accumulate).
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
    *) echo "Unknown arg: $1"; usage; exit 2 ;;
  esac
done

if [[ ! -d "$PROTON_ROOT" ]]; then
  echo "ProtonDrive root not found: $PROTON_ROOT" >&2
  exit 1
fi

if [[ ! -f "$EXCLUDES_FILE" ]]; then
  echo "Excludes file not found: $EXCLUDES_FILE" >&2
  exit 1
fi

mkdir -p "$DEST"

# macOS ships an older rsync, so stick to widely supported flags.
# Keep output reasonably small by default (launchd logs can grow fast).
RSYNC=(/usr/bin/rsync -aE --human-readable --stats --delete-delay)
RSYNC+=(--exclude-from="$EXCLUDES_FILE")

if [[ $DELETE -eq 0 ]]; then
  # Remove any delete flags we set above
  RSYNC=(/usr/bin/rsync -aE --human-readable --stats)
  RSYNC+=(--exclude-from="$EXCLUDES_FILE")
fi

if [[ $DRY_RUN -eq 1 ]]; then
  RSYNC+=(--dry-run)
fi

# Ensure we don't accidentally traverse outside expectations if a path is missing.
require_path() {
  local p="$1"
  if [[ ! -e "$p" ]]; then
    echo "Skipping missing path: $p" >&2
    return 1
  fi
  return 0
}

# Core directories
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

# Config & dotfiles
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

# Use --relative so files land under DEST with full-ish paths (home/...).
# Example: $DEST/home/abhimehrotra/Documents/...
run_rsync_relative() {
  local label="$1"; shift
  local -a items=("$@")

  echo "==> Backing up: $label"

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

  set +e
  "${RSYNC[@]}" --relative "${existing[@]}" "$DEST/"
  local rc=$?
  set -e

  # rsync 24 = "Partial transfer due to vanished source files" (common on macOS)
  if [[ $rc -ne 0 && $rc -ne 24 ]]; then
    return $rc
  fi

  return 0
}

run_rsync_relative "core directories" "${CORE[@]}"
run_rsync_relative "dotfiles/config" "${DOTFILES[@]}"

echo "Done. Destination: $DEST"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "(dry-run) No changes were made. Re-run with --run to apply."
fi
