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
[[ -z ${VIRTUAL_ENV:-} ]] && [[ ${PATH%%:*} != */.venv/bin ]]
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

# 12. doctor --fix recovers when a directory occupies a runtime file path (D4)
export HOME="${TEST_DIR}/doctor-dir-home"
mkdir -p "${HOME}/.gemini/config" "${HOME}/dev"
git init -q "${HOME}/dev/ctrld-sync"
"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" install --pilot --source-repo "${MOCK_SRC}" >/dev/null 2>&1
rm -f "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh"
mkdir -p "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh/nested"
check_exit "doctor detects invalid-type when directory occupies proactive-worktree.sh" 1 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --repo ctrld-sync
check_grep "doctor reports invalid-type for directory at file path" "^runtime_worktree_sh=invalid-type$" "${TEST_DIR}/check.log"
check_grep "doctor reports degraded on invalid-type" "^runtime_health=degraded$" "${TEST_DIR}/check.log"

check_exit "doctor --fix displaces occupying directory and restores executable file" 0 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --fix --source-repo "${MOCK_SRC}" --repo ctrld-sync
check_grep "doctor --fix reports auto_healed_install=yes only after runtime is healthy" "^auto_healed_install=yes$" "${TEST_DIR}/check.log"
check_grep "doctor --fix reports runtime_health=ok after dir repair" "^runtime_health=ok$" "${TEST_DIR}/check.log"
check_grep "doctor --fix reports runtime_worktree_sh=ok" "^runtime_worktree_sh=ok$" "${TEST_DIR}/check.log"
check "repaired proactive-worktree.sh is a regular executable file" \
	test -f "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh" -a -x "${HOME}/.gemini/config/proactive/scripts/proactive-worktree.sh"
check "unexpected directory was preserved as .invalid-dir backup" \
	python3 - "${HOME}/.gemini/config/proactive/scripts" <<'PY'
import pathlib, sys
matches = list(pathlib.Path(sys.argv[1]).glob("proactive-worktree.sh.invalid-dir.*"))
assert len(matches) == 1 and matches[0].is_dir(), matches
PY

# 13. sweep-date + overnight UTC-midnight stage-repo alignment (D3) & renamed base-check (D2)
SWEEP_DATE_UTC="$("${CTL_SCRIPT}" sweep-date --cron "50 23 * * 1-5" --now "2026-11-24T00:10:00Z")"
check "sweep-date maps post-midnight UTC triage to previous UTC sweep date" test "${SWEEP_DATE_UTC}" = "2026-11-23"
SWEEP_DATE_CDT="$("${CTL_SCRIPT}" sweep-date --cron "CRON_TZ=America/Chicago 50 18 * * 1-5" --now "2026-07-15T00:10:00Z")"
check "sweep-date handles CRON_TZ=America/Chicago across UTC midnight (CDT)" test "${SWEEP_DATE_CDT}" = "2026-07-14"
SWEEP_DATE_DAY="$("${CTL_SCRIPT}" sweep-date --cron "CRON_TZ=America/Chicago 15 8 * * 1-5" --now "2026-11-23T14:35:00Z")"
check "sweep-date keeps same UTC date for morning CST sweep" test "${SWEEP_DATE_DAY}" = "2026-11-23"

export HOME="${TEST_DIR}/stage-overnight-home"
mkdir -p "${HOME}/.gemini/config"
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1
check_exit "stage-repo supports overnight crons spanning UTC midnight" 0 \
	"${CTL_SCRIPT}" stage-repo --repo Seatek_Analysis --repo-path "__HOME__/research/seatek-local" \
	--cron "50 23 * * 1-5" --triage-cron "10 0 * * 2-6"
check "overnight stage-repo binds --repo in prepare and sweep-date in both sidecars" python3 - "${HOME}" <<'PY'
import json, pathlib, sys
home = pathlib.Path(sys.argv[1])
s_doc = json.loads((home / ".gemini/config/sidecars/proactive-sweep-Seatek_Analysis/sidecar.json").read_text(encoding="utf-8"))
t_doc = json.loads((home / ".gemini/config/sidecars/proactive-triage-Seatek_Analysis/sidecar.json").read_text(encoding="utf-8"))
assert "prepare --repo abhimehro/Seatek_Analysis" in s_doc["args"][-1]
assert "sweep-date --cron '50 23 * * 1-5'" in s_doc["args"][-1]
assert "sweep-date --cron '50 23 * * 1-5'" in t_doc["args"][-1]
assert '--date "$SWEEP_DATE"' in t_doc["args"][-1]
ctl_cmd = f"command({home}/.gemini/config/proactive/scripts/antigravity-proactive-ctl.sh sweep-date)"
assert ctl_cmd in s_doc["agent_permissions"]["access_grants"]
assert ctl_cmd in t_doc["agent_permissions"]["access_grants"]
PY

RENAMED_BASE="${TEST_DIR}/renamed-seatek-remote.git"
RENAMED_SEED="${TEST_DIR}/renamed-seatek-seed"
RENAMED_CLONE="${TEST_DIR}/custom-seatek/seatek-local"
RENAMED_WT_ROOT="${TEST_DIR}/renamed-wt"
mkdir -p "${RENAMED_SEED}" "${TEST_DIR}/custom-seatek" "${RENAMED_WT_ROOT}"
git init -q --bare "${RENAMED_BASE}"
git init -q "${RENAMED_SEED}"
git -C "${RENAMED_SEED}" config user.email "test@example.com"
git -C "${RENAMED_SEED}" config user.name "Test"
printf 'ok\n' >"${RENAMED_SEED}/README.md"
git -C "${RENAMED_SEED}" add README.md
git -C "${RENAMED_SEED}" commit -q -m "init"
git -C "${RENAMED_SEED}" branch -M main
git -C "${RENAMED_SEED}" remote add origin "${RENAMED_BASE}"
git -C "${RENAMED_SEED}" push -q -u origin main
git --git-dir="${RENAMED_BASE}" symbolic-ref HEAD refs/heads/main
git clone -q "${RENAMED_BASE}" "${RENAMED_CLONE}"
git -C "${RENAMED_CLONE}" remote set-head origin -a >/dev/null 2>&1
WT_RENAMED="$("${WT_SCRIPT}" prepare --repo abhimehro/Seatek_Analysis --repo-path "${RENAMED_CLONE}" --lens code-health --worktree-root "${RENAMED_WT_ROOT}")"
check_exit "base-check accepts worktree prepared with explicit --repo from renamed checkout" 0 \
	"${CTL_SCRIPT}" base-check --repo Seatek_Analysis --worktree "${WT_RENAMED}" --test-cmd "true"
check_grep "base-check reports canonical Seatek_Analysis repo identity" "^REPO: abhimehro/Seatek_Analysis$" "${TEST_DIR}/check.log"

# 14. CodeRabbit hardening regressions ([4],[7],[8],[12],[14],[19],[22],[23],[24],[27],[28])

# [4] Weekday-only cron skips weekend across Monday pre-slot / UTC boundary
SWEEP_DATE_MON_UTC="$("${CTL_SCRIPT}" sweep-date --cron "50 23 * * 1-5" --now "2026-11-23T00:10:00Z")"
check "sweep-date skips Sunday to Friday for Monday 00:10Z (50 23 * * 1-5)" test "${SWEEP_DATE_MON_UTC}" = "2026-11-20"
SWEEP_DATE_MON_CST="$("${CTL_SCRIPT}" sweep-date --cron "CRON_TZ=America/Chicago 15 8 * * 1-5" --now "2026-11-23T06:00:00Z")"
check "sweep-date skips weekend to Friday for Monday 00:00 CST (15 8 * * 1-5)" test "${SWEEP_DATE_MON_CST}" = "2026-11-20"

# [12] & [7] Missing pilot sidecar template fails install --pilot and doctor --fix propagates failure
BAD_PILOT_SRC="${TEST_DIR}/bad-pilot-src"
cp -R "${MOCK_SRC}" "${BAD_PILOT_SRC}"
rm -f "${BAD_PILOT_SRC}/configs/antigravity/sidecars/proactive-pilot-triage.sidecar.json"
export HOME="${TEST_DIR}/bad-pilot-home"
mkdir -p "${HOME}/.gemini/config" "${HOME}/dev"
git init -q "${HOME}/dev/ctrld-sync"
check_exit "install --pilot fails exit 1 when pilot triage template is missing" 1 \
	"${BAD_PILOT_SRC}/scripts/antigravity-proactive-ctl.sh" install --pilot --source-repo "${BAD_PILOT_SRC}"
check_grep "install --pilot names missing pilot template" "Missing pilot sidecar template" "${TEST_DIR}/check.log"

check_exit "doctor --fix reports auto_healed_install=failed and exits 1 when install fails" 1 \
	"${BAD_PILOT_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --fix --source-repo "${BAD_PILOT_SRC}" --repo ctrld-sync
check_grep "doctor --fix emits auto_healed_install=failed" "^auto_healed_install=failed$" "${TEST_DIR}/check.log"
check_grep "doctor --fix emits DEGRADED on failed auto-heal" "^doctor_status=DEGRADED$" "${TEST_DIR}/check.log"

# [8] doctor distinguishes FAIL_FETCH from FAIL_AUTH when preflight exits 6 with git_fetch=failed
FETCH_MOCK_SRC="${TEST_DIR}/doctor-fetch-src"
cp -R "${MOCK_SRC}" "${FETCH_MOCK_SRC}"
cat >"${FETCH_MOCK_SRC}/scripts/proactive-worktree.sh" <<'MOCK'
#!/usr/bin/env bash
echo "git_fetch=failed"
echo "preflight=FAIL"
exit 6
MOCK
chmod +x "${FETCH_MOCK_SRC}/scripts/proactive-worktree.sh"
export HOME="${TEST_DIR}/doctor-fetch-home"
mkdir -p "${HOME}/.gemini/config" "${HOME}/dev"
git init -q "${HOME}/dev/ctrld-sync"
"${FETCH_MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" install --pilot --source-repo "${FETCH_MOCK_SRC}" >/dev/null 2>&1
check_exit "doctor maps preflight exit 6 git_fetch=failed to FAIL_FETCH" 1 \
	"${FETCH_MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --repo ctrld-sync
check_grep "doctor emits FAIL_FETCH for fetch failures" "^repo_ctrld-sync=FAIL_FETCH$" "${TEST_DIR}/check.log"

# [27] doctor rejects hooks.json missing enabled proactive-safety-guard or invalid JSON
export HOME="${TEST_DIR}/doctor-guard-home"
mkdir -p "${HOME}/.gemini/config" "${HOME}/dev"
git init -q "${HOME}/dev/ctrld-sync"
"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" install --pilot --source-repo "${MOCK_SRC}" >/dev/null 2>&1
printf '{"sonar-secrets":{"enabled":true}}\n' >"${HOME}/.gemini/config/hooks.json"
check_exit "doctor flags hooks_guard=missing when proactive-safety-guard absent" 1 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --repo ctrld-sync
check_grep "doctor reports hooks_guard=missing" "^hooks_guard=missing$" "${TEST_DIR}/check.log"
check_grep "doctor reports degraded on missing guard" "^runtime_health=degraded$" "${TEST_DIR}/check.log"

