#!/usr/bin/env bash
# Unit tests for GitNexus bootstrap in scripts/cursor_cloud_workspace_install.sh.
# Mocks: npm, gitnexus, and the image-pinned Node executable.
set -euo pipefail

echo "=========================================="
echo "Testing cursor_cloud_workspace_install.sh"
echo "=========================================="

TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'cursor-cloud-install-test')"
export TEST_DIR
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/cursor_cloud_workspace_install.sh"
DOCKERFILE="${REPO_ROOT}/.cursor/Dockerfile"

cleanup() {
	rm -rf "${TEST_DIR}"
}
trap cleanup EXIT

fail() {
	echo "FAIL: $*" >&2
	exit 1
}

PASS=0
pass() {
	echo "PASS: $*"
	PASS=$((PASS + 1))
}

assert_grep() {
	local pattern="$1" file="$2" message="$3"
	grep -Eq -- "${pattern}" "${file}" || fail "${message}: $(cat "${file}" 2>/dev/null || true)"
}

assert_not_grep() {
	local pattern="$1" file="$2" message="$3"
	if grep -Eq -- "${pattern}" "${file}" 2>/dev/null; then
		fail "${message}: $(cat "${file}")"
	fi
}

write_mock() {
	local name="$1"
	local body="$2"
	printf '%s\n' '#!/usr/bin/env bash' 'set -euo pipefail' "${body}" >"${MOCK_BIN}/${name}"
	chmod +x "${MOCK_BIN}/${name}"
}

make_git_repo() {
	local repo="$1"
	mkdir -p "${repo}"
	git -C "${repo}" init -q
}

[[ -x ${SCRIPT} ]] || fail "script missing or not executable"
[[ -f ${DOCKERFILE} ]] || fail "Cursor Cloud Dockerfile missing"

HOME="${TEST_DIR}/home"
export HOME
MOCK_BIN="${TEST_DIR}/mock-bin"
mkdir -p "${HOME}/.local/bin" "${MOCK_BIN}"

# The production path is intentionally absolute. Patch only the disposable copy
# so wrapper behavior can be exercised without touching /usr/local/bin.
TEST_SCRIPT="${TEST_DIR}/cursor_cloud_workspace_install.sh"
# Replacement text must stay literal: GITNEXUS_TEST_NODE_BIN expands at
# runtime when the patched copy is sourced, not during this sed.
# shellcheck disable=SC2016
sed 's|local node_bin="/usr/local/bin/node"|local node_bin="${GITNEXUS_TEST_NODE_BIN:-/usr/local/bin/node}"|' \
	"${SCRIPT}" >"${TEST_SCRIPT}"
# shellcheck source=scripts/cursor_cloud_workspace_install.sh
source "${TEST_SCRIPT}"
GITNEXUS_TEST_NODE_BIN="${MOCK_BIN}/node"
export GITNEXUS_TEST_NODE_BIN

echo ""
echo "Test 1: version matching accepts decorated pinned output"
echo "---"
gitnexus_version_matches 'GitNexus CLI v1.6.12' || fail "decorated pinned version should match"
gitnexus_version_matches '1.6.12' || fail "plain pinned version should match"
pass "pinned version output is recognized"

echo ""
echo "Test 2: version matching rejects empty, wrong, and substring output"
echo "---"
for reported in '' 'GitNexus unknown' '1.6.11' '1.6.120' '9.1.6.12'; do
	if gitnexus_version_matches "${reported}"; then
		fail "unexpected version match for '${reported}'"
	fi
done
pass "invalid versions are rejected exactly"

echo ""
echo "Test 3: a matching CLI skips npm"
echo "---"
rm -f "${HOME}/.local/bin/gitnexus"
write_mock gitnexus 'printf "%s\n" "GitNexus 1.6.12"'
write_mock npm "printf '%s\n' called >>'${TEST_DIR}/npm-unexpected.log'"
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" ensure_gitnexus >"${TEST_DIR}/t3.out" 2>&1 ||
	fail "matching CLI should satisfy ensure_gitnexus: $(cat "${TEST_DIR}/t3.out")"
