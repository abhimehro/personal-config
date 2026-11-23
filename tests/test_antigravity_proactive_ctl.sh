#!/usr/bin/env bash
#
# Unit tests for scripts/antigravity-proactive-ctl.sh
# Verifies idempotent install, chmod 700 transcript/report dirs, weekday Chicago cron,
# allows_user_interactions=false, timezone-aware disposable cron canary staging/cleanup,
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

# 1. Install pilot setup into isolated HOME (including clean migration from legacy symlinks)
ln -s "${REPO_ROOT}/configs/antigravity/skills/proactive-sentinel" "${HOME}/.gemini/config/skills/proactive-sentinel"
ln -s "${REPO_ROOT}/configs/antigravity/hooks.json" "${HOME}/.gemini/config/hooks.json"
"${CTL_SCRIPT}" install --pilot >"${TEST_DIR}/install.log" 2>&1

for skill in proactive-sentinel proactive-bolt proactive-palette proactive-code-health proactive-repo-sweep; do
	check "skill copied as directory: ${skill}" test -d "${HOME}/.gemini/config/skills/${skill}"
	check "skill is not a symlink: ${skill}" test ! -L "${HOME}/.gemini/config/skills/${skill}"
	check "skill SKILL.md present: ${skill}" test -f "${HOME}/.gemini/config/skills/${skill}/SKILL.md"
done

check "global hooks.json copied as regular file" test -f "${HOME}/.gemini/config/hooks.json"
check "global hooks.json is not a symlink" test ! -L "${HOME}/.gemini/config/hooks.json"
check "deployed proactive-worktree.sh is executable" test -x "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh"
check "deployed antigravity-proactive-ctl.sh is executable" test -x "${HOME}/.gemini/config/proactive/scripts/antigravity-proactive-ctl.sh"
check "deployed proactive-guard.py present" test -f "${HOME}/.gemini/config/proactive/hooks/proactive-guard.py"
check "reports directory created" test -d "${HOME}/.gemini/antigravity/proactive-reports"
check "migrating legacy symlinks creates no spurious hooks backup" bash -c "! compgen -G '${HOME}/.gemini/config/hooks.json.backup.*' >/dev/null"

# Second install must be idempotent without creating backup churn
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1
check "idempotent reinstall creates no spurious hooks backup" bash -c "! compgen -G '${HOME}/.gemini/config/hooks.json.backup.*' >/dev/null"

SIDECAR_FILE="${HOME}/.gemini/config/sidecars/proactive-pilot-ctrld-sync/sidecar.json"
TRIAGE_SIDECAR_FILE="${HOME}/.gemini/config/sidecars/proactive-pilot-triage/sidecar.json"
check "disabled pilot sidecar.json created" test -f "${SIDECAR_FILE}"
check "disabled triage sidecar.json created" test -f "${TRIAGE_SIDECAR_FILE}"
check_grep "pilot sidecar uses deployed proactive-worktree.sh" "\.gemini/config/proactive/scripts/proactive-worktree\.sh" "${SIDECAR_FILE}"
check_grep "pilot sidecar includes Step 0 preflight --auto-heal" "preflight --repo abhimehro/ctrld-sync --repo-path .* --auto-heal" "${SIDECAR_FILE}"
check_grep "pilot sidecar grants gh auth status" '"command\(gh auth status\)"' "${SIDECAR_FILE}"
check_grep "triage sidecar uses deployed antigravity-proactive-ctl.sh" "\.gemini/config/proactive/scripts/antigravity-proactive-ctl\.sh" "${TRIAGE_SIDECAR_FILE}"
check_grep "triage sidecar grants ctl doctor" 'antigravity-proactive-ctl\.sh doctor' "${TRIAGE_SIDECAR_FILE}"
check "user_config.json NOT created or self-enabled" test ! -f "${HOME}/.gemini/config/sidecars/proactive-pilot-ctrld-sync/user_config.json"
check "triage user_config.json NOT created or self-enabled" test ! -f "${HOME}/.gemini/config/sidecars/proactive-pilot-triage/user_config.json"
check_grep "sidecar uses weekday daily local Chicago cron" "CRON_TZ=America/Chicago 15 8 \* \* 1-5" "${SIDECAR_FILE}"
check_grep "sidecar sets allows_user_interactions false" '"allows_user_interactions": false' "${SIDECAR_FILE}"
check "sidecar JSON is valid" python3 -m json.tool "${SIDECAR_FILE}"
check "triage sidecar JSON is valid" python3 -m json.tool "${TRIAGE_SIDECAR_FILE}"

# 2. Disposable timezone-aware cron canary staging and cleanup
"${CTL_SCRIPT}" canary-stage --offset-minutes 4 >"${TEST_DIR}/canary.log" 2>&1
CANARY_FILE="${HOME}/.gemini/config/sidecars/proactive-cron-canary/sidecar.json"
check "canary sidecar.json staged" test -f "${CANARY_FILE}"
check "canary sidecar permissions 0600" python3 -c 'import os,sys; m=oct(os.stat(sys.argv[1]).st_mode & 0o777); sys.exit(0 if m=="0o600" else 1)' "${CANARY_FILE}"
check "canary user_config.json NOT self-enabled" test ! -f "${HOME}/.gemini/config/sidecars/proactive-cron-canary/user_config.json"
check_grep "canary defaults to CRON_TZ=America/Chicago" "CRON_TZ=America/Chicago " "${CANARY_FILE}"
check_grep "canary receipt renamed off UTC default" "canary-america-chicago-receipt\.md" "${CANARY_FILE}"
check_grep "canary confirmation prints zone plus local and UTC times" "America/Chicago.*UTC" "${TEST_DIR}/canary.log"

# Verify local vs UTC hour conversion and midnight date rollover (04:58 UTC + 4m = 05:02 UTC = 23:02 CST prev day)
env PROACTIVE_CANARY_NOW_UTC="2026-11-13T04:58:00Z" "${CTL_SCRIPT}" canary-stage --offset-minutes 4 >"${TEST_DIR}/canary-rollover.log" 2>&1
check_grep "canary converts UTC into America/Chicago local hour and date" '"CRON_TZ=America/Chicago 2 23 12 11 \*"' "${CANARY_FILE}"

