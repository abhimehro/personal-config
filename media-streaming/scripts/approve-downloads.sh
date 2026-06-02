#!/bin/bash
#
# Approve Alldebrid Downloads
# Moves reviewed files from ~/CloudMedia/approval_needed into ~/CloudMedia/staging.
# The existing rename-media/FileBot pipeline then handles staging -> processed -> upload_stage/cloud.
#
set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

APPROVAL_DIR="$HOME/CloudMedia/approval_needed"
STAGING_DIR="$HOME/CloudMedia/staging"
LOG_FILE="$HOME/Library/Logs/approve-downloads.log"
LOCK_FILE="$HOME/.media_upload.lock"

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

is_video_file() {
	case "$1" in
	*.[mM][pP]4 | *.[mM][kK][vV] | *.[aA][vV][iI] | *.[mM][oO][vV] | *.[mM]4[vV]) return 0 ;;
	*) return 1 ;;
	esac
}

usage() {
	cat <<'EOF'
Usage:
  approve-downloads                 Move all approved video downloads into staging
  approve-downloads <file-name>      Move one specific file from approval_needed into staging
  approve-downloads --list           List files waiting for approval
EOF
}

mkdir -p "$APPROVAL_DIR" "$STAGING_DIR" "$(dirname "$LOG_FILE")"

if [[ ${1-} == "--help" || ${1-} == "-h" ]]; then
	usage
	exit 0
fi

if [[ ${1-} == "--list" ]]; then
	found=0
	while IFS= read -r -d "" file; do
		found=1
		printf '%s\n' "${file##*/}"
	done < <(find "$APPROVAL_DIR" -maxdepth 1 -type f ! -name ".*" -print0)
	if [[ $found -eq 0 ]]; then
		echo "No downloads waiting for approval."
	fi
	exit 0
fi

if [[ -f $LOCK_FILE ]]; then
	log "Upload/processing lock is active. Refusing to move downloads into staging."
	exit 1
fi

move_one() {
	local src="$1"
	local name dest base ext counter

	if [[ ! -f $src ]]; then
		log "File not found: $src"
		return 1
	fi

	name="${src##*/}"

	if ! is_video_file "$name"; then
		log "Skipping non-video file: $name"
		return 0
	fi

	base="${name%.*}"
	ext="${name##*.}"
	dest="$STAGING_DIR/$name"
	counter=1

	while [[ -e $dest ]]; do
		dest="$STAGING_DIR/${base} (${counter}).${ext}"
		((counter++)) || true
	done

	log "Approving download: $name -> $dest"
	mv "$src" "$dest"
}

if [[ $# -gt 0 ]]; then
	target="$APPROVAL_DIR/${1}"
	move_one "$target"
else
	found=0
	while IFS= read -r -d "" file; do
		found=1
		move_one "$file"
	done < <(find "$APPROVAL_DIR" -maxdepth 1 -type f ! -name ".*" -print0 | sort -z)
	if [[ $found -eq 0 ]]; then
		log "No downloads waiting for approval."
	fi
fi

log "Approval pass complete. Files in staging will be picked up by rename-media.sh."