printf '{invalid-json\n' >"${HOME}/.gemini/config/hooks.json"
check_exit "doctor flags hooks_guard=invalid-json on malformed hooks.json" 1 \
	"${MOCK_SRC}/scripts/antigravity-proactive-ctl.sh" doctor --repo ctrld-sync
check_grep "doctor reports hooks_guard=invalid-json" "^hooks_guard=invalid-json$" "${TEST_DIR}/check.log"

# [14] disable detects JSON-escaped \/ runtime marker in restored custom hooks.json
export HOME="${TEST_DIR}/sanitize-escaped-home"
mkdir -p "${HOME}/.gemini/config"
"${CTL_SCRIPT}" install >/dev/null 2>&1
printf '%s\n' '{"custom-escaped":{"cmd":"/custom-home\/.gemini\/config\/proactive\/hooks\/proactive-guard.py"}}' >"${HOME}/.gemini/config/hooks.json"
"${CTL_SCRIPT}" install >/dev/null 2>&1
"${CTL_SCRIPT}" disable >"${TEST_DIR}/disable-escaped.log" 2>&1
check 'disable preserves runtime dir when restored hooks use JSON-escaped \/ marker' test -d "${HOME}/.gemini/config/proactive"
check "disable keeps custom-escaped hook intact" grep -q "custom-escaped" "${HOME}/.gemini/config/hooks.json"

# [19] install backs up custom non-legacy symlink at skill path instead of deleting it
export HOME="${TEST_DIR}/custom-skill-symlink-home"
CUSTOM_SYMLINK_TARGET="${TEST_DIR}/custom-bolt-symlink-target"
mkdir -p "${HOME}/.gemini/config/skills" "${CUSTOM_SYMLINK_TARGET}"
printf 'custom bolt\n' >"${CUSTOM_SYMLINK_TARGET}/SKILL.md"
ln -s "${CUSTOM_SYMLINK_TARGET}" "${HOME}/.gemini/config/skills/proactive-bolt"
"${CTL_SCRIPT}" install >/dev/null 2>&1
check "install backs up custom non-legacy skill symlink" bash -c "compgen -G '${HOME}/.gemini/config/skills/proactive-bolt.backup.*' >/dev/null"
check "install replaces custom skill symlink with real managed directory" bash -c "test -d '${HOME}/.gemini/config/skills/proactive-bolt' && test ! -L '${HOME}/.gemini/config/skills/proactive-bolt'"

# [22] audit-missed honors --cron and stage-repo forwards --cron to audit-missed in triage prompt
export HOME="${TEST_DIR}/audit-cron-home"
mkdir -p "${HOME}/.gemini/config"
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1
check_exit "audit-missed records custom --cron scheduled slot" 0 \
	"${CTL_SCRIPT}" audit-missed --date "2026-11-23" --repo "ctrld-sync" --cron "50 23 * * 1-5"
check_grep "audit-missed writes custom UTC slot to digest" "^- Scheduled Slot: 2026-11-23 23:50 UTC$" \
	"${HOME}/.gemini/antigravity/proactive-reports/2026-11-23-ctrld-sync.md"
check_exit "stage-repo succeeds for custom cron with audit-missed forwarding" 0 \
	"${CTL_SCRIPT}" stage-repo --repo "ctrld-sync" --cron "50 23 * * 1-5" --triage-cron "10 0 * * 2-6"
check "stage-repo passes --cron to audit-missed inside triage prompt" python3 - "${HOME}/.gemini/config/sidecars/proactive-triage-ctrld-sync/sidecar.json" <<'PYTEST'
import json, pathlib, sys
t_doc = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert "audit-missed --date \"$SWEEP_DATE\" --repo ctrld-sync --cron '50 23 * * 1-5'" in t_doc["args"][-1], t_doc["args"][-1]
PYTEST

# [28] stage-repo refuses to overwrite custom non-managed sidecars before writing either file
export HOME="${TEST_DIR}/stage-collision-home"
mkdir -p "${HOME}/.gemini/config/sidecars/proactive-triage-ctrld-sync"
printf '{"custom_triage":true}\n' >"${HOME}/.gemini/config/sidecars/proactive-triage-ctrld-sync/sidecar.json"
check_exit "stage-repo refuses overwrite when triage sidecar is unmanaged custom file" 1 \
	"${CTL_SCRIPT}" stage-repo --repo "ctrld-sync"
check "stage-repo leaves custom triage sidecar untouched on collision" grep -q "custom_triage" \
	"${HOME}/.gemini/config/sidecars/proactive-triage-ctrld-sync/sidecar.json"
check "stage-repo does not write sweep sidecar when triage sidecar collides" \
	test ! -e "${HOME}/.gemini/config/sidecars/proactive-sweep-ctrld-sync/sidecar.json"

# [24] hooks.json missing-guard branch emits machine-readable deny JSON on stdout + stderr + exit 2
rc_hook_json=0
env HOME="${HOOK_HOME}" sh -c "${HOOK_CMD}" </dev/null >"${TEST_DIR}/hook-missing.out" 2>"${TEST_DIR}/hook-missing.err" || rc_hook_json=$?
check "hooks.json missing-guard exits 2" test "${rc_hook_json}" -eq 2
check "hooks.json missing-guard emits valid deny JSON on stdout" python3 - "${TEST_DIR}/hook-missing.out" <<'PYTEST'
import json, pathlib, sys
doc = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert doc.get("decision") == "deny" and "missing" in doc.get("reason", ""), doc
PYTEST
check_grep "hooks.json missing-guard also logs error on stderr" "proactive-guard\.py missing" "${TEST_DIR}/hook-missing.err"

# [23] base-check prepends worktree PYTHONPATH when falling back to repo .venv/bin (editable install guard)
ED_BARE="${TEST_DIR}/ed-remote.git"
ED_SEED="${TEST_DIR}/ed-seed"
ED_CLONE="${TEST_DIR}/ed-repo"
ED_WT_ROOT="${TEST_DIR}/ed-wt"
mkdir -p "${ED_SEED}/edpkg" "${ED_WT_ROOT}"
git init -q --bare "${ED_BARE}"
git init -q "${ED_SEED}"
git -C "${ED_SEED}" config user.email "test@example.com"
git -C "${ED_SEED}" config user.name "Test"
printf 'OK = True\n' >"${ED_SEED}/edpkg/__init__.py"
git -C "${ED_SEED}" add edpkg/__init__.py
git -C "${ED_SEED}" commit -q -m "init editable pkg"
git -C "${ED_SEED}" branch -M main
git -C "${ED_SEED}" remote add origin "${ED_BARE}"
git -C "${ED_SEED}" push -q -u origin main
git clone -q "${ED_BARE}" "${ED_CLONE}"
mkdir -p "${ED_CLONE}/.venv/bin"
cat >"${ED_CLONE}/.venv/bin/edcheck" <<MOCK
#!${REAL_PYTHON3}
import os
import sys

# Simulate an editable .pth entry pointing at primary clone at the end of sys.path;
# PYTHONPATH set by run_segment_in must put the candidate/base worktree ahead of it.
sys.path.append("${ED_CLONE}")
pp = os.environ.get("PYTHONPATH", "")
assert pp, "expected PYTHONPATH to be set on repo .venv fallback"
assert os.path.realpath(pp.split(":")[0]) == os.path.realpath(os.getcwd()), (pp, os.getcwd())
import edpkg  # noqa: E402
assert edpkg.OK, f"imported broken edpkg from {edpkg.__file__}"
MOCK
chmod +x "${ED_CLONE}/.venv/bin/edcheck"
WT_ED="$("${WT_SCRIPT}" prepare --repo-path "${ED_CLONE}" --lens code-health --worktree-root "${ED_WT_ROOT}")"
printf 'OK = False\n' >"${WT_ED}/edpkg/__init__.py"
git -C "${WT_ED}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "break candidate edpkg"
check_exit "base-check uses candidate PYTHONPATH ahead of repo editable path on fallback" 2 \
	"${CTL_SCRIPT}" base-check --repo ed-repo --worktree "${WT_ED}" --test-cmd "edcheck"
check_grep "base-check classifies broken candidate with editable venv fallback as CAUSED_BY_CHANGE" "^VERDICT: CAUSED_BY_CHANGE$" "${TEST_DIR}/check.log"
ED_STATUS="$(GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git -C "${WT_ED}" status --porcelain --untracked-files=all)"
check "base-check leaves candidate worktree free of untracked bytecode" test -z "${ED_STATUS}"

# 15. CodeRabbit pass-2 regressions ([4], [8] src-layout, [20])

# [8] src/-layout candidate PYTHONPATH takes precedence over primary src/ editable path
SRCE_BARE="${TEST_DIR}/srce-remote.git"
SRCE_SEED="${TEST_DIR}/srce-seed"
SRCE_CLONE="${TEST_DIR}/srce-repo"
SRCE_WT_ROOT="${TEST_DIR}/srce-wt"
mkdir -p "${SRCE_SEED}/src/srcpkg" "${SRCE_WT_ROOT}"
git init -q --bare "${SRCE_BARE}"
git init -q "${SRCE_SEED}"
git -C "${SRCE_SEED}" config user.email "test@example.com"
git -C "${SRCE_SEED}" config user.name "Test"
printf 'OK = True\n' >"${SRCE_SEED}/src/srcpkg/__init__.py"
git -C "${SRCE_SEED}" add src/srcpkg/__init__.py
git -C "${SRCE_SEED}" commit -q -m "init src-layout pkg"
git -C "${SRCE_SEED}" branch -M main
git -C "${SRCE_SEED}" remote add origin "${SRCE_BARE}"
git -C "${SRCE_SEED}" push -q -u origin main
git clone -q "${SRCE_BARE}" "${SRCE_CLONE}"
mkdir -p "${SRCE_CLONE}/.venv/bin"
cat >"${SRCE_CLONE}/.venv/bin/srccheck" <<MOCK
#!${REAL_PYTHON3}
import os
import sys

sys.path.append(os.path.join("${SRCE_CLONE}", "src"))
pp = os.environ.get("PYTHONPATH", "")
assert pp, "expected PYTHONPATH on src-layout repo .venv fallback"
assert os.path.realpath(pp.split(":")[0]) == os.path.realpath(os.path.join(os.getcwd(), "src")), (pp, os.getcwd())
import srcpkg  # noqa: E402
assert srcpkg.OK, f"imported broken srcpkg from {srcpkg.__file__}"
MOCK
chmod +x "${SRCE_CLONE}/.venv/bin/srccheck"
WT_SRCE="$("${WT_SCRIPT}" prepare --repo-path "${SRCE_CLONE}" --lens code-health --worktree-root "${SRCE_WT_ROOT}")"
printf 'OK = False\n' >"${WT_SRCE}/src/srcpkg/__init__.py"
git -C "${WT_SRCE}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "break candidate srcpkg"
check_exit "base-check prepends src/ to PYTHONPATH for src-layout repos" 2 \
	"${CTL_SCRIPT}" base-check --repo srce-repo --worktree "${WT_SRCE}" --test-cmd "srccheck"
