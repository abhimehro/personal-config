#!/usr/bin/env bash
# Tests for GitNexus bootstrap in scripts/cursor_cloud_workspace_install.sh.
set -euo pipefail

echo "=========================================="
echo "Testing cursor_cloud_workspace_install.sh"
echo "=========================================="

TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'cursor-cloud-install-test')"
export TEST_DIR
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/cursor_cloud_workspace_install.sh"

cleanup() {
	rm -rf "${TEST_DIR}"
}
trap cleanup EXIT

fail() {
	echo "❌ FAIL: $*" >&2
	exit 1
}

PASS=0
pass() {
	echo "✅ PASS: $*"
	PASS=$((PASS + 1))
}

[[ -x "${SCRIPT}" ]] || fail "script missing or not executable"

# Source functions without running the installer (BASH_SOURCE != $0).
# shellcheck source=scripts/cursor_cloud_workspace_install.sh
source "${SCRIPT}"

HOME="${TEST_DIR}/home"
export HOME
mkdir -p "${HOME}"

MOCK_BIN="${TEST_DIR}/mock_bin"
mkdir -p "${MOCK_BIN}"
REPOS_ROOT="${TEST_DIR}/repos"
mkdir -p "${REPOS_ROOT}"

write_mock() {
	local name="$1"
	local body="$2"
	printf '%s\n' "#!/usr/bin/env bash" "${body}" >"${MOCK_BIN}/${name}"
	chmod +x "${MOCK_BIN}/${name}"
}

make_git_repo() {
	local repo="$1"
	mkdir -p "${repo}"
	git -C "${repo}" init -q
}

echo ""
echo "Test 1: skip npm when pinned gitnexus is already on PATH"
echo "---"
write_mock gitnexus 'echo "1.6.12"'
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" HOME="${HOME}" \
	ensure_gitnexus >"${TEST_DIR}/t1.out" 2>&1 || fail "ensure_gitnexus should succeed"
grep -q "already present" "${TEST_DIR}/t1.out" || fail "expected already-present log, got: $(cat "${TEST_DIR}/t1.out")"
pass "skip reinstall when version matches"

echo ""
echo "Test 2: skip when npm is missing"
echo "---"
rm -f "${MOCK_BIN}/gitnexus" "${MOCK_BIN}/npm"
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" HOME="${HOME}" \
	ensure_gitnexus >"${TEST_DIR}/t2.out" 2>&1 || fail "ensure_gitnexus should skip, not fail"
grep -q "npm not on PATH" "${TEST_DIR}/t2.out" || fail "expected npm-missing skip, got: $(cat "${TEST_DIR}/t2.out")"
pass "skip install when npm missing"

echo ""
echo "Test 3: npm install uses pinned version and --prefix \$HOME/.local"
echo "---"
rm -f "${MOCK_BIN}/gitnexus"
write_mock npm "echo \"npm \$*\" >>\"${TEST_DIR}/npm.log\"
mkdir -p \"${HOME}/.local/bin\"
printf '%s\\n' '#!/usr/bin/env bash' 'echo 1.6.12' >\"${HOME}/.local/bin/gitnexus\"
chmod +x \"${HOME}/.local/bin/gitnexus\""
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" HOME="${HOME}" \
	ensure_gitnexus >"${TEST_DIR}/t3.out" 2>&1 || fail "ensure_gitnexus install path failed: $(cat "${TEST_DIR}/t3.out")"
[[ -f "${TEST_DIR}/npm.log" ]] || fail "npm was not invoked; installer said: $(cat "${TEST_DIR}/t3.out")"
grep -q "gitnexus@1.6.12" "${TEST_DIR}/npm.log" || fail "npm was not asked for gitnexus@1.6.12: $(cat "${TEST_DIR}/npm.log")"
grep -q -- "--prefix ${HOME}/.local" "${TEST_DIR}/npm.log" || fail "npm missing --prefix HOME/.local"
grep -q -- "--global" "${TEST_DIR}/npm.log" || fail "npm missing --global"
pass "pinned npm install under HOME/.local"

echo ""
echo "Test 4: reinstall when version mismatches"
echo "---"
: >"${TEST_DIR}/npm.log"
rm -f "${HOME}/.local/bin/gitnexus"
write_mock gitnexus 'echo "9.9.9"'
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" HOME="${HOME}" \
	ensure_gitnexus >"${TEST_DIR}/t4.out" 2>&1 || fail "mismatch path failed"