# Verify DST boundaries: spring forward (07:58 UTC + 4m = 08:02 UTC = 03:02 CDT) and fall back (06:58 UTC + 4m = 07:02 UTC = 01:02 CST)
env PROACTIVE_CANARY_NOW_UTC="2026-03-08T07:58:00Z" "${CTL_SCRIPT}" canary-stage --offset-minutes 4 >"${TEST_DIR}/canary-spring.log" 2>&1
check_grep "canary handles spring-forward DST transition" '"CRON_TZ=America/Chicago 2 3 8 3 \*"' "${CANARY_FILE}"
env PROACTIVE_CANARY_NOW_UTC="2026-11-01T06:58:00Z" "${CTL_SCRIPT}" canary-stage --offset-minutes 4 >"${TEST_DIR}/canary-fallback.log" 2>&1
check_grep "canary handles fall-back DST transition" '"CRON_TZ=America/Chicago 2 1 1 11 \*"' "${CANARY_FILE}"

# Keep explicit UTC reachable for per-sidecar-isolation tests, and fail closed on invalid timezones
env PROACTIVE_CANARY_NOW_UTC="2026-11-13T04:58:00Z" "${CTL_SCRIPT}" canary-stage --offset-minutes 4 --timezone UTC >"${TEST_DIR}/canary-utc.log" 2>&1
check_grep "canary explicit --timezone UTC uses CRON_TZ=UTC" '"CRON_TZ=UTC 2 5 13 11 \*"' "${CANARY_FILE}"
check_grep "canary explicit --timezone UTC uses utc receipt name" "canary-utc-receipt\.md" "${CANARY_FILE}"
check_exit "canary-stage rejects unknown IANA timezone" 1 \
	"${CTL_SCRIPT}" canary-stage --timezone "Mars/Olympus_Mons"
check_exit "canary-stage rejects missing flag value cleanly" 1 \
	"${CTL_SCRIPT}" canary-stage --timezone

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

# 5. Status reports installed state cleanly (and catches dangling symlinks / non-exec runtime)
"${CTL_SCRIPT}" status >"${TEST_DIR}/status.log" 2>&1
check_grep "status reports active skills" "^skills_linked=5/5$" "${TEST_DIR}/status.log"
check_grep "status reports copy hooks mode" "^hooks_mode=copy$" "${TEST_DIR}/status.log"
check_grep "status reports zero dangling links" "^dangling_links=0$" "${TEST_DIR}/status.log"
check_grep "status reports healthy deployed runtime scripts" "^runtime_worktree_sh=ok$" "${TEST_DIR}/status.log"
check_grep "status reports healthy deployed ctl script" "^runtime_ctl_sh=ok$" "${TEST_DIR}/status.log"
check_grep "status reports healthy deployed guard script" "^runtime_guard_py=ok$" "${TEST_DIR}/status.log"
check_grep "status reports stopped runtime with no scheduler log" "pilot_runtime=stopped" "${TEST_DIR}/status.log"
check_grep "status reports triage sidecar present" "triage_sidecar=present" "${TEST_DIR}/status.log"
check_grep "status reports stopped triage runtime with no scheduler log" "triage_runtime=stopped" "${TEST_DIR}/status.log"

# Introduce dangling skill + hooks symlinks and non-executable worktree script
rm -rf "${HOME}/.gemini/config/skills/proactive-palette" "${HOME}/.gemini/config/hooks.json"
ln -s "${TEST_DIR}/missing-skill-target" "${HOME}/.gemini/config/skills/proactive-palette"
ln -s "${TEST_DIR}/missing-hooks-target" "${HOME}/.gemini/config/hooks.json"
chmod 644 "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh"
"${CTL_SCRIPT}" status >"${TEST_DIR}/status-broken.log" 2>&1
check_grep "status excludes dangling skill symlink from healthy count" "^skills_linked=4/5$" "${TEST_DIR}/status-broken.log"
check_grep "status excludes dangling hooks symlink" "^hooks_linked=no$" "${TEST_DIR}/status-broken.log"
check_grep "status identifies broken hooks symlink mode" "^hooks_mode=broken-symlink$" "${TEST_DIR}/status-broken.log"
check_grep "status counts both dangling symlinks" "^dangling_links=2$" "${TEST_DIR}/status-broken.log"
check_grep "status flags non-executable worktree runner" "^runtime_worktree_sh=not-executable$" "${TEST_DIR}/status-broken.log"

# Re-install repairs broken symlinks and permissions cleanly
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1
"${CTL_SCRIPT}" status >"${TEST_DIR}/status-repaired.log" 2>&1
check_grep "reinstall restores skills_linked=5/5 after dangling symlinks" "^skills_linked=5/5$" "${TEST_DIR}/status-repaired.log"
check_grep "reinstall clears dangling links count" "^dangling_links=0$" "${TEST_DIR}/status-repaired.log"
check_grep "reinstall restores executable worktree runner" "^runtime_worktree_sh=ok$" "${TEST_DIR}/status-repaired.log"

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
rm -rf "${HOME}/.gemini/config/skills/proactive-bolt"
ln -s "${FOREIGN_SKILL}" "${HOME}/.gemini/config/skills/proactive-bolt"

"${CTL_SCRIPT}" disable >"${TEST_DIR}/disable.log" 2>&1
check "disable removes pilot sidecar.json" test ! -f "${SIDECAR_FILE}"
check "disable removes managed skill directory" test ! -e "${HOME}/.gemini/config/skills/proactive-repo-sweep"
check "disable removes deployed runtime directory" test ! -d "${HOME}/.gemini/config/proactive"
check "disable leaves a user-managed skill symlink in place" test "$(readlink "${HOME}/.gemini/config/skills/proactive-bolt")" = "${FOREIGN_SKILL}"
check_grep "disable reports the skipped user-managed symlink" "skipped .*proactive-bolt" "${TEST_DIR}/disable.log"
check_grep "disable counts only the managed skills it removed" "removed 4 managed proactive skill" "${TEST_DIR}/disable.log"
check "disable restores previous hooks.json backup" test -f "${HOME}/.gemini/config/hooks.json"
check_grep "disable logs restored hooks backup" "restored previous hooks.json" "${TEST_DIR}/disable.log"
check_grep "disable logs ordered sidecar-first teardown" "Step 1/3: removed sidecar" "${TEST_DIR}/disable.log"
check_grep "disable prints legacy Jules restore instructions" "ENABLE_LEGACY_JULES" "${TEST_DIR}/disable.log"

