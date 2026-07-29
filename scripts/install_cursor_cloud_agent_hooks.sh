#!/usr/bin/env bash
# Sync canonical Cloud Agent secret-scan hooks into Cursor's injected hook directory.
#
# Cursor writes copies under ~/.cursor/agent-hooks/<workspace-hash>/ (outside git).
# Those copies can lag behind the repo and still use ${!SECRET_NAME}, which breaks
# when CLOUD_AGENT_INJECTED_SECRET_NAMES contains labels with spaces (e.g. "GitHub SSH Key").
#
# Canonical sources (reviewable in git):
#   scripts/cursor_cloud_agent_pre_commit.sh  -> pre-commit.cursor
#   scripts/cursor_cloud_agent_commit_msg.sh   -> commit-msg.cursor
#
# A directory is updated only when **both** hook files already exist as **regular**
# non-symlink files (Cursor’s normal layout). We use install(1) instead of cp so we
# never follow a symlink target and overwrite an arbitrary path.
#
# Usage:
#   ./scripts/install_cursor_cloud_agent_hooks.sh              # all hook dirs under ~/.cursor/agent-hooks
#   ./scripts/install_cursor_cloud_agent_hooks.sh /path/to/dir # single workspace hash directory
# Env:
#   CURSOR_AGENT_HOOKS_DIR  if set, only sync this directory (non-empty).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT
readonly PRE_COMMIT_SRC="${REPO_ROOT}/scripts/cursor_cloud_agent_pre_commit.sh"
readonly COMMIT_MSG_SRC="${REPO_ROOT}/scripts/cursor_cloud_agent_commit_msg.sh"

log() { printf '[cursor-cloud-hooks] %s\n' "$*" >&2; }

require_sources() {
	if [[ ! -f $PRE_COMMIT_SRC ]]; then
		log "Missing canonical pre-commit source: $PRE_COMMIT_SRC"
		exit 1
	fi
	if [[ ! -f $COMMIT_MSG_SRC ]]; then
		log "Missing canonical commit-msg source: $COMMIT_MSG_SRC"
		exit 1
	fi
}

# SECURITY: Refuse symlink hook paths — a symlink can point outside dest_dir; treat as unsafe.
# NOTE: `[[ -e symlink ]]` is false for a **broken** symlink, so we must test `-L` before `-e`
# or we would mis-classify broken symlinks as "missing" and skip instead of refusing.
hooks_are_safe_regular_files() {
	local dest_dir="$1"
	local pc="${dest_dir}/pre-commit.cursor"
	local cm="${dest_dir}/commit-msg.cursor"
	if [[ -L $pc ]] || [[ -L $cm ]]; then
		log "refuse: hook paths must not be symlinks: $dest_dir"
		return 2
	fi
	if [[ -f $pc && -f $cm ]]; then
		return 0
	fi
	return 1
}

install_into_dir() {
	local dest_dir="$1"
	if [[ ! -d $dest_dir ]]; then
		log "skip (not a directory): $dest_dir"
		return 0
	fi

	# NOTE: Cannot call hooks_are_safe_regular_files and then read $? under `set -e` — a non-zero
	# return would exit the script before assignment. Use if/else and read $? in the else branch.
	if hooks_are_safe_regular_files "$dest_dir"; then
		# install -m 0755 replaces destination atomically where supported; avoids cp following symlinks.
		install -m 0755 "$PRE_COMMIT_SRC" "${dest_dir}/pre-commit.cursor"
		install -m 0755 "$COMMIT_MSG_SRC" "${dest_dir}/commit-msg.cursor"
		log "updated hooks in $dest_dir"
	else
		case $? in
		2)
			return 1
			;;
		*)
			log "skip (need both pre-commit.cursor and commit-msg.cursor as regular files): $dest_dir"
			return 0
			;;
		esac
	fi
}

main() {
	require_sources

	if [[ -n ${CURSOR_AGENT_HOOKS_DIR-} ]]; then
		install_into_dir "$CURSOR_AGENT_HOOKS_DIR"
		return 0
	fi

	if [[ $# -ge 1 ]]; then
		install_into_dir "$1"
		return 0
	fi

	local base="${HOME}/.cursor/agent-hooks"
	if [[ ! -d $base ]]; then
		log "no directory $base — nothing to do (hooks not injected in this environment)"
		return 0
	fi

	local found=0
	local entry
	for entry in "$base"/*; do
		[[ -e $entry ]] || continue
		if [[ -d $entry ]]; then
			found=1
			install_into_dir "$entry" || return 1
		fi
	done

	if [[ $found -eq 0 ]]; then
		log "no subdirectories under $base — nothing to do"
	fi
}

main "$@"