grep -q "reinstalling" "${TEST_DIR}/t4.out" || fail "expected reinstall log: $(cat "${TEST_DIR}/t4.out")"
grep -q "gitnexus@1.6.12" "${TEST_DIR}/npm.log" || fail "mismatch path did not call npm"
pass "reinstall on version mismatch"

echo ""
echo "Test 5: index uses --index-only --skip-fts and skips repoprompt-ce"
echo "---"
: >"${TEST_DIR}/gitnexus.log"
rm -f "${HOME}/.local/bin/gitnexus"
write_mock gitnexus "echo \"gitnexus \$*\" >>\"${TEST_DIR}/gitnexus.log\"
echo \"1.6.12\""
make_git_repo "${REPOS_ROOT}/personal-config"
make_git_repo "${REPOS_ROOT}/ctrld-sync"
make_git_repo "${REPOS_ROOT}/repoprompt-ce"
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" HOME="${HOME}" REPOS_ROOT="${REPOS_ROOT}" \
	index_gitnexus_repos >"${TEST_DIR}/t5.out" 2>&1 || fail "index_gitnexus_repos failed: $(cat "${TEST_DIR}/t5.out")"
grep -q "analyze --index-only --skip-fts" "${TEST_DIR}/gitnexus.log" || fail "missing analyze flags: $(cat "${TEST_DIR}/gitnexus.log")"
# Two indexable git repos (personal-config, ctrld-sync); Swift repo must not be analyzed.
count="$(grep -c "analyze --index-only --skip-fts" "${TEST_DIR}/gitnexus.log" || true)"
[[ "${count}" -eq 2 ]] || fail "expected 2 analyze calls, got ${count}: $(cat "${TEST_DIR}/gitnexus.log")"
grep -q "skip repoprompt-ce" "${TEST_DIR}/t5.out" || fail "expected HOLD_PLATFORM skip for repoprompt-ce"
pass "index flags and repoprompt-ce skip"

echo ""
echo "Test 6: .gitnexus/ is appended to .git/info/exclude once"
echo "---"
exclude_gitnexus_index "${REPOS_ROOT}/personal-config" || fail "exclude first call"
exclude_gitnexus_index "${REPOS_ROOT}/personal-config" || fail "exclude second call"
hits="$(grep -cFx '.gitnexus/' "${REPOS_ROOT}/personal-config/.git/info/exclude")"
[[ "${hits}" -eq 1 ]] || fail "expected one .gitnexus/ exclude line, got ${hits}"
pass "exclude file is idempotent"

echo ""
echo "Test 7: sourcing the script does not run the installer"
echo "---"
# Already sourced at the top; 'done' would have printed if main ran.
if grep -q "cursor_cloud_workspace_install: done" "${TEST_DIR}/t1.out" 2>/dev/null; then
	fail "main ran during ensure_gitnexus"
fi
pass "functions are sourceable without running main"

echo ""
echo "Test 8: substring versions do not satisfy the pin"
echo "---"
gitnexus_version_matches "1.6.12" || fail "exact 1.6.12 should match"
gitnexus_version_matches "gitnexus 1.6.12" || fail "prefixed 1.6.12 should match"
if gitnexus_version_matches "1.6.120"; then
	fail "1.6.120 must not match 1.6.12"
fi
if gitnexus_version_matches "9.1.6.12"; then
	fail "9.1.6.12 must not match 1.6.12"
fi
pass "version compare is an exact token, not a substring"

echo ""
echo "Test 9: npm install failure fails the snapshot helper"
echo "---"
rm -f "${MOCK_BIN}/gitnexus"
write_mock npm "echo npm-fail >>\"${TEST_DIR}/npm.log\"; exit 1"
hash -r
if PATH="${MOCK_BIN}:/usr/bin:/bin" HOME="${HOME}" \
	ensure_gitnexus >"${TEST_DIR}/t9.out" 2>&1; then
	fail "ensure_gitnexus should fail when npm install fails: $(cat "${TEST_DIR}/t9.out")"
fi
grep -q "npm install failed" "${TEST_DIR}/t9.out" || fail "expected npm-failure log: $(cat "${TEST_DIR}/t9.out")"
pass "npm install failure is fatal"

echo ""
echo "All cursor_cloud_workspace_install tests passed (${PASS})."