# Copy deployment must preserve user content and refresh managed assets.
# Use a separate home so these cases cannot inherit backups from earlier tests.
export HOME="${TEST_DIR}/deployment-home"
CONFIG="${HOME}/.gemini/config"
RUNTIME="${CONFIG}/proactive"
SKILL="${CONFIG}/skills/proactive-bolt"
mkdir -p "${SKILL}"
printf 'user skill\n' >"${SKILL}/SKILL.md"
printf 'user skill\n' >"${TEST_DIR}/expected-user-skill.md"
printf '{"user_hook": true}\n' >"${TEST_DIR}/original-hooks.json"
cp "${TEST_DIR}/original-hooks.json" "${CONFIG}/hooks.json"
"${CTL_SCRIPT}" install >"${TEST_DIR}/copy-install.log" 2>&1
check "install backs up unmanaged skill content" cmp "${CONFIG}"/skills/proactive-bolt.backup.*/SKILL.md "${TEST_DIR}/expected-user-skill.md"
check "install backs up unmanaged hooks content" cmp "${CONFIG}"/hooks.json.backup.* "${TEST_DIR}/original-hooks.json"
check "deployed runtime and hook permissions are restricted" python3 - "${CONFIG}" <<'PYTEST'
import pathlib
import stat
import sys

root = pathlib.Path(sys.argv[1])
expected = {
    "hooks.json": 0o600,
    "proactive": 0o700,
    "proactive/scripts": 0o700,
    "proactive/hooks": 0o700,
    "proactive/.hooks-managed": 0o600,
    "proactive/scripts/proactive-worktree.sh": 0o755,
    "proactive/scripts/antigravity-proactive-ctl.sh": 0o755,
    "proactive/hooks/proactive-guard.py": 0o644,
}
assert all(stat.S_IMODE((root / name).stat().st_mode) == mode
           for name, mode in expected.items())
PYTEST

# Stop before mutation if a regression has linked either asset to the checkout.
python3 - "${RUNTIME}/scripts/proactive-worktree.sh" "${REPO_ROOT}/scripts/proactive-worktree.sh" "${SKILL}" "${REPO_ROOT}/configs/antigravity/skills/proactive-bolt" <<'PYTEST'
import pathlib
import sys

for deployed, source in zip(sys.argv[1::2], sys.argv[2::2]):
    if pathlib.Path(deployed).samefile(source):
        sys.exit(f"Refusing to mutate deployed asset linked to source: {deployed}")
PYTEST

# A changed deployed copy must never change the source repository.
printf 'stale runtime\n' >"${RUNTIME}/scripts/proactive-worktree.sh"
touch "${SKILL}/obsolete-file"
"${CTL_SCRIPT}" install >/dev/null 2>&1
check "reinstall refreshes runtime bytes from source" cmp "${RUNTIME}/scripts/proactive-worktree.sh" "${REPO_ROOT}/scripts/proactive-worktree.sh"
check "reinstall drops obsolete managed skill files" test ! -e "${SKILL}/obsolete-file"
check "reinstall refreshes skill bytes from source" cmp "${SKILL}/SKILL.md" "${REPO_ROOT}/configs/antigravity/skills/proactive-bolt/SKILL.md"

# A matching stamp authorizes removal; user edits must revoke that authority.
printf '{"edited_hook": true}\n' >"${CONFIG}/hooks.json"
cp "${CONFIG}/hooks.json" "${TEST_DIR}/edited-hooks.json"
rm "${SKILL}/.managed-by-proactive-ctl"
"${CTL_SCRIPT}" disable >"${TEST_DIR}/disable-edited.log" 2>&1
check "disable preserves hooks changed since deployment" cmp "${CONFIG}/hooks.json" "${TEST_DIR}/edited-hooks.json"
check "disable preserves unmarked skill directory" test -f "${SKILL}/SKILL.md"
check "disable preserves runtime while custom hooks remain" test -d "${RUNTIME}"
check "disable does not consume original hooks backup" cmp "${CONFIG}"/hooks.json.backup.* "${TEST_DIR}/original-hooks.json"

rm "${CONFIG}"/hooks.json.backup.*

# Reinstall must back up the edit, and rollback must restore that latest edit.
"${CTL_SCRIPT}" install >/dev/null 2>&1
"${CTL_SCRIPT}" disable >/dev/null 2>&1
check "rollback restores hooks edited before reinstall" cmp "${CONFIG}/hooks.json" "${TEST_DIR}/edited-hooks.json"

# Status must distinguish missing assets from healthy copies.
export HOME="${TEST_DIR}/empty-status-home"
"${CTL_SCRIPT}" status >"${TEST_DIR}/status-empty.log" 2>&1
for field in 'skills_linked=0/5' 'hooks_linked=no' 'hooks_mode=absent' 'dangling_links=0' 'runtime_worktree_sh=missing' 'runtime_ctl_sh=missing' 'runtime_guard_py=missing'; do
	check "empty status reports ${field}" grep -qxF "${field}" "${TEST_DIR}/status-empty.log"
done

# Identical-bytes unmanaged hooks.json must still be backed up and restored on disable.
export HOME="${TEST_DIR}/identical-hooks-home"
mkdir -p "${HOME}/.gemini/config"
cp "${REPO_ROOT}/configs/antigravity/hooks.json" "${HOME}/.gemini/config/hooks.json"
"${CTL_SCRIPT}" install >/dev/null 2>&1
check "install backs up unmanaged hooks.json even when contents match" compgen -G "${HOME}/.gemini/config/hooks.json.backup.*"
"${CTL_SCRIPT}" disable >/dev/null 2>&1
check "disable restores non-proactive entries and strips dangling guard from matching backup" python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if "sonar-secrets" in d and "proactive-safety-guard" not in d else 1)' "${HOME}/.gemini/config/hooks.json"