check_grep "base-check classifies broken src-layout candidate as CAUSED_BY_CHANGE" "^VERDICT: CAUSED_BY_CHANGE$" "${TEST_DIR}/check.log"

# [4] Custom sidecar referencing .gemini/config/proactive/scripts/ without marker survives stage-repo and disable
export HOME="${TEST_DIR}/sidecar-ownership-home"
mkdir -p "${HOME}/.gemini/config/sidecars/proactive-sweep-ctrld-sync"
CUSTOM_REF_SIDECAR="${HOME}/.gemini/config/sidecars/proactive-sweep-ctrld-sync/sidecar.json"
printf '{"builtin":"schedule","args":["0 9 * * *","%s/.gemini/config/proactive/scripts/custom.sh"]}\n' "${HOME}" >"${CUSTOM_REF_SIDECAR}"
printf '{"enabled":true}\n' >"${HOME}/.gemini/config/sidecars/proactive-sweep-ctrld-sync/user_config.json"
"${CTL_SCRIPT}" install >/dev/null 2>&1
check_exit "stage-repo refuses overwrite of unmanaged sidecar referencing proactive scripts" 1 \
	"${CTL_SCRIPT}" stage-repo --repo ctrld-sync
check "stage-repo preserved custom sidecar lacking ownership marker" grep -q "custom.sh" "${CUSTOM_REF_SIDECAR}"
"${CTL_SCRIPT}" disable >/dev/null 2>&1
check "disable preserved custom sidecar lacking ownership marker" test -f "${CUSTOM_REF_SIDECAR}"

# [20] Custom proactive-safety-guard entry without proactive marker survives disable alongside custom runtime hook
export HOME="${TEST_DIR}/custom-guard-entry-home"
mkdir -p "${HOME}/.gemini/config"
"${CTL_SCRIPT}" install >/dev/null 2>&1
python3 - "${HOME}/.gemini/config/hooks.json" <<'PYTEST'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(json.dumps({
    "proactive-safety-guard": {"enabled": True, "PreToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "echo user-custom-guard"}]}]},
    "other-runtime-hook": {"cmd": "$HOME/.gemini/config/proactive/hooks/helper.py"},
}) + "\n", encoding="utf-8")
PYTEST
"${CTL_SCRIPT}" install >/dev/null 2>&1
"${CTL_SCRIPT}" disable >/dev/null 2>&1
check "disable preserves custom proactive-safety-guard when it lacks proactive marker" python3 - "${HOME}/.gemini/config/hooks.json" <<'PYTEST'
import json, pathlib, sys
d = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert "proactive-safety-guard" in d, d
assert "user-custom-guard" in json.dumps(d["proactive-safety-guard"])
assert "other-runtime-hook" in d
PYTEST

# [BUG_0004] Overnight zoned cron crossing UTC midnight records local date rather than UTC date
export HOME="${TEST_DIR}/audit-overnight-home"
mkdir -p "${HOME}/.gemini/config"
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1
check_exit "audit-missed handles zoned evening cron crossing UTC midnight" 0 \
	"${CTL_SCRIPT}" audit-missed --date "2026-11-21" --repo "ctrld-sync" --cron "CRON_TZ=America/Chicago 50 18 * * 1-5"
check_grep "audit-missed records Friday local date for Saturday 00:50 UTC digest" \
	"^- Scheduled Slot: 2026-11-20 18:50 America/Chicago \(00:50 UTC\)$" \
	"${HOME}/.gemini/antigravity/proactive-reports/2026-11-21-ctrld-sync.md"

# 16. stage-repo --stagger schedules, [PROACTIVE-JUDGE-SHADOW] sidecar grants, and
#     two-tier Judge flows (offline, clean routine pass, major escalation, sentinel
#     privacy gate, harness/regression rejection retirement, and >7d auto-expire)

# 16.1 stage-repo --stagger vs default schedules and Judge sidecar grants
export HOME="${TEST_DIR}/s16-stagger-home"
mkdir -p "${HOME}/.gemini/config"
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1

check_exit "stage-repo --stagger stages ctrld-sync" 0 \
	"${CTL_SCRIPT}" stage-repo --repo ctrld-sync --stagger
check_exit "stage-repo --stagger stages email-security-pipeline" 0 \
	"${CTL_SCRIPT}" stage-repo --repo email-security-pipeline --stagger
check_exit "stage-repo --stagger stages Seatek_Analysis" 0 \
	"${CTL_SCRIPT}" stage-repo --repo Seatek_Analysis --stagger
check_exit "stage-repo without --stagger keeps default 08:15 / 08:35 schedule" 0 \
	"${CTL_SCRIPT}" stage-repo --repo personal-config

check "stage-repo --stagger generates distinct non-overlapping weekday crons and Judge grants" \
	python3 - "${HOME}" <<'PYTEST'
import json
import pathlib
import sys

home = pathlib.Path(sys.argv[1])
sidecars = home / ".gemini/config/sidecars"


def load_pair(repo: str):
    s = json.loads((sidecars / f"proactive-sweep-{repo}/sidecar.json").read_text(encoding="utf-8"))
    t = json.loads((sidecars / f"proactive-triage-{repo}/sidecar.json").read_text(encoding="utf-8"))
    return s, t


cs_s, cs_t = load_pair("ctrld-sync")
esp_s, esp_t = load_pair("email-security-pipeline")
sea_s, sea_t = load_pair("Seatek_Analysis")
pc_s, pc_t = load_pair("personal-config")

assert cs_s["args"][0] == "CRON_TZ=America/Chicago 15 8 * * 1-5", cs_s["args"][0]
assert cs_t["args"][0] == "CRON_TZ=America/Chicago 35 8 * * 1-5", cs_t["args"][0]
assert esp_s["args"][0] == "CRON_TZ=America/Chicago 40 8 * * 1-5", esp_s["args"][0]
assert esp_t["args"][0] == "CRON_TZ=America/Chicago 0 9 * * 1-5", esp_t["args"][0]
assert sea_s["args"][0] == "CRON_TZ=America/Chicago 55 9 * * 1-5", sea_s["args"][0]
assert sea_t["args"][0] == "CRON_TZ=America/Chicago 15 10 * * 1-5", sea_t["args"][0]

staggered_crons = [
    cs_s["args"][0],
    cs_t["args"][0],
    esp_s["args"][0],
    esp_t["args"][0],
    sea_s["args"][0],
    sea_t["args"][0],
]
assert len(set(staggered_crons)) == 6, staggered_crons

def to_minutes(expr: str) -> int:
    parts = expr.split()
    return int(parts[2]) * 60 + int(parts[1])

mins = [to_minutes(c) for c in staggered_crons]
assert mins == sorted(mins), mins
for idx in range(1, len(mins)):
    assert mins[idx] > mins[idx - 1], mins

# Default without --stagger preserves 15 8 / 35 8
assert pc_s["args"][0] == "CRON_TZ=America/Chicago 15 8 * * 1-5", pc_s["args"][0]
assert pc_t["args"][0] == "CRON_TZ=America/Chicago 35 8 * * 1-5", pc_t["args"][0]

ctl_sh = f"{home}/.gemini/config/proactive/scripts/antigravity-proactive-ctl.sh"
wt_sh = f"{home}/.gemini/config/proactive/scripts/proactive-worktree.sh"

for repo, s_doc, t_doc in (
    ("ctrld-sync", cs_s, cs_t),
    ("email-security-pipeline", esp_s, esp_t),
    ("Seatek_Analysis", sea_s, sea_t),
    ("personal-config", pc_s, pc_t),
):
    s_prompt = s_doc["args"][-1]
    t_prompt = t_doc["args"][-1]
    assert "--auto-expire" in s_prompt, s_prompt
    assert "--include-worktrees" in s_prompt, s_prompt
    assert t_prompt.startswith("[PROACTIVE-JUDGE-SHADOW]"), t_prompt
    assert f"{ctl_sh} judge --repo {repo}" in t_prompt, t_prompt
    grants = t_doc["agent_permissions"]["access_grants"]
    for req_grant in (
        f"read_file({home}/dev/{repo})",
        f"command({ctl_sh} judge)",
        f"command({ctl_sh} doctor)",
        f"command({ctl_sh} base-check)",
        f"command({ctl_sh} audit-missed)",
        f"command({ctl_sh} sweep-date)",
        f"command({wt_sh})",
        "command(ocr)",
        "command(coderabbit)",
        "command(lrc)",
        "command(node)",
    ):
        assert req_grant in grants, (repo, req_grant, grants)
PYTEST

# 16.2 judge offline (--skip-tier2) and mocked Tier 2 reviewer flows
export HOME="${TEST_DIR}/s16-judge-home"
S16_MOCK_BIN="${TEST_DIR}/s16_mock_bin"
S16_REPOS_PARENT="${TEST_DIR}/s16_dev"
S16_WT_ROOT="${TEST_DIR}/s16_worktrees"
S16_BARE="${TEST_DIR}/s16_ctrl_remote.git"
S16_SEED="${TEST_DIR}/s16_ctrl_seed"
S16_CLONE="${S16_REPOS_PARENT}/ctrld-sync"
S16_REPORTS="${HOME}/.gemini/antigravity/proactive-reports"
S16_LEDGER="${S16_REPORTS}/judge-shadow-ledger.jsonl"

export S16_OCR_PREVIEW_LOG="${TEST_DIR}/s16_ocr_preview.log"
export S16_OCR_REVIEW_LOG="${TEST_DIR}/s16_ocr_review.log"
export S16_OCR_MODE_FILE="${TEST_DIR}/s16_ocr_mode"
export S16_CR_LOG="${TEST_DIR}/s16_cr.log"
export S16_CR_MODE_FILE="${TEST_DIR}/s16_cr_mode"
export S16_LRC_LOG="${TEST_DIR}/s16_lrc.log"
export S16_REAL_PY3
S16_REAL_PY3="$(command -v python3)"

mkdir -p "${HOME}/.gemini/config" "${S16_MOCK_BIN}" "${S16_REPOS_PARENT}" "${S16_WT_ROOT}" "${S16_SEED}/src"
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1

cat >"${S16_MOCK_BIN}/gh" <<'MOCK'
#!/usr/bin/env bash
if [[ "$1" == "auth" && "$2" == "status" ]]; then
	exit 0
fi
echo "[]"
exit 0
MOCK

cat >"${S16_MOCK_BIN}/ruff" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK

cat >"${S16_MOCK_BIN}/uv" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK

cat >"${S16_MOCK_BIN}/ocr" <<'MOCK'
#!/usr/bin/env bash
if [[ "$1" == "delegate" && "$2" == "preview" ]]; then
	printf '%s\n' "$*" >>"${S16_OCR_PREVIEW_LOG}"
	echo '{"files":[]}'
	exit 0
fi
if [[ "$1" == "review" ]]; then
	printf '%s\n' "$*" >>"${S16_OCR_REVIEW_LOG}"
	out_file=""
	prev=""
	for arg in "$@"; do
		if [[ ${prev} == "--output" ]]; then
			out_file="${arg}"
		fi
		prev="${arg}"
	done
	mode="$(cat "${S16_OCR_MODE_FILE}" 2>/dev/null || echo "clean")"
	payload='{"findings":[]}'
	if [[ ${mode} == "high" ]]; then
		payload='{"findings":[{"severity":"high","message":"unsafe shell interpolation"}]}'
	fi
	if [[ -n ${out_file} ]]; then
		printf '%s\n' "${payload}" >"${out_file}"
	fi
	printf '%s\n' "${payload}"
	exit 0
fi
exit 0
MOCK

cat >"${S16_MOCK_BIN}/coderabbit" <<'MOCK'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"${S16_CR_LOG}"
if [[ "$1" == "auth" && "$2" == "status" ]]; then
	echo '{"authenticated":true}'
	exit 0
fi
if [[ "$1" == "review" ]]; then
	mode="$(cat "${S16_CR_MODE_FILE}" 2>/dev/null || echo "clean")"
	case "${mode}" in
	clean)
		echo '{"type":"complete","status":"review_completed","findings":[]}'
		exit 0
		;;
	major)
		echo '{"type":"finding","severity":"major","message":"stale cache lock not released on exception"}'
		echo '{"type":"complete","status":"review_completed"}'
		exit 0
		;;
	degraded)
		echo '{"type":"action_required","status":"rate_limited"}'
		exit 1
		;;
	esac
