#!/usr/bin/env bash
#
# Unit tests for scripts/proactive-worktree.sh
# Verifies dynamic default branch resolution, collision-proof worktrees,
# disabled push remotes in local mode, PR file-path collision & local/remote
# throttle checks, tamper-evident verify gates against edited build/lock/scripts
# and nested test files, numeric-equivalence enforcement for research repos,
# and 21-day TTL cleanup preserving unmerged candidate commits.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_SCRIPT="${REPO_ROOT}/scripts/proactive-worktree.sh"

TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'test-proactive-wt')"
trap 'rm -rf "$TEST_DIR"' EXIT

export HOME="${TEST_DIR}/home"
MOCK_BIN="${TEST_DIR}/mock_bin"
WT_ROOT="${TEST_DIR}/worktrees"
mkdir -p "${HOME}" "${MOCK_BIN}" "${WT_ROOT}"

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

if [[ ! -x ${TARGET_SCRIPT} ]]; then
	echo "FAIL: target script missing or not executable: ${TARGET_SCRIPT}"
	exit 1
fi

# Set up a bare upstream repo whose default branch is 'trunk' (not 'main')
BARE_REMOTE="${TEST_DIR}/remote.git"
SEED_REPO="${TEST_DIR}/seed"
LOCAL_CLONE="${TEST_DIR}/Seatek_Analysis"

git init --bare -q "${BARE_REMOTE}"
git init -q "${SEED_REPO}"
git -C "${SEED_REPO}" config user.email "test@example.com"
git -C "${SEED_REPO}" config user.name "Test User"
git -C "${SEED_REPO}" checkout -q -b trunk

mkdir -p "${SEED_REPO}/src/pkg/tests" "${SEED_REPO}/tests" "${SEED_REPO}/scripts"
cat >"${SEED_REPO}/Makefile" <<'EOF'
test:
	@echo "ENV_SSH=$(SSH_AUTH_SOCK) ENV_GH=$(GH_TOKEN)" > .verify-env.log
	@bash tests/run_tests.sh
EOF
cat >"${SEED_REPO}/src/module.py" <<'EOF'
def compute(x):
    return x * 2
EOF
cat >"${SEED_REPO}/tests/run_tests.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "${SEED_REPO}/tests/run_tests.sh"

git -C "${SEED_REPO}" add .
git -C "${SEED_REPO}" commit -q -m "initial commit on trunk"
git -C "${SEED_REPO}" remote add origin "${BARE_REMOTE}"
git -C "${SEED_REPO}" push -q -u origin trunk
git --git-dir="${BARE_REMOTE}" symbolic-ref HEAD refs/heads/trunk

git clone -q "${BARE_REMOTE}" "${LOCAL_CLONE}"
git -C "${LOCAL_CLONE}" remote set-head origin -a >/dev/null 2>&1

# 1. Dynamic default branch + collision-proof worktree + push URL disabled
WT1="$("${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens bolt --worktree-root "${WT_ROOT}")"
WT2="$("${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens bolt --worktree-root "${WT_ROOT}")"

check "prepare creates first worktree directory" test -d "${WT1}"
check "prepare creates distinct second worktree on same-day rerun" test "${WT1}" != "${WT2}"
check "prepare disables push remote in local-only mode" test "$(git -C "${WT1}" remote get-url --push origin)" = "DISABLED"

# 1b. Input allowlists and repo-path canonicalization (nothing below creates a worktree)
check_exit "prepare rejects unknown lens (case-sensitive allowlist)" 1 \
	"${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens Palette --worktree-root "${WT_ROOT}"
check_grep "prepare names the rejected lens" "Unknown lens: Palette" "${TEST_DIR}/check.log"
check_exit "prepare rejects unknown mode instead of leaving push URL enabled" 1 \
	"${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens bolt --mode locall --worktree-root "${WT_ROOT}"
check_grep "prepare names the rejected mode" "Unknown mode: locall" "${TEST_DIR}/check.log"
check_exit "prepare blocks palette lens on research repo given an absolute path" 3 \
	"${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens palette --worktree-root "${WT_ROOT}"