assert_grep 'gitnexus 1\.6\.12 already present' "${TEST_DIR}/t3.out" "missing already-present log"
[[ ! -e ${TEST_DIR}/npm-unexpected.log ]] || fail "npm should not run for an already matching CLI"
pass "matching CLI short-circuits installation"

echo ""
echo "Test 4: missing npm is a non-fatal skip"
echo "---"
rm -f "${HOME}/.local/bin/gitnexus" "${MOCK_BIN}/gitnexus" "${MOCK_BIN}/npm"
NO_NPM_BIN="${TEST_DIR}/no-npm-bin"
mkdir -p "${NO_NPM_BIN}"
for cmd in date mkdir dirname grep head printf cat rm chmod ln bash; do
	cp_path="$(command -v "${cmd}" || true)"
	if [[ -n ${cp_path} ]]; then
		ln -sf "${cp_path}" "${NO_NPM_BIN}/${cmd}"
	fi
done
hash -r
PATH="${MOCK_BIN}:${NO_NPM_BIN}" ensure_gitnexus >"${TEST_DIR}/t4.out" 2>&1 ||
	fail "missing npm should skip GitNexus installation"
assert_grep 'skip gitnexus \(npm not on PATH' "${TEST_DIR}/t4.out" "missing npm skip log"
pass "workspace setup tolerates images without npm"

echo ""
echo "Test 5: npm installation is exact-versioned and HOME-scoped"
echo "---"
write_mock npm "printf '%s\\n' \"\$*\" >>'${TEST_DIR}/npm-install.log'
printf '%s\\n' '#!/usr/bin/env bash' 'printf \"%s\\n\" \"GitNexus 1.6.12\"' >'${HOME}/.local/bin/gitnexus'
chmod +x '${HOME}/.local/bin/gitnexus'"
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" ensure_gitnexus >"${TEST_DIR}/t5.out" 2>&1 ||
	fail "pinned install path failed: $(cat "${TEST_DIR}/t5.out")"
assert_grep 'install --global --prefix .*/home/\.local gitnexus@1\.6\.12' "${TEST_DIR}/npm-install.log" \
	"npm command did not pin GitNexus under HOME"
pass "npm install uses the pinned version and user prefix"

echo ""
echo "Test 6: a mismatched CLI is replaced with the pinned version"
echo "---"
rm -f "${HOME}/.local/bin/gitnexus"
write_mock gitnexus 'printf "%s\n" "GitNexus 9.9.9"'
: >"${TEST_DIR}/npm-install.log"
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" ensure_gitnexus >"${TEST_DIR}/t6.out" 2>&1 ||
	fail "mismatch reinstall path failed: $(cat "${TEST_DIR}/t6.out")"
assert_grep "present but version 'GitNexus 9\.9\.9' != 1\.6\.12; reinstalling" "${TEST_DIR}/t6.out" \
	"missing mismatch log"
assert_grep 'gitnexus@1\.6\.12' "${TEST_DIR}/npm-install.log" "mismatch did not trigger pinned npm install"
pass "mismatched CLI triggers reinstall"

echo ""
echo "Test 7: npm install failure is fatal"
echo "---"
rm -f "${HOME}/.local/bin/gitnexus" "${MOCK_BIN}/gitnexus"
write_mock npm 'exit 23'
hash -r
actual=0
PATH="${MOCK_BIN}:/usr/bin:/bin" ensure_gitnexus >"${TEST_DIR}/t7.out" 2>&1 || actual=$?
[[ ${actual} -eq 1 ]] || fail "npm failure should make ensure_gitnexus exit 1, got ${actual}"
assert_grep 'gitnexus npm install failed' "${TEST_DIR}/t7.out" "missing npm failure log"
pass "failed install cannot be mistaken for success"