fi
exit 0
MOCK

cat >"${S16_MOCK_BIN}/lrc" <<'MOCK'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"${S16_LRC_LOG}"
if [[ "$1" == "usage" ]]; then
	echo '{"can_trigger_reviews":true,"envelope":{"loc_remaining_month":5000}}'
	exit 0
fi
if [[ "$1" == "review" ]]; then
	echo '{"findings":[]}'
	exit 0
fi
exit 0
MOCK

chmod +x \
	"${S16_MOCK_BIN}/gh" \
	"${S16_MOCK_BIN}/ruff" \
	"${S16_MOCK_BIN}/uv" \
	"${S16_MOCK_BIN}/ocr" \
	"${S16_MOCK_BIN}/coderabbit" \
	"${S16_MOCK_BIN}/lrc"

git init -q --bare "${S16_BARE}"
git init -q "${S16_SEED}"
git -C "${S16_SEED}" config user.email "test@example.com"
git -C "${S16_SEED}" config user.name "Test"
cat >"${S16_SEED}/Makefile" <<'EOF'
test:
	@true
EOF
cat >"${S16_SEED}/pyproject.toml" <<'EOF'
[project]
name = "ctrld-sync-fixture"
version = "0.1.0"
EOF
touch "${S16_SEED}/uv.lock"
printf 'def alpha():\n    return 1\n' >"${S16_SEED}/src/mod1.py"
printf 'def beta():\n    return 2\n' >"${S16_SEED}/src/mod2.py"
printf 'def clean_fn():\n    return 3\n' >"${S16_SEED}/src/pass_clean.py"
printf 'def major_fn():\n    return 4\n' >"${S16_SEED}/src/major_case.py"
printf 'def tiebreak_fn():\n    return 5\n' >"${S16_SEED}/src/tiebreak.py"
printf 'def sentinel_fn():\n    return 6\n' >"${S16_SEED}/src/sentinel_note.py"
git -C "${S16_SEED}" add .
git -C "${S16_SEED}" commit -q -m "s16 seed"
git -C "${S16_SEED}" branch -M main
git -C "${S16_SEED}" remote add origin "${S16_BARE}"
git -C "${S16_SEED}" push -q -u origin main
git --git-dir="${S16_BARE}" symbolic-ref HEAD refs/heads/main
git clone -q "${S16_BARE}" "${S16_CLONE}"
git -C "${S16_CLONE}" remote set-head origin -a >/dev/null 2>&1

# (a) Offline (--skip-tier2): evaluates UNJUDGED worktrees -> 0600 ledger, ## Judge Evaluation
#     with deterministic Action line (zero '?' at end), transitions to JUDGED, unblocks check-throttle
WT_S16_OFF1="$(PATH="${S16_MOCK_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_CLONE}" --lens bolt --worktree-root "${S16_WT_ROOT}")"
WT_S16_OFF2="$(PATH="${S16_MOCK_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_CLONE}" --lens code-health --worktree-root "${S16_WT_ROOT}")"
printf 'def alpha():\n    return 10\n' >"${WT_S16_OFF1}/src/mod1.py"
git -C "${WT_S16_OFF1}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "bolt: speed up alpha"
printf 'def beta():\n    return 20\n' >"${WT_S16_OFF2}/src/mod2.py"
git -C "${WT_S16_OFF2}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "chore(qa): clean beta"

PATH="${S16_MOCK_BIN}:${PATH}" check_exit "2 UNJUDGED candidates block check-throttle before judge runs" 5 \
	"${WT_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${S16_WT_ROOT}" \
	--include-worktrees --repo-path "${S16_CLONE}" --max-open 2

DIGEST_OFF="${S16_REPORTS}/2026-11-25-ctrld-sync.md"
cat >"${DIGEST_OFF}" <<EOF
# Proactive Sweep Digest (2026-11-25 - ctrld-sync)

- Status: CANDIDATE_READY
- Substatus: NONE
- Lens: bolt
- Worktree: ${WT_S16_OFF1}
EOF
chmod 600 "${DIGEST_OFF}"
: >"${S16_OCR_REVIEW_LOG}"
: >"${S16_CR_LOG}"
: >"${S16_LRC_LOG}"

PATH="${S16_MOCK_BIN}:${PATH}" check_exit "judge --skip-tier2 evaluates UNJUDGED worktrees offline" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-11-25 \
	--worktree-root "${S16_WT_ROOT}" --repo-root-parent "${S16_REPOS_PARENT}" --skip-tier2
check_grep "judge --skip-tier2 reports judged_now=2" "^judged_now=2$" "${TEST_DIR}/check.log"
check_grep "judge --skip-tier2 reports unjudged_open=0" "^unjudged_open=0$" "${TEST_DIR}/check.log"
check_grep "judge --skip-tier2 reports judged_open=2" "^judged_open=2$" "${TEST_DIR}/check.log"
check "judge --skip-tier2 skips cloud ocr review, coderabbit, and lrc" \
	bash -c "test ! -s '${S16_OCR_REVIEW_LOG}' && test ! -s '${S16_CR_LOG}' && test ! -s '${S16_LRC_LOG}'"
check "judge writes 0600 judge-shadow-ledger.jsonl and deterministic digest evaluation without '?'" \
	python3 - "${S16_LEDGER}" "${DIGEST_OFF}" "${WT_S16_OFF1}" <<'PYTEST'
import json
import os
import pathlib
import sys

ledger = pathlib.Path(sys.argv[1])
digest = pathlib.Path(sys.argv[2])
wt1 = sys.argv[3]

assert ledger.is_file()
assert (os.stat(ledger).st_mode & 0o777) == 0o600, oct(os.stat(ledger).st_mode)
assert (os.stat(digest).st_mode & 0o777) == 0o600, oct(os.stat(digest).st_mode)

rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
wt_rows = [r for r in rows if r.get("worktree") == wt1]
assert len(wt_rows) == 1, rows
row = wt_rows[0]
assert row["verdict"] == "JUDGE_ESCALATE_HUMAN", row
assert row["subreason"] == "TIER2_SKIPPED_OFFLINE", row
assert row["ocr_review"] == "skipped_tier2", row
assert row["coderabbit"] == "skipped_tier2", row
assert row["lrc"] == "skipped_policy", row

d_txt = digest.read_text(encoding="utf-8")
assert "## Judge Evaluation" in d_txt, d_txt
assert "- Verdict: JUDGE_ESCALATE_HUMAN" in d_txt, d_txt
assert "- Action: promote | reject | expire (default: expire on 2026-12-02)" in d_txt, d_txt
for ln in d_txt.splitlines():
    assert not ln.rstrip().endswith("?"), f"open-ended question line found: {ln}"
PYTEST

PATH="${S16_MOCK_BIN}:${PATH}" check_exit "judge transitioning candidates to JUDGED unblocks check-throttle" 0 \
	"${WT_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${S16_WT_ROOT}" \
	--include-worktrees --repo-path "${S16_CLONE}" --max-open 2

# (b) Clean ocr (0 issues) + clean coderabbit (review_completed, 0 findings) -> JUDGE_PASS_ROUTINE
#     and keeps lrc skipped_policy (sparing lrc usage!)
WT_S16_PASS="$(PATH="${S16_MOCK_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_CLONE}" --lens code-health --worktree-root "${S16_WT_ROOT}")"
printf 'def clean_fn():\n    return 30\n' >"${WT_S16_PASS}/src/pass_clean.py"
git -C "${WT_S16_PASS}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "chore(qa): simplify clean_fn"
DIGEST_PASS="${S16_REPORTS}/2026-11-26-ctrld-sync.md"
cat >"${DIGEST_PASS}" <<EOF
# Proactive Sweep Digest (2026-11-26 - ctrld-sync)

- Status: CANDIDATE_READY
- Substatus: NONE
- Lens: code-health
- Worktree: ${WT_S16_PASS}
EOF
chmod 600 "${DIGEST_PASS}"
printf 'clean\n' >"${S16_OCR_MODE_FILE}"
printf 'clean\n' >"${S16_CR_MODE_FILE}"
: >"${S16_OCR_REVIEW_LOG}"
: >"${S16_CR_LOG}"
: >"${S16_LRC_LOG}"

PATH="${S16_MOCK_BIN}:${PATH}" check_exit "judge emits JUDGE_PASS_ROUTINE when ocr and coderabbit pass cleanly" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-11-26 \
	--worktree-root "${S16_WT_ROOT}" --repo-root-parent "${S16_REPOS_PARENT}"
check "judge invoked ocr review and coderabbit but spared lrc" \
	bash -c "test -s '${S16_OCR_REVIEW_LOG}' && test -s '${S16_CR_LOG}' && test ! -s '${S16_LRC_LOG}'"
check "judge ledger and digest record JUDGE_PASS_ROUTINE and lrc=skipped_policy" \
	python3 - "${S16_LEDGER}" "${DIGEST_PASS}" "${WT_S16_PASS}" <<'PYTEST'
import json
import pathlib
import sys

rows = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
wt_rows = [r for r in rows if r.get("worktree") == sys.argv[3]]
assert len(wt_rows) == 1, rows
row = wt_rows[0]
assert row["verdict"] == "JUDGE_PASS_ROUTINE", row
assert row["subreason"] == "ALL_TIERS_CLEAN", row
assert row["ocr_review"] == "completed", row
assert row["coderabbit"] == "review_completed", row
assert row["lrc"] == "skipped_policy", row
assert row["lrc_executed"] is False, row