# Restored hooks.json containing proactive-safety-guard is stripped safely while preserving custom hooks;
# custom references elsewhere under ~/.gemini/config/proactive/ keep runtime_dir intact.
export HOME="${TEST_DIR}/sanitize-hooks-home"
mkdir -p "${HOME}/.gemini/config"
"${CTL_SCRIPT}" install >/dev/null 2>&1
python3 - "${HOME}/.gemini/config/hooks.json" <<'PYTEST'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
doc = json.loads(p.read_text())
doc["custom-hook"] = {"enabled": True, "PreToolUse": []}
p.write_text(json.dumps(doc, indent=2) + "\n")
PYTEST
"${CTL_SCRIPT}" install >/dev/null 2>&1
"${CTL_SCRIPT}" disable >"${TEST_DIR}/disable-sanitized.log" 2>&1
check "restored custom hook remains active after disable" python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if "custom-hook" in d and "proactive-safety-guard" not in d else 1)' "${HOME}/.gemini/config/hooks.json"
check "runtime dir removed when restored hooks no longer reference it" test ! -d "${HOME}/.gemini/config/proactive"

"${CTL_SCRIPT}" install >/dev/null 2>&1
python3 - "${HOME}/.gemini/config/hooks.json" <<'PYTEST'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(json.dumps({"custom-uses-runtime": {"cmd": "$HOME/.gemini/config/proactive/hooks/proactive-guard.py"}}) + "\n")
PYTEST
"${CTL_SCRIPT}" install >/dev/null 2>&1
"${CTL_SCRIPT}" disable >"${TEST_DIR}/disable-preserved.log" 2>&1
check "runtime dir preserved when restored backup references it outside managed guard" test -d "${HOME}/.gemini/config/proactive"
check "preserved hooks warning mentions manual cleanup" grep -q "manual cleanup" "${TEST_DIR}/disable-preserved.log"

rm -f "${HOME}/.gemini/config/hooks.json.backup."*
printf '{invalid json ".gemini/config/proactive"\n' >"${HOME}/.gemini/config/hooks.json"
"${CTL_SCRIPT}" install >/dev/null 2>&1
"${CTL_SCRIPT}" disable >"${TEST_DIR}/disable-invalid-json.log" 2>&1
check "runtime dir preserved when restored hooks backup is invalid JSON" test -d "${HOME}/.gemini/config/proactive"
check "invalid JSON hooks log mentions parse failure" grep -q "could not be parsed as JSON" "${TEST_DIR}/disable-invalid-json.log"
check "invalid JSON hooks content left untouched" grep -q '{invalid json' "${HOME}/.gemini/config/hooks.json"

# Deployed CLI lifecycle (install --pilot, status, disable), --source-repo, and invalid-type/preflight guards.
export HOME="${TEST_DIR}/deployed-cli-home"
mkdir -p "${HOME}/.gemini/config"
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1
DEPLOYED_CTL="${HOME}/.gemini/config/proactive/scripts/antigravity-proactive-ctl.sh"
check_exit "deployed CLI reinstalls cleanly using recorded .source-repo" 0 \
	"${DEPLOYED_CTL}" install --pilot
rm -f "${HOME}/.gemini/config/proactive/.source-repo"
check_exit "deployed CLI fails clearly without .source-repo or --source-repo" 1 \
	"${DEPLOYED_CTL}" install --pilot
check_grep "deployed CLI error guides operator to checkout or --source-repo" '[-]-source-repo' "${TEST_DIR}/check.log"
check_exit "deployed CLI reinstalls cleanly with explicit --source-repo" 0 \
	"${DEPLOYED_CTL}" install --pilot --source-repo "${REPO_ROOT}"

# Missing source asset fails in preflight without mutating the healthy live installation.
INCOMPLETE_SRC="${TEST_DIR}/incomplete-src"
mkdir -p "${INCOMPLETE_SRC}/scripts" "${INCOMPLETE_SRC}/configs/antigravity/hooks" "${INCOMPLETE_SRC}/configs/antigravity/skills"
cp "${REPO_ROOT}/scripts/proactive-worktree.sh" "${INCOMPLETE_SRC}/scripts/"
cp "${REPO_ROOT}/scripts/antigravity-proactive-ctl.sh" "${INCOMPLETE_SRC}/scripts/"
check_exit "install aborts in preflight when source asset is missing" 1 \
	"${DEPLOYED_CTL}" install --source-repo "${INCOMPLETE_SRC}"
check "live hooks.json preserved untouched after preflight failure" cmp "${HOME}/.gemini/config/hooks.json" "${REPO_ROOT}/configs/antigravity/hooks.json"
check "live runtime guard preserved after preflight failure" test -f "${HOME}/.gemini/config/proactive/hooks/proactive-guard.py"

# Type checks in status: directory & broken symlink at runtime paths.
rm -rf "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh" "${HOME}/.gemini/config/proactive/hooks/proactive-guard.py"
mkdir -p "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh" "${HOME}/.gemini/config/proactive/hooks/proactive-guard.py"
rm -f "${DEPLOYED_CTL}"
ln -s "${TEST_DIR}/missing-deployed-ctl" "${DEPLOYED_CTL}"
"${CTL_SCRIPT}" status >"${TEST_DIR}/status-badtypes.log" 2>&1
check_grep "status rejects directory at script path as invalid-type" "^runtime_worktree_sh=invalid-type$" "${TEST_DIR}/status-badtypes.log"
check_grep "status rejects directory at guard path as invalid-type" "^runtime_guard_py=invalid-type$" "${TEST_DIR}/status-badtypes.log"
check_grep "status catches dangling symlink at runtime ctl path" "^runtime_ctl_sh=broken-symlink$" "${TEST_DIR}/status-badtypes.log"
check_grep "status increments dangling_links for broken runtime symlink" "^dangling_links=1$" "${TEST_DIR}/status-badtypes.log"

