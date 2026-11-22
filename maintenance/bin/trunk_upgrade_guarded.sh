#!/usr/bin/env bash

# Guarded Trunk upgrade: upgrades linters/tools/plugins/runtimes/CLI while
# enforcing the pinact 4.1.1 pin documented in .trunk/trunk.yaml.
#
# WHY: pinact v5 rejects the single-dash -format flag that trunk plugins
# v1.11.0 still passes via pinact_run.py. `trunk upgrade` ignores pin
# comments and bumps pinact anyway, so this script reverts it after
# upgrading. Verified 2026-11-03: pinact 5.0.2 errors "unknown flag: -format".
#
# USAGE:
#   trunk_upgrade_guarded.sh [repo_dir ...]   # defaults to all ~/dev Trunk repos
#   TRUNK_PINACT_VERSION=4.1.1 ...            # override pin target
#
# Behavior per repo:
#   1. Requires a clean .trunk/trunk.yaml (no unstaged changes) unless FORCE=1.
#   2. Runs `trunk upgrade -y --no-progress`.
#   3. Reverts any pinact version above the pin back to the pin.
#   4. Verifies the config parses via `trunk upgrade --dry-run`.
#   5. Commits ONLY .trunk/trunk.yaml (never sweeps untracked files).
#   6. Pushes to origin HEAD branch via gh credential helper (SSH-agent-safe).
#
# Exit codes: 0 all repos OK, 1 one or more repos failed.

set -euo pipefail

export HOME="${HOME:-/Users/speedybee}"

PINACT_PIN="${TRUNK_PINACT_VERSION:-4.1.1}"
DEV_ROOT="${TRUNK_DEV_ROOT:-$HOME/dev}"
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/trunk_upgrade_guarded.log"

log() {
	echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] [trunk-guard] $*" | tee -a "$LOG_FILE"
}

warn() {
	echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] [trunk-guard] $*" | tee -a "$LOG_FILE" >&2
}

fail() {
	echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] [trunk-guard] $*" | tee -a "$LOG_FILE" >&2
}

# Discover Trunk repos: explicit args, else every ~/dev repo with .trunk/trunk.yaml.
if [[ $# -gt 0 ]]; then
	repos=("$@")
else
	repos=()
	for d in "$DEV_ROOT"/*/; do
		[[ -f "$d/.trunk/trunk.yaml" ]] && repos+=("$d")
	done
fi

[[ ${#repos[@]} -gt 0 ]] || {
	log "No Trunk repos found under $DEV_ROOT"
	exit 0
}

FAILED=()

for repo in "${repos[@]}"; do
	repo="${repo%/}"
	name="$(basename "$repo")"
	log "=== $name: starting guarded upgrade ==="

	if [[ ! -d "$repo/.trunk" ]]; then
		fail "$name: no .trunk directory, skipping"
		FAILED+=("$name")
		continue
	fi

	# Require clean trunk.yaml unless FORCE=1.
	if [[ ${FORCE:-0} != "1" ]] && ! git -C "$repo" diff --quiet -- .trunk/trunk.yaml; then
		fail "$name: .trunk/trunk.yaml has unstaged changes (commit or stash first, or FORCE=1). Skipping."
		FAILED+=("$name")
		continue
	fi

	# 1. Upgrade everything.
	if ! (cd "$repo" && trunk upgrade -y --no-progress >>"$LOG_FILE" 2>&1); then
		fail "$name: trunk upgrade failed"
		FAILED+=("$name")
		continue
	fi

	# 2. Revert pinact if it moved past the pin.
	if grep -qE "^\s*- pinact@" "$repo/.trunk/trunk.yaml"; then
		current="$(grep -oE 'pinact@[0-9.]+' "$repo/.trunk/trunk.yaml" | head -1 | cut -d@ -f2)"
		if [[ "$current" != "$PINACT_PIN" ]]; then
			log "$name: reverting pinact $current -> $PINACT_PIN"
			sed -i '' "s/- pinact@${current}/- pinact@${PINACT_PIN}/" "$repo/.trunk/trunk.yaml"
		fi
	fi

	# 3. Validate config still parses.
	if ! (cd "$repo" && trunk upgrade --dry-run --no-progress >>"$LOG_FILE" 2>&1); then
		fail "$name: trunk config validation failed after upgrade; inspect manually"
		FAILED+=("$name")
		continue
	fi

	# 4. Commit only trunk.yaml if changed.
	if git -C "$repo" status --porcelain -- .trunk/trunk.yaml | grep -q .; then
		branch="$(git -C "$repo" branch --show-current)"
		git -C "$repo" add .trunk/trunk.yaml
		git -C "$repo" commit -m "chore(trunk): upgrade linters and tools, pin pinact at $PINACT_PIN

trunk upgrade bumps pinact past the documented 4.1.1 pin (v5 rejects
the single-dash -format flag passed by trunk plugins v1.11.0 via
pinact_run.py). Guarded script reverted it; all other linters,
runtimes, plugins, and CLI upgraded to latest." >>"$LOG_FILE" 2>&1 || {
			fail "$name: commit failed"
			FAILED+=("$name")
			continue
		}
		# 5. Push via gh HTTPS credentials (SSH-agent-safe).
		if ! git -C "$repo" -c credential.helper='!gh auth git-credential' \
			-c url."https://github.com/".insteadOf="git@github.com:" \
			-c url."https://github.com/".insteadOf="ssh://git@github.com/" \
			push origin HEAD >>"$LOG_FILE" 2>&1; then
			fail "$name: push failed (committed locally; push manually)"
			FAILED+=("$name")
			continue
		fi
		log "$name: committed and pushed on $branch"
	else
		log "$name: no changes after upgrade"
	fi

	log "=== $name: done ==="
done

if [[ ${#FAILED[@]} -gt 0 ]]; then
	fail "Failed repos: ${FAILED[*]}"
	exit 1
fi

log "All ${#repos[@]} repos upgraded cleanly with pinact@$PINACT_PIN enforced."
exit 0