d_txt = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
assert "- Verdict: JUDGE_PASS_ROUTINE" in d_txt, d_txt
assert "- Action: promote | reject | expire (default: expire on 2026-12-03)" in d_txt, d_txt
for ln in d_txt.splitlines():
    assert not ln.rstrip().endswith("?"), ln
PYTEST

# Verify sparing lrc tie-breaker DOES run when explicitly requested (--with-lrc) and quota permits
WT_S16_LRC="$(PATH="${S16_MOCK_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_CLONE}" --lens code-health --worktree-root "${S16_WT_ROOT}")"
printf 'def tiebreak_fn():\n    return 50\n' >"${WT_S16_LRC}/src/tiebreak.py"
git -C "${WT_S16_LRC}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "chore(qa): tiebreak edit"
: >"${S16_LRC_LOG}"
PATH="${S16_MOCK_BIN}:${PATH}" check_exit "judge --with-lrc runs lrc usage check and review when eligible" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-11-26 \
	--worktree-root "${S16_WT_ROOT}" --repo-root-parent "${S16_REPOS_PARENT}" --with-lrc
check "lrc mock recorded usage inspect and review calls under --with-lrc" test -s "${S16_LRC_LOG}"
check "ledger records lrc_executed=True and lrc=completed for tie-breaker run" \
	python3 - "${S16_LEDGER}" "${WT_S16_LRC}" <<'PYTEST'
import json
import pathlib
import sys

rows = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
wt_rows = [r for r in rows if r.get("worktree") == sys.argv[2]]
assert len(wt_rows) == 1, rows
assert wt_rows[0]["lrc_executed"] is True, wt_rows[0]
assert wt_rows[0]["lrc"] == "completed", wt_rows[0]
PYTEST

# (c) Mocked coderabbit returning a major finding -> JUDGE_ESCALATE_HUMAN (preserving severity)
WT_S16_MAJOR="$(PATH="${S16_MOCK_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_CLONE}" --lens bolt --worktree-root "${S16_WT_ROOT}")"
printf 'def major_fn():\n    return 40\n' >"${WT_S16_MAJOR}/src/major_case.py"
git -C "${WT_S16_MAJOR}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "bolt: refactor major_fn"
DIGEST_MAJOR="${S16_REPORTS}/2026-11-27-ctrld-sync.md"
cat >"${DIGEST_MAJOR}" <<EOF
# Proactive Sweep Digest (2026-11-27 - ctrld-sync)

- Status: CANDIDATE_READY
- Substatus: NONE
- Lens: bolt
- Worktree: ${WT_S16_MAJOR}
EOF
chmod 600 "${DIGEST_MAJOR}"
printf 'clean\n' >"${S16_OCR_MODE_FILE}"
printf 'major\n' >"${S16_CR_MODE_FILE}"
: >"${S16_LRC_LOG}"

PATH="${S16_MOCK_BIN}:${PATH}" check_exit "judge escalates candidate when coderabbit reports a major finding" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-11-27 \
	--worktree-root "${S16_WT_ROOT}" --repo-root-parent "${S16_REPOS_PARENT}"
check "judge preserves coderabbit major severity count and emits JUDGE_ESCALATE_HUMAN" \
	python3 - "${S16_LEDGER}" "${DIGEST_MAJOR}" "${WT_S16_MAJOR}" <<'PYTEST'
import json
import pathlib
import sys

rows = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
wt_rows = [r for r in rows if r.get("worktree") == sys.argv[3]]
assert len(wt_rows) == 1, rows
row = wt_rows[0]
assert row["verdict"] == "JUDGE_ESCALATE_HUMAN", row
assert row["subreason"] == "REVIEWER_FINDINGS_PRESENT", row
assert row["coderabbit"] == "review_completed", row
assert row["tier2"]["coderabbit_counts"]["major"] == 1, row

d_txt = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
assert "- Verdict: JUDGE_ESCALATE_HUMAN" in d_txt, d_txt
assert "major=1" in d_txt, d_txt
PYTEST

# (d) sentinel lens / SECURITY_REPORT_ONLY -> strictly skips cloud coderabbit, ocr review, and lrc
#     (verify mock invocation logs are empty!) and emits JUDGE_ESCALATE_HUMAN
WT_S16_SENT="$(PATH="${S16_MOCK_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_CLONE}" --lens sentinel --worktree-root "${S16_WT_ROOT}")"
printf 'def sentinel_fn():\n    return 60\n' >"${WT_S16_SENT}/src/sentinel_note.py"
git -C "${WT_S16_SENT}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "sentinel: local repro"
DIGEST_SENT="${S16_REPORTS}/2026-11-28-ctrld-sync.md"
cat >"${DIGEST_SENT}" <<EOF
# Proactive Sweep Digest (2026-11-28 - ctrld-sync)

- Status: SECURITY_REPORT_ONLY
- Substatus: NONE
- Lens: sentinel
- Worktree: ${WT_S16_SENT}
EOF
chmod 600 "${DIGEST_SENT}"
printf 'clean\n' >"${S16_CR_MODE_FILE}"
: >"${S16_OCR_REVIEW_LOG}"
: >"${S16_CR_LOG}"
: >"${S16_LRC_LOG}"

PATH="${S16_MOCK_BIN}:${PATH}" check_exit "judge evaluates sentinel candidate locally without cloud reviewers" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-11-28 \
	--worktree-root "${S16_WT_ROOT}" --repo-root-parent "${S16_REPOS_PARENT}" --with-lrc
check "sentinel privacy gate kept ocr review, coderabbit, and lrc invocation logs completely empty" \
	bash -c "test ! -s '${S16_OCR_REVIEW_LOG}' && test ! -s '${S16_CR_LOG}' && test ! -s '${S16_LRC_LOG}'"
check "sentinel candidate ledger row records skipped_privacy and JUDGE_ESCALATE_HUMAN" \
	python3 - "${S16_LEDGER}" "${WT_S16_SENT}" <<'PYTEST'
import json
import pathlib
import sys

rows = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
wt_rows = [r for r in rows if r.get("worktree") == sys.argv[2]]
assert len(wt_rows) == 1, rows
row = wt_rows[0]
assert row["verdict"] == "JUDGE_ESCALATE_HUMAN", row
assert row["subreason"] == "SECURITY_REPORT_ONLY_LOCAL_BOUNDARY", row
assert row["ocr_review"] == "skipped_privacy", row
assert row["coderabbit"] == "skipped_privacy", row
assert row["lrc"] == "skipped_privacy", row
PYTEST

# Also test digest-only SECURITY_REPORT_ONLY (no worktree) on a second repo
S16_ESP_BARE="${TEST_DIR}/s16_esp_remote.git"
S16_ESP_SEED="${TEST_DIR}/s16_esp_seed"
S16_ESP_CLONE="${S16_REPOS_PARENT}/email-security-pipeline"
mkdir -p "${S16_ESP_SEED}/src"
git init -q --bare "${S16_ESP_BARE}"
git init -q "${S16_ESP_SEED}"
git -C "${S16_ESP_SEED}" config user.email "test@example.com"
git -C "${S16_ESP_SEED}" config user.name "Test"
printf 'VALUE = 42\n' >"${S16_ESP_SEED}/src/service.py"
git -C "${S16_ESP_SEED}" add src/service.py
git -C "${S16_ESP_SEED}" commit -q -m "esp seed"
git -C "${S16_ESP_SEED}" branch -M main
git -C "${S16_ESP_SEED}" remote add origin "${S16_ESP_BARE}"
git -C "${S16_ESP_SEED}" push -q -u origin main
git --git-dir="${S16_ESP_BARE}" symbolic-ref HEAD refs/heads/main
git clone -q "${S16_ESP_BARE}" "${S16_ESP_CLONE}"
git -C "${S16_ESP_CLONE}" remote set-head origin -a >/dev/null 2>&1
mkdir -p "${S16_ESP_CLONE}/.venv/bin"
cat >"${S16_ESP_CLONE}/.venv/bin/python3" <<'MOCK'
#!/usr/bin/env bash
if [[ "$1" == "-m" && "$2" == "pytest" ]]; then
	if [[ "$3" == "--version" ]]; then
		echo "pytest 8.0.0"
		exit 0
	fi
	exec "${S16_REAL_PY3}" -c "import service; assert service.VALUE == 42"
fi
exec "${S16_REAL_PY3}" "$@"
MOCK
ln -sf "${S16_MOCK_BIN}/ruff" "${S16_ESP_CLONE}/.venv/bin/ruff"
chmod +x "${S16_ESP_CLONE}/.venv/bin/python3"

DIGEST_SEC_NOWT="${S16_REPORTS}/2026-11-28-email-security-pipeline.md"
cat >"${DIGEST_SEC_NOWT}" <<'EOF'
# Proactive Sweep Digest (2026-11-28 - email-security-pipeline)

- Status: SECURITY_REPORT_ONLY
- Substatus: NONE
- Lens: sentinel
EOF
chmod 600 "${DIGEST_SEC_NOWT}"
: >"${S16_OCR_REVIEW_LOG}"
: >"${S16_CR_LOG}"
: >"${S16_LRC_LOG}"

PATH="${S16_MOCK_BIN}:${PATH}" check_exit "judge handles worktree-less SECURITY_REPORT_ONLY digest with zero cloud calls" 0 \
	"${CTL_SCRIPT}" judge --repo email-security-pipeline --date 2026-11-28 \
	--worktree-root "${S16_WT_ROOT}" --repo-root-parent "${S16_REPOS_PARENT}"
check "worktree-less SECURITY_REPORT_ONLY kept all cloud reviewer logs empty" \
	bash -c "test ! -s '${S16_OCR_REVIEW_LOG}' && test ! -s '${S16_CR_LOG}' && test ! -s '${S16_LRC_LOG}'"
check_grep "worktree-less SECURITY_REPORT_ONLY digest receives JUDGE_ESCALATE_HUMAN" \
	"^- Verdict: JUDGE_ESCALATE_HUMAN$" "${DIGEST_SEC_NOWT}"

# (e) Harness-violating candidate (Makefile edited) AND CAUSED_BY_CHANGE GATE_FAILURE ->
#     emits JUDGE_REJECT and removes rejected worktree + proactive/* branch after ledger receipt!
WT_S16_HARNESS="$(PATH="${S16_MOCK_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_CLONE}" --lens code-health --worktree-root "${S16_WT_ROOT}")"
BRANCH_S16_HARNESS="$(git -C "${WT_S16_HARNESS}" symbolic-ref --quiet --short HEAD)"
printf '\t@echo tampered\n' >>"${WT_S16_HARNESS}/Makefile"
git -C "${WT_S16_HARNESS}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "tamper Makefile"
DIGEST_HARNESS="${S16_REPORTS}/2026-11-30-ctrld-sync.md"
cat >"${DIGEST_HARNESS}" <<EOF
# Proactive Sweep Digest (2026-11-30 - ctrld-sync)