rm -rf "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh" "${HOME}/.gemini/config/proactive/hooks/proactive-guard.py" "${DEPLOYED_CTL}"
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1
check_exit "deployed CLI runs status cleanly" 0 "${DEPLOYED_CTL}" status
check_exit "deployed CLI runs base-check via sibling runtime proactive-worktree.sh" 0 \
	env PATH="${MOCK_BIN_PY}:${PATH}" "${DEPLOYED_CTL}" base-check --repo bc-repo --worktree "${WT_DEFAULT}"
check_exit "deployed CLI runs disable cleanly" 0 "${DEPLOYED_CTL}" disable
check "deployed CLI disable removed managed runtime" test ! -d "${HOME}/.gemini/config/proactive"

# deploy_skill_dir rollback restores both managed and unmanaged skills when staging mv fails.
MOCK_MV_BIN="${TEST_DIR}/mock_mv_bin"
MOCK_MV_LOG="${TEST_DIR}/mv-rejected.log"
mkdir -p "${MOCK_MV_BIN}"
REAL_MV="$(command -v mv)"
cat >"${MOCK_MV_BIN}/mv" <<EOF
#!/usr/bin/env bash
for arg in "\$@"; do
	case "\${arg}" in
	*/proactive-bolt.tmp.*)
		printf '%s\n' "\$*" >"${MOCK_MV_LOG}"
		exit 1
		;;
	esac
done
exec "${REAL_MV}" "\$@"
EOF
chmod +x "${MOCK_MV_BIN}/mv"
for kind in managed unmanaged; do
	export HOME="${TEST_DIR}/rollback-${kind}-home"
	mkdir -p "${HOME}/.gemini/config"
	"${CTL_SCRIPT}" install >/dev/null 2>&1
	BOLT_DIR="${HOME}/.gemini/config/skills/proactive-bolt"
	if [[ ${kind} == "unmanaged" ]]; then
		rm -rf "${BOLT_DIR}"
		mkdir -p "${BOLT_DIR}"
	fi
	echo "preserve-${kind}" >"${BOLT_DIR}/sentinel-${kind}.txt"
	rm -f "${MOCK_MV_LOG}"
	check_exit "install fails when ${kind} skill staging mv fails" 1 \
		env PATH="${MOCK_MV_BIN}:${PATH}" "${CTL_SCRIPT}" install
	check "${kind} rollback triggered mocked mv rejection" test -s "${MOCK_MV_LOG}"
	check_grep "${kind} rollback ran staging mv error handler" 'ERROR: failed to move staged directory .*proactive-bolt\.tmp\.' "${TEST_DIR}/check.log"
	check "${kind} skill restored after failed mv" test -f "${BOLT_DIR}/sentinel-${kind}.txt"
	check "no lingering ${kind} tmp or backup skill dir after failed mv" \
		python3 -c 'import glob, sys; sys.exit(1 if glob.glob(sys.argv[1] + ".*") else 0)' "${BOLT_DIR}"
done

# 8. base-check resolves repo_path/.venv/bin (and candidate .venv/bin), strips VIRTUAL_ENV,
#    and skips .venv prepending when the stage runs through `uv run`.
export HOME="${TEST_DIR}/venv-bc-home"
mkdir -p "${HOME}/.gemini/config"
VENV_REMOTE="${TEST_DIR}/venv-remote.git"
VENV_SEED="${TEST_DIR}/venv-seed"
VENV_CLONE="${TEST_DIR}/venv-repo"
VENV_WT_ROOT="${TEST_DIR}/venv-worktrees"
VENV_OUTER_BIN="${TEST_DIR}/venv-outer-bin"
mkdir -p "${VENV_WT_ROOT}" "${VENV_OUTER_BIN}"

git init --bare -q "${VENV_REMOTE}"
git init -q "${VENV_SEED}"
git -C "${VENV_SEED}" config user.email "test@example.com"
git -C "${VENV_SEED}" config user.name "Test User"
git -C "${VENV_SEED}" checkout -q -b main
printf 'ok\n' >"${VENV_SEED}/app.txt"
git -C "${VENV_SEED}" add .
git -C "${VENV_SEED}" commit -q -m "base"
git -C "${VENV_SEED}" remote add origin "${VENV_REMOTE}"
git -C "${VENV_SEED}" push -q -u origin main
git --git-dir="${VENV_REMOTE}" symbolic-ref HEAD refs/heads/main
git clone -q "${VENV_REMOTE}" "${VENV_CLONE}"
git -C "${VENV_CLONE}" remote set-head origin -a >/dev/null 2>&1

cat >"${VENV_OUTER_BIN}/fake-runner" <<'MOCK'
#!/usr/bin/env bash
echo "OUTER_RUNNER_SHOULD_NOT_WIN" >&2
exit 1
MOCK
chmod +x "${VENV_OUTER_BIN}/fake-runner"

mkdir -p "${VENV_CLONE}/.venv/bin"
cat >"${VENV_CLONE}/.venv/bin/fake-runner" <<'MOCK'
#!/usr/bin/env bash
printf 'RUNNER=repo-venv VIRTUAL_ENV=%s\n' "${VIRTUAL_ENV:-UNSET}"
[[ -z ${VIRTUAL_ENV:-} ]]
MOCK
chmod +x "${VENV_CLONE}/.venv/bin/fake-runner"

WT_VENV_REPO="$("${WT_SCRIPT}" prepare --repo-path "${VENV_CLONE}" --lens code-health --worktree-root "${VENV_WT_ROOT}")"
check_exit "base-check resolves repo_path/.venv/bin and unsets VIRTUAL_ENV" 0 \
	env VIRTUAL_ENV="/tmp/stale-venv" PATH="${VENV_OUTER_BIN}:${PATH}" \
	"${CTL_SCRIPT}" base-check --repo venv-repo --worktree "${WT_VENV_REPO}" --test-cmd "fake-runner"
check_grep "base-check with repo .venv reports NO_FAILURE" "^VERDICT: NO_FAILURE$" "${TEST_DIR}/check.log"

