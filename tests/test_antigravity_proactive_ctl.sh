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

# 3. Post-merge Sentinel lease verification (rejects unmerged, stale, future, and malformed input)
# Merge timestamps are generated at run time because the lease requires a fresh merge.
iso_offset() {
	python3 -c 'import datetime,sys; print((datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=int(sys.argv[1]))).strftime("%Y-%m-%dT%H:%M:%SZ"))' "$1"
}
export MOCK_NOW_ISO MOCK_STALE_ISO MOCK_FUTURE_ISO
MOCK_NOW_ISO="$(iso_offset -30)"
MOCK_STALE_ISO="$(iso_offset -7200)"
MOCK_FUTURE_ISO="$(iso_offset 3600)"
cat >"${MOCK_BIN}/gh" <<'MOCK'
#!/usr/bin/env bash
case " $* " in
*" 99 "*) echo "{\"state\":\"MERGED\",\"mergedAt\":\"${MOCK_NOW_ISO}\"}" ;;
*" 98 "*) echo "{\"state\":\"MERGED\",\"mergedAt\":\"${MOCK_STALE_ISO}\"}" ;;
*" 97 "*) echo "{\"state\":\"MERGED\",\"mergedAt\":\"${MOCK_FUTURE_ISO}\"}" ;;
*) echo '{"state":"OPEN","mergedAt":null}' ;;
esac
MOCK
chmod +x "${MOCK_BIN}/gh"
LEASE_FILE="${HOME}/.gemini/antigravity/proactive-reports/.sentinel-post-merge-lease.json"

PATH="${MOCK_BIN}:${PATH}" check_exit "sentinel-post-merge rejects unmerged PR" 1 \
	"${CTL_SCRIPT}" sentinel-post-merge --repo ctrld-sync --pr 12
PATH="${MOCK_BIN}:${PATH}" check_exit "sentinel-post-merge rejects stale merge outside window" 1 \
	"${CTL_SCRIPT}" sentinel-post-merge --repo ctrld-sync --pr 98
check_grep "sentinel-post-merge explains the post-merge window" "post-merge window" "${TEST_DIR}/check.log"
PATH="${MOCK_BIN}:${PATH}" check_exit "sentinel-post-merge rejects future merge timestamp" 1 \
	"${CTL_SCRIPT}" sentinel-post-merge --repo ctrld-sync --pr 97
PATH="${MOCK_BIN}:${PATH}" check_exit "sentinel-post-merge rejects non-numeric --pr" 1 \
	"${CTL_SCRIPT}" sentinel-post-merge --repo ctrld-sync --pr "99 --json"
PATH="${MOCK_BIN}:${PATH}" check_exit "sentinel-post-merge rejects dot-dot --repo" 1 \
	"${CTL_SCRIPT}" sentinel-post-merge --repo .. --pr 99
check "no lease written by any rejected request" test ! -f "${LEASE_FILE}"
PATH="${MOCK_BIN}:${PATH}" check_exit "sentinel-post-merge issues lease for freshly merged PR" 0 \
	"${CTL_SCRIPT}" sentinel-post-merge --repo ctrld-sync --pr 99
check "sentinel lease file written" test -f "${LEASE_FILE}"

# 4. MISSED status audit records missed run when expected weekday digest is absent
REPORTS="${HOME}/.gemini/antigravity/proactive-reports"
"${CTL_SCRIPT}" audit-missed --date 2026-11-02 --repo ctrld-sync >"${TEST_DIR}/missed.log" 2>&1
check_grep "audit-missed writes Status: MISSED digest" "Status: MISSED" "${REPORTS}/2026-11-02-ctrld-sync.md"
# 08:15 America/Chicago is 14:15 UTC under standard time (CST) and 13:15 UTC under daylight time (CDT)
check_grep "audit-missed slot is 14:15 UTC under standard time" "08:15 America/Chicago \(14:15 UTC\)" "${REPORTS}/2026-11-02-ctrld-sync.md"
"${CTL_SCRIPT}" audit-missed --date 2026-06-01 --repo ctrld-sync >"${TEST_DIR}/missed-dst.log" 2>&1
check_grep "audit-missed slot is 13:15 UTC under daylight time" "08:15 America/Chicago \(13:15 UTC\)" "${REPORTS}/2026-06-01-ctrld-sync.md"
check_exit "audit-missed rejects impossible calendar date" 1 \
	"${CTL_SCRIPT}" audit-missed --date 2026-02-30 --repo ctrld-sync
check_exit "audit-missed rejects malformed date" 1 \
	"${CTL_SCRIPT}" audit-missed --date 2026-1-2 --repo ctrld-sync
check_exit "audit-missed rejects dot-dot repo name" 1 \
	"${CTL_SCRIPT}" audit-missed --date 2026-11-03 --repo ..
check "audit-missed wrote nothing for rejected input" test -z "$(find "${REPORTS}" -name '2026-11-03*' -o -name '2026-02-30*' -o -name '2026-1-2*' 2>/dev/null)"

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

# A user-managed symlink at a proactive skill path must survive rollback untouched
FOREIGN_SKILL="${TEST_DIR}/user-managed-skill"
mkdir -p "${FOREIGN_SKILL}"
rm -f "${HOME}/.gemini/config/skills/proactive-bolt"
ln -s "${FOREIGN_SKILL}" "${HOME}/.gemini/config/skills/proactive-bolt"

"${CTL_SCRIPT}" disable >"${TEST_DIR}/disable.log" 2>&1
check "disable removes pilot sidecar.json" test ! -f "${SIDECAR_FILE}"
check "disable removes skill symlink" test ! -L "${HOME}/.gemini/config/skills/proactive-repo-sweep"
check "disable leaves a user-managed skill symlink in place" test "$(readlink "${HOME}/.gemini/config/skills/proactive-bolt")" = "${FOREIGN_SKILL}"
check_grep "disable reports the skipped user-managed symlink" "skipped .*proactive-bolt" "${TEST_DIR}/disable.log"
check_grep "disable counts only the symlinks it removed" "unlinked 4 proactive skill symlinks" "${TEST_DIR}/disable.log"
check "disable restores previous hooks.json backup" test -f "${HOME}/.gemini/config/hooks.json"
check_grep "disable logs restored hooks backup" "restored previous hooks.json" "${TEST_DIR}/disable.log"
check_grep "disable logs ordered sidecar-first teardown" "Step 1/3: removed sidecar" "${TEST_DIR}/disable.log"
check_grep "disable prints legacy Jules restore instructions" "ENABLE_LEGACY_JULES" "${TEST_DIR}/disable.log"

echo ""
echo "Summary: PASS=${PASS} FAIL=${FAIL}"
[[ ${FAIL} -eq 0 ]]
