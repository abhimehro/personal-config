#!/usr/bin/env bash
#
# Unit tests for scripts/antigravity-proactive-ctl.sh
# Verifies idempotent install, chmod 700 transcript/report dirs, weekday UTC cron,
# allows_user_interactions=false, disposable cron canary staging/cleanup,
# post-merge Sentinel lease verification, MISSED digest audit, base-relative
# classification of verify failures (NO_FAILURE / FLAKE_ON_RETRY /
# PRE_EXISTING_ON_BASE / CAUSED_BY_CHANGE) including test-command resolution
# through proactive-worktree.sh print-test-cmd, and ordered rollback.

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

# 6. base-check classifies a verify failure relative to a pristine base worktree.
#    A verify failure is not automatically the candidate's fault: Jules stranded
#    four good PRs on breakage the change did not cause.
WT_SCRIPT="${REPO_ROOT}/scripts/proactive-worktree.sh"
BC_REMOTE="${TEST_DIR}/bc-remote.git"
BC_SEED="${TEST_DIR}/bc-seed"
BC_CLONE="${TEST_DIR}/bc-repo"
BC_WT_ROOT="${TEST_DIR}/bc-worktrees"
mkdir -p "${BC_WT_ROOT}"

git init --bare -q "${BC_REMOTE}"
git init -q "${BC_SEED}"
git -C "${BC_SEED}" config user.email "test@example.com"
git -C "${BC_SEED}" config user.name "Test User"
git -C "${BC_SEED}" checkout -q -b main
cat >"${BC_SEED}/stage1.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"${BC_SEED}/stage2.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "${BC_SEED}/stage1.sh" "${BC_SEED}/stage2.sh"
git -C "${BC_SEED}" add .
git -C "${BC_SEED}" commit -q -m "green base"
git -C "${BC_SEED}" remote add origin "${BC_REMOTE}"
git -C "${BC_SEED}" push -q -u origin main
git --git-dir="${BC_REMOTE}" symbolic-ref HEAD refs/heads/main
git clone -q "${BC_REMOTE}" "${BC_CLONE}"
git -C "${BC_CLONE}" remote set-head origin -a >/dev/null 2>&1

BC_TEST_CMD="bash stage1.sh && bash stage2.sh"

# (a) Nothing fails: there is no failure to classify.
WT_OK="$("${WT_SCRIPT}" prepare --repo-path "${BC_CLONE}" --lens code-health --worktree-root "${BC_WT_ROOT}")"
check_exit "base-check reports NO_FAILURE when every stage passes" 0 \
	"${CTL_SCRIPT}" base-check --repo bc-repo --worktree "${WT_OK}" --test-cmd "${BC_TEST_CMD}"
check_grep "base-check prints the NO_FAILURE verdict" "^VERDICT: NO_FAILURE$" "${TEST_DIR}/check.log"
check_grep "base-check maps NO_FAILURE to Substatus NONE" "^SUBSTATUS: NONE$" "${TEST_DIR}/check.log"

# (b) Base is green but the candidate breaks a stage: a real regression.
WT_BAD="$("${WT_SCRIPT}" prepare --repo-path "${BC_CLONE}" --lens code-health --worktree-root "${BC_WT_ROOT}")"
printf '#!/usr/bin/env bash\nexit 1\n' >"${WT_BAD}/stage2.sh"
git -C "${WT_BAD}" config user.email "test@example.com"
git -C "${WT_BAD}" config user.name "Test User"
git -C "${WT_BAD}" commit -qam "chore(qa): break stage two"
BC_DIGEST="${TEST_DIR}/bc-digest.md"
printf '# Proactive Sweep Digest\n\n- Status: CANDIDATE_READY\n' >"${BC_DIGEST}"
chmod 600 "${BC_DIGEST}"
check_exit "base-check exits 2 when the candidate causes the failure" 2 \
	"${CTL_SCRIPT}" base-check --repo bc-repo --worktree "${WT_BAD}" --test-cmd "${BC_TEST_CMD}" \
	--digest "${BC_DIGEST}"
check_grep "base-check names the regression verdict" "^VERDICT: CAUSED_BY_CHANGE$" "${TEST_DIR}/check.log"
check_grep "base-check maps the regression to GATE_FAILURE" "^SUBSTATUS: GATE_FAILURE$" "${TEST_DIR}/check.log"
check_grep "base-check identifies the failing stage" "stage 1 \(bash stage2.sh\)" "${TEST_DIR}/check.log"
check_grep "base-check appends a classification section to the digest" "^## Base-Check Classification$" "${BC_DIGEST}"
check_grep "base-check records the verdict in the digest" "^- Verdict: CAUSED_BY_CHANGE$" "${BC_DIGEST}"
BC_DIGEST_PERMS="$(stat -c '%a' "${BC_DIGEST}" 2>/dev/null || stat -f '%OLp' "${BC_DIGEST}")"
check "base-check keeps the digest at mode 600" test "${BC_DIGEST_PERMS}" = "600"
check "base-check removes its temporary base worktree" bash -c "! git -C '${WT_BAD}' worktree list | grep -q '/base'"

# (c) Base is already broken: the candidate inherits the failure and stays promotable.
printf '#!/usr/bin/env bash\nexit 1\n' >"${BC_CLONE}/stage2.sh"
git -C "${BC_CLONE}" config user.email "test@example.com"
git -C "${BC_CLONE}" config user.name "Test User"
git -C "${BC_CLONE}" commit -qam "break stage two on main"
git -C "${BC_CLONE}" push -q origin main
WT_PRE="$("${WT_SCRIPT}" prepare --repo-path "${BC_CLONE}" --lens code-health --worktree-root "${BC_WT_ROOT}")"
check_exit "base-check exits 0 when the failure pre-exists on base" 0 \
	"${CTL_SCRIPT}" base-check --repo bc-repo --worktree "${WT_PRE}" --test-cmd "${BC_TEST_CMD}"