echo ""
echo "Test 8: successful npm without an executable fails post-install verification"
echo "---"
write_mock npm 'exit 0'
hash -r
actual=0
PATH="${MOCK_BIN}:/usr/bin:/bin" ensure_gitnexus >"${TEST_DIR}/t8.out" 2>&1 || actual=$?
[[ ${actual} -eq 1 ]] || fail "missing installed executable should exit 1, got ${actual}"
assert_grep 'gitnexus installed but not on PATH' "${TEST_DIR}/t8.out" "missing post-install PATH failure"
pass "post-install executable presence is verified"

echo ""
echo "Test 9: a wrong post-install version fails verification"
echo "---"
write_mock npm "printf '%s\\n' '#!/usr/bin/env bash' 'printf \"%s\\n\" \"GitNexus 1.6.11\"' >'${HOME}/.local/bin/gitnexus'
chmod +x '${HOME}/.local/bin/gitnexus'"
hash -r
actual=0
PATH="${MOCK_BIN}:/usr/bin:/bin" ensure_gitnexus >"${TEST_DIR}/t9.out" 2>&1 || actual=$?
[[ ${actual} -eq 1 ]] || fail "wrong installed version should exit 1, got ${actual}"
assert_grep "version 'GitNexus 1\.6\.11' does not match 1\.6\.12" "${TEST_DIR}/t9.out" \
	"missing wrong-version failure"
pass "post-install version is verified exactly"

echo ""
echo "Test 10: image-Node wrapper preserves every CLI argument"
echo "---"
gitnexus_js="${HOME}/.local/lib/node_modules/gitnexus/dist/cli/index.js"
mkdir -p "$(dirname "${gitnexus_js}")"
printf '%s\n' '// test fixture' >"${gitnexus_js}"
write_mock node "printf 'argc=%s\\n' \"\$#\" >'${TEST_DIR}/node-args.log'
printf 'arg=%s\\n' \"\$@\" >>'${TEST_DIR}/node-args.log'"
rm -f "${HOME}/.local/bin/gitnexus"
gitnexus_wrap_with_image_node || fail "wrapper creation failed"
[[ -x ${HOME}/.local/bin/gitnexus ]] || fail "wrapper was not executable"
"${HOME}/.local/bin/gitnexus" alpha 'two words'
grep -qxF 'argc=3' "${TEST_DIR}/node-args.log" || fail "wrapper changed the argument count"
grep -qxF "arg=${gitnexus_js}" "${TEST_DIR}/node-args.log" || fail "wrapper omitted the CLI entrypoint"
grep -qxF 'arg=alpha' "${TEST_DIR}/node-args.log" || fail "wrapper omitted the first argument"
grep -qxF 'arg=two words' "${TEST_DIR}/node-args.log" || fail "wrapper split a spaced argument"
pass "wrapper forces image Node and preserves arguments"

echo ""
echo "Test 10b: wrapper replaces an npm symlink without clobbering the CLI JS"
echo "---"
# Reproduce npm global layout: bin/gitnexus -> ../lib/node_modules/gitnexus/dist/cli/index.js
rm -f "${HOME}/.local/bin/gitnexus"
printf '%s\n' '#!/usr/bin/env node' '// npm-installed CLI fixture' >"${gitnexus_js}"
ln -s "${gitnexus_js}" "${HOME}/.local/bin/gitnexus"
[[ -L "${HOME}/.local/bin/gitnexus" ]] || fail "test setup did not create an npm-style symlink"
gitnexus_wrap_with_image_node || fail "wrapper should succeed when dest is a symlink"
[[ ! -L "${HOME}/.local/bin/gitnexus" ]] || fail "wrapper left a symlink in place"
[[ -x "${HOME}/.local/bin/gitnexus" ]] || fail "wrapper was not a regular executable"
head -n1 "${gitnexus_js}" | grep -Eq 'node' || fail "wrapper clobbered the CLI entrypoint through the symlink"
grep -qF "exec ${MOCK_BIN}/node ${gitnexus_js} \"\$@\"" "${HOME}/.local/bin/gitnexus" ||
	fail "wrapper body does not exec image Node against the intact CLI"