WT_VENV_CAND="$("${WT_SCRIPT}" prepare --repo-path "${VENV_CLONE}" --lens code-health --worktree-root "${VENV_WT_ROOT}")"
mkdir -p "${WT_VENV_CAND}/.venv/bin"
cat >"${WT_VENV_CAND}/.venv/bin/fake-runner" <<'MOCK'
#!/usr/bin/env bash
echo "CANDIDATE_VENV_FAIL" >&2
exit 1
MOCK
chmod +x "${WT_VENV_CAND}/.venv/bin/fake-runner"
check_exit "base-check uses candidate .venv/bin first and falls back to repo_path/.venv/bin on base" 2 \
	env VIRTUAL_ENV="/tmp/stale-venv" PATH="${VENV_OUTER_BIN}:${PATH}" \
	"${CTL_SCRIPT}" base-check --repo venv-repo --worktree "${WT_VENV_CAND}" --test-cmd "fake-runner"
check_grep "base-check classifies candidate-venv failure as CAUSED_BY_CHANGE" "^VERDICT: CAUSED_BY_CHANGE$" "${TEST_DIR}/check.log"

cat >"${VENV_OUTER_BIN}/uv" <<'MOCK'
#!/usr/bin/env bash
[[ -z ${VIRTUAL_ENV:-} ]]
[[ ${PATH%%:*} != */.venv/bin ]]
MOCK
chmod +x "${VENV_OUTER_BIN}/uv"
cat >"${VENV_CLONE}/.venv/bin/uv" <<'MOCK'
#!/usr/bin/env bash
echo "VENV_UV_SHOULD_NOT_BE_PREPENDED" >&2
exit 1
MOCK
chmod +x "${VENV_CLONE}/.venv/bin/uv"
check_exit "base-check skips .venv prepending for uv run stages while still unsetting VIRTUAL_ENV" 0 \
	env VIRTUAL_ENV="/tmp/stale-venv" PATH="${VENV_OUTER_BIN}:${PATH}" \
	"${CTL_SCRIPT}" base-check --repo venv-repo --worktree "${WT_VENV_REPO}" --test-cmd "uv run pytest -q"
check_grep "base-check uv run stage reports NO_FAILURE" "^VERDICT: NO_FAILURE$" "${TEST_DIR}/check.log"

# 9. doctor and doctor --fix (mocking proactive-worktree.sh via isolated MOCK_SRC)
export HOME="${TEST_DIR}/doctor-home"
mkdir -p "${HOME}/.gemini/config" "${HOME}/dev"

MOCK_SRC="${TEST_DIR}/doctor-mock-src"
mkdir -p "${MOCK_SRC}/scripts" "${MOCK_SRC}/configs/antigravity/hooks" "${MOCK_SRC}/configs/antigravity/sidecars"
cp "${REPO_ROOT}/scripts/antigravity-proactive-ctl.sh" "${MOCK_SRC}/scripts/"
cp "${REPO_ROOT}/configs/antigravity/hooks/proactive-guard.py" "${MOCK_SRC}/configs/antigravity/hooks/"
cp "${REPO_ROOT}/configs/antigravity/hooks.json" "${MOCK_SRC}/configs/antigravity/"
cp -R "${REPO_ROOT}/configs/antigravity/skills" "${MOCK_SRC}/configs/antigravity/"
cp "${REPO_ROOT}/configs/antigravity/sidecars/"*.sidecar.json "${MOCK_SRC}/configs/antigravity/sidecars/"

PF_CALLS_LOG="${TEST_DIR}/doctor-pf-calls.log"
PF_MODE_FILE="${TEST_DIR}/doctor-pf-mode"
cat >"${MOCK_SRC}/scripts/proactive-worktree.sh" <<MOCK
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"${PF_CALLS_LOG}"
repo=""
prev_arg=""
for arg in "\$@"; do
	if [[ \${prev_arg} == "--repo" ]]; then
		repo="\${arg##*/}"
		break
	fi
	prev_arg="\${arg}"
done
mode="\$(cat "${PF_MODE_FILE}" 2>/dev/null || echo "pass")"
case "\${mode}" in
pass)
	echo "repo=abhimehro/\${repo}"
	echo "preflight=PASS"
	exit 0
	;;
auth)
	echo "gh_auth=failed"
	echo "preflight=FAIL"
	exit 6
	;;
toolchain)
	echo "toolchain=missing"
	echo "remediation=uv sync --frozen --all-extras"
	echo "preflight=FAIL"
	exit 7
	;;
error)
	echo "preflight=FAIL"
	exit 2
	;;
esac
MOCK
chmod +x "${MOCK_SRC}/scripts/proactive-worktree.sh"

git init -q "${HOME}/dev/ctrld-sync"

printf 'pass\n' >"${PF_MODE_FILE}"
: >"${PF_CALLS_LOG}"
check_exit "doctor exits 1 when runtime is not installed" 1 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --repo ctrld-sync
check_grep "doctor reports degraded runtime_health" "^runtime_health=degraded$" "${TEST_DIR}/check.log"
check_grep "doctor still checks target repo and reports PASS" "^repo_ctrld-sync=PASS$" "${TEST_DIR}/check.log"
check_grep "doctor reports DEGRADED overall status" "^doctor_status=DEGRADED$" "${TEST_DIR}/check.log"

: >"${PF_CALLS_LOG}"
check_exit "doctor --fix self-heals missing runtime and passes" 0 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --fix --source-repo "${MOCK_SRC}" --repo ctrld-sync
check_grep "doctor --fix emits auto_healed_install=yes" "^auto_healed_install=yes$" "${TEST_DIR}/check.log"
check_grep "doctor --fix reports runtime_health=ok" "^runtime_health=ok$" "${TEST_DIR}/check.log"
check_grep "doctor --fix reports repo PASS" "^repo_ctrld-sync=PASS$" "${TEST_DIR}/check.log"
check_grep "doctor --fix reports doctor_status=HEALTHY" "^doctor_status=HEALTHY$" "${TEST_DIR}/check.log"
check_grep "doctor --fix forwards --auto-heal to preflight" "^preflight --repo abhimehro/ctrld-sync --repo-path ${HOME}/dev/ctrld-sync --auto-heal$" "${PF_CALLS_LOG}"