check_grep "base-check names the pre-existing verdict" "^VERDICT: PRE_EXISTING_ON_BASE$" "${TEST_DIR}/check.log"
check_grep "base-check maps pre-existing breakage to PRE_EXISTING_FAILURE" "^SUBSTATUS: PRE_EXISTING_FAILURE$" "${TEST_DIR}/check.log"
check_grep "base-check records the base sha it compared against" "^BASE_SHA: [0-9a-f]{7,40}$" "${TEST_DIR}/check.log"

# (d) One flake-retry before classifying, so an unrelated flaky shard is not
#     charged to the candidate and no base run is needed.
FLAKE_STATE="${TEST_DIR}/flake-state"
cat >"${TEST_DIR}/flake.sh" <<EOF
#!/usr/bin/env bash
if [[ -f "${FLAKE_STATE}" ]]; then exit 0; fi
touch "${FLAKE_STATE}"
exit 1
EOF
chmod +x "${TEST_DIR}/flake.sh"
rm -f "${FLAKE_STATE}"
WT_FLAKE="$("${WT_SCRIPT}" prepare --repo-path "${BC_CLONE}" --lens code-health --worktree-root "${BC_WT_ROOT}")"
check_exit "base-check exits 0 when the failing stage passes on retry" 0 \
	"${CTL_SCRIPT}" base-check --repo bc-repo --worktree "${WT_FLAKE}" --test-cmd "bash ${TEST_DIR}/flake.sh"
check_grep "base-check names the flake verdict" "^VERDICT: FLAKE_ON_RETRY$" "${TEST_DIR}/check.log"
check_grep "base-check maps a flake to Substatus NONE" "^SUBSTATUS: NONE$" "${TEST_DIR}/check.log"

# (e) Fail closed rather than classify against a base that cannot be materialised.
WT_BOGUS="$("${WT_SCRIPT}" prepare --repo-path "${BC_CLONE}" --lens code-health --worktree-root "${BC_WT_ROOT}")"
BOGUS_META="$(git -C "${WT_BOGUS}" rev-parse --git-dir)/proactive-meta.json"
python3 - "${BOGUS_META}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    meta = json.load(handle)
meta["base_sha"] = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(meta, handle)
PY
check_exit "base-check exits 6 when the base worktree cannot be created" 6 \
	"${CTL_SCRIPT}" base-check --repo bc-repo --worktree "${WT_BOGUS}" --test-cmd "${BC_TEST_CMD}"
check_grep "base-check explains the unusable base sha" "pristine base worktree" "${TEST_DIR}/check.log"

# (f) Usage and identity guards.
check_exit "base-check requires --repo and --worktree" 1 \
	"${CTL_SCRIPT}" base-check --repo bc-repo
check_exit "base-check rejects a --repo that does not match the worktree" 1 \
	"${CTL_SCRIPT}" base-check --repo other-repo --worktree "${WT_OK}" --test-cmd "${BC_TEST_CMD}"
check_grep "base-check explains the repo mismatch" "does not match the worktree's repo_name" "${TEST_DIR}/check.log"
check_exit "base-check rejects a directory that is not a proactive worktree" 1 \
	"${CTL_SCRIPT}" base-check --repo bc-repo --worktree "${BC_CLONE}" --test-cmd "${BC_TEST_CMD}"
check_grep "base-check explains the missing metadata" "proactive-meta.json" "${TEST_DIR}/check.log"
check_exit "base-check rejects a missing --digest path" 1 \
	"${CTL_SCRIPT}" base-check --repo bc-repo --worktree "${WT_OK}" --test-cmd "${BC_TEST_CMD}" \
	--digest "${TEST_DIR}/no-such-digest.md"
check_exit "base-check rejects an unknown flag" 1 \
	"${CTL_SCRIPT}" base-check --repo bc-repo --worktree "${WT_OK}" --nonsense

# (g) Production path: the triage sidecar never passes --test-cmd, so base-check must
#     resolve it through proactive-worktree.sh print-test-cmd and then run it. An
#     unmapped repo name resolves to the pytest default, which the stub below passes.
MOCK_BIN_PY="${TEST_DIR}/mock_bin_py"
mkdir -p "${MOCK_BIN_PY}"
REAL_PYTHON3="$(command -v python3)"
cat >"${MOCK_BIN_PY}/python3" <<MOCK
#!/usr/bin/env bash
# base-check reads proactive-meta.json via 'python3 -c'; only the resolved test
# command ('python3 -m pytest -q') should reach the stub.
if [[ "\$1" == "-c" ]]; then
	exec "${REAL_PYTHON3}" "\$@"
fi
exit 0
MOCK
chmod +x "${MOCK_BIN_PY}/python3"
WT_DEFAULT="$("${WT_SCRIPT}" prepare --repo-path "${BC_CLONE}" --lens code-health --worktree-root "${BC_WT_ROOT}")"
# env, not a PATH= prefix on check_exit: bash keeps a function-call assignment in
# effect for the rest of the file, which would leak the stub into later sections.
check_exit "base-check resolves its test command from print-test-cmd" 0 \
	env PATH="${MOCK_BIN_PY}:${PATH}" "${CTL_SCRIPT}" base-check --repo bc-repo --worktree "${WT_DEFAULT}"
check_grep "base-check classifies the resolved default command" "^VERDICT: NO_FAILURE$" "${TEST_DIR}/check.log"

# 7. Ordered rollback (disable) removes sidecars BEFORE hooks.json and restores previous hooks.json backup
echo '{"custom_user_hook": true}' >"${HOME}/.gemini/config/hooks.json.backup.20261031_120000"

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
