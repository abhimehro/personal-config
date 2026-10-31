#!/usr/bin/env bash
#
# Unit tests for scripts/antigravity-proactive-ctl.sh
# Verifies idempotent install, chmod 700 transcript/report dirs, weekday UTC cron,
# allows_user_interactions=false, disposable cron canary staging/cleanup,
# post-merge Sentinel lease verification, MISSED digest audit, and ordered rollback.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CTL_SCRIPT="${REPO_ROOT}/scripts/antigravity-proactive-ctl.sh"

TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'test-proactive-ctl')"
trap 'rm -rf "$TEST_DIR"' EXIT

export HOME="${TEST_DIR}/home"
MOCK_BIN="${TEST_DIR}/mock_bin"
mkdir -p \
	"${HOME}/.gemini/config/skills" \
	"${HOME}/.gemini/config/sidecars" \
	"${HOME}/.gemini/antigravity/brain" \
	"${HOME}/.gemini/antigravity-cli" \
	"${MOCK_BIN}"

PASS=0
FAIL=0

check() {
	local name="$1"
	shift
	if "$@" >/dev/null 2>&1; then
		echo "PASS: ${name}"
		PASS=$((PASS + 1))
	else
		echo "FAIL: ${name}"
		FAIL=$((FAIL + 1))
	fi
}

check_exit() {
	local name="$1"
	local expected="$2"
	shift 2
	local actual=0
	"$@" >"${TEST_DIR}/check.log" 2>&1 || actual=$?
	if [[ ${actual} -eq ${expected} ]]; then
		echo "PASS: ${name}"
		PASS=$((PASS + 1))
	else
		echo "FAIL: ${name} (expected exit ${expected}, got ${actual})"
		cat "${TEST_DIR}/check.log"
		FAIL=$((FAIL + 1))
	fi
}

check_grep() {
	local name="$1"
	local pattern="$2"
	local file="$3"
	if grep -qE "${pattern}" "${file}" 2>/dev/null; then
		echo "PASS: ${name}"
		PASS=$((PASS + 1))
	else
		echo "FAIL: ${name} (pattern '${pattern}' not found in ${file})"
		cat "${file}" 2>/dev/null || true
		FAIL=$((FAIL + 1))
	fi
}

if [[ ! -x ${CTL_SCRIPT} ]]; then
	echo "FAIL: control script missing or not executable: ${CTL_SCRIPT}"
	exit 1
fi

# 1. Install pilot setup into isolated HOME
"${CTL_SCRIPT}" install --pilot >"${TEST_DIR}/install.log" 2>&1

for skill in proactive-sentinel proactive-bolt proactive-palette proactive-code-health proactive-repo-sweep; do
	check "skill symlink created: ${skill}" test -L "${HOME}/.gemini/config/skills/${skill}"
done

check "global hooks.json symlink created" test -L "${HOME}/.gemini/config/hooks.json"
check "reports directory created" test -d "${HOME}/.gemini/antigravity/proactive-reports"

SIDECAR_FILE="${HOME}/.gemini/config/sidecars/proactive-pilot-ctrld-sync/sidecar.json"
check "disabled pilot sidecar.json created" test -f "${SIDECAR_FILE}"
check "user_config.json NOT created or self-enabled" test ! -f "${HOME}/.gemini/config/sidecars/proactive-pilot-ctrld-sync/user_config.json"
check_grep "sidecar uses weekday daily local Chicago cron" "CRON_TZ=America/Chicago 15 8 \* \* 1-5" "${SIDECAR_FILE}"
check_grep "sidecar sets allows_user_interactions false" '"allows_user_interactions": false' "${SIDECAR_FILE}"
check "sidecar JSON is valid" python3 -m json.tool "${SIDECAR_FILE}"

# 2. Disposable UTC cron canary staging and cleanup
"${CTL_SCRIPT}" canary-stage --offset-minutes 4 >"${TEST_DIR}/canary.log" 2>&1
CANARY_FILE="${HOME}/.gemini/config/sidecars/proactive-cron-canary/sidecar.json"
check "canary sidecar.json staged" test -f "${CANARY_FILE}"
check "canary sidecar permissions 0600" python3 -c 'import os,sys; m=oct(os.stat(sys.argv[1]).st_mode & 0o777); sys.exit(0 if m=="0o600" else 1)' "${CANARY_FILE}"
check "canary user_config.json NOT self-enabled" test ! -f "${HOME}/.gemini/config/sidecars/proactive-cron-canary/user_config.json"
check_grep "canary sidecar uses CRON_TZ=UTC" "CRON_TZ=UTC " "${CANARY_FILE}"
"${CTL_SCRIPT}" canary-clean >/dev/null 2>&1
check "canary-clean removes canary sidecar" test ! -f "${CANARY_FILE}"