cd "${LOCAL_CLONE}"
check_exit "prepare blocks palette lens on research repo given --repo-path ." 3 \
	"${TARGET_SCRIPT}" prepare --repo-path . --lens palette --worktree-root "${WT_ROOT}"
cd "${REPO_ROOT}"

# 2. Tamper-evident verify blocks modified build/lock/scripts and nested test files
echo "	@echo PWNED" >>"${WT1}/Makefile"
check_exit "verify blocks modified Makefile with exit 2" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens code-health
check_grep "verify reports protected file name" "Makefile" "${TEST_DIR}/check.log"
git -C "${WT1}" checkout -q -- Makefile

echo "lock-tamper" >"${WT1}/uv.lock"
check_exit "verify blocks untracked uv.lock with exit 2" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens code-health
rm -f "${WT1}/uv.lock"

echo "pytest==0.0.0" >"${WT1}/requirements-dev.txt"
check_exit "verify blocks requirements-dev.txt with exit 2" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens code-health
rm -f "${WT1}/requirements-dev.txt"

mkdir -p "${WT1}/scripts" "${WT1}/src/pkg/tests"
echo "echo tamper" >"${WT1}/scripts/helper.sh"
check_exit "verify blocks lowercase scripts/* path with exit 2" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens code-health
rm -rf "${WT1}/scripts"

mkdir -p "${WT1}/src/subpkg/scripts"
echo "echo tamper" >"${WT1}/src/subpkg/scripts/run.sh"
check_exit "verify blocks nested */scripts/* path with exit 2" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens code-health
rm -rf "${WT1}/src/subpkg/scripts"

echo "import setuptools" >"${WT1}/src/subpkg/setup.py"
check_exit "verify blocks nested */setup.py path with exit 2" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens code-health
rm -rf "${WT1}/src/subpkg"

echo "def test_x(): pass" >"${WT1}/src/pkg/tests/test_nested.py"
check_exit "verify blocks nested */tests/* path with exit 2" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens code-health
rm -rf "${WT1}/src/pkg"

echo "echo PWNED" >>"${WT1}/tests/run_tests.sh"
check_exit "verify blocks modified test file by default with exit 2" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens code-health
git -C "${WT1}" checkout -q -- tests/run_tests.sh

# A new .gitignore could hide later files from the untracked scan, so it is protected
printf 'tests/new_*\n' >"${WT1}/.gitignore"
check_exit "verify blocks new .gitignore with exit 2" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens code-health
check_grep "verify reports .gitignore as the protected file" "\.gitignore" "${TEST_DIR}/check.log"
rm -f "${WT1}/.gitignore"

# 3. Verify strips ambient credentials and passes on clean production edit
cat >"${WT1}/src/module.py" <<'EOF'
def compute(x):
    return x + x
EOF
# WT1 was prepared with the bolt lens on a research repo, so a --lens override must
# not be able to skip the numeric-equivalence gate that bolt requires.
check_exit "verify rejects --lens override that would skip the research-repo Bolt gate" 3 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens code-health --test-cmd "make test"
check_grep "verify explains the Bolt numeric gate" "requires --numeric-check-cmd" "${TEST_DIR}/check.log"

# The clean-edit and credential-stripping checks use a worktree prepared for code-health
WT_CH="$("${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens code-health --worktree-root "${WT_ROOT}")"
cp "${WT1}/src/module.py" "${WT_CH}/src/module.py"
SSH_AUTH_SOCK="/tmp/fake.sock" GH_TOKEN="secret_tok" check_exit \
	"verify runs cleanly on production source edit" 0 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_CH}" --lens code-health --test-cmd "make test"
check_grep "verify strips SSH_AUTH_SOCK and GH_TOKEN" "^ENV_SSH= ENV_GH=$" "${WT_CH}/.verify-env.log"
rm -f "${WT_CH}/.verify-env.log"
git -C "${WT_CH}" checkout -q -- src/module.py