pass "npm symlink destinations are replaced safely"

echo ""
echo "Test 10c: wrapper source safely quotes special-character paths"
echo "---"
special_home="${TEST_DIR}/home with space'quote\$dollar"
special_node_name="node with space'quote\$dollar"
special_node="${MOCK_BIN}/${special_node_name}"
special_js="${special_home}/.local/lib/node_modules/gitnexus/dist/cli/index.js"
mkdir -p "$(dirname "${special_js}")" "${special_home}/.local/bin"
printf '%s\n' '// test fixture' >"${special_js}"
write_mock "${special_node_name}" "printf 'arg=%s\\n' \"\$@\" >'${TEST_DIR}/special-node-args.log'"
HOME="${special_home}" GITNEXUS_TEST_NODE_BIN="${special_node}" gitnexus_wrap_with_image_node ||
	fail "wrapper creation should support special-character paths"
special_wrapper="${special_home}/.local/bin/gitnexus"
bash -n "${special_wrapper}" || fail "wrapper with special-character paths is not valid shell source"
"${special_wrapper}" 'forwarded;argument'
grep -qxF "arg=${special_js}" "${TEST_DIR}/special-node-args.log" ||
	fail "wrapper changed the special-character CLI path"
grep -qxF 'arg=forwarded;argument' "${TEST_DIR}/special-node-args.log" ||
	fail "wrapper did not preserve forwarded arguments with special characters"
pass "wrapper safely quotes Node and CLI paths"

echo ""
echo "Test 11: wrapper is a no-op when either prerequisite is absent"
echo "---"
rm -f "${HOME}/.local/bin/gitnexus" "${gitnexus_js}"
gitnexus_wrap_with_image_node || fail "missing JS entrypoint should be non-fatal"
[[ ! -e ${HOME}/.local/bin/gitnexus ]] || fail "wrapper was created without the CLI entrypoint"
printf '%s\n' '// test fixture' >"${gitnexus_js}"
rm -f "${MOCK_BIN}/node"
gitnexus_wrap_with_image_node || fail "missing image Node should be non-fatal"
[[ ! -e ${HOME}/.local/bin/gitnexus ]] || fail "wrapper was created without image Node"
pass "wrapper requires both Node and the installed CLI"

echo ""
echo "Test 12: indexing gracefully skips when the CLI is unavailable"
echo "---"
rm -f "${HOME}/.local/bin/gitnexus" "${MOCK_BIN}/gitnexus"
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" index_gitnexus_repos >"${TEST_DIR}/t12.out" 2>&1 ||
	fail "indexing without a CLI should be a non-fatal skip"
assert_grep 'skip gitnexus index \(cli missing\)' "${TEST_DIR}/t12.out" "missing CLI skip log"
pass "indexing is optional when called independently"

echo ""
echo "Test 13: index uses safe flags, runs inside each repo, and skips the Swift tree"
echo "---"
REPOS_ROOT="${TEST_DIR}/repos-success"
make_git_repo "${REPOS_ROOT}/personal-config"
make_git_repo "${REPOS_ROOT}/ctrld-sync"
make_git_repo "${REPOS_ROOT}/repoprompt-ce"
write_mock gitnexus "printf '%s|%s\\n' \"\${PWD}\" \"\$*\" >>'${TEST_DIR}/gitnexus-success.log'"
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" REPOS_ROOT="${REPOS_ROOT}" \
	index_gitnexus_repos >"${TEST_DIR}/t13.out" 2>&1 || fail "indexing valid repos failed"
