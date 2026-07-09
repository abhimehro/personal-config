#!/usr/bin/env bash
# ==============================================================================
# PHASE 1: GITHUB ACTIONS WORKFLOW UPDATER
# ==============================================================================
# Part of SecOps Autopilot
# Cadence: Weekly (Mondays at 9:00 AM)
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=secops/lib/ai_engine.sh
source "$SCRIPT_DIR/lib/ai_engine.sh" # provides run_timeout

DEV_ROOT="$HOME/dev"
REPOS=(
	"personal-config"
	"ctrld-sync"
	"email-security-pipeline"
	"Seatek_Analysis"
	"Hydrograph_Versus_Seatek_Sensors_Project"
	"series_correction_project_updated"
)
LOCKFILE=".github/aw/actions-lock.json"
LOG_FILE="$HOME/.workflow-updater-history.log"
BRANCH="main"
: "${SECOPS_GH_TIMEOUT:=300}" # network ops cap

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >>"$LOG_FILE"; }

update_repo() {
	local repo="$1"
	local dir="$DEV_ROOT/$repo"

	if [ ! -d "$dir/.git" ]; then
		echo "skip: $repo (not a git repo)"
		log "SKIP - $repo not a git repo."
		return 0
	fi

	echo "==> $repo"
	# Run the rest of the function in a subshell so the `cd` is scoped and
	# never leaks the main process's working directory to the next iteration.
	# `return` inside a subshell would error, so we use `exit` — the subshell's
	# exit code is naturally propagated as this function's return code.
	(
		cd "$dir"

		# Only act if this repo actually uses gh-aw lockfiles.
		if [ ! -f "$LOCKFILE" ]; then
			echo "  skip: no $LOCKFILE"
			log "SKIP - $repo has no $LOCKFILE."
			exit 0
		fi

		if ! command -v gh &>/dev/null || ! gh extension list | grep -q "gh-aw"; then
			echo "  warn: gh-aw not available, skipping update."
			log "SKIP - $repo gh-aw unavailable."
			exit 0
		fi

		echo "  updating actions via gh-aw..."
		if ! run_timeout "$SECOPS_GH_TIMEOUT" gh aw update --verbose; then
			echo "  gh aw update failed/timed out, skipping repo."
			log "FAIL - $repo gh aw update failed or timed out."
			exit 1
		fi

		if git diff --quiet -- "$LOCKFILE"; then
			echo "  up to date."
			log "NO-OP - $repo workflows up to date."
			exit 0
		fi

		# Safeguard: never commit compiled lock files.
		echo "  resetting compiled .lock.yml files..."
		git checkout -- .github/workflows/*.lock.yml 2>/dev/null || true

		# Dry-run compile validation before committing.
		echo "  validating compile (dry run)..."
		if ! run_timeout "$SECOPS_GH_TIMEOUT" gh aw compile --validate 2>/dev/null; then
			echo "  compile validation FAILED, aborting commit."
			log "FAIL - $repo compile validation failed."
			exit 1
		fi

		echo "  diff:"
		git diff -- "$LOCKFILE"

		git add "$LOCKFILE"
		if ! git commit -m "chore(deps): update GitHub Actions versions [$(date '+%Y-%m-%d')]"; then
			echo "  git commit failed."
			log "FAIL - $repo git commit failed."
			exit 1
		fi
		if ! run_timeout "$SECOPS_GH_TIMEOUT" git push origin "$BRANCH"; then
			echo "  git push failed/timed out."
			log "FAIL - $repo git push failed or timed out."
			exit 1
		fi

		echo "  done."
		log "SUCCESS - $repo updated action lockfile."
	)
}

echo "Starting Phase 1: Workflow Updater..."
log "START - Phase 1 run begin."
overall=0
for repo in "${REPOS[@]}"; do
	# Mirror Phase 3's pattern: bracket the call with set +e / set -e and
	# capture rc explicitly, so `set -e` semantics inside update_repo are
	# preserved (the `if ! update_repo` form disables them in the callee).
	set +e
	update_repo "$repo"
	rc=$?
	set -e
	if [ "$rc" -ne 0 ]; then
		overall=1
	fi
done

if [ "$overall" -eq 0 ]; then
	log "SUCCESS - Phase 1 complete."
else
	log "PARTIAL - Phase 1 completed with one or more failures."
fi
echo "Phase 1 complete. See $LOG_FILE."
exit "$overall"
