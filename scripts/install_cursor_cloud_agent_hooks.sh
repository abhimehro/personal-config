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
		printf 'Missing canonical pre-commit source: %s\n' "$PRE_COMMIT_SRC" >&2
		exit 1
	fi
	if [[ ! -f $COMMIT_MSG_SRC ]]; then
		printf 'Missing canonical commit-msg source: %s\n' "$COMMIT_MSG_SRC" >&2
		exit 1
	fi
}

install_into_dir() {
	local dest_dir="$1"
	if [[ ! -d $dest_dir ]]; then
		log "skip (not a directory): $dest_dir"
		return 0
	fi

	local installed=0
	if [[ -f ${dest_dir}/pre-commit.cursor ]] || [[ -f ${dest_dir}/commit-msg.cursor ]]; then
		cp -f "$PRE_COMMIT_SRC" "${dest_dir}/pre-commit.cursor"
		cp -f "$COMMIT_MSG_SRC" "${dest_dir}/commit-msg.cursor"
		chmod a+x "${dest_dir}/pre-commit.cursor" "${dest_dir}/commit-msg.cursor"
		log "updated hooks in $dest_dir"
		installed=1
	fi
	if [[ $installed -eq 0 ]]; then
		log "skip (no pre-commit.cursor / commit-msg.cursor present): $dest_dir"
	fi
}

main() {
	require_sources

	if [[ -n ${CURSOR_AGENT_HOOKS_DIR:-} ]]; then
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
			install_into_dir "$entry"
		fi
	done

	if [[ $found -eq 0 ]]; then
		log "no subdirectories under $base — nothing to do"
	fi
}

main "$@"