# Verification must propagate failures and keep the two edit permissions independent.
check_exit "verify propagates failing test command" 7 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_CH}" --test-cmd "exit 7"
check_exit "verify propagates failing numeric check" 8 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_CH}" --test-cmd "true" --numeric-check-cmd "exit 8"
echo "tamper" >"${WT_CH}/package.json"
echo "test change" >>"${WT_CH}/tests/run_tests.sh"
check_exit "allow-test-edits does not permit harness changes" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_CH}" --allow-test-edits --test-cmd "true"
rm -f "${WT_CH}/package.json"
check_exit "allow-harness-changes does not permit test edits" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_CH}" --allow-harness-changes --test-cmd "true"
check_exit "explicit test-edit permission permits the test change" 0 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_CH}" --allow-test-edits --test-cmd "true"
git -C "${WT_CH}" checkout -q -- tests/run_tests.sh

# A rename still changes the protected source path, even if the destination is safe.
git -C "${WT_CH}" mv tests/run_tests.sh src/moved.sh
check_exit "verify detects a renamed protected test" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_CH}" --test-cmd "true"
git -C "${WT_CH}" reset -q HEAD -- tests/run_tests.sh src/moved.sh
rm -f "${WT_CH}/src/moved.sh"
git -C "${WT_CH}" checkout -q -- tests/run_tests.sh

# 4. Research repo Bolt pass requires explicit numeric-equivalence check
check_exit "verify blocks research-repo bolt pass without numeric gate" 3 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens bolt --test-cmd "make test"
check_exit "verify allows research-repo bolt pass when numeric gate passes" 0 \
	"${TARGET_SCRIPT}" verify --worktree "${WT1}" --lens bolt --test-cmd "make test" \
	--numeric-check-cmd "python3 -c 'import math; assert math.isclose(4.0, 4.0, rel_tol=1e-10, abs_tol=1e-12)'"
rm -f "${WT1}/.verify-env.log"
git -C "${WT1}" checkout -q -- src/module.py

# 5. Mock gh CLI to test file-path PR collision & remote/local throttle
cat >"${MOCK_BIN}/gh" <<'MOCK'
#!/usr/bin/env bash
if [[ "$*" == *"pr list"* ]] && [[ "$*" == *"files"* ]]; then
	cat <<'JSON'
[
  {
    "number": 42,
    "title": "⚡bolt: speed up sync",
    "isDraft": true,
    "createdAt": "2026-10-30T10:00:00Z",
    "files": [
      {"path": "src/module.py"},
      {"path": ".jules/sentinel.md"},
      {"path": ".github/workflows/ci.yml"}
    ]
  }
]
JSON
	exit 0
fi
echo "[]"
exit 0
MOCK
chmod +x "${MOCK_BIN}/gh"

PATH="${MOCK_BIN}:${PATH}" check_exit "check-collisions detects overlapping PR file path" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/module.py"
PATH="${MOCK_BIN}:${PATH}" check_exit "check-collisions detects overlapping PR file with leading ./" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "./src/module.py"
PATH="${MOCK_BIN}:${PATH}" check_exit "check-collisions detects collision on .jules/sentinel.md with leading ./" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "./.jules/sentinel.md"
PATH="${MOCK_BIN}:${PATH}" check_exit "check-collisions detects collision on .github/ workflow path" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "./.github/workflows/ci.yml"
PATH="${MOCK_BIN}:${PATH}" check_exit "check-collisions allows non-overlapping file path" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/other.py"
PATH="${MOCK_BIN}:${PATH}" check_exit "check-collisions allows non-overlapping hidden path" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "./.jules/bolt.md"

# 5a. A PR whose files list is truncated (changedFiles > files) must fail closed
MOCK_BIN_TRUNC="${TEST_DIR}/mock_bin_trunc"
mkdir -p "${MOCK_BIN_TRUNC}"
cat >"${MOCK_BIN_TRUNC}/gh" <<'MOCK'
#!/usr/bin/env bash
if [[ "$*" == *"pr list"* ]] && [[ "$*" == *"changedFiles"* ]]; then
	cat <<'JSON'
[
  {
    "number": 43,
    "title": "large refactor",
    "isDraft": false,
    "createdAt": "2026-10-30T10:00:00Z",
    "changedFiles": 150,
    "files": [{"path": "src/unrelated.py"}]
  }
]
JSON
	exit 0