assert_grep "${REPOS_ROOT}/personal-config\|analyze --index-only --skip-fts" \
	"${TEST_DIR}/gitnexus-success.log" "personal-config was not analyzed in its own directory"
assert_grep "${REPOS_ROOT}/ctrld-sync\|analyze --index-only --skip-fts" \
	"${TEST_DIR}/gitnexus-success.log" "ctrld-sync was not analyzed in its own directory"
count="$(grep -cF '|analyze --index-only --skip-fts' "${TEST_DIR}/gitnexus-success.log" || true)"
[[ ${count} -eq 2 ]] || fail "expected exactly two analyze calls, got ${count}"
assert_not_grep 'repoprompt-ce\|analyze' "${TEST_DIR}/gitnexus-success.log" \
	"repoprompt-ce must not be analyzed on the Linux cloud worker"
assert_grep 'skip repoprompt-ce \(OOM on Linux cloud VMs; HOLD_PLATFORM\)' "${TEST_DIR}/t13.out" \
	"missing repoprompt-ce HOLD_PLATFORM log"
pass "index command is scoped and the OOM-prone repo is skipped"

echo ""
echo "Test 14: repository exclusions preserve existing entries and are idempotent"
echo "---"
exclude_file="${REPOS_ROOT}/personal-config/.git/info/exclude"
printf '%s\n' 'existing-cache/' >"${exclude_file}"
exclude_gitnexus_index "${REPOS_ROOT}/personal-config" || fail "first exclusion update failed"
exclude_gitnexus_index "${REPOS_ROOT}/personal-config" || fail "second exclusion update failed"
grep -qxF 'existing-cache/' "${exclude_file}" || fail "existing exclusion was not preserved"
hits="$(grep -cFx '.gitnexus/' "${exclude_file}")"
[[ ${hits} -eq 1 ]] || fail "expected one .gitnexus/ exclusion, got ${hits}"
non_git_repo="${TEST_DIR}/not-a-git-repo"
mkdir -p "${non_git_repo}"
exclude_gitnexus_index "${non_git_repo}" || fail "non-Git directory should be ignored"
[[ ! -e ${non_git_repo}/.git ]] || fail "exclusion helper created Git metadata unexpectedly"
pass "Git exclusion update is additive, repeatable, and Git-only"

