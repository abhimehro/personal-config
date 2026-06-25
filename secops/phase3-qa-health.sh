#!/usr/bin/env bash
# ==============================================================================
# PHASE 3: QA, HEALTH CHECK, & DRIFT DETECTION
# ==============================================================================
# Part of SecOps Autopilot
# Cadence: Daily (8:00 AM)
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/ai_engine.sh
source "$SCRIPT_DIR/lib/ai_engine.sh"

DEV_ROOT="$HOME/dev"
REPOS=(
	"personal-config"
	"ctrld-sync"
	"email-security-pipeline"
	"Seatek_Analysis"
	"Hydrograph_Versus_Seatek_Sensors_Project"
	"series_correction_project_updated"
)
LOG_FILE="$HOME/.qa-health-history.log"
SSH_ROTATION_PLIST="$HOME/Library/LaunchAgents/com.speedybee.sshkeyrotation.plist"
SSH_ROTATION_LABEL="com.speedybee.sshkeyrotation"

# Per-repo test wall-clock cap (seconds) so a hung suite can't wedge the daemon.
: "${SECOPS_TEST_TIMEOUT:=600}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >>"$LOG_FILE"; }

notify() {
	local msg="$1"
	osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title (item 2 of argv)' -e 'end run' -- "$msg" "SecOps Autopilot" 2>/dev/null || true
}

# Decide and run the repo's OWN declared test command.
# Returns: 0 pass, 1 fail, 2 no-test-path (skip — not a failure).
run_project_tests() {
	local dir="$1"
	# Run in a subshell so the `cd` is scoped and can't leak the main
	# process's cwd to the next repo iteration. `exit` codes from the
	# subshell are naturally propagated as this function's return code.
	(
		cd "$dir"

		# 1) Makefile is the strongest signal of the repo's real convention.
		if [ -f "Makefile" ]; then
			if grep -qE '^test-all:' Makefile; then
				run_timeout "$SECOPS_TEST_TIMEOUT" make test-all 2>&1
				exit $?
			elif grep -qE '^test:' Makefile; then
				run_timeout "$SECOPS_TEST_TIMEOUT" make test 2>&1
				exit $?
			fi
		fi

		# 2) Node project — only if a real "test" script is declared.
		if [ -f "package.json" ]; then
			if node -e 'process.exit((require("./package.json").scripts||{}).test?0:1)' 2>/dev/null; then
				run_timeout "$SECOPS_TEST_TIMEOUT" npm run test -- --watchAll=false 2>&1
				exit $?
			else
				echo "package.json present but no 'test' script declared — skipping."
				exit 2
			fi
		fi

		# 3) Python project — prefer the repo's own venv, then a pytest on PATH.
		if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ] || [ -f "pytest.ini" ]; then
			if [ -x ".venv/bin/pytest" ]; then
				run_timeout "$SECOPS_TEST_TIMEOUT" .venv/bin/pytest 2>&1
				exit $?
			elif command -v pytest &>/dev/null; then
				run_timeout "$SECOPS_TEST_TIMEOUT" pytest 2>&1
				exit $?
			else
				echo "Python project but no .venv/pytest available — skipping."
				exit 2
			fi
		fi

		echo "no recognized test path, skipping."
		exit 2
	)
}

audit_system_drift() {
	echo "Auditing system configuration drift..."

	if command -v scutil &>/dev/null; then
		echo "DNS configuration:"
		scutil --dns | grep -A 5 "nameserver" || true
	fi

	if [ -f "$DEV_ROOT/personal-config/scripts/verify_ssh_config.sh" ]; then
		echo "SSH Config Status:"
		bash "$DEV_ROOT/personal-config/scripts/verify_ssh_config.sh" || true
	fi

	if [ -f "$SSH_ROTATION_PLIST" ]; then
		if launchctl list | grep -q "$SSH_ROTATION_LABEL"; then
			echo "SSH key rotation LaunchAgent: active."
		else
			echo "SSH key rotation LaunchAgent: present but inactive."
		fi
	else
		echo "SSH key rotation LaunchAgent: plist missing."
	fi
}

echo "Starting Phase 3: QA & Drift Audit..."
log "START - Phase 3 run begin."
overall=0

# --- Per-repo build/test verification ---
for repo in "${REPOS[@]}"; do
	dir="$DEV_ROOT/$repo"
	if [ ! -d "$dir/.git" ]; then
		echo "skip: $repo (not a git repo)"
		log "SKIP - $repo not a git repo."
		continue
	fi

	echo "==> testing $repo"
	set +e
	run_project_tests "$dir" >"/tmp/test_run_${repo}.log" 2>&1
	rc=$?
	set -e

	case "$rc" in
	0)
		echo "  $repo: passed."
		log "PASS - $repo."
		;;
	2)
		echo "  $repo: no test path, skipped."
		log "SKIP - $repo no test path."
		;;
	124)
		echo "  $repo: tests TIMED OUT (>${SECOPS_TEST_TIMEOUT}s)."
		notify "QA timeout in ${repo}."
		log "TIMEOUT - $repo exceeded ${SECOPS_TEST_TIMEOUT}s."
		overall=1
		;;
	*)
		echo "  tests FAILED for $repo (rc=$rc), requesting diagnostics..."
		ai_diagnose "Analyze this test failure log, identify the root cause, and provide a concise step-by-step fix following Security-First Development guidelines. Be brief." \
			<"/tmp/test_run_${repo}.log" || true
		notify "QA failed in ${repo}. Diagnostics generated."
		log "FAIL - $repo test regression (rc=$rc)."
		overall=1
		;;
	esac
done

# --- System-level Drift Audit ---
audit_system_drift >/tmp/drift_audit.log 2>&1
echo "Drift audit summary:"
ai_diagnose "Review this system configuration log. Are there signs of configuration drift, inactive launch daemons, or DNS leaks? Respond with 'No drift detected' or a short warning list. Do not suggest applying changes automatically. Be brief." \
	</tmp/drift_audit.log || true

if [ "$overall" -eq 0 ]; then
	echo "Phase 3 complete. System healthy and aligned."
	log "SUCCESS - All checks passed or skipped."
else
	echo "Phase 3 complete with failures. See $LOG_FILE."
	log "PARTIAL - One or more repos failed."
fi

exit "$overall"