fi
echo "[]"
exit 0
MOCK
chmod +x "${MOCK_BIN_TRUNC}/gh"
PATH="${MOCK_BIN_TRUNC}:${PATH}" check_exit "check-collisions fails closed when a PR files list is truncated" 5 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/other.py"
check_grep "check-collisions reports the truncated PR" "lists 1 of 150 changed files" "${TEST_DIR}/check.log"

# 5b. Local 2B candidate worktree throttle (>= 2 local unmerged candidates blocks even with 0 GitHub PRs)
WT_CAND1="$("${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens code-health --worktree-root "${WT_ROOT}")"
WT_CAND2="$("${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens bolt --worktree-root "${WT_ROOT}")"
git -C "${WT_CAND1}" config user.email "test@example.com"
git -C "${WT_CAND1}" config user.name "Test User"
git -C "${WT_CAND2}" config user.email "test@example.com"
git -C "${WT_CAND2}" config user.name "Test User"
echo "# opt1" >>"${WT_CAND1}/src/module.py"
git -C "${WT_CAND1}" commit -am "chore(qa): candidate 1" -q
echo "# opt2" >>"${WT_CAND2}/src/module.py"
git -C "${WT_CAND2}" commit -am "⚡bolt: candidate 2" -q

PATH="${MOCK_BIN}:${PATH}" check_exit "check-throttle blocks when >=2 local unreviewed worktree candidates exist (2B)" 5 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/Seatek_Analysis --worktree-root "${WT_ROOT}"

# Remove WT_CAND2 so only 1 local candidate remains (WT_CAND1 kept for TTL test below)
git -C "${LOCAL_CLONE}" worktree remove --force "${WT_CAND2}"

cat >"${MOCK_BIN}/gh" <<'MOCK'
#!/usr/bin/env bash
cat <<'JSON'
[
  {"number": 10, "title": "⚡bolt: opt 1", "isDraft": true, "createdAt": "2026-10-30T10:00:00Z", "files": []},
  {"number": 11, "title": "🎨palette: opt 2", "isDraft": true, "createdAt": "2026-10-30T12:00:00Z", "files": []}
]
JSON
MOCK
chmod +x "${MOCK_BIN}/gh"

PATH="${MOCK_BIN}:${PATH}" check_exit "check-throttle blocks when >=2 proactive drafts open" 5 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${WT_ROOT}" --now-epoch 1793448000

cat >"${MOCK_BIN}/gh" <<'MOCK'
#!/usr/bin/env bash
cat <<'JSON'
[
  {"number": 10, "title": "chore(qa): dead code", "isDraft": true, "createdAt": "2026-10-01T10:00:00Z", "files": []}
]
JSON
MOCK
chmod +x "${MOCK_BIN}/gh"

PATH="${MOCK_BIN}:${PATH}" check_exit "check-throttle blocks when unreviewed draft is >7 days old" 5 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${WT_ROOT}" --now-epoch 1793448000

# 6. TTL cleanup (default 21d) prunes stale empty worktrees, preserves dirty, unmerged-commit, and fresh worktrees
echo "uncommitted" >"${WT2}/dirty.txt"
# Backdate WT1 (clean, 0 commits ahead), WT2 (dirty), and WT_CAND1 (clean working tree, 1 unmerged commit ahead!)
touch -t 202001010000 "${WT1}" "${WT2}" "${WT_CAND1}"
WT3="$("${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens sentinel --worktree-root "${WT_ROOT}")"

check_exit "cleanup runs with default 21-day TTL" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${WT_ROOT}"
check "cleanup removed stale empty worktree WT1" test ! -d "${WT1}"
check "cleanup preserved stale dirty worktree WT2" test -d "${WT2}"
check "cleanup preserved stale worktree WT_CAND1 with unmerged commit" test -d "${WT_CAND1}"
check "cleanup preserved fresh worktree WT3" test -d "${WT3}"

echo ""
echo "Summary: PASS=${PASS} FAIL=${FAIL}"
[[ ${FAIL} -eq 0 ]]
