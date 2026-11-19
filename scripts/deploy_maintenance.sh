#!/usr/bin/env bash
#
# Deploy Maintenance - Copy tracked maintenance files to the live install dir
#
# ~/Library/Maintenance is where launchd agents execute from. It must NOT be a
# symlink into the repo: a symlink makes the live scripts track whatever branch
# happens to be checked out, so a `git checkout` silently rewrites production
# behaviour with no deploy step. That is how the 60-minute SSH wait window was
# reverted to 30 minutes on 2026-11-16.
#
# This script copies the tracked files into a real directory instead. The repo
# stays the source of truth; the live copy only changes when you run this.
#
# Usage:
#   ./scripts/deploy_maintenance.sh            # deploy
#   ./scripts/deploy_maintenance.sh --check    # report drift, change nothing
#   ./scripts/deploy_maintenance.sh --dry-run  # show what would change
#
# Exit codes: 0 success or no drift, 1 drift found in --check, 2 setup error.

set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}"
SRC="$REPO_ROOT/maintenance"
DEST="${MAINTENANCE_INSTALL_DIR:-$HOME/Library/Maintenance}"

log() { printf '[INFO] %s\n' "$*"; }
success() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; }
error() { printf '[ERROR] %s\n' "$*" >&2; }

MODE=deploy
case "${1:-}" in
--check) MODE=check ;;
--dry-run) MODE=dry-run ;;
-h | --help)
	sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
	exit 0
	;;
"") ;;
*)
	error "Unknown argument: $1"
	exit 2
	;;
esac

[[ -d $SRC ]] || {
	error "Source not found: $SRC"
	exit 2
}

# Collect the files to deploy. Runtime state (tmp/, reports/, archive/) is
# excluded: copying it would clobber live logs with whatever the repo holds.
# macOS ships bash 3.2, which has no mapfile, so read into an array manually.
FILES=()
while IFS= read -r rel; do
	[[ -n $rel ]] && FILES+=("$rel")
done < <(
	cd "$SRC" && find . -type f \
		! -path "./tmp/*" ! -path "./reports/*" ! -path "./archive/*" \
		! -name "*.bak" ! -name "*.bak.*" ! -name "*.orig" \
		! -name ".DS_Store" |
		sed 's|^\./||' | sort
)

if [[ ${#FILES[@]} -eq 0 ]]; then
	error "No files found to deploy under $SRC"
	exit 2
fi

# The symlink case is the whole reason this script exists, so call it out.
if [[ -L $DEST ]]; then
	warn "$DEST is a symlink -> $(readlink "$DEST")"
	warn "Live scripts currently track the checked-out branch."
	if [[ $MODE == check ]]; then
		error "Drift: $DEST must be a real directory, not a symlink"
		exit 1
	fi
fi

drift=0
changed=0
for rel in "${FILES[@]}"; do
	src_file="$SRC/$rel"
	dest_file="$DEST/$rel"

	if [[ -f $dest_file ]] && cmp -s "$src_file" "$dest_file"; then
		continue
	fi

	drift=$((drift + 1))
	if [[ $MODE == check ]]; then
		warn "drift: $rel"
		continue
	fi
	if [[ $MODE == dry-run ]]; then
		log "would update: $rel"
		continue
	fi

	mkdir -p "$(dirname "$dest_file")"
	if [[ $rel == *.sh ]]; then
		install -m 755 "$src_file" "$dest_file"
	else
		install -m 644 "$src_file" "$dest_file"
	fi
	changed=$((changed + 1))
done

if [[ $MODE == check ]]; then
	if [[ $drift -gt 0 ]]; then
		warn "$drift file(s) differ from the repo"
		exit 1
	fi
	success "Live maintenance tree matches the repo"
	exit 0
fi

if [[ $MODE == dry-run ]]; then
	log "$drift file(s) would change"
	exit 0
fi

# Replace the symlink only after the copy succeeded, so a failure leaves the
# previous working tree in place.
if [[ -L $DEST ]]; then
	rm -f "$DEST"
	mkdir -p "$DEST"
	for rel in "${FILES[@]}"; do
		src_file="$SRC/$rel"
		dest_file="$DEST/$rel"
		mkdir -p "$(dirname "$dest_file")"
		if [[ $rel == *.sh ]]; then
			install -m 755 "$src_file" "$dest_file"
		else
			install -m 644 "$src_file" "$dest_file"
		fi
	done
	success "Replaced symlink with a real directory at $DEST"
fi

success "Deployed $changed file(s) to $DEST"