# Reintroduce runtime defects and verify deployed CLI self-heals using recorded .source-repo
chmod 644 "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh"
rm -rf "${HOME}/.gemini/config/skills/proactive-palette"
ln -s "${TEST_DIR}/missing-skill-target" "${HOME}/.gemini/config/skills/proactive-palette"
check_exit "deployed doctor --fix repairs runtime defects using recorded .source-repo" 0 \
	"${HOME}/.gemini/config/proactive/scripts/antigravity-proactive-ctl.sh" doctor --fix --repo ctrld-sync
check_grep "deployed doctor --fix emits auto_healed_install=yes" "^auto_healed_install=yes$" "${TEST_DIR}/check.log"
check_grep "deployed doctor --fix restores runtime_health=ok" "^runtime_health=ok$" "${TEST_DIR}/check.log"

: >"${PF_CALLS_LOG}"
check_exit "doctor defaults to ctrld-sync and forwards --skip-fetch" 0 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --skip-fetch
check_grep "doctor --skip-fetch forwards flag without --auto-heal" "^preflight --repo abhimehro/ctrld-sync --repo-path ${HOME}/dev/ctrld-sync --skip-fetch$" "${PF_CALLS_LOG}"
check_grep "doctor reports HEALTHY" "^doctor_status=HEALTHY$" "${TEST_DIR}/check.log"

check_exit "doctor emits MISSING_REPO when repo directory is absent" 1 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --repo personal-config
check_grep "doctor prints MISSING_REPO" "^repo_personal-config=MISSING_REPO$" "${TEST_DIR}/check.log"
check_grep "doctor prints DEGRADED on missing repo" "^doctor_status=DEGRADED$" "${TEST_DIR}/check.log"

printf 'auth\n' >"${PF_MODE_FILE}"
check_exit "doctor maps preflight exit 6 to FAIL_AUTH" 1 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --repo ctrld-sync
check_grep "doctor prints FAIL_AUTH" "^repo_ctrld-sync=FAIL_AUTH$" "${TEST_DIR}/check.log"

printf 'toolchain\n' >"${PF_MODE_FILE}"
check_exit "doctor maps preflight exit 7 to FAIL_TOOLCHAIN and surfaces remediation" 1 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --repo ctrld-sync
check_grep "doctor prints FAIL_TOOLCHAIN" "^repo_ctrld-sync=FAIL_TOOLCHAIN$" "${TEST_DIR}/check.log"
check_grep "doctor surfaces remediation hint" "^repo_ctrld-sync_remediation=uv sync --frozen --all-extras$" "${TEST_DIR}/check.log"

printf 'error\n' >"${PF_MODE_FILE}"
check_exit "doctor maps unexpected preflight failure to FAIL_ERROR" 1 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --repo ctrld-sync
check_grep "doctor prints FAIL_ERROR" "^repo_ctrld-sync=FAIL_ERROR$" "${TEST_DIR}/check.log"

printf 'pass\n' >"${PF_MODE_FILE}"
for all_r in ctrld-sync email-security-pipeline personal-config Hydrograph_Versus_Seatek_Sensors_Project Seatek_Analysis series_correction_project_updated repoprompt-ce; do
	git init -q "${HOME}/dev/${all_r}"
done
: >"${PF_CALLS_LOG}"
check_exit "doctor --all-repos checks all 7 repos and exits 0 when healthy" 0 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --all-repos
for all_r in ctrld-sync email-security-pipeline personal-config Hydrograph_Versus_Seatek_Sensors_Project Seatek_Analysis series_correction_project_updated repoprompt-ce; do
	check_grep "doctor --all-repos reports PASS for ${all_r}" "^repo_${all_r}=PASS$" "${TEST_DIR}/check.log"
done

# 10. stage-repo stages core and research sidecars cleanly and disable removes only managed ones
export HOME="${TEST_DIR}/stage-repo-home"
mkdir -p "${HOME}/.gemini/config"
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1

check_exit "stage-repo stages core repo sidecars" 0 \
	"${CTL_SCRIPT}" stage-repo --repo abhimehro/email-security-pipeline
CORE_SWEEP="${HOME}/.gemini/config/sidecars/proactive-sweep-email-security-pipeline/sidecar.json"
CORE_TRIAGE="${HOME}/.gemini/config/sidecars/proactive-triage-email-security-pipeline/sidecar.json"
check "core sweep sidecar created" test -f "${CORE_SWEEP}"
check "core triage sidecar created" test -f "${CORE_TRIAGE}"
check "core sweep user_config.json NOT created" test ! -f "${HOME}/.gemini/config/sidecars/proactive-sweep-email-security-pipeline/user_config.json"
check "core triage user_config.json NOT created" test ! -f "${HOME}/.gemini/config/sidecars/proactive-triage-email-security-pipeline/user_config.json"
check "core sweep sidecar mode 0600" python3 -c 'import os,sys; sys.exit(0 if (os.stat(sys.argv[1]).st_mode & 0o777)==0o600 else 1)' "${CORE_SWEEP}"
check "core triage sidecar mode 0600" python3 -c 'import os,sys; sys.exit(0 if (os.stat(sys.argv[1]).st_mode & 0o777)==0o600 else 1)' "${CORE_TRIAGE}"
check "core sweep sidecar is valid JSON with expanded HOME and core lenses" python3 - "${CORE_SWEEP}" "${HOME}" <<'PYTEST'
import json, pathlib, sys
raw = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
home = sys.argv[2]
assert "__HOME__" not in raw
doc = json.loads(raw)
assert doc["args"][0] == "CRON_TZ=America/Chicago 15 8 * * 1-5"
prompt = doc["args"][-1]
assert f"{home}/.gemini/config/proactive/scripts/proactive-worktree.sh preflight --repo abhimehro/email-security-pipeline --repo-path {home}/dev/email-security-pipeline --auto-heal" in prompt
assert "bolt, code-health, and palette" in prompt
grants = doc["agent_permissions"]["access_grants"]
assert doc["agent_permissions"]["allows_user_interactions"] is False
assert "command(gh auth status)" in grants
assert f"command({home}/.gemini/config/proactive/scripts/proactive-worktree.sh)" in grants
PYTEST
check "core triage sidecar is valid JSON with doctor grant" python3 - "${CORE_TRIAGE}" "${HOME}" <<'PYTEST'
import json, pathlib, sys
raw = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
home = sys.argv[2]
assert "__HOME__" not in raw
doc = json.loads(raw)
assert doc["args"][0] == "CRON_TZ=America/Chicago 35 8 * * 1-5"
grants = doc["agent_permissions"]["access_grants"]
assert doc["agent_permissions"]["allows_user_interactions"] is True
assert f"command({home}/.gemini/config/proactive/scripts/antigravity-proactive-ctl.sh doctor)" in grants
PYTEST

