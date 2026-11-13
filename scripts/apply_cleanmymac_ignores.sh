#!/usr/bin/env bash
#
# Apply CleanMyMac Ignores - Reconcile the CLI ignore list with the repo
#
# CleanMyMac keeps its ignore list in an encrypted binary store, so the list
# cannot be version controlled directly. configs/cleanmymac/ignore-paths.txt is
# the source of truth; this script pushes it into the CLI.
#
# The CLI and the GUI keep separate ignore stores. This script only manages the
# CLI. Add the same paths in the GUI under Settings, Privacy, Exclusions.
#
# Usage:
#   ./scripts/apply_cleanmymac_ignores.sh           # apply the list
#   ./scripts/apply_cleanmymac_ignores.sh --check   # report drift, change nothing
#
# Exit codes: 0 success or no drift, 1 drift found in --check mode, 2 setup error.

set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}"
SOURCE_FILE="$REPO_ROOT/configs/cleanmymac/ignore-paths.txt"
CLI="/Applications/CleanMyMac_5_CLI.app/Contents/MacOS/CleanMyMac_5_CLI"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { printf '%b\n' "${BLUE}[INFO]${NC} $*"; }
success() { printf '%b\n' "${GREEN}[OK]${NC} $*"; }
warn() { printf '%b\n' "${YELLOW}[WARN]${NC} $*"; }
error() { printf '%b\n' "${RED}[ERROR]${NC} $*" >&2; }

CHECK_ONLY=0
case "${1:-}" in
	--check) CHECK_ONLY=1 ;;
	-h | --help)
		sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
		exit 0
		;;
	"") ;;
	*)
		error "Unknown argument: $1"
		exit 2
		;;
esac

[[ -r $SOURCE_FILE ]] || {
	error "Source list not found: $SOURCE_FILE"
	exit 2
}

if [[ ! -x $CLI ]]; then
	warn "CleanMyMac CLI not installed at $CLI (skipping)"
	exit 0
fi

# Read the desired paths, skipping comments and blank lines.
desired=()
while IFS= read -r line || [[ -n $line ]]; do
	line="${line#"${line%%[![:space:]]*}"}"
	line="${line%"${line##*[![:space:]]}"}"
	[[ -z $line || $line == \#* ]] && continue
	desired+=("$line")
done <"$SOURCE_FILE"

if [[ ${#desired[@]} -eq 0 ]]; then
	warn "No paths listed in $SOURCE_FILE"
	exit 0
fi

# `ignore list` is an interactive TUI, so it needs stdin closed and a timeout.
current_raw=""
if ! current_raw=$(timeout 20 "$CLI" ignore list </dev/null 2>&1); then
	# The TUI exits non-zero after printing; treat captured output as success.
	:
fi

drift=0
for path in "${desired[@]}"; do
	if grep -Fq -- "$path" <<<"$current_raw"; then
		success "already ignored: $path"
	else
		drift=$((drift + 1))
		if [[ $CHECK_ONLY -eq 1 ]]; then
			warn "missing from ignore list: $path"
		else
			log "adding: $path"
			if "$CLI" ignore add "$path" >/dev/null 2>&1; then
				success "added: $path"
			else
				error "failed to add: $path"
				exit 1
			fi
		fi
	fi
done

if [[ $CHECK_ONLY -eq 1 ]]; then
	if [[ $drift -gt 0 ]]; then
		warn "$drift path(s) missing from the CleanMyMac ignore list"
		exit 1
	fi
	success "CleanMyMac ignore list matches $SOURCE_FILE"
	exit 0
fi

success "CleanMyMac ignore list reconciled (${#desired[@]} paths)"