echo ""
echo "Test 15: an analyze failure is non-fatal and later repos are still indexed"
echo "---"
REPOS_ROOT="${TEST_DIR}/repos-analyze-failure"
make_git_repo "${REPOS_ROOT}/personal-config"
make_git_repo "${REPOS_ROOT}/ctrld-sync"
write_mock gitnexus "printf '%s|%s\\n' \"\${PWD}\" \"\$*\" >>'${TEST_DIR}/gitnexus-failure.log'
[[ \"\${PWD}\" != '${REPOS_ROOT}/personal-config' ]]"
hash -r
PATH="${MOCK_BIN}:/usr/bin:/bin" REPOS_ROOT="${REPOS_ROOT}" \
	index_gitnexus_repos >"${TEST_DIR}/t15.out" 2>&1 || fail "analyze failures should be non-fatal"
assert_grep 'analyze failed for personal-config \(non-fatal\)' "${TEST_DIR}/t15.out" \
	"failed analysis was not logged"
assert_grep "${REPOS_ROOT}/ctrld-sync\|analyze --index-only --skip-fts" \
	"${TEST_DIR}/gitnexus-failure.log" "indexing did not continue after an earlier failure"
pass "one repository cannot block indexing the rest"

echo ""
echo "Test 16: an exclusion failure skips only the affected repository"
echo "---"
REPOS_ROOT="${TEST_DIR}/repos-exclude-failure"
make_git_repo "${REPOS_ROOT}/personal-config"
make_git_repo "${REPOS_ROOT}/ctrld-sync"
write_mock gitnexus "printf '%s|%s\\n' \"\${PWD}\" \"\$*\" >>'${TEST_DIR}/gitnexus-exclude.log'"
hash -r
(
	exclude_gitnexus_index() {
		[[ $1 != "${REPOS_ROOT}/personal-config" ]]
	}
	PATH="${MOCK_BIN}:/usr/bin:/bin" REPOS_ROOT="${REPOS_ROOT}" \
		index_gitnexus_repos >"${TEST_DIR}/t16.out" 2>&1
) || fail "exclusion failure should be isolated"
assert_grep 'skip personal-config \(cannot update Git exclusion\)' "${TEST_DIR}/t16.out" \
	"failed exclusion was not logged"
assert_not_grep 'personal-config\|analyze' "${TEST_DIR}/gitnexus-exclude.log" \
	"repo with failed exclusion should not be analyzed"
assert_grep "${REPOS_ROOT}/ctrld-sync\|analyze --index-only --skip-fts" \
	"${TEST_DIR}/gitnexus-exclude.log" "later repo was not analyzed after exclusion failure"
pass "exclusion failure is isolated to one repo"

echo ""
echo "Test 17: logs resolve HOME at call time and persist the timestamped line"
echo "---"
log_home="${TEST_DIR}/log-home"
HOME="${log_home}" log 'test message with spaces' >"${TEST_DIR}/t17.out"
log_file="${log_home}/.local/state/cursor-cloud-workspace-install.log"
assert_grep '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z cursor_cloud_workspace_install: test message with spaces$' \
	"${TEST_DIR}/t17.out" "stdout log does not have the UTC timestamp format"
cmp -s "${TEST_DIR}/t17.out" "${log_file}" || fail "persistent log did not match stdout"
pass "logging honors the active HOME"

echo ""
echo "Test 18: sourcing the production script has no installer side effects"
echo "---"
source_home="${TEST_DIR}/source-home"
mkdir -p "${source_home}"
HOME="${source_home}" bash -c 'source "$1"' _ "${SCRIPT}" >"${TEST_DIR}/t18.out" 2>&1 ||
	fail "production script should be sourceable"
[[ ! -s ${TEST_DIR}/t18.out ]] || fail "sourcing unexpectedly printed output: $(cat "${TEST_DIR}/t18.out")"
[[ ! -e ${source_home}/.local/state/cursor-cloud-workspace-install.log ]] ||
	fail "sourcing unexpectedly created an install log"
pass "source guard prevents main from running"

echo ""
echo "Test 19: image and installer keep the runtime and CLI contracts coupled"
echo "---"
assert_grep 'node_version="22\.18\.0"' "${DOCKERFILE}" "Dockerfile Node pin changed unexpectedly"
assert_grep 'amd64\) node_dist="linux-x64"; node_sha="[0-9a-f]{64}"' "${DOCKERFILE}" \
	"amd64 Node artifact is not SHA-pinned"
assert_grep 'arm64\) node_dist="linux-arm64"; node_sha="[0-9a-f]{64}"' "${DOCKERFILE}" \
	"arm64 Node artifact is not SHA-pinned"
assert_not_grep 'npm install .*gitnexus' "${DOCKERFILE}" \
	"Dockerfile should provide Node while the workspace installer owns user-scoped GitNexus installation"
assert_grep "GITNEXUS_PINNED_VERSION=\"${GITNEXUS_PINNED_VERSION}\"" "${SCRIPT}" \
	"installer pin changed after sourcing"
assert_grep 'local node_bin="/usr/local/bin/node"' "${SCRIPT}" \
	"GitNexus wrapper no longer forces the image Node runtime"
pass "image checksums and installer ownership remain explicit"

echo ""
echo "Test 20: repository-wide ignore covers GitNexus index contents"
echo "---"
git -C "${REPO_ROOT}" check-ignore -q .gitnexus/index.db || fail ".gitnexus contents are not ignored"
pass "GitNexus indexes remain untracked"

echo ""
echo "All cursor_cloud_workspace_install tests passed (${PASS})."