- Status: CANDIDATE_READY
- Substatus: NONE
- Lens: code-health
- Worktree: ${WT_S16_HARNESS}
EOF
chmod 600 "${DIGEST_HARNESS}"

PATH="${S16_MOCK_BIN}:${PATH}" check_exit "judge rejects harness-violating candidate (Makefile edited)" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-11-30 \
	--worktree-root "${S16_WT_ROOT}" --repo-root-parent "${S16_REPOS_PARENT}"
check_grep "judge reports rejected_now=1 for Makefile tamper" "^rejected_now=1$" "${TEST_DIR}/check.log"
check "judge removed rejected Makefile-tampered worktree directory" test ! -d "${WT_S16_HARNESS}"
check "judge deleted rejected Makefile-tampered proactive/* branch" \
	bash -c "! git -C '${S16_CLONE}' rev-parse --verify --quiet 'refs/heads/${BRANCH_S16_HARNESS}' >/dev/null 2>&1"
check "ledger recorded JUDGE_REJECT receipt for Makefile violation before retirement" \
	python3 - "${S16_LEDGER}" "${DIGEST_HARNESS}" "${WT_S16_HARNESS}" <<'PYTEST'
import json
import pathlib
import sys

rows = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
wt_rows = [r for r in rows if r.get("worktree") == sys.argv[3]]
assert len(wt_rows) == 1, rows
assert wt_rows[0]["verdict"] == "JUDGE_REJECT", wt_rows[0]
assert wt_rows[0]["subreason"] == "HARNESS_OR_COVERAGE_VIOLATION", wt_rows[0]
d_txt = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
assert "- Verdict: JUDGE_REJECT" in d_txt, d_txt
assert "- Action: reject (retired automatically on 2026-11-30)" in d_txt, d_txt
for ln in d_txt.splitlines():
    assert not ln.rstrip().endswith("?"), ln
PYTEST

# CAUSED_BY_CHANGE GATE_FAILURE candidate -> auto-runs base-check -> JUDGE_REJECT + worktree & branch retirement
WT_S16_REGR="$(PATH="${S16_MOCK_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/email-security-pipeline --repo-path "${S16_ESP_CLONE}" --lens bolt --worktree-root "${S16_WT_ROOT}")"
BRANCH_S16_REGR="$(git -C "${WT_S16_REGR}" symbolic-ref --quiet --short HEAD)"
printf 'VALUE = -1\n' >"${WT_S16_REGR}/src/service.py"
git -C "${WT_S16_REGR}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "bolt: introduce regression"
DIGEST_REGR="${S16_REPORTS}/2026-12-01-email-security-pipeline.md"
cat >"${DIGEST_REGR}" <<EOF
# Proactive Sweep Digest (2026-12-01 - email-security-pipeline)

- Status: CANDIDATE_READY
- Substatus: GATE_FAILURE
- Lens: bolt
- Worktree: ${WT_S16_REGR}
EOF
chmod 600 "${DIGEST_REGR}"

PATH="${S16_MOCK_BIN}:${PATH}" check_exit "judge classifies GATE_FAILURE via base-check and rejects CAUSED_BY_CHANGE regression" 0 \
	"${CTL_SCRIPT}" judge --repo email-security-pipeline --date 2026-12-01 \
	--worktree-root "${S16_WT_ROOT}" --repo-root-parent "${S16_REPOS_PARENT}"
check_grep "judge reports rejected_now=1 for CAUSED_BY_CHANGE candidate" "^rejected_now=1$" "${TEST_DIR}/check.log"
check "judge removed CAUSED_BY_CHANGE rejected worktree directory" test ! -d "${WT_S16_REGR}"
check "judge deleted CAUSED_BY_CHANGE rejected proactive/* branch" \
	bash -c "! git -C '${S16_ESP_CLONE}' rev-parse --verify --quiet 'refs/heads/${BRANCH_S16_REGR}' >/dev/null 2>&1"
check "ledger and digest record BASE_CHECK_CAUSED_BY_CHANGE JUDGE_REJECT receipt" \
	python3 - "${S16_LEDGER}" "${DIGEST_REGR}" "${WT_S16_REGR}" <<'PYTEST'
import json
import pathlib
import sys

rows = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
wt_rows = [r for r in rows if r.get("worktree") == sys.argv[3]]
assert len(wt_rows) == 1, rows
assert wt_rows[0]["verdict"] == "JUDGE_REJECT", wt_rows[0]
assert wt_rows[0]["subreason"] == "BASE_CHECK_CAUSED_BY_CHANGE", wt_rows[0]
d_txt = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
assert "## Base-Check Classification" in d_txt, d_txt
assert "- Verdict: JUDGE_REJECT" in d_txt, d_txt
PYTEST

# (f) Auto-expires >7d JUDGED worktrees (--now-epoch) to EXPIRED on disk while logging EXPIRED to ledger
S16_FUTURE_EPOCH="$(
	python3 - <<'PY'
import datetime as dt

print(int(dt.datetime.now(dt.timezone.utc).timestamp()) + (10 * 86400))
PY
)"
PATH="${S16_MOCK_BIN}:${PATH}" check_exit "judge auto-expires >7d JUDGED worktrees to EXPIRED under --now-epoch" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-12-10 \
	--worktree-root "${S16_WT_ROOT}" --repo-root-parent "${S16_REPOS_PARENT}" \
	--now-epoch "${S16_FUTURE_EPOCH}" --skip-tier2
check_grep "judge reports judged_open=0 after >7d auto-expire" "^judged_open=0$" "${TEST_DIR}/check.log"
check_grep "judge reports expired_preserved=6 for all 6 prior JUDGED ctrld-sync worktrees" "^expired_preserved=6$" "${TEST_DIR}/check.log"
check "auto-expired JUDGED worktree remains preserved on disk" test -d "${WT_S16_PASS}"
check "worktree metadata and judge-shadow-ledger.jsonl both record EXPIRED" \
	python3 - "${S16_LEDGER}" "${WT_S16_PASS}" <<'PYTEST'
import json
import pathlib
import subprocess
import sys

rows = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
exp_rows = [r for r in rows if r.get("worktree") == sys.argv[2] and r.get("verdict") == "EXPIRED"]
assert len(exp_rows) == 1, rows
assert exp_rows[0]["subreason"] == "SLA_7D_AUTO_EXPIRE", exp_rows[0]

git_dir = subprocess.check_output(["git", "-C", sys.argv[2], "rev-parse", "--git-dir"], text=True).strip()
meta = json.loads((pathlib.Path(git_dir) / "proactive-meta.json").read_text(encoding="utf-8"))
assert meta.get("lifecycle_state") == "EXPIRED", meta
assert meta.get("expire_reason") == "SLA_7D_AUTO_EXPIRE", meta
PYTEST

# 16.3 Judge hardening regressions: T1 digest attribution + SECURITY_REPORT_ONLY precedence,
#      T2 verify flag replay, T3 dirty fingerprinted JUDGED invalidation, T9 GitNexus degraded,
#      CodeRabbit empty OCR payload rejection, and NO_WORKTREE SECURITY_REPORT_ONLY deduping
S16_HARD_HOME="${TEST_DIR}/s16-hard-home"
S16_HARD_WT="${S16_HARD_HOME}/.gemini/antigravity/worktrees"
S16_HARD_REPORTS="${S16_HARD_HOME}/.gemini/antigravity/proactive-reports"
S16_HARD_REPOS="${S16_HARD_HOME}/dev"
S16_HARD_BARE="${TEST_DIR}/s16-hard-bare.git"
S16_HARD_SEED="${TEST_DIR}/s16-hard-seed"
S16_HARD_CLONE="${S16_HARD_REPOS}/ctrld-sync"
S16_HARD_BIN="${TEST_DIR}/s16-hard-bin"
mkdir -p "${S16_HARD_WT}" "${S16_HARD_REPORTS}" "${S16_HARD_REPOS}" "${S16_HARD_BIN}" "${S16_HARD_SEED}/src" "${S16_HARD_SEED}/tests"

cp "${S16_MOCK_BIN}/gh" "${S16_MOCK_BIN}/ruff" "${S16_MOCK_BIN}/coderabbit" "${S16_MOCK_BIN}/lrc" "${S16_HARD_BIN}/"
cat >"${S16_HARD_BIN}/uv" <<'MOCK'
#!/usr/bin/env bash
if [[ "$*" == *"pytest"* ]]; then
	exec python3 -m unittest discover -s tests -p "test_*.py" -q
fi
exit 0
MOCK
cat >"${S16_HARD_BIN}/ocr" <<'MOCK'
#!/usr/bin/env bash
if [[ "$1" == "delegate" && "$2" == "preview" ]]; then
	echo '{"files":[]}'
	exit 0
fi
if [[ "$1" == "review" ]]; then
	printf '%s\n' "$*" >>"${S16_HARD_OCR_LOG}"
	out_file=""
	prev=""
	for arg in "$@"; do
		if [[ ${prev} == "--output" ]]; then
			out_file="${arg}"
		fi
		prev="${arg}"
	done
	mode="$(cat "${S16_HARD_OCR_MODE}" 2>/dev/null || echo "clean")"
	payload='{"findings":[]}'
	if [[ ${mode} == "empty" ]]; then
		payload='{}'
	fi
	if [[ -n ${out_file} ]]; then
		printf '%s\n' "${payload}" >"${out_file}"
	fi
	printf '%s\n' "${payload}"
	exit 0
fi
exit 0
MOCK
cat >"${S16_HARD_BIN}/node" <<'MOCK'
#!/usr/bin/env bash
if [[ "$*" == *"run.cjs impact"* ]]; then
	mode="$(cat "${S16_HARD_GN_MODE}" 2>/dev/null || echo "low")"
	if [[ ${mode} == "degraded" ]]; then
		echo '{"error":"index missing"}' >&2
		exit 2
	fi
	echo '{"risk":"LOW"}'
	exit 0
fi
exit 0
MOCK
chmod +x "${S16_HARD_BIN}/uv" "${S16_HARD_BIN}/ocr" "${S16_HARD_BIN}/node"

export S16_HARD_OCR_MODE="${TEST_DIR}/s16-hard-ocr.mode"
export S16_HARD_OCR_LOG="${TEST_DIR}/s16-hard-ocr.log"
export S16_HARD_GN_MODE="${TEST_DIR}/s16-hard-gn.mode"
printf 'clean\n' >"${S16_HARD_OCR_MODE}"
printf 'low\n' >"${S16_HARD_GN_MODE}"
: >"${S16_HARD_OCR_LOG}"
export HOME="${S16_HARD_HOME}"
"${CTL_SCRIPT}" install --pilot >/dev/null 2>&1