check_exit "stage-repo stages research repo sidecars with custom crons" 0 \
	"${CTL_SCRIPT}" stage-repo --repo Seatek_Analysis --cron "CRON_TZ=UTC 0 9 * * 1-5" --triage-cron "CRON_TZ=UTC 25 9 * * 1-5" --repo-path "__HOME__/research/Seatek_Analysis"
RES_SWEEP="${HOME}/.gemini/config/sidecars/proactive-sweep-Seatek_Analysis/sidecar.json"
RES_TRIAGE="${HOME}/.gemini/config/sidecars/proactive-triage-Seatek_Analysis/sidecar.json"
check "research sweep sidecar enforces no palette and mandatory numeric check" python3 - "${RES_SWEEP}" "${RES_TRIAGE}" "${HOME}" <<'PYTEST'
import json, pathlib, sys
s_raw = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
t_raw = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
home = sys.argv[3]
assert "__HOME__" not in s_raw and "__HOME__" not in t_raw
s_doc = json.loads(s_raw)
t_doc = json.loads(t_raw)
assert s_doc["args"][0] == "CRON_TZ=UTC 0 9 * * 1-5"
assert t_doc["args"][0] == "CRON_TZ=UTC 25 9 * * 1-5"
prompt = s_doc["args"][-1]
assert f"{home}/research/Seatek_Analysis" in prompt
assert "--numeric-check-cmd" in prompt
assert "NEVER run palette" in prompt
assert "code-health and bolt" in prompt
assert f"read_file({home}/research/Seatek_Analysis)" in s_doc["agent_permissions"]["access_grants"]
PYTEST

check_exit "stage-repo rejects missing --repo" 1 "${CTL_SCRIPT}" stage-repo
check_exit "stage-repo rejects dot-dot --repo" 1 "${CTL_SCRIPT}" stage-repo --repo "abhimehro/.."

UNRELATED_DIR="${HOME}/.gemini/config/sidecars/proactive-sweep-user-custom"
mkdir -p "${UNRELATED_DIR}"
printf '{"builtin": "schedule", "args": ["0 10 * * *", "echo", "custom"]}\n' >"${UNRELATED_DIR}/sidecar.json"
printf '{"enabled": true}\n' >"${UNRELATED_DIR}/user_config.json"

"${CTL_SCRIPT}" disable >/dev/null 2>&1
check "disable removes managed staged core sweep sidecar" test ! -e "${CORE_SWEEP}"
check "disable removes managed staged core triage sidecar" test ! -e "${CORE_TRIAGE}"
check "disable removes managed staged research sweep sidecar" test ! -e "${RES_SWEEP}"
check "disable removes managed staged research triage sidecar" test ! -e "${RES_TRIAGE}"
check "disable preserves unrelated proactive-sweep-* sidecar.json" test -f "${UNRELATED_DIR}/sidecar.json"
check "disable preserves unrelated proactive-sweep-* user_config.json" test -f "${UNRELATED_DIR}/user_config.json"

# 11. configs/antigravity/hooks.json prefers deployed guard, falls back to repo checkout, and fails closed (exit 2)
HOOK_HOME="${TEST_DIR}/hook-fallback-home"
mkdir -p "${HOOK_HOME}/.gemini/config/proactive/hooks" "${HOOK_HOME}/dev/personal-config/configs/antigravity/hooks"
HOOK_CMD="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["proactive-safety-guard"]["PreToolUse"][0]["hooks"][0]["command"])' "${REPO_ROOT}/configs/antigravity/hooks.json")"
check "hooks.json command retains .gemini/config/proactive/ marker" grep -qF ".gemini/config/proactive/" "${REPO_ROOT}/configs/antigravity/hooks.json"

cat >"${HOOK_HOME}/.gemini/config/proactive/hooks/proactive-guard.py" <<'PY'
print('{"decision":"allow","reason":"from-deployed"}')
PY
cat >"${HOOK_HOME}/dev/personal-config/configs/antigravity/hooks/proactive-guard.py" <<'PY'
print('{"decision":"allow","reason":"from-repo-fallback"}')
PY

check_exit "hooks.json command succeeds when deployed guard exists" 0 \
	env HOME="${HOOK_HOME}" sh -c "${HOOK_CMD}" </dev/null
check_grep "hooks.json prefers deployed guard over repo checkout" "from-deployed" "${TEST_DIR}/check.log"

rm -f "${HOOK_HOME}/.gemini/config/proactive/hooks/proactive-guard.py"
check_exit "hooks.json command succeeds via repo fallback when deployed guard is missing" 0 \
	env HOME="${HOOK_HOME}" sh -c "${HOOK_CMD}" </dev/null
check_grep "hooks.json falls back to repo checkout guard" "from-repo-fallback" "${TEST_DIR}/check.log"

rm -f "${HOOK_HOME}/dev/personal-config/configs/antigravity/hooks/proactive-guard.py"
check_exit "hooks.json fails closed with exit 2 when both deployed and repo guards are missing" 2 \
	env HOME="${HOOK_HOME}" sh -c "${HOOK_CMD}" </dev/null
check_grep "hooks.json prints clear missing-guard error" "proactive-guard\.py missing" "${TEST_DIR}/check.log"

echo ""
echo "Summary: PASS=${PASS} FAIL=${FAIL}"
[[ ${FAIL} -eq 0 ]]