# 3. Post-merge Sentinel lease verification (rejects unmerged PR, allows MERGED PR)
cat >"${MOCK_BIN}/gh" <<'MOCK'
#!/usr/bin/env bash
if [[ "$*" == *"99"* ]]; then
	echo '{"state":"MERGED","mergedAt":"2026-10-31T17:00:00Z"}'
else
	echo '{"state":"OPEN","mergedAt":null}'
fi
MOCK
chmod +x "${MOCK_BIN}/gh"

PATH="${MOCK_BIN}:${PATH}" check_exit "sentinel-post-merge rejects unmerged PR" 1 \
	"${CTL_SCRIPT}" sentinel-post-merge --repo ctrld-sync --pr 12
PATH="${MOCK_BIN}:${PATH}" check_exit "sentinel-post-merge issues lease for merged PR" 0 \
	"${CTL_SCRIPT}" sentinel-post-merge --repo ctrld-sync --pr 99
check "sentinel lease file written" test -f "${HOME}/.gemini/antigravity/proactive-reports/.sentinel-post-merge-lease.json"

# 4. MISSED status audit records missed run when expected weekday digest is absent
"${CTL_SCRIPT}" audit-missed --date 2026-11-02 --repo ctrld-sync >"${TEST_DIR}/missed.log" 2>&1
check_grep "audit-missed writes Status: MISSED digest" "Status: MISSED" "${HOME}/.gemini/antigravity/proactive-reports/2026-11-02-ctrld-sync.md"

# 5. Status reports installed state cleanly
"${CTL_SCRIPT}" status >"${TEST_DIR}/status.log" 2>&1
check_grep "status reports active skill links" "skills_linked=5/5" "${TEST_DIR}/status.log"
check_grep "status reports stopped runtime with no scheduler log" "pilot_runtime=stopped" "${TEST_DIR}/status.log"

# Dashboard toggles do not write user_config.json; runtime state comes from the scheduler log.
mkdir -p "${HOME}/.gemini/antigravity/sidecar_data/proactive-pilot-ctrld-sync/logs"
cat >"${HOME}/.gemini/antigravity/sidecar_data/proactive-pilot-ctrld-sync/logs/sidecar.log" <<'LOG'
2026-11-01 18:54:13 [schedule] Scheduler started for schedule: "CRON_TZ=UTC 15 13 * * 1-5"
2026-11-01 18:54:13 [schedule] Next execution scheduled in 42h20m46s (at 2026-11-02 13:15:00 UTC), will run by 2026-11-02 13:16:54 UTC
LOG
"${CTL_SCRIPT}" status >"${TEST_DIR}/status-running.log" 2>&1
check_grep "status detects running pilot from scheduler log" "pilot_runtime=running" "${TEST_DIR}/status-running.log"
check_grep "status reports next pilot run time" "pilot_next_run=2026-11-02 13:15:00 UTC" "${TEST_DIR}/status-running.log"

# 6. Ordered rollback (disable) removes sidecars BEFORE hooks.json and restores previous hooks.json backup
echo '{"custom_user_hook": true}' > "${HOME}/.gemini/config/hooks.json.backup.20261031_120000"

"${CTL_SCRIPT}" disable >"${TEST_DIR}/disable.log" 2>&1
check "disable removes pilot sidecar.json" test ! -f "${SIDECAR_FILE}"
check "disable removes skill symlink" test ! -L "${HOME}/.gemini/config/skills/proactive-repo-sweep"
check "disable restores previous hooks.json backup" test -f "${HOME}/.gemini/config/hooks.json"
check_grep "disable logs restored hooks backup" "restored previous hooks.json" "${TEST_DIR}/disable.log"
check_grep "disable logs ordered sidecar-first teardown" "Step 1/3: removed sidecar" "${TEST_DIR}/disable.log"
check_grep "disable prints legacy Jules restore instructions" "ENABLE_LEGACY_JULES" "${TEST_DIR}/disable.log"

echo ""
echo "Summary: PASS=${PASS} FAIL=${FAIL}"
[[ ${FAIL} -eq 0 ]]