git init -q --bare "${S16_HARD_BARE}"
git init -q "${S16_HARD_SEED}"
git -C "${S16_HARD_SEED}" config user.email "test@example.com"
git -C "${S16_HARD_SEED}" config user.name "Test"
mkdir -p "${S16_HARD_SEED}/.gitnexus"
cat >"${S16_HARD_SEED}/.gitnexus/run.cjs" <<'EOF'
// placeholder
EOF
cat >"${S16_HARD_SEED}/Makefile" <<'EOF'
test:
	@python3 -m unittest discover -s tests -p "test_*.py" -q
EOF
cat >"${S16_HARD_SEED}/pyproject.toml" <<'EOF'
[project]
name = "ctrld-sync-hardening-fixture"
version = "0.1.0"
EOF
touch "${S16_HARD_SEED}/uv.lock"
printf 'def helper():\n    return 1\n' >"${S16_HARD_SEED}/src/mod.py"
printf 'import unittest\nfrom src.mod import helper\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(helper(), 1)\n' >"${S16_HARD_SEED}/tests/test_mod.py"
git -C "${S16_HARD_SEED}" add .
git -C "${S16_HARD_SEED}" commit -q -m "hardening seed"
git -C "${S16_HARD_SEED}" branch -M main
git -C "${S16_HARD_SEED}" remote add origin "${S16_HARD_BARE}"
git -C "${S16_HARD_SEED}" push -q -u origin main
git --git-dir="${S16_HARD_BARE}" symbolic-ref HEAD refs/heads/main
git clone -q "${S16_HARD_BARE}" "${S16_HARD_CLONE}"
git -C "${S16_HARD_CLONE}" remote set-head origin -a >/dev/null 2>&1

# (1) T1 + CodeRabbit axmu: SECURITY_REPORT_ONLY exact digest takes precedence over today's digest even if today's mentions short_sha
WT_HARD_SEC="$(PATH="${S16_HARD_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_HARD_CLONE}" --lens code-health --worktree-root "${S16_HARD_WT}")"
printf 'def helper():\n    return 2\n' >"${WT_HARD_SEC}/src/mod.py"
git -C "${WT_HARD_SEC}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "fix: harden mod"
SEC_HEAD_SHORT="$(git -C "${WT_HARD_SEC}" rev-parse --short=7 HEAD)"
cat >"${S16_HARD_REPORTS}/2026-12-10-ctrld-sync.md" <<EOF
# Proactive Sweep Digest (2026-12-10 - ctrld-sync)

- Status: SECURITY_REPORT_ONLY
- Substatus: NONE
- Lens: code-health
- Worktree: ${WT_HARD_SEC}
EOF
cat >"${S16_HARD_REPORTS}/2026-12-11-ctrld-sync.md" <<EOF
# Proactive Sweep Digest (2026-12-11 - ctrld-sync)

- Status: CANDIDATE_READY
- Substatus: NONE
- Lens: code-health
- Note: mentions commit ${SEC_HEAD_SHORT} on another branch proactive/other
- Worktree: ${S16_HARD_WT}/proactive-ctrld-sync-nonexistent
EOF
chmod 600 "${S16_HARD_REPORTS}/2026-12-10-ctrld-sync.md" "${S16_HARD_REPORTS}/2026-12-11-ctrld-sync.md"

: >"${S16_HARD_OCR_LOG}"
: >"${S16_CR_LOG}"
PATH="${S16_HARD_BIN}:${PATH}" check_exit "judge enforces exact SECURITY_REPORT_ONLY digest over today short-sha match" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-12-11 \
	--worktree-root "${S16_HARD_WT}" --repo-root-parent "${S16_HARD_REPOS}"
check "privacy gate kept cloud ocr review and coderabbit skipped despite code-health lens" \
	bash -c "test ! -s '${S16_HARD_OCR_LOG}' && test ! -s '${S16_CR_LOG}'"

# Remove WT_HARD_SEC cleanly after verifying privacy gate
git -C "${S16_HARD_CLONE}" worktree remove --force "${WT_HARD_SEC}" >/dev/null 2>&1 || rm -rf "${WT_HARD_SEC}"
git -C "${S16_HARD_CLONE}" worktree prune >/dev/null 2>&1 || true

# (2) T9 + CodeRabbit axm9: empty '{}' OCR payload and degraded GitNexus fail closed to JUDGE_ESCALATE_HUMAN
WT_HARD_E="$(PATH="${S16_HARD_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_HARD_CLONE}" --lens code-health --worktree-root "${S16_HARD_WT}")"
printf 'def helper():\n    return 3\n' >"${WT_HARD_E}/src/mod.py"
printf 'import unittest\nfrom src.mod import helper\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(helper(), 3)\n' >"${WT_HARD_E}/tests/test_mod.py"
git -C "${WT_HARD_E}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "chore: update helper and test"
# Run verify with --allow-test-edits to test T2 persistence
PATH="${S16_HARD_BIN}:${PATH}" check_exit "verify --allow-test-edits persists override flags (T2)" 0 \
	"${WT_SCRIPT}" verify --worktree "${WT_HARD_E}" --lens code-health --test-cmd "true" --allow-test-edits

printf 'empty\n' >"${S16_HARD_OCR_MODE}"
printf 'degraded\n' >"${S16_HARD_GN_MODE}"
cat >"${S16_HARD_REPORTS}/2026-12-12-ctrld-sync.md" <<EOF
# Proactive Sweep Digest (2026-12-12 - ctrld-sync)

- Status: CANDIDATE_READY
- Substatus: NONE
- Lens: code-health
- Worktree: ${WT_HARD_E}
EOF
chmod 600 "${S16_HARD_REPORTS}/2026-12-12-ctrld-sync.md"

PATH="${S16_HARD_BIN}:${PATH}" check_exit "judge escalates on degraded GitNexus & empty OCR '{}' (never JUDGE_PASS_ROUTINE)" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-12-12 \
	--worktree-root "${S16_HARD_WT}" --repo-root-parent "${S16_HARD_REPOS}"
check "judge recorded T2 verify_probe_rc=0, ocr=degraded, gitnexus_degraded=True, and JUDGE_ESCALATE_HUMAN" \
	python3 - "${S16_HARD_HOME}/.gemini/antigravity/proactive-reports/judge-shadow-ledger.jsonl" "${WT_HARD_E}" <<'PYTEST'
import json, pathlib, sys
rows = [json.loads(l) for l in pathlib.Path(sys.argv[1]).read_text().splitlines() if l.strip()]
w = [r for r in rows if r.get("worktree") == sys.argv[2]]
assert len(w) == 1, rows
assert w[0]["verdict"] == "JUDGE_ESCALATE_HUMAN", w[0]
assert w[0]["tier1"]["verify_probe_rc"] == 0, w[0]
assert w[0]["tier1"]["gitnexus_degraded"] is True, w[0]
assert w[0]["ocr_review"] == "degraded", w[0]
PYTEST

# (3) T3 + T10: dirty GATE_FAILURE base-check cleared -> fingerprinted JUDGED, invalidated upon subsequent dirty edit
git -C "${S16_HARD_CLONE}" worktree remove --force "${WT_HARD_E}" >/dev/null 2>&1 || rm -rf "${WT_HARD_E}"
git -C "${S16_HARD_CLONE}" worktree prune >/dev/null 2>&1 || true

# Break test on base and sync S16_HARD_CLONE BEFORE prepare so base_sha genuinely fails tests (PRE_EXISTING_ON_BASE)
printf 'def helper():\n    return 99\n' >"${S16_HARD_SEED}/src/mod.py"
git -C "${S16_HARD_SEED}" commit -aq -m "break test on base"
git -C "${S16_HARD_SEED}" push -q origin main
git -C "${S16_HARD_CLONE}" fetch -q origin main
git -C "${S16_HARD_CLONE}" reset -q --hard origin/main

WT_HARD_D="$(PATH="${S16_HARD_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_HARD_CLONE}" --lens bolt --worktree-root "${S16_HARD_WT}")"
printf '# unrelated dirty edit on already-broken base\n' >>"${WT_HARD_D}/src/mod.py"
cat >"${S16_HARD_REPORTS}/2026-12-13-ctrld-sync.md" <<EOF
# Proactive Sweep Digest (2026-12-13 - ctrld-sync)

- Status: CANDIDATE_READY
- Substatus: GATE_FAILURE
- Lens: bolt
- Worktree: ${WT_HARD_D}
EOF
chmod 600 "${S16_HARD_REPORTS}/2026-12-13-ctrld-sync.md"

PATH="${S16_HARD_BIN}:${PATH}" check_exit "judge transitions dirty cleared GATE_FAILURE candidate to fingerprinted JUDGED" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-12-13 \
	--worktree-root "${S16_HARD_WT}" --repo-root-parent "${S16_HARD_REPOS}"
check_grep "dirty cleared GATE_FAILURE reports judged_now=1 and judged_open=1" "^judged_open=1$" "${TEST_DIR}/check.log"
check "ledger confirms PRE_EXISTING_ON_BASE classification for dirty cleared candidate" \
	python3 - "${S16_HARD_HOME}/.gemini/antigravity/proactive-reports/judge-shadow-ledger.jsonl" "${WT_HARD_D}" <<'PYTEST'
import json, pathlib, sys
rows = [json.loads(l) for l in pathlib.Path(sys.argv[1]).read_text().splitlines() if l.strip()]
w = [r for r in rows if r.get("worktree") == sys.argv[2]]
assert len(w) == 1, rows
assert w[0]["tier1"]["base_check"] == "PRE_EXISTING_ON_BASE", w[0]
assert w[0]["verdict"] == "JUDGE_ESCALATE_HUMAN", w[0]
PYTEST

printf '# further dirty mutation\n' >>"${WT_HARD_D}/src/mod.py"
PATH="${S16_HARD_BIN}:${PATH}" check_exit "mutating dirty worktree invalidates fingerprinted JUDGED back to UNJUDGED" 5 \
	"${WT_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${S16_HARD_WT}" \
	--include-worktrees --repo-path "${S16_HARD_CLONE}" --max-open 1

# (3b) Devin bbJX & b576 & b5-U: append level-1 '# Reviewer notes' after Judge Evaluation, commit revision, re-run without --force-rejudge
printf '\n# Reviewer notes\nManual check verified base failure.\n' >>"${S16_HARD_REPORTS}/2026-12-13-ctrld-sync.md"
printf 'clean\n' >"${S16_HARD_OCR_MODE}"
printf 'low\n' >"${S16_HARD_GN_MODE}"
printf 'def helper():\n    return 1\n' >"${WT_HARD_D}/src/mod.py"
git -C "${WT_HARD_D}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "fix mod helper on candidate branch"
HEAD_HARD_D_REV="$(git -C "${WT_HARD_D}" rev-parse HEAD)"
PATH="${S16_HARD_BIN}:${PATH}" check_exit "judge re-evaluates new commit and replaces stale Judge Evaluation block without --force-rejudge" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-12-13 \
	--worktree-root "${S16_HARD_WT}" --repo-root-parent "${S16_HARD_REPOS}"
check "digest Judge Evaluation updated in-place preserving '# Reviewer notes' without stale Action" \
	python3 - "${S16_HARD_REPORTS}/2026-12-13-ctrld-sync.md" "${HEAD_HARD_D_REV}" <<'PYTEST'
import pathlib, re, sys
txt = pathlib.Path(sys.argv[1]).read_text()
new_sha = sys.argv[2]
assert txt.count("## Judge Evaluation") == 1, txt
assert "# Reviewer notes\nManual check verified base failure." in txt, txt
judge_blk = [b for b in re.split(r"(?m)(?=^#{1,2}\s)", txt) if b.startswith("## Judge Evaluation")][0]
assert f"- Head SHA: {new_sha}" in judge_blk, judge_blk
assert "- Verdict: JUDGE_PASS_ROUTINE" in judge_blk, judge_blk
action_lines = [ln for ln in judge_blk.splitlines() if ln.strip().startswith("- Action:")]
assert action_lines and "- Action: promote | reject | expire" in action_lines[0] and len(action_lines) == 1, judge_blk
PYTEST

# (4) CodeRabbit axnE: SECURITY_REPORT_ONLY with 0 active worktrees deduplicates NO_WORKTREE cleanly across re-runs
git -C "${S16_HARD_CLONE}" worktree remove --force "${WT_HARD_D}" >/dev/null 2>&1 || rm -rf "${WT_HARD_D}"
git -C "${S16_HARD_CLONE}" worktree prune >/dev/null 2>&1 || true
cat >"${S16_HARD_REPORTS}/2026-12-14-ctrld-sync.md" <<'EOF'
# Proactive Sweep Digest (2026-12-14 - ctrld-sync)

- Status: SECURITY_REPORT_ONLY
- Substatus: NONE
- Lens: sentinel
EOF
chmod 600 "${S16_HARD_REPORTS}/2026-12-14-ctrld-sync.md"
PATH="${S16_HARD_BIN}:${PATH}" check_exit "first judge run annotates NO_WORKTREE SECURITY_REPORT_ONLY" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-12-14 \
	--worktree-root "${S16_HARD_WT}" --repo-root-parent "${S16_HARD_REPOS}"
PATH="${S16_HARD_BIN}:${PATH}" check_exit "second judge run dedupes NO_WORKTREE Judge Evaluation header" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-12-14 \
	--worktree-root "${S16_HARD_WT}" --repo-root-parent "${S16_HARD_REPOS}"
check "NO_WORKTREE digest contains exactly one ## Judge Evaluation section" \
	python3 - "${S16_HARD_REPORTS}/2026-12-14-ctrld-sync.md" <<'PYTEST'
import pathlib, sys
txt = pathlib.Path(sys.argv[1]).read_text()
assert txt.count("## Judge Evaluation") == 1, txt
assert "- Head SHA: NO_WORKTREE" in txt, txt
PYTEST

# (5) Devin bbHG: preflight exit 7 on an early repo escalates that repo without aborting later healthy repos
S16_HARD_ESP_BARE="${TEST_DIR}/s16-hard-esp.git"
S16_HARD_ESP_SEED="${TEST_DIR}/s16-hard-esp-seed"
S16_HARD_ESP_CLONE="${S16_HARD_REPOS}/email-security-pipeline"
mkdir -p "${S16_HARD_ESP_SEED}/src"
git init -q --bare "${S16_HARD_ESP_BARE}"
git init -q "${S16_HARD_ESP_SEED}"
git -C "${S16_HARD_ESP_SEED}" config user.email "test@example.com"
git -C "${S16_HARD_ESP_SEED}" config user.name "Test"
cat >"${S16_HARD_ESP_SEED}/Makefile" <<'EOF'
test:
	@true
EOF
printf 'VALUE = 1\n' >"${S16_HARD_ESP_SEED}/src/svc.py"
git -C "${S16_HARD_ESP_SEED}" add .
git -C "${S16_HARD_ESP_SEED}" commit -q -m "esp hard seed"
git -C "${S16_HARD_ESP_SEED}" branch -M main
git -C "${S16_HARD_ESP_SEED}" remote add origin "${S16_HARD_ESP_BARE}"
git -C "${S16_HARD_ESP_SEED}" push -q -u origin main
git --git-dir="${S16_HARD_ESP_BARE}" symbolic-ref HEAD refs/heads/main
git clone -q "${S16_HARD_ESP_BARE}" "${S16_HARD_ESP_CLONE}"
git -C "${S16_HARD_ESP_CLONE}" remote set-head origin -a >/dev/null 2>&1
mkdir -p "${S16_HARD_ESP_CLONE}/.venv/bin"
cat >"${S16_HARD_ESP_CLONE}/.venv/bin/python3" <<'MOCK'
#!/usr/bin/env bash
if [[ "$1" == "-m" && "$2" == "pytest" ]]; then
	echo "pytest 8.0.0"
	exit 0
fi
exec "${S16_REAL_PY3}" "$@"
MOCK
ln -sf "${S16_MOCK_BIN}/ruff" "${S16_HARD_ESP_CLONE}/.venv/bin/ruff"
chmod +x "${S16_HARD_ESP_CLONE}/.venv/bin/python3"

WT_HARD_MISS_TC="$(PATH="${S16_HARD_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_HARD_CLONE}" --lens code-health --worktree-root "${S16_HARD_WT}")"
printf 'def extra():\n    return 2\n' >"${WT_HARD_MISS_TC}/src/extra.py"
git -C "${WT_HARD_MISS_TC}" add src/extra.py
git -C "${WT_HARD_MISS_TC}" -c user.email="test@example.com" -c user.name="Test" commit -q -m "add extra"
# Remove uv.lock from S16_HARD_CLONE clone (untracked/committed removal on local clone worktree) so preflight exits 7
rm -f "${S16_HARD_CLONE}/uv.lock"

WT_HARD_ESP="$(PATH="${S16_HARD_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/email-security-pipeline --repo-path "${S16_HARD_ESP_CLONE}" --lens code-health --worktree-root "${S16_HARD_WT}")"
printf 'VALUE = 2\n' >"${WT_HARD_ESP}/src/svc.py"
git -C "${WT_HARD_ESP}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "update svc"

cat >"${S16_HARD_REPORTS}/2026-12-15-ctrld-sync.md" <<EOF
# Proactive Sweep Digest (2026-12-15 - ctrld-sync)

- Status: CANDIDATE_READY
- Substatus: NONE
- Lens: code-health
- Worktree: ${WT_HARD_MISS_TC}
EOF
cat >"${S16_HARD_REPORTS}/2026-12-15-email-security-pipeline.md" <<EOF
# Proactive Sweep Digest (2026-12-15 - email-security-pipeline)

- Status: CANDIDATE_READY
- Substatus: NONE
- Lens: code-health
- Worktree: ${WT_HARD_ESP}
EOF
chmod 600 "${S16_HARD_REPORTS}/2026-12-15-ctrld-sync.md" "${S16_HARD_REPORTS}/2026-12-15-email-security-pipeline.md"

PATH="${S16_HARD_BIN}:${PATH}" check_exit "multi-repo judge continues to email-security-pipeline after ctrld-sync preflight exit 7" 0 \
	"${CTL_SCRIPT}" judge --repo ctrld-sync --repo email-security-pipeline --date 2026-12-15 \
	--worktree-root "${S16_HARD_WT}" --repo-root-parent "${S16_HARD_REPOS}"
check "ctrld-sync escalated with PREFLIGHT_MISSING_TOOLCHAIN and email-security-pipeline passed cleanly" \
	python3 - "${S16_HARD_HOME}/.gemini/antigravity/proactive-reports/judge-shadow-ledger.jsonl" "${WT_HARD_MISS_TC}" "${WT_HARD_ESP}" <<'PYTEST'
import json, pathlib, sys
rows = [json.loads(l) for l in pathlib.Path(sys.argv[1]).read_text().splitlines() if l.strip()]
cs = [r for r in rows if r.get("worktree") == sys.argv[2]]
esp = [r for r in rows if r.get("worktree") == sys.argv[3]]
assert len(cs) == 1 and cs[0]["subreason"] == "PREFLIGHT_MISSING_TOOLCHAIN", cs
assert len(esp) == 1 and esp[0]["verdict"] == "JUDGE_PASS_ROUTINE", esp
PYTEST

# (6) Devin cF5S: unreadable untracked file causing empty starting fingerprint prevents deletion even on Makefile JUDGE_REJECT
if [[ $(id -u) -ne 0 ]]; then
	touch "${S16_HARD_CLONE}/uv.lock"
	WT_HARD_UNREAD="$(PATH="${S16_HARD_BIN}:${PATH}" "${WT_SCRIPT}" prepare --repo abhimehro/ctrld-sync --repo-path "${S16_HARD_CLONE}" --lens code-health --worktree-root "${S16_HARD_WT}")"
	printf '\t@echo tamper\n' >>"${WT_HARD_UNREAD}/Makefile"
	git -C "${WT_HARD_UNREAD}" -c user.email="test@example.com" -c user.name="Test" commit -aq -m "tamper Makefile with unreadable file"
	printf 'secret note\n' >"${WT_HARD_UNREAD}/unreadable.log"
	chmod 000 "${WT_HARD_UNREAD}/unreadable.log"
	cat >"${S16_HARD_REPORTS}/2026-12-16-ctrld-sync.md" <<EOF
# Proactive Sweep Digest (2026-12-16 - ctrld-sync)

- Status: CANDIDATE_READY
- Substatus: NONE
- Lens: code-health
- Worktree: ${WT_HARD_UNREAD}
EOF
	chmod 600 "${S16_HARD_REPORTS}/2026-12-16-ctrld-sync.md"
	PATH="${S16_HARD_BIN}:${PATH}" check_exit "judge escalates without deleting worktree when fingerprint fails on unreadable file" 0 \
		"${CTL_SCRIPT}" judge --repo ctrld-sync --date 2026-12-16 \
		--worktree-root "${S16_HARD_WT}" --repo-root-parent "${S16_HARD_REPOS}"
	check "unreadable-fingerprint worktree preserved on disk despite Makefile tamper" test -d "${WT_HARD_UNREAD}"
	check "ledger recorded WORKTREE_IDENTITY_UNVERIFIED JUDGE_ESCALATE_HUMAN" \
		python3 - "${S16_HARD_HOME}/.gemini/antigravity/proactive-reports/judge-shadow-ledger.jsonl" "${WT_HARD_UNREAD}" <<'PYTEST'
import json, pathlib, sys
rows = [json.loads(l) for l in pathlib.Path(sys.argv[1]).read_text().splitlines() if l.strip()]
u = [r for r in rows if r.get("worktree") == sys.argv[2]]
assert len(u) == 1, rows
assert u[0]["verdict"] == "JUDGE_ESCALATE_HUMAN", u[0]
assert u[0]["subreason"] == "WORKTREE_IDENTITY_UNVERIFIED", u[0]
PYTEST
	chmod 600 "${WT_HARD_UNREAD}/unreadable.log" || true
fi

echo ""
echo "Summary: PASS=${PASS} FAIL=${FAIL}"
[[ ${FAIL} -eq 0 ]]
