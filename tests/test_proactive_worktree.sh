#!/usr/bin/env bash
#
# Unit tests for scripts/proactive-worktree.sh
# Verifies dynamic default branch resolution, collision-proof worktrees,
# disabled push remotes in local mode, PR file-path collision & local/remote
# throttle checks, tamper-evident verify gates against edited build/lock/scripts
# and nested test files, the base-relative semantic test-coverage gate (lost
# methods, removed containers, count drops, pinned expectations, static floor),
# the fail-closed undefined-name tier (blocks with no checker installed,
# propagates a real F821 finding),
# fail-closed origin refresh before ref-based throttle verdicts, cross-root
# candidate counting via check-throttle --include-worktrees, file-path collisions
# against live candidate worktrees via check-collisions --include-worktrees
# (including human-worktree and already-merged-candidate exclusion), the
# print-test-cmd mapping the ctl CLI's base-check resolves instead of duplicating,
# numeric-equivalence enforcement for research repos, and 21-day TTL cleanup
# preserving unmerged candidate commits.

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

# Undefined-name checker stand-in. The gate resolves ruff -> `uv run ruff` ->
# pyflakes and FAILS CLOSED when none exist, so every verify path needs a
# deterministic provider regardless of what the host happens to have installed.
# Kept in its own dir rather than MOCK_BIN so it cannot interact with the mock gh
# that later tests add there. Behaviour is driven by an env-pointed flag file so
# one test can make it report a finding.
LINT_BIN="${TEST_DIR}/lint_bin"
mkdir -p "${LINT_BIN}"
cat >"${LINT_BIN}/ruff" <<'MOCK'
#!/usr/bin/env bash
if [[ -n "${RUFF_MOCK_FAIL_FILE:-}" && -f "${RUFF_MOCK_FAIL_FILE}" ]]; then
	echo "src/names.py:2:20: F821 Undefined name \`undefined_helper\`"
	exit 1
fi
exit 0
MOCK
chmod +x "${LINT_BIN}/ruff"
RUFF_FAIL_FLAG="${TEST_DIR}/ruff_reports_finding"
export RUFF_MOCK_FAIL_FILE="${RUFF_FAIL_FLAG}"
export PATH="${LINT_BIN}:${PATH}"
export PROACTIVE_FETCH_BACKOFF_S=0
export PROACTIVE_GH_BACKOFF_S=0

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

# Base Python test file: 3 tests across 2 containers, so the semantic gate has a
# known before-count to compare against.
cat >"${SEED_REPO}/tests/test_module.py" <<'EOF'
import unittest


class TestCompute(unittest.TestCase):
    def test_doubles(self):
        self.assertEqual(2 * 2, 4)

    def test_zero(self):
        self.assertEqual(0 * 2, 0)


class TestHelpers(unittest.TestCase):
    def test_identity(self):
        self.assertTrue(True)
EOF

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

# 4b. Semantic test-coverage gate: base-relative AST diff + test count + static checks.
# A hunk that applies cleanly can still delete coverage as collateral, and losing a
# test does not fail a suite, so the count is compared rather than trusted.
WT_SEM="$("${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens code-health --worktree-root "${WT_ROOT}")"

# (a) Drop one method; the fixture suite stays green, so only this gate can catch it.
python3 - "${WT_SEM}/tests/test_module.py" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
path.write_text(
    text.replace("    def test_zero(self):\n        self.assertEqual(0 * 2, 0)\n\n", ""),
    encoding="utf-8",
)
PY
check_exit "semantic gate blocks a dropped test method even though the suite passes" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_SEM}" --lens code-health --test-cmd "make test" --allow-test-edits
check_grep "semantic gate names the lost test" "LOST tests/test_module.py: lost test TestCompute.test_zero" "${TEST_DIR}/check.log"
check_grep "semantic gate reports before/after counts" "tests_before=3 tests_after=2" "${TEST_DIR}/check.log"

# (b) An intentional reduction is declarable, and a wrong declaration still fails.
check_exit "semantic gate accepts a pinned intentional reduction" 0 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_SEM}" --lens code-health --test-cmd "make test" \
	--allow-test-edits --expected-test-count 2
check_exit "semantic gate rejects a wrong pinned count" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_SEM}" --lens code-health --test-cmd "make test" \
	--allow-test-edits --expected-test-count 3
check_grep "semantic gate explains the count mismatch" "expected-test-count 3 but the worktree has 2 tests" "${TEST_DIR}/check.log"
check_exit "semantic gate rejects a non-integer --expected-test-count" 1 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_SEM}" --lens code-health --expected-test-count many

# (c) Removing a whole container is reported by name.
git -C "${WT_SEM}" checkout -q -- tests/test_module.py
python3 - "${WT_SEM}/tests/test_module.py" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
path.write_text(text[: text.index("class TestHelpers")].rstrip() + "\n", encoding="utf-8")
PY
check_exit "semantic gate blocks a removed test container" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_SEM}" --lens code-health --test-cmd "make test" --allow-test-edits
check_grep "semantic gate names the removed container" "removed test container TestHelpers" "${TEST_DIR}/check.log"

# (d) Purely additive test changes pass and are reported for review.
git -C "${WT_SEM}" checkout -q -- tests/test_module.py
cat >>"${WT_SEM}/tests/test_module.py" <<'EOF'


class TestAdded(unittest.TestCase):
    def test_new_coverage(self):
        self.assertTrue(True)
EOF
check_exit "semantic gate passes an additive test change" 0 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_SEM}" --lens code-health --test-cmd "make test" --allow-test-edits
check_grep "semantic gate reports the added container" "ADDED tests/test_module.py: added test container TestAdded" "${TEST_DIR}/check.log"

# (e) Deleting a test file drops every test it held.
git -C "${WT_SEM}" checkout -q -- tests/test_module.py
rm -f "${WT_SEM}/tests/test_module.py"
check_exit "semantic gate blocks deleting a whole test file" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_SEM}" --lens code-health --test-cmd "make test" --allow-test-edits
check_grep "semantic gate reports the full count drop" "tests_before=3 tests_after=0" "${TEST_DIR}/check.log"
git -C "${WT_SEM}" checkout -q -- tests/test_module.py

# (f) Dependency-free static floor: a touched file that does not parse is blocked
#     even when no test file changed.
cat >"${WT_SEM}/src/broken.py" <<'EOF'
def compute(x)
    return x
EOF
check_exit "static floor blocks a touched file that does not parse" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_SEM}" --lens code-health --test-cmd "make test"
check_grep "static floor names the unparseable file" "SYNTAX: src/broken.py:1: expected ':'" "${TEST_DIR}/check.log"
rm -f "${WT_SEM}/src/broken.py" "${WT_SEM}/.verify-env.log"

# (g) Fail closed when no undefined-name checker is installed. Tier 1 (AST parse)
#     proves a file is syntactically valid, not that its names resolve, so a
#     missing linter must block rather than silently degrade a required gate to
#     the parse floor. ruff is pinned in requirements.txt so a provisioned
#     environment always has one; this asserts the unprovisioned path.
#     uv is deliberately kept off PATH too - it is a valid ruff provider for
#     uv-managed repos, so its presence would take a different branch.
cat >"${WT_SEM}/src/names.py" <<'EOF'
def compute(x):
    return undefined_helper(x)
EOF
NOLINT_BIN="${TEST_DIR}/nolint_bin"
mkdir -p "${NOLINT_BIN}"
for b in bash env git python3 make cat grep sed mktemp dirname pwd rm touch uname tr cut head wc tee ln mkdir date sort awk find xargs basename expr test; do
	if p="$(command -v "${b}" 2>/dev/null)"; then
		ln -sf "${p}" "${NOLINT_BIN}/${b}"
	fi
done
check_exit "static checks fail closed when no undefined-name checker is installed" 2 \
	env PATH="${NOLINT_BIN}" HOME="${HOME}" "${TARGET_SCRIPT}" verify \
	--worktree "${WT_SEM}" --lens code-health --test-cmd "make test"
check_grep "static checks report the missing checker instead of passing" "No undefined-name checker available" "${TEST_DIR}/check.log"
rm -f "${WT_SEM}/src/names.py" "${WT_SEM}/.verify-env.log"

# (h) A real undefined-name finding propagates as a block. Presence of a checker
#     is not the same as consulting its verdict, so assert the exit code is wired
#     through and the finding text reaches the operator.
cat >"${WT_SEM}/src/names.py" <<'EOF'
def compute(x):
    return undefined_helper(x)
EOF
touch "${RUFF_FAIL_FLAG}"
check_exit "static checks block on an undefined-name finding" 2 \
	"${TARGET_SCRIPT}" verify --worktree "${WT_SEM}" --lens code-health --test-cmd "make test"
check_grep "static checks surface the F821 finding" "F821 Undefined name" "${TEST_DIR}/check.log"
rm -f "${RUFF_FAIL_FLAG}" "${WT_SEM}/src/names.py" "${WT_SEM}/.verify-env.log"

# (i) uv-managed static checks pass --frozen iff uv.lock is present (without downgrading lockfiles)
UV_MOCK_BIN="${TEST_DIR}/uv_mock_bin"
mkdir -p "${UV_MOCK_BIN}"
for b in bash env git python3 make cat grep sed mktemp dirname pwd rm touch uname tr cut head wc tee ln mkdir date sort awk find xargs basename expr test; do
	if p="$(command -v "${b}" 2>/dev/null)"; then
		ln -sf "${p}" "${UV_MOCK_BIN}/${b}"
	fi
done
UV_ARGS_LOG="${TEST_DIR}/uv_args.log"
cat >"${UV_MOCK_BIN}/uv" <<MOCK
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"${UV_ARGS_LOG}"
exit 0
MOCK
chmod +x "${UV_MOCK_BIN}/uv"
cat >"${WT_SEM}/src/names.py" <<'EOF'
def compute(x):
    return x + 1
EOF
cat >"${WT_SEM}/pyproject.toml" <<'EOF'
[project]
name = "demo"
version = "0.1.0"
EOF
touch "${WT_SEM}/uv.lock"
: >"${UV_ARGS_LOG}"
check_exit "uv static checks pass --frozen when uv.lock exists" 0 \
	env PATH="${UV_MOCK_BIN}" HOME="${HOME}" "${TARGET_SCRIPT}" verify \
	--worktree "${WT_SEM}" --lens code-health --allow-harness-changes --test-cmd "true"
check_grep "uv static check invocation includes --frozen with uv.lock" "(^| )run --frozen --all-extras ruff check( |$)" "${UV_ARGS_LOG}"
rm -f "${WT_SEM}/uv.lock"
: >"${UV_ARGS_LOG}"
check_exit "uv static checks omit --frozen when uv.lock is absent" 0 \
	env PATH="${UV_MOCK_BIN}" HOME="${HOME}" "${TARGET_SCRIPT}" verify \
	--worktree "${WT_SEM}" --lens code-health --allow-harness-changes --test-cmd "true"
check_grep "uv static checks still invoke uv run ruff without uv.lock" "(^| )run --all-extras ruff check( |$)" "${UV_ARGS_LOG}"
check "uv static check invocation omits --frozen without uv.lock" bash -c "! grep -q -- '--frozen' '${UV_ARGS_LOG}'"
rm -f "${WT_SEM}/src/names.py" "${WT_SEM}/pyproject.toml" "${UV_ARGS_LOG}"

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

# 5c. A ref-based throttle verdict must not be rendered from a stale origin ref.
BROKEN_REMOTE_CLONE="${TEST_DIR}/broken-remote"
git clone -q "${BARE_REMOTE}" "${BROKEN_REMOTE_CLONE}"
git -C "${BROKEN_REMOTE_CLONE}" remote set-url origin "${TEST_DIR}/does-not-exist.git"
WT_BROKEN="$("${TARGET_SCRIPT}" prepare --repo-path "${BROKEN_REMOTE_CLONE}" --lens bolt --worktree-root "${WT_ROOT}")"
PATH="${MOCK_BIN}:${PATH}" check_exit "check-throttle fails closed when origin cannot be fetched" 6 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/broken-remote --worktree-root "${WT_ROOT}" \
	--repo-path "${BROKEN_REMOTE_CLONE}"
check_grep "check-throttle explains the fetch precondition" "git fetch failed" "${TEST_DIR}/check.log"
git -C "${BROKEN_REMOTE_CLONE}" worktree remove --force "${WT_BROKEN}"

# 5d. --include-worktrees closes the gap where a candidate prepared under a
#     different worktree root is invisible to the cap.
MOCK_BIN_EMPTY="${TEST_DIR}/mock_bin_empty"
mkdir -p "${MOCK_BIN_EMPTY}"
cat >"${MOCK_BIN_EMPTY}/gh" <<'MOCK'
#!/usr/bin/env bash
echo "[]"
MOCK
chmod +x "${MOCK_BIN_EMPTY}/gh"

INC_CLONE="${TEST_DIR}/ctrld-sync"
git clone -q "${BARE_REMOTE}" "${INC_CLONE}"
git -C "${INC_CLONE}" remote set-head origin -a >/dev/null 2>&1
ALT_WT_ROOT="${TEST_DIR}/worktrees-alt"
EMPTY_WT_ROOT="${TEST_DIR}/worktrees-empty"
mkdir -p "${ALT_WT_ROOT}" "${EMPTY_WT_ROOT}"

WT_ALT1="$("${TARGET_SCRIPT}" prepare --repo-path "${INC_CLONE}" --lens bolt --worktree-root "${ALT_WT_ROOT}")"
WT_ALT2="$("${TARGET_SCRIPT}" prepare --repo-path "${INC_CLONE}" --lens code-health --worktree-root "${ALT_WT_ROOT}")"
for alt in "${WT_ALT1}" "${WT_ALT2}"; do
	git -C "${alt}" config user.email "test@example.com"
	git -C "${alt}" config user.name "Test User"
	echo "# alt candidate" >>"${alt}/src/module.py"
	git -C "${alt}" commit -am "chore(qa): alt root candidate" -q
done

# A human worktree matches neither proactive metadata nor a proactive/* branch,
# so it must stay out of the candidate count.
git -C "${INC_CLONE}" worktree add -q -b human/scratch "${TEST_DIR}/human-wt" HEAD

PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-throttle misses cross-root candidates without --include-worktrees" 0 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${EMPTY_WT_ROOT}"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-throttle counts cross-root candidates with --include-worktrees" 5 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${EMPTY_WT_ROOT}" \
	--include-worktrees --repo-path "${INC_CLONE}"
check_grep "check-throttle reports the cross-root candidate count" "THROTTLED: 2 unreviewed local candidate worktrees for ctrld-sync" "${TEST_DIR}/check.log"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-throttle does not count a human worktree" 0 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${EMPTY_WT_ROOT}" \
	--include-worktrees --repo-path "${INC_CLONE}" --max-open 3
check_exit "--include-worktrees requires --repo-path" 1 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${EMPTY_WT_ROOT}" \
	--include-worktrees
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "--include-worktrees fails closed when worktrees cannot be enumerated" 6 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${EMPTY_WT_ROOT}" \
	--include-worktrees --repo-path "${TEST_DIR}/not-a-repo"
check_grep "--include-worktrees explains the enumeration failure" "could not enumerate worktrees" "${TEST_DIR}/check.log"

# 5e. G-5: check-collisions must see live candidate worktrees, not only open PRs.
#     In 2B local-first mode there are no bot PRs, so a PR-only gate is a no-op
#     for exactly the collision class that stranded real work (two sessions
#     editing parse_inventory.py in the same burst).
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions is a no-op for a local candidate without --include-worktrees" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/module.py"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions detects a live candidate worktree path" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/module.py" \
	--include-worktrees --repo-path "${INC_CLONE}"
check_grep "check-collisions names the colliding candidate worktree" "live candidate worktree" "${TEST_DIR}/check.log"
check_grep "check-collisions names the colliding path" "already touches src/module.py" "${TEST_DIR}/check.log"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions allows a path no candidate touches" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/unrelated.py" \
	--include-worktrees --repo-path "${INC_CLONE}"

# A human worktree is not a proactive candidate, so its edits must not block a sweep.
echo "human edit" >"${TEST_DIR}/human-wt/human_only.py"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions ignores a human worktree path" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "human_only.py" \
	--include-worktrees --repo-path "${INC_CLONE}"

# A candidate whose work already merged is not a collision: its paths are on the
# base branch now, and counting it would block that file for the whole 21-day TTL.
MERGED_BARE="${TEST_DIR}/merged-remote.git"
git init -q --bare "${MERGED_BARE}"
MERGED_SEED="${TEST_DIR}/merged-seed"
git clone -q "${BARE_REMOTE}" "${MERGED_SEED}"
git -C "${MERGED_SEED}" remote set-url origin "${MERGED_BARE}"
git -C "${MERGED_SEED}" push -q origin HEAD:refs/heads/main
# A freshly init'd bare repo points HEAD at a branch that does not exist yet, so
# set it before any clone tries to resolve origin/HEAD.
git -C "${MERGED_BARE}" symbolic-ref HEAD refs/heads/main
MERGED_CLONE="${TEST_DIR}/merged-clone"
git clone -q "${MERGED_BARE}" "${MERGED_CLONE}"
git -C "${MERGED_CLONE}" remote set-head origin -a >/dev/null 2>&1
WT_MERGED="$("${TARGET_SCRIPT}" prepare --repo-path "${MERGED_CLONE}" --lens code-health --worktree-root "${WT_ROOT}")"
git -C "${WT_MERGED}" config user.email "test@example.com"
git -C "${WT_MERGED}" config user.name "Test User"
echo "merged marker" >"${WT_MERGED}/src/merged_marker.py"
git -C "${WT_MERGED}" add -A
git -C "${WT_MERGED}" commit -q -m "chore(qa): candidate that later merges"
# Push from the clone, not the worktree: prepare sets a worktree-scoped
# pushurl=DISABLED in local mode, which is exactly what should block this.
git -C "${MERGED_CLONE}" push -q origin "$(git -C "${WT_MERGED}" rev-parse HEAD)":refs/heads/main
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions ignores a candidate whose work already merged" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/merged_marker.py" \
	--include-worktrees --repo-path "${MERGED_CLONE}"
check_exit "check-collisions --include-worktrees requires --repo-path" 1 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/module.py" --include-worktrees
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions fails closed when worktrees cannot be enumerated" 6 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/module.py" \
	--include-worktrees --repo-path "${TEST_DIR}/not-a-repo"
check_grep "check-collisions explains the enumeration failure" "could not enumerate worktrees" "${TEST_DIR}/check.log"

# The open-PR half of the gate must still fire now that worktree paths are unioned
# in. MOCK_BIN/gh was rewritten by the throttle cases above, so use a dedicated
# mock that returns a PR whose files overlap the target.
MOCK_BIN_PR="${TEST_DIR}/mock_bin_pr"
mkdir -p "${MOCK_BIN_PR}"
cat >"${MOCK_BIN_PR}/gh" <<'MOCK'
#!/usr/bin/env bash
cat <<'JSON'
[
  {
    "number": 42,
    "title": "⚡bolt: speed up sync",
    "isDraft": true,
    "createdAt": "2026-10-30T10:00:00Z",
    "files": [{"path": "src/module.py"}]
  }
]
JSON
MOCK
chmod +x "${MOCK_BIN_PR}/gh"

PATH="${MOCK_BIN_PR}:${PATH}" check_exit "check-collisions still detects an open PR path with --include-worktrees" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/module.py" \
	--include-worktrees --repo-path "${INC_CLONE}"
check_grep "check-collisions still names the open PR" "Open PR #42" "${TEST_DIR}/check.log"
check_grep "check-collisions reports both the PR and the candidate worktree" "live candidate worktree" "${TEST_DIR}/check.log"

# 5f. print-test-cmd is the single source of truth the ctl CLI's base-check reads,
#     so the repo -> test-command mapping cannot drift from the one verify uses.
PTC_MAPPED="$("${TARGET_SCRIPT}" print-test-cmd --repo-name abhimehro/ctrld-sync)"
check "print-test-cmd strips the owner and prints the mapped compound command" test "${PTC_MAPPED}" = "uv run --frozen --all-extras pytest tests/ test_main.py -q && uv run --frozen --all-extras ruff check ."
PTC_DEFAULT="$("${TARGET_SCRIPT}" print-test-cmd --repo-name some-unmapped-repo)"
check "print-test-cmd falls back to the pytest default for an unmapped repo" test "${PTC_DEFAULT}" = "python3 -m pytest -q"
check_exit "print-test-cmd requires --repo-name" 1 "${TARGET_SCRIPT}" print-test-cmd
check_exit "print-test-cmd rejects an unknown flag" 1 \
	"${TARGET_SCRIPT}" print-test-cmd --repo-name ctrld-sync --nonsense

# 5g. Squash-merged local worktrees (1-commit and multi-commit) must not remain
#     counted as unreviewed candidates in check-throttle, check-collisions, or cleanup.
SQUASH_BARE="${TEST_DIR}/squash-remote.git"
SQUASH_SEED="${TEST_DIR}/squash-seed"
SQUASH_CLONE="${TEST_DIR}/squash-repo"
SQUASH_WT_ROOT="${TEST_DIR}/squash-worktrees"
mkdir -p "${SQUASH_WT_ROOT}"
git init -q --bare "${SQUASH_BARE}"
git clone -q "${BARE_REMOTE}" "${SQUASH_SEED}"
git -C "${SQUASH_SEED}" remote set-url origin "${SQUASH_BARE}"
git -C "${SQUASH_SEED}" push -q origin HEAD:refs/heads/main
git -C "${SQUASH_BARE}" symbolic-ref HEAD refs/heads/main
git clone -q "${SQUASH_BARE}" "${SQUASH_CLONE}"
git -C "${SQUASH_CLONE}" config user.email "test@example.com"
git -C "${SQUASH_CLONE}" config user.name "Test User"
git -C "${SQUASH_CLONE}" remote set-head origin -a >/dev/null 2>&1

WT_SQ1="$("${TARGET_SCRIPT}" prepare --repo-path "${SQUASH_CLONE}" --lens bolt --worktree-root "${SQUASH_WT_ROOT}")"
git -C "${WT_SQ1}" config user.email "test@example.com"
git -C "${WT_SQ1}" config user.name "Test User"
echo "sq1" >"${WT_SQ1}/src/sq1.py"
git -C "${WT_SQ1}" add -A
git -C "${WT_SQ1}" commit -q -m "⚡bolt: single commit candidate"

WT_SQ2="$("${TARGET_SCRIPT}" prepare --repo-path "${SQUASH_CLONE}" --lens code-health --worktree-root "${SQUASH_WT_ROOT}")"
git -C "${WT_SQ2}" config user.email "test@example.com"
git -C "${WT_SQ2}" config user.name "Test User"
echo "sq2-a" >"${WT_SQ2}/src/sq2.py"
git -C "${WT_SQ2}" add -A
git -C "${WT_SQ2}" commit -q -m "chore(qa): multi commit part 1"
echo "sq2-b" >>"${WT_SQ2}/src/sq2.py"
git -C "${WT_SQ2}" add -A
git -C "${WT_SQ2}" commit -q -m "chore(qa): multi commit part 2"

WT_UNMERGED="$("${TARGET_SCRIPT}" prepare --repo-path "${SQUASH_CLONE}" --lens palette --worktree-root "${SQUASH_WT_ROOT}")"
git -C "${WT_UNMERGED}" config user.email "test@example.com"
git -C "${WT_UNMERGED}" config user.name "Test User"
echo "unmerged-1" >"${WT_UNMERGED}/src/unmerged.py"
git -C "${WT_UNMERGED}" add -A
git -C "${WT_UNMERGED}" commit -q -m "🎨palette: unmerged part 1"
echo "unmerged-2" >>"${WT_UNMERGED}/src/unmerged.py"
git -C "${WT_UNMERGED}" add -A
git -C "${WT_UNMERGED}" commit -q -m "🎨palette: unmerged part 2"

# Advance main with an unrelated commit, then squash-merge both WT_SQ1 and WT_SQ2
echo "unrelated main change" >"${SQUASH_CLONE}/src/unrelated_main.py"
git -C "${SQUASH_CLONE}" add -A
git -C "${SQUASH_CLONE}" commit -q -m "docs: unrelated main update"
SQ1_HEAD="$(git -C "${WT_SQ1}" rev-parse HEAD)"
SQ2_HEAD="$(git -C "${WT_SQ2}" rev-parse HEAD)"
git -C "${SQUASH_CLONE}" merge --squash -q "${SQ1_HEAD}"
git -C "${SQUASH_CLONE}" commit -q -m "⚡bolt: single commit candidate (#101)"
git -C "${SQUASH_CLONE}" merge --squash -q "${SQ2_HEAD}"
git -C "${SQUASH_CLONE}" commit -q -m "chore(qa): multi commit (#102)"
git -C "${SQUASH_CLONE}" push -q origin main

PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-throttle excludes 1-commit and multi-commit squash-merged worktrees" 0 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/squash-repo --worktree-root "${SQUASH_WT_ROOT}" \
	--include-worktrees --repo-path "${SQUASH_CLONE}" --max-open 2
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-throttle still counts unmerged candidate alongside squash-merged ones" 5 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/squash-repo --worktree-root "${SQUASH_WT_ROOT}" \
	--include-worktrees --repo-path "${SQUASH_CLONE}" --max-open 1
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions ignores 1-commit squash-merged worktree path" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/squash-repo --file "src/sq1.py" \
	--include-worktrees --repo-path "${SQUASH_CLONE}"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions ignores multi-commit squash-merged worktree path" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/squash-repo --file "src/sq2.py" \
	--include-worktrees --repo-path "${SQUASH_CLONE}"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions still detects unmerged candidate path" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/squash-repo --file "src/unmerged.py" \
	--include-worktrees --repo-path "${SQUASH_CLONE}"

# A candidate with a merged prefix and a new follow-up is still unreviewed.
# This prevents cherry/patch-id matching from accepting a partial merge.
echo "sq1 follow-up" >>"${WT_SQ1}/src/sq1.py"
git -C "${WT_SQ1}" commit -qam "bolt: unmerged follow-up"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "collision retains candidate with only its prefix merged" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/squash-repo --file "src/sq1.py" \
	--include-worktrees --repo-path "${SQUASH_CLONE}"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "throttle counts partially merged candidate" 5 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/squash-repo --worktree-root "${SQUASH_WT_ROOT}" \
	--include-worktrees --repo-path "${SQUASH_CLONE}" --max-open 2
# Restore the fully merged candidate for the lookback & cleanup assertions below.
git -C "${WT_SQ1}" reset -q --hard "${SQ1_HEAD}"

# Unbounded upstream scan stays intact beyond 200 commits, while explicit PROACTIVE_SQUASH_LOOKBACK is honored
python3 - "${SQUASH_CLONE}" <<'PYFAST'
import subprocess, sys
repo = sys.argv[1]
proc = subprocess.Popen(
    ["git", "-C", repo, "fast-import", "--quiet"],
    stdin=subprocess.PIPE,
    text=True,
)
parent = subprocess.check_output(["git", "-C", repo, "rev-parse", "main"], text=True).strip()
lines = []
for i in range(205):
    data = f"noise {i}\n"
    msg = f"docs: noise {i}\n"
    lines.append(f"commit refs/heads/main\nmark :{i+1}\ncommitter T <t@e.com> {1700000000+i} +0000\ndata {len(msg)}\n{msg}")
    if i == 0:
        lines.append(f"from {parent}\n")
    lines.append(f"M 100644 inline src/noise.txt\ndata {len(data)}\n{data}\n")
proc.communicate("".join(lines))
assert proc.returncode == 0
PYFAST
git -C "${SQUASH_CLONE}" reset -q --hard main
git -C "${SQUASH_CLONE}" push -q origin main
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "unbounded scan still detects squash-merged candidate past 200 upstream commits" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/squash-repo --file "src/sq2.py" \
	--include-worktrees --repo-path "${SQUASH_CLONE}"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit \
	"bounded PROACTIVE_SQUASH_LOOKBACK=5 conservatively retains candidate outside lookback window" 4 \
	env PROACTIVE_SQUASH_LOOKBACK=5 "${TARGET_SCRIPT}" check-collisions --repo abhimehro/squash-repo --file "src/sq2.py" \
	--include-worktrees --repo-path "${SQUASH_CLONE}"

MOCK_BIN_NO_VERBATIM="${TEST_DIR}/mock_bin_no_verbatim"
mkdir -p "${MOCK_BIN_NO_VERBATIM}"
REAL_GIT="$(command -v git)"
cat >"${MOCK_BIN_NO_VERBATIM}/git" <<EOF
#!/usr/bin/env bash
if [[ "\${1:-}" == "patch-id" ]]; then
	for arg in "\$@"; do
		if [[ "\${arg}" == "--verbatim" ]]; then
			echo "usage: git patch-id [--stable | --unstable]" >&2
			exit 129
		fi
	done
fi
exec "${REAL_GIT}" "\$@"
EOF
chmod +x "${MOCK_BIN_NO_VERBATIM}/git"
PATH="${MOCK_BIN_NO_VERBATIM}:${MOCK_BIN_EMPTY}:${PATH}" check_exit \
	"check-collisions retains squash-merged candidate when git patch-id --verbatim is unavailable" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/squash-repo --file "src/sq2.py" \
	--include-worktrees --repo-path "${SQUASH_CLONE}"
check_grep "missing git patch-id --verbatim emits warning" "git patch-id --verbatim is unavailable" "${TEST_DIR}/check.log"
check "missing git patch-id --verbatim warns only once per run" \
	python3 -c 'import sys; sys.exit(0 if open(sys.argv[1], encoding="utf-8").read().count("git patch-id --verbatim is unavailable") == 1 else 1)' "${TEST_DIR}/check.log"

touch -t 202001010000 "${WT_SQ1}" "${WT_SQ2}" "${WT_UNMERGED}"
check_exit "cleanup runs on squash-merged worktrees" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${SQUASH_WT_ROOT}"
check "cleanup removed stale 1-commit squash-merged worktree WT_SQ1" test ! -d "${WT_SQ1}"
check "cleanup removed stale multi-commit squash-merged worktree WT_SQ2" test ! -d "${WT_SQ2}"
check "cleanup preserved stale unmerged multi-commit worktree WT_UNMERGED" test -d "${WT_UNMERGED}"

# 5h. Patch equivalence must preserve semantically significant whitespace (e.g., Python indentation/strings).
WS_BARE="${TEST_DIR}/ws-remote.git"
WS_SEED="${TEST_DIR}/ws-seed"
WS_CLONE="${TEST_DIR}/ws-repo"
WS_WT_ROOT="${TEST_DIR}/ws-worktrees"
mkdir -p "${WS_WT_ROOT}"
git init -q --bare "${WS_BARE}"
git init -q "${WS_SEED}"
git -C "${WS_SEED}" config user.email "test@example.com"
git -C "${WS_SEED}" config user.name "Test User"
git -C "${WS_SEED}" checkout -q -b main
mkdir -p "${WS_SEED}/src"
cat >"${WS_SEED}/src/app.py" <<'EOF'
def run(enabled):
    if enabled:
        prepare()
EOF
cat >"${WS_SEED}/src/str_case.py" <<'EOF'
def label():
    return "a b"
EOF
git -C "${WS_SEED}" add -A
git -C "${WS_SEED}" commit -q -m "base"
git -C "${WS_SEED}" remote add origin "${WS_BARE}"
git -C "${WS_SEED}" push -q -u origin main
git -C "${WS_BARE}" symbolic-ref HEAD refs/heads/main
git clone -q "${WS_BARE}" "${WS_CLONE}"
git -C "${WS_CLONE}" config user.email "test@example.com"
git -C "${WS_CLONE}" config user.name "Test User"
git -C "${WS_CLONE}" remote set-head origin -a >/dev/null 2>&1

WT_WS_INDENT="$("${TARGET_SCRIPT}" prepare --repo-path "${WS_CLONE}" --lens bolt --worktree-root "${WS_WT_ROOT}")"
git -C "${WT_WS_INDENT}" config user.email "test@example.com"
git -C "${WT_WS_INDENT}" config user.name "Test User"
cat >"${WT_WS_INDENT}/src/app.py" <<'EOF'
def run(enabled):
    if enabled:
        prepare()
        finish()
EOF
git -C "${WT_WS_INDENT}" commit -qam "⚡bolt: finish inside conditional"

WT_WS_STR="$("${TARGET_SCRIPT}" prepare --repo-path "${WS_CLONE}" --lens palette --worktree-root "${WS_WT_ROOT}")"
git -C "${WT_WS_STR}" config user.email "test@example.com"
git -C "${WT_WS_STR}" config user.name "Test User"
cat >"${WT_WS_STR}/src/str_case.py" <<'EOF'
def label():
    return "ab"
EOF
git -C "${WT_WS_STR}" commit -qam "🎨palette: compact label"

# Upstream commits differ ONLY by indentation (4 spaces outside `if`) and internal string spaces ("a  b")
cat >"${WS_CLONE}/src/app.py" <<'EOF'
def run(enabled):
    if enabled:
        prepare()
    finish()
EOF
git -C "${WS_CLONE}" commit -qam "upstream finish outside conditional"
cat >"${WS_CLONE}/src/str_case.py" <<'EOF'
def label():
    return "a  b"
EOF
git -C "${WS_CLONE}" commit -qam "upstream two spaces"
git -C "${WS_CLONE}" push -q origin main

PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-throttle retains whitespace-divergent Python candidates" 5 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/ws-repo --worktree-root "${WS_WT_ROOT}" \
	--include-worktrees --repo-path "${WS_CLONE}" --max-open 2
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions retains indentation-different Python candidate" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ws-repo --file "src/app.py" \
	--include-worktrees --repo-path "${WS_CLONE}"
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions retains string-whitespace-different Python candidate" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ws-repo --file "src/str_case.py" \
	--include-worktrees --repo-path "${WS_CLONE}"
touch -t 202001010000 "${WT_WS_INDENT}" "${WT_WS_STR}"
check_exit "cleanup runs cleanly on whitespace-divergent candidates" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${WS_WT_ROOT}"
check "cleanup preserved indentation-different candidate WT_WS_INDENT" test -d "${WT_WS_INDENT}"
check "cleanup preserved string-whitespace-different candidate WT_WS_STR" test -d "${WT_WS_STR}"

# 5i. Linear individually cherry-picked multi-commit branch vs merge commit resolution
WT_CHERRY="$("${TARGET_SCRIPT}" prepare --repo-path "${WS_CLONE}" --lens code-health --worktree-root "${WS_WT_ROOT}")"
git -C "${WT_CHERRY}" config user.email "test@example.com"
git -C "${WT_CHERRY}" config user.name "Test User"
echo "c1" >"${WT_CHERRY}/src/cherry_only.py"
git -C "${WT_CHERRY}" add -A
git -C "${WT_CHERRY}" commit -q -m "chore(qa): cherry part 1"
CHERRY_C1="$(git -C "${WT_CHERRY}" rev-parse HEAD)"
echo "c2" >>"${WT_CHERRY}/src/cherry_only.py"
git -C "${WT_CHERRY}" add -A
git -C "${WT_CHERRY}" commit -q -m "chore(qa): cherry part 2"
CHERRY_C2="$(git -C "${WT_CHERRY}" rev-parse HEAD)"
echo "diverge" >"${WS_CLONE}/src/cherry_diverge.py"
git -C "${WS_CLONE}" add -A
git -C "${WS_CLONE}" commit -q -m "docs: diverge main before cherry-pick"
git -C "${WS_CLONE}" cherry-pick "${CHERRY_C1}" "${CHERRY_C2}" >/dev/null
git -C "${WS_CLONE}" push -q origin main
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions excludes individually cherry-picked multi-commit branch" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ws-repo --file "src/cherry_only.py" \
	--include-worktrees --repo-path "${WS_CLONE}"

WT_MERGE="$("${TARGET_SCRIPT}" prepare --repo-path "${WS_CLONE}" --lens code-health --worktree-root "${WS_WT_ROOT}")"
git -C "${WT_MERGE}" config user.email "test@example.com"
git -C "${WT_MERGE}" config user.name "Test User"
echo "merge_c1" >"${WT_MERGE}/src/merge_case.py"
git -C "${WT_MERGE}" add -A
git -C "${WT_MERGE}" commit -q -m "chore(qa): candidate commit A"
MERGE_C1="$(git -C "${WT_MERGE}" rev-parse HEAD)"
git -C "${WS_CLONE}" cherry-pick "${MERGE_C1}" >/dev/null
echo "upstream_override" >"${WS_CLONE}/src/merge_case.py"
git -C "${WS_CLONE}" add -A
git -C "${WS_CLONE}" commit -q -m "upstream override to 2"
git -C "${WS_CLONE}" push -q origin main
git -C "${WT_MERGE}" fetch -q origin
git -C "${WT_MERGE}" merge -q --no-edit -s ours origin/main
echo "candidate_conflict_resolution" >"${WT_MERGE}/src/merge_case.py"
git -C "${WT_MERGE}" add -A
git -C "${WT_MERGE}" commit -q --amend --no-edit
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions retains candidate with merge-commit resolution" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ws-repo --file "src/merge_case.py" \
	--include-worktrees --repo-path "${WS_CLONE}"

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

# 7. Portable bounded timeout helper & GitHub SSH URL detector
run_wt_timeout() {
	(
		source "${TARGET_SCRIPT}"
		run_with_timeout "$@"
	)
}

check_not_grep() {
	local pattern="$1"
	local file="$2"
	if grep -q -- "${pattern}" "${file}" 2>/dev/null; then
		return 1
	fi
	return 0
}

check_ssh_url_expect() {
	local url="$1"
	local expected_rc="$2"
	(
		source "${TARGET_SCRIPT}"
		local rc=0
		is_github_ssh_url "${url}" || rc=$?
		[[ ${rc} -eq ${expected_rc} ]]
	)
}

check_fetch_transport() {
	local force_ssh="$1"
	local repo_dir="$2"
	local expected_transport="$3"
	env PATH="${FETCH_MOCK_BIN}:${PATH}" PROACTIVE_FETCH_FORCE_SSH="${force_ssh}" \
		bash -s "${TARGET_SCRIPT}" "${repo_dir}" "${expected_transport}" <<'EOF'
set -Eeuo pipefail
source "$1"
fetch_origin_resilient "$2"
[[ ${LAST_FETCH_TRANSPORT} == "$3" ]]
EOF
}

run_fetch_exhaust_with_summary() {
	local retries="$1"
	local backoff_s="$2"
	local repo_dir="$3"
	env PATH="${FETCH_MOCK_BIN}:${PATH}" PROACTIVE_FETCH_RETRIES="${retries}" PROACTIVE_FETCH_BACKOFF_S="${backoff_s}" \
		bash -s "${TARGET_SCRIPT}" "${repo_dir}" <<'EOF'
set -Eeuo pipefail
source "$1"
rc=0
fetch_origin_resilient "$2" || rc=$?
printf 'SUMMARY=%s\n' "${FETCH_FAILURE_SUMMARY}" >&2
exit "${rc}"
EOF
}

run_fetch_invalid_knobs() {
	local repo_dir="$1"
	env PATH="${FETCH_MOCK_BIN}:${PATH}" \
		PROACTIVE_FETCH_RETRIES=bogus \
		PROACTIVE_FETCH_BACKOFF_S=-1 \
		PROACTIVE_FETCH_TIMEOUT_S=0 \
		PROACTIVE_FETCH_FORCE_SSH=yes \
		bash -s "${TARGET_SCRIPT}" "${repo_dir}" <<'EOF'
set -Eeuo pipefail
source "$1"
fetch_origin_resilient "$2" >/dev/null
EOF
}

check_sleep_backoff_log() {
	local log_file="$1"
	local expected="$2"
	local head_val=""
	head_val="$(head -n 2 "${log_file}" | tr '\n' ',')"
	[[ ${head_val} == "${expected}" ]]
}

check_git_config_unset() {
	local repo_dir="$1"
	local key="$2"
	local val=""
	val="$(git -C "${repo_dir}" config --get "${key}" 2>/dev/null || true)"
	[[ -z ${val} ]]
}

check_git_ref_absent() {
	local repo_dir="$1"
	local ref_name="$2"
	if git -C "${repo_dir}" show-ref --verify --quiet "${ref_name}"; then
		return 1
	fi
	return 0
}

check_resolve_verify_prefix() {
	local wt_dir="$1"
	local repo_dir="$2"
	local cmd="$3"
	local expected_prefix="$4"
	local expect_match="$5"
	(
		source "${TARGET_SCRIPT}"
		local out=""
		out="$(resolve_verify_path "${wt_dir}" "${repo_dir}" "${cmd}")"
		if [[ ${expect_match} == "yes" ]]; then
			[[ ${out} == "${expected_prefix}"* ]]
		else
			[[ ${out} != "${expected_prefix}"* ]]
		fi
	)
}

check_exit "run_with_timeout passes through exit 0" 0 \
	run_wt_timeout 5 true
check_exit "run_with_timeout propagates child exit code 42" 42 \
	run_wt_timeout 5 bash -c "exit 42"
check_exit "run_with_timeout exits 124 on timeout without leaking args" 124 \
	run_wt_timeout 1 python3 -c "import time; time.sleep(5)" --secret-token-flag
check_grep "run_with_timeout prints cmd[0] on timeout" "Command timed out after 1s: python3" "${TEST_DIR}/check.log"
check "run_with_timeout timeout stderr omits secret args" \
	check_not_grep "--secret-token-flag" "${TEST_DIR}/check.log"
check_exit "run_with_timeout exits 127 when command is missing without leaking args" 127 \
	run_wt_timeout 5 nonexistent_cmd_for_test --secret-flag
check_grep "run_with_timeout reports missing cmd[0]" "Command not found: nonexistent_cmd_for_test" "${TEST_DIR}/check.log"
check "run_with_timeout missing-cmd stderr omits secret args" \
	check_not_grep "--secret-flag" "${TEST_DIR}/check.log"

check "is_github_ssh_url accepts git@github.com:*" \
	check_ssh_url_expect "git@github.com:abhimehro/ctrld-sync.git" 0
check "is_github_ssh_url accepts ssh://git@github.com/*" \
	check_ssh_url_expect "ssh://git@github.com/abhimehro/ctrld-sync.git" 0
check "is_github_ssh_url rejects https://github.com/*" \
	check_ssh_url_expect "https://github.com/abhimehro/ctrld-sync.git" 1
check "is_github_ssh_url rejects non-GitHub SSH URL" \
	check_ssh_url_expect "git@gitlab.com:abhimehro/ctrld-sync.git" 1

# 8. Resilient headless Git fetch transports, fallback, backoff, env validation, & prepare fallback
FETCH_MOCK_BIN="${TEST_DIR}/fetch_mock_bin"
mkdir -p "${FETCH_MOCK_BIN}"
FETCH_LOG="${TEST_DIR}/fetch_git.log"
FETCH_SLEEP_LOG="${TEST_DIR}/fetch_sleep.log"
FETCH_MODE_FILE="${TEST_DIR}/fetch_mode"
REAL_GIT_BIN="$(command -v git)"

cat >"${FETCH_MOCK_BIN}/gh" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK
chmod +x "${FETCH_MOCK_BIN}/gh"

cat >"${FETCH_MOCK_BIN}/sleep" <<MOCK
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"${FETCH_SLEEP_LOG}"
exit 0
MOCK
chmod +x "${FETCH_MOCK_BIN}/sleep"

cat >"${FETCH_MOCK_BIN}/git" <<MOCK
#!/usr/bin/env bash
is_fetch=0
has_gh_helper=0
has_instead_of=0
for arg in "\$@"; do
	case "\${arg}" in
	fetch)
		is_fetch=1
		;;
	*gh\ auth\ git-credential*)
		has_gh_helper=1
		;;
	url.https://github.com/.insteadOf=*)
		has_instead_of=1
		;;
	esac
done
if [[ \${is_fetch} -eq 1 ]]; then
	printf 'TERM=%s SSH=%s ARGS=%s\n' "\${GIT_TERMINAL_PROMPT:-}" "\${GIT_SSH_COMMAND:-}" "\$*" >>"${FETCH_LOG}"
	mode="\$(cat "${FETCH_MODE_FILE}" 2>/dev/null || echo "ok")"
	case "\${mode}" in
	all_ok)
		exit 0
		;;
	fail_https_gh)
		if [[ \${has_gh_helper} -eq 1 ]]; then
			echo "fatal: gh auth token rejected" >&2
			exit 1
		fi
		exit 0
		;;
	fail_both_https)
		if [[ \${has_instead_of} -eq 1 ]]; then
			echo "fatal: https blocked" >&2
			exit 1
		fi
		exit 0
		;;
	fail_all)
		echo "fatal: simulated fetch failure line 1" >&2
		echo "fatal: simulated fetch failure final" >&2
		exit 1
		;;
	sleep_hang)
		python3 -c 'import time; time.sleep(5)'
		exit 0
		;;
	esac
fi
exec "${REAL_GIT_BIN}" "\$@"
MOCK
chmod +x "${FETCH_MOCK_BIN}/git"

SSH_REMOTE_CLONE="${TEST_DIR}/ssh-remote-clone"
git clone -q "${BARE_REMOTE}" "${SSH_REMOTE_CLONE}"
git -C "${SSH_REMOTE_CLONE}" remote set-head origin -a >/dev/null 2>&1
git -C "${SSH_REMOTE_CLONE}" remote set-url origin "git@github.com:abhimehro/demo.git"

# 8a. https-gh primary transport for GitHub SSH URL
: >"${FETCH_LOG}"
printf 'all_ok\n' >"${FETCH_MODE_FILE}"
check "fetch_origin_resilient uses https-gh first for GitHub SSH URL" \
	check_fetch_transport 0 "${SSH_REMOTE_CLONE}" "https-gh"
check_grep "https-gh disables terminal prompts" "TERM=0" "${FETCH_LOG}"
check_grep "https-gh configures gh credential helper" "credential\.helper=!gh auth git-credential" "${FETCH_LOG}"
check_grep "https-gh rewrites git@github.com: to https" "url\.https://github\.com/\.insteadOf=git@github\.com:" "${FETCH_LOG}"
check_grep "https-gh rewrites ssh://git@github.com/ to https" "url\.https://github\.com/\.insteadOf=ssh://git@github\.com/" "${FETCH_LOG}"

# 8b. https-gh -> https-anon fallback
: >"${FETCH_LOG}"
printf 'fail_https_gh\n' >"${FETCH_MODE_FILE}"
check "fetch_origin_resilient falls back from https-gh to https-anon" \
	check_fetch_transport 0 "${SSH_REMOTE_CLONE}" "https-anon"

# 8c. https-anon -> ssh-batch fallback
: >"${FETCH_LOG}"
printf 'fail_both_https\n' >"${FETCH_MODE_FILE}"
check "fetch_origin_resilient falls back from https-anon to ssh-batch" \
	check_fetch_transport 0 "${SSH_REMOTE_CLONE}" "ssh-batch"
check_grep "ssh-batch configures BatchMode=yes and ConnectTimeout=10" "SSH=ssh -o BatchMode=yes -o ConnectTimeout=10" "${FETCH_LOG}"

# 8d. PROACTIVE_FETCH_FORCE_SSH=1 skips HTTPS transports
: >"${FETCH_LOG}"
printf 'all_ok\n' >"${FETCH_MODE_FILE}"
check "PROACTIVE_FETCH_FORCE_SSH=1 forces ssh-batch directly" \
	check_fetch_transport 1 "${SSH_REMOTE_CLONE}" "ssh-batch"
check "PROACTIVE_FETCH_FORCE_SSH=1 does not attempt HTTPS rewrite" \
	check_not_grep "insteadOf=" "${FETCH_LOG}"

# 8e. Local bare remote and https:// use direct transport
: >"${FETCH_LOG}"
check "fetch_origin_resilient uses direct transport for local bare remote" \
	check_fetch_transport 0 "${LOCAL_CLONE}" "direct"

# 8f. Retries, backoff_s * attempt, failure summary, and invalid env knob warnings
: >"${FETCH_LOG}"
: >"${FETCH_SLEEP_LOG}"
printf 'fail_all\n' >"${FETCH_MODE_FILE}"
check_exit "fetch_origin_resilient fails when all transports exhaust retries" 1 \
	run_fetch_exhaust_with_summary 3 1 "${SSH_REMOTE_CLONE}"
check_grep "fetch failure summary records https-gh last stderr line" "https-gh: fatal: simulated fetch failure final" "${TEST_DIR}/check.log"
check_grep "fetch failure summary records https-anon last stderr line" "https-anon: fatal: simulated fetch failure final" "${TEST_DIR}/check.log"
check_grep "fetch failure summary records ssh-batch last stderr line" "ssh-batch: fatal: simulated fetch failure final" "${TEST_DIR}/check.log"
check "fetch retry backoff scales as backoff_s * attempt (1 then 2)" \
	check_sleep_backoff_log "${FETCH_SLEEP_LOG}" "1,2,"

printf 'all_ok\n' >"${FETCH_MODE_FILE}"
check_exit "invalid fetch env knobs warn and fall back cleanly" 0 \
	run_fetch_invalid_knobs "${LOCAL_CLONE}"
check_grep "invalid PROACTIVE_FETCH_RETRIES logs warning" "Ignoring invalid PROACTIVE_FETCH_RETRIES=bogus" "${TEST_DIR}/check.log"
check_grep "invalid PROACTIVE_FETCH_BACKOFF_S logs warning" "Ignoring invalid PROACTIVE_FETCH_BACKOFF_S=-1" "${TEST_DIR}/check.log"
check_grep "invalid PROACTIVE_FETCH_TIMEOUT_S logs warning" "Ignoring invalid PROACTIVE_FETCH_TIMEOUT_S=0" "${TEST_DIR}/check.log"
check_grep "invalid PROACTIVE_FETCH_FORCE_SSH logs warning" "Ignoring invalid PROACTIVE_FETCH_FORCE_SSH=yes" "${TEST_DIR}/check.log"

# 8g. Hung fetch times out via PROACTIVE_FETCH_TIMEOUT_S and fails closed in require_fresh_origin_ref
printf 'sleep_hang\n' >"${FETCH_MODE_FILE}"
check_exit "check-throttle fails closed with exit 6 when fetch times out" 6 \
	env PATH="${FETCH_MOCK_BIN}:${PATH}" PROACTIVE_FETCH_RETRIES=1 PROACTIVE_FETCH_TIMEOUT_S=1 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/demo --worktree-root "${WT_ROOT}" --repo-path "${LOCAL_CLONE}" --include-worktrees
check_grep "timed-out fetch includes tried summary" "tried: direct:" "${TEST_DIR}/check.log"

# 8h. cmd_prepare warns and falls back to local ref when fetch fails
printf 'fail_all\n' >"${FETCH_MODE_FILE}"
WT_FALLBACK=""
WT_FALLBACK="$(env PATH="${FETCH_MOCK_BIN}:${PATH}" PROACTIVE_FETCH_RETRIES=1 "${TARGET_SCRIPT}" prepare --repo-path "${SSH_REMOTE_CLONE}" --lens bolt --worktree-root "${WT_ROOT}" 2>"${TEST_DIR}/prepare_warn.log")"
check "prepare still creates worktree when fetch fails" test -d "${WT_FALLBACK}"
check_grep "prepare emits fallback warning on fetch failure" "\[WARN\] prepare: could not refresh origin" "${TEST_DIR}/prepare_warn.log"
git -C "${SSH_REMOTE_CLONE}" worktree remove --force "${WT_FALLBACK}"

# 9. Resilient GitHub CLI wrapper run_gh_resilient
GH_MOCK_BIN="${TEST_DIR}/gh_mock_bin"
mkdir -p "${GH_MOCK_BIN}"
GH_COUNT_FILE="${TEST_DIR}/gh_count"
GH_MODE_FILE="${TEST_DIR}/gh_mode"
cat >"${GH_MOCK_BIN}/gh" <<MOCK
#!/usr/bin/env bash
cnt=0
if [[ -f "${GH_COUNT_FILE}" ]]; then
	cnt="\$(cat "${GH_COUNT_FILE}")"
fi
cnt=\$((cnt + 1))
printf '%s\n' "\${cnt}" >"${GH_COUNT_FILE}"
mode="\$(cat "${GH_MODE_FILE}" 2>/dev/null || echo "ok")"
case "\${mode}" in
transient_recover)
	if [[ \${cnt} -lt 2 ]]; then
		echo "HTTP 502 Bad Gateway" >&2
		exit 1
	fi
	echo "[]"
	exit 0
	;;
bad_json_recover)
	if [[ \${cnt} -lt 2 ]]; then
		echo "{not-valid-json"
		exit 0
	fi
	echo "[]"
	exit 0
	;;
bad_json_always)
	echo "not-json"
	exit 0
	;;
perm_401)
	echo "HTTP 401: Bad credentials" >&2
	exit 1
	;;
perm_not_logged_in)
	echo "To get started with GitHub CLI, please run: gh auth login" >&2
	echo "You are not logged into any GitHub hosts" >&2
	exit 1
	;;
perm_404)
	echo "HTTP 404: Not Found" >&2
	exit 1
	;;
perm_repo)
	echo "GraphQL: Could not resolve to a Repository with the name 'o/r'." >&2
	exit 1
	;;
perm_flag)
	echo "unknown flag: --bogus" >&2
	exit 1
	;;
timeout_hang)
	python3 -c 'import time; time.sleep(5)'
	exit 0
	;;
esac
echo "[]"
MOCK
chmod +x "${GH_MOCK_BIN}/gh"

printf '0\n' >"${GH_COUNT_FILE}"
printf 'transient_recover\n' >"${GH_MODE_FILE}"
PATH="${GH_MOCK_BIN}:${PATH}" check_exit "check-collisions recovers from transient gh failure on retry" 0 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/other.py"
check "run_gh_resilient retried transient failure (2 attempts)" test "$(cat "${GH_COUNT_FILE}")" = "2"

printf '0\n' >"${GH_COUNT_FILE}"
printf 'bad_json_recover\n' >"${GH_MODE_FILE}"
PATH="${GH_MOCK_BIN}:${PATH}" check_exit "check-throttle retries when gh --json emits invalid JSON" 0 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${EMPTY_WT_ROOT}"
check "run_gh_resilient retried invalid JSON output (2 attempts)" test "$(cat "${GH_COUNT_FILE}")" = "2"

printf '0\n' >"${GH_COUNT_FILE}"
printf 'bad_json_always\n' >"${GH_MODE_FILE}"
PATH="${GH_MOCK_BIN}:${PATH}" check_exit "check-collisions exits 6 when gh --json always returns invalid JSON" 6 \
	env PROACTIVE_GH_RETRIES=2 "${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/other.py"
check_grep "run_gh_resilient reports attempt count on JSON failure" "failed after 2 attempt\(s\):" "${TEST_DIR}/check.log"

for perm_mode in perm_401 perm_not_logged_in perm_404 perm_repo perm_flag; do
	printf '0\n' >"${GH_COUNT_FILE}"
	printf '%s\n' "${perm_mode}" >"${GH_MODE_FILE}"
	PATH="${GH_MOCK_BIN}:${PATH}" check_exit "run_gh_resilient fails fast on ${perm_mode}" 6 \
		env PROACTIVE_GH_RETRIES=3 "${TARGET_SCRIPT}" check-collisions --repo abhimehro/ctrld-sync --file "src/other.py"
	check "run_gh_resilient did not retry permanent error ${perm_mode}" test "$(cat "${GH_COUNT_FILE}")" = "1"
	check_grep "run_gh_resilient reports 1 attempt on ${perm_mode}" "failed after 1 attempt\(s\):" "${TEST_DIR}/check.log"
done

printf '0\n' >"${GH_COUNT_FILE}"
printf 'timeout_hang\n' >"${GH_MODE_FILE}"
PATH="${GH_MOCK_BIN}:${PATH}" check_exit "run_gh_resilient bounds hung gh via PROACTIVE_GH_TIMEOUT_S" 6 \
	env PROACTIVE_GH_RETRIES=2 PROACTIVE_GH_TIMEOUT_S=1 "${TARGET_SCRIPT}" check-throttle --repo abhimehro/ctrld-sync --worktree-root "${EMPTY_WT_ROOT}"
check "run_gh_resilient retried hung gh up to PROACTIVE_GH_RETRIES=2" test "$(cat "${GH_COUNT_FILE}")" = "2"
check_grep "run_gh_resilient reports 2 attempts after timeout" "failed after 2 attempt\(s\):" "${TEST_DIR}/check.log"

# 10. Headless local-mode commit safety (worktree-scoped commit.gpgsign=false)
WT_LOCAL_GPG="$("${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens bolt --mode local --worktree-root "${WT_ROOT}")"
WT_DRAFT_GPG="$("${TARGET_SCRIPT}" prepare --repo-path "${LOCAL_CLONE}" --lens bolt --mode draft-pr --worktree-root "${WT_ROOT}")"
check "prepare --mode local sets worktree commit.gpgsign=false" \
	test "$(git -C "${WT_LOCAL_GPG}" config --get commit.gpgsign)" = "false"
check "prepare --mode local does not alter primary checkout commit.gpgsign" \
	check_git_config_unset "${LOCAL_CLONE}" "commit.gpgsign"
check "prepare --mode draft-pr leaves commit.gpgsign unset" \
	check_git_config_unset "${WT_DRAFT_GPG}" "commit.gpgsign"
check "prepare --mode draft-pr leaves pushurl enabled" \
	test "$(git -C "${WT_DRAFT_GPG}" remote get-url --push origin)" != "DISABLED"
git -C "${LOCAL_CLONE}" worktree remove --force "${WT_LOCAL_GPG}"
git -C "${LOCAL_CLONE}" worktree remove --force "${WT_DRAFT_GPG}"

# 11. Multi-repo test runner & repo .venv resolution
PTC_SERIES="$("${TARGET_SCRIPT}" print-test-cmd --repo-name series_correction_project_updated)"
check "print-test-cmd maps series_correction_project_updated to scripts/tests/" \
	test "${PTC_SERIES}" = "MPLBACKEND=Agg python3 -m pytest scripts/tests/ -q"

mkdir -p "${TEST_DIR}/rvp_uv/.venv/bin" "${TEST_DIR}/rvp_wt/.venv/bin" "${TEST_DIR}/rvp_repo/.venv/bin"
check "resolve_verify_path skips .venv when test_cmd uses uv run" \
	check_resolve_verify_prefix "${TEST_DIR}/rvp_uv" "${TEST_DIR}/rvp_uv" "uv run pytest" "${TEST_DIR}/rvp_uv/.venv/bin:" "no"
check "resolve_verify_path prefers wt_path/.venv/bin over repo_path/.venv/bin" \
	check_resolve_verify_prefix "${TEST_DIR}/rvp_wt" "${TEST_DIR}/rvp_repo" "python3 -m pytest" "${TEST_DIR}/rvp_wt/.venv/bin:" "yes"
check "resolve_verify_path falls back to repo_path/.venv/bin when wt has no .venv" \
	check_resolve_verify_prefix "${TEST_DIR}/rvp_missing" "${TEST_DIR}/rvp_repo" "python3 -m pytest" "${TEST_DIR}/rvp_repo/.venv/bin:" "yes"

VENV_CLONE="${TEST_DIR}/venv-repo"
git clone -q "${BARE_REMOTE}" "${VENV_CLONE}"
git -C "${VENV_CLONE}" remote set-head origin -a >/dev/null 2>&1
mkdir -p "${VENV_CLONE}/.venv/bin"
REAL_PY3_PATH="$(command -v python3)"
cat >"${VENV_CLONE}/.venv/bin/python3" <<MOCK
#!/usr/bin/env bash
exec "${REAL_PY3_PATH}" "\$@"
MOCK
cat >"${VENV_CLONE}/.venv/bin/pytest_marker" <<'MOCK'
#!/usr/bin/env bash
printf 'VENV_STATE=%s TOOL=%s\n' "${VIRTUAL_ENV:-UNSET}" "$0" > .venv-verify.log
exit 0
MOCK
cat >"${VENV_CLONE}/.venv/bin/ruff" <<'MOCK'
#!/usr/bin/env bash
if [[ -n "${REPO_VENV_RUFF_FAIL:-}" && -f "${REPO_VENV_RUFF_FAIL}" ]]; then
	echo "src/venv_names.py:2:5: F821 Undefined name \`from_venv\`"
	exit 1
fi
exit 0
MOCK
chmod +x "${VENV_CLONE}/.venv/bin/python3" "${VENV_CLONE}/.venv/bin/pytest_marker" "${VENV_CLONE}/.venv/bin/ruff"

WT_VENV="$("${TARGET_SCRIPT}" prepare --repo-path "${VENV_CLONE}" --lens code-health --worktree-root "${WT_ROOT}")"
cat >"${WT_VENV}/src/venv_names.py" <<'EOF'
def ok(x):
    return x + 1
EOF
# Run with NOLINT_BIN (no global ruff/uv) + poisoned VIRTUAL_ENV to prove cmd_verify
# unsets VIRTUAL_ENV, injects repo .venv/bin onto PATH, and resolves .venv/bin/ruff.
check_exit "verify resolves repo .venv/bin for test_cmd and static checks while unsetting VIRTUAL_ENV" 0 \
	env PATH="${NOLINT_BIN}" HOME="${HOME}" VIRTUAL_ENV="/tmp/stale-other-venv" \
	"${TARGET_SCRIPT}" verify --worktree "${WT_VENV}" --lens code-health --test-cmd "pytest_marker"
check_grep "verify cleared VIRTUAL_ENV and ran repo .venv tool" "^VENV_STATE=UNSET TOOL=.*\.venv/bin/pytest_marker$" "${WT_VENV}/.venv-verify.log"

# Verify repo .venv/bin/ruff findings still block
REPO_VENV_RUFF_FAIL_FLAG="${TEST_DIR}/repo_venv_ruff_fail"
touch "${REPO_VENV_RUFF_FAIL_FLAG}"
check_exit "verify blocks when repo .venv/bin/ruff reports F821" 2 \
	env PATH="${NOLINT_BIN}" HOME="${HOME}" REPO_VENV_RUFF_FAIL="${REPO_VENV_RUFF_FAIL_FLAG}" \
	"${TARGET_SCRIPT}" verify --worktree "${WT_VENV}" --lens code-health --test-cmd "pytest_marker"
check_grep "verify surfaces F821 from repo .venv/bin/ruff" "F821 Undefined name" "${TEST_DIR}/check.log"
rm -f "${REPO_VENV_RUFF_FAIL_FLAG}"

# Verify fallback to repo .venv/bin/python3 -m pyflakes when ruff is absent
rm -f "${VENV_CLONE}/.venv/bin/ruff"
cat >"${VENV_CLONE}/.venv/bin/python3" <<MOCK
#!/usr/bin/env bash
if [[ "\$1" == "-c" && "\${2:-}" == "import pyflakes" ]]; then
	exit 0
fi
if [[ "\$1" == "-m" && "\$2" == "pyflakes" ]]; then
	if [[ -n "\${REPO_VENV_PYFLAKES_FAIL:-}" && -f "\${REPO_VENV_PYFLAKES_FAIL}" ]]; then
		echo "src/venv_names.py:2: undefined name 'from_pyflakes'"
		exit 1
	fi
	exit 0
fi
exec "${REAL_PY3_PATH}" "\$@"
MOCK
chmod +x "${VENV_CLONE}/.venv/bin/python3"
check_exit "verify falls back to repo .venv/bin/python3 pyflakes when ruff absent" 0 \
	env PATH="${NOLINT_BIN}" HOME="${HOME}" \
	"${TARGET_SCRIPT}" verify --worktree "${WT_VENV}" --lens code-health --test-cmd "pytest_marker"
touch "${REPO_VENV_RUFF_FAIL_FLAG}"
check_exit "verify blocks when repo .venv/bin/python3 pyflakes reports finding" 2 \
	env PATH="${NOLINT_BIN}" HOME="${HOME}" REPO_VENV_PYFLAKES_FAIL="${REPO_VENV_RUFF_FAIL_FLAG}" \
	"${TARGET_SCRIPT}" verify --worktree "${WT_VENV}" --lens code-health --test-cmd "pytest_marker"
check_grep "verify surfaces finding from repo .venv/bin/python3 pyflakes" "undefined name 'from_pyflakes'" "${TEST_DIR}/check.log"
rm -f "${REPO_VENV_RUFF_FAIL_FLAG}"
git -C "${VENV_CLONE}" worktree remove --force "${WT_VENV}"

# 12. Self-healing cleanup --prune-merged
PRUNE_BARE="${TEST_DIR}/prune-remote.git"
PRUNE_SEED="${TEST_DIR}/prune-seed"
PRUNE_CLONE="${TEST_DIR}/prune-repo"
PRUNE_WT_ROOT="${TEST_DIR}/prune-worktrees"
mkdir -p "${PRUNE_WT_ROOT}"
git init -q --bare "${PRUNE_BARE}"
git clone -q "${BARE_REMOTE}" "${PRUNE_SEED}"
git -C "${PRUNE_SEED}" remote set-url origin "${PRUNE_BARE}"
git -C "${PRUNE_SEED}" push -q origin HEAD:refs/heads/main
git -C "${PRUNE_BARE}" symbolic-ref HEAD refs/heads/main
git clone -q "${PRUNE_BARE}" "${PRUNE_CLONE}"
git -C "${PRUNE_CLONE}" config user.email "test@example.com"
git -C "${PRUNE_CLONE}" config user.name "Test User"
git -C "${PRUNE_CLONE}" remote set-head origin -a >/dev/null 2>&1

# (a) Fresh ancestor-merged worktree
WT_P_ANC="$("${TARGET_SCRIPT}" prepare --repo-path "${PRUNE_CLONE}" --lens bolt --worktree-root "${PRUNE_WT_ROOT}")"
BR_P_ANC="$(git -C "${WT_P_ANC}" symbolic-ref --short HEAD)"
git -C "${WT_P_ANC}" config user.email "test@example.com"
git -C "${WT_P_ANC}" config user.name "Test User"
echo "anc" >"${WT_P_ANC}/src/anc.py"
git -C "${WT_P_ANC}" add -A
git -C "${WT_P_ANC}" commit -q -m "⚡bolt: ancestor merged"
git -C "${PRUNE_CLONE}" merge -q --no-edit "$(git -C "${WT_P_ANC}" rev-parse HEAD)"

# (b) Fresh squash-merged worktree
WT_P_SQ="$("${TARGET_SCRIPT}" prepare --repo-path "${PRUNE_CLONE}" --lens code-health --worktree-root "${PRUNE_WT_ROOT}")"
BR_P_SQ="$(git -C "${WT_P_SQ}" symbolic-ref --short HEAD)"
git -C "${WT_P_SQ}" config user.email "test@example.com"
git -C "${WT_P_SQ}" config user.name "Test User"
echo "sq" >"${WT_P_SQ}/src/sq_prune.py"
git -C "${WT_P_SQ}" add -A
git -C "${WT_P_SQ}" commit -q -m "chore(qa): squash merged"
git -C "${PRUNE_CLONE}" merge --squash -q "$(git -C "${WT_P_SQ}" rev-parse HEAD)"
git -C "${PRUNE_CLONE}" commit -q -m "chore(qa): squash merged (#200)"
git -C "${PRUNE_CLONE}" push -q origin main

# (c) Fresh clean unmerged worktree (must survive)
WT_P_UNMERGED="$("${TARGET_SCRIPT}" prepare --repo-path "${PRUNE_CLONE}" --lens bolt --worktree-root "${PRUNE_WT_ROOT}")"
BR_P_UNMERGED="$(git -C "${WT_P_UNMERGED}" symbolic-ref --short HEAD)"
git -C "${WT_P_UNMERGED}" config user.email "test@example.com"
git -C "${WT_P_UNMERGED}" config user.name "Test User"
echo "keep" >"${WT_P_UNMERGED}/src/keep_unmerged.py"
git -C "${WT_P_UNMERGED}" add -A
git -C "${WT_P_UNMERGED}" commit -q -m "⚡bolt: unmerged keep"

# (d) Fresh dirty worktree (must survive)
WT_P_DIRTY="$("${TARGET_SCRIPT}" prepare --repo-path "${PRUNE_CLONE}" --lens bolt --worktree-root "${PRUNE_WT_ROOT}")"
echo "dirty" >"${WT_P_DIRTY}/dirty.txt"

# (e) Clean merged worktree on non-proactive/* branch: worktree removed, human branch kept!
WT_P_HUMAN_BR="$("${TARGET_SCRIPT}" prepare --repo-path "${PRUNE_CLONE}" --lens bolt --worktree-root "${PRUNE_WT_ROOT}")"
git -C "${WT_P_HUMAN_BR}" checkout -q -b feature/human-keep
git -C "${WT_P_HUMAN_BR}" config user.email "test@example.com"
git -C "${WT_P_HUMAN_BR}" config user.name "Test User"
echo "human" >"${WT_P_HUMAN_BR}/src/human_merged.py"
git -C "${WT_P_HUMAN_BR}" add -A
git -C "${WT_P_HUMAN_BR}" commit -q -m "human merged commit"
git -C "${PRUNE_CLONE}" merge -q --no-edit "$(git -C "${WT_P_HUMAN_BR}" rev-parse HEAD)"
git -C "${PRUNE_CLONE}" push -q origin main

# Default cleanup without --prune-merged keeps all fresh worktrees
check_exit "plain cleanup preserves fresh merged worktrees (21d TTL intact)" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${PRUNE_WT_ROOT}"
check "plain cleanup kept fresh WT_P_ANC" test -d "${WT_P_ANC}"
check "plain cleanup kept fresh WT_P_SQ" test -d "${WT_P_SQ}"

# cleanup --prune-merged removes merged worktrees & proactive/* branches, keeps unmerged/dirty & non-proactive branch
check_exit "cleanup --prune-merged runs cleanly" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${PRUNE_WT_ROOT}" --prune-merged
check "cleanup --prune-merged removed fresh ancestor-merged WT_P_ANC" test ! -d "${WT_P_ANC}"
check "cleanup --prune-merged deleted proactive/* branch for WT_P_ANC" \
	check_git_ref_absent "${PRUNE_CLONE}" "refs/heads/${BR_P_ANC}"
check "cleanup --prune-merged removed fresh squash-merged WT_P_SQ" test ! -d "${WT_P_SQ}"
check "cleanup --prune-merged deleted proactive/* branch for WT_P_SQ" \
	check_git_ref_absent "${PRUNE_CLONE}" "refs/heads/${BR_P_SQ}"
check "cleanup --prune-merged removed clean merged WT_P_HUMAN_BR" test ! -d "${WT_P_HUMAN_BR}"
check "cleanup --prune-merged kept non-proactive branch feature/human-keep" \
	git -C "${PRUNE_CLONE}" show-ref --verify --quiet "refs/heads/feature/human-keep"
check "cleanup --prune-merged preserved unmerged WT_P_UNMERGED" test -d "${WT_P_UNMERGED}"
check "cleanup --prune-merged kept unmerged branch" \
	git -C "${PRUNE_CLONE}" show-ref --verify --quiet "refs/heads/${BR_P_UNMERGED}"
check "cleanup --prune-merged preserved dirty WT_P_DIRTY" test -d "${WT_P_DIRTY}"

# Preserve worktree when repo_path fetch fails
PRUNE_BROKEN_CLONE="${TEST_DIR}/prune-broken-clone"
git clone -q "${PRUNE_BARE}" "${PRUNE_BROKEN_CLONE}"
git -C "${PRUNE_BROKEN_CLONE}" remote set-head origin -a >/dev/null 2>&1
WT_P_BROKEN="$("${TARGET_SCRIPT}" prepare --repo-path "${PRUNE_BROKEN_CLONE}" --lens bolt --worktree-root "${PRUNE_WT_ROOT}")"
git -C "${PRUNE_BROKEN_CLONE}" remote set-url origin "${TEST_DIR}/nonexistent-prune-remote.git"
check_exit "cleanup --prune-merged preserves worktree when origin fetch fails" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${PRUNE_WT_ROOT}" --prune-merged
check "cleanup --prune-merged kept WT_P_BROKEN on fetch error" test -d "${WT_P_BROKEN}"

# 13. preflight subcommand (validation, auto-heal, skip-fetch, gh auth, all 7 repo toolchains)
PF_MOCK_BIN="${TEST_DIR}/pf_mock_bin"
mkdir -p "${PF_MOCK_BIN}"
PF_GH_FAIL="${TEST_DIR}/pf_gh_fail"
cat >"${PF_MOCK_BIN}/gh" <<MOCK
#!/usr/bin/env bash
if [[ -f "${PF_GH_FAIL}" ]]; then
	echo "You are not logged into any GitHub hosts" >&2
	exit 1
fi
echo "Logged in to github.com"
exit 0
MOCK
cat >"${PF_MOCK_BIN}/uv" <<'MOCK'
#!/usr/bin/env bash
if [[ -n "${PF_UV_FAIL:-}" && -f "${PF_UV_FAIL}" ]]; then
	exit 1
fi
exit 0
MOCK
cat >"${PF_MOCK_BIN}/flake8" <<'MOCK'
#!/usr/bin/env bash
echo "7.0.0"
exit 0
MOCK
cat >"${PF_MOCK_BIN}/Rscript" <<'MOCK'
#!/usr/bin/env bash
if [[ -n "${PF_RSCRIPT_FAIL:-}" && -f "${PF_RSCRIPT_FAIL}" ]]; then
	exit 1
fi
exit 0
MOCK
chmod +x "${PF_MOCK_BIN}/gh" "${PF_MOCK_BIN}/uv" "${PF_MOCK_BIN}/flake8" "${PF_MOCK_BIN}/Rscript"

# Build a clean python3 wrapper in PF_MOCK_BIN that answers pytest --version
cat >"${PF_MOCK_BIN}/python3" <<MOCK
#!/usr/bin/env bash
if [[ "\$1" == "-m" && "\$2" == "pytest" && "\$3" == "--version" ]]; then
	if [[ -n "\${PF_PYTEST_FAIL:-}" && -f "\${PF_PYTEST_FAIL}" ]]; then
		exit 1
	fi
	echo "pytest 8.0.0"
	exit 0
fi
exec "${REAL_PY3_PATH}" "\$@"
MOCK
chmod +x "${PF_MOCK_BIN}/python3"

# 13a. Validation & auth/fetch failures
check_exit "preflight requires --repo and --repo-path" 1 \
	"${TARGET_SCRIPT}" preflight --repo abhimehro/ctrld-sync
check_exit "preflight rejects non-git --repo-path" 1 \
	"${TARGET_SCRIPT}" preflight --repo abhimehro/ctrld-sync --repo-path "${TEST_DIR}/not-a-git-repo"

check_exit "preflight exits 6 on git fetch failure" 6 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight \
	--repo abhimehro/prune-broken-clone --repo-path "${PRUNE_BROKEN_CLONE}"
check_grep "preflight reports git_fetch=failed" "^git_fetch=failed$" "${TEST_DIR}/check.log"
check_grep "preflight reports preflight=FAIL on fetch failure" "^preflight=FAIL$" "${TEST_DIR}/check.log"

touch "${PF_GH_FAIL}"
check_exit "preflight exits 6 on gh auth failure" 6 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight \
	--repo abhimehro/personal-config --repo-path "${PRUNE_CLONE}"
check_grep "preflight reports gh_auth=failed" "^gh_auth=failed$" "${TEST_DIR}/check.log"
rm -f "${PF_GH_FAIL}"

# --skip-fetch bypasses fetch failure on broken remote
PF_SKIP_REPO="${TEST_DIR}/pf_repos/personal-config"
mkdir -p "${TEST_DIR}/pf_repos"
git clone -q "${PRUNE_BARE}" "${PF_SKIP_REPO}"
git -C "${PF_SKIP_REPO}" remote set-url origin "${TEST_DIR}/nonexistent-skip-remote.git"
check_exit "preflight --skip-fetch succeeds without network fetch" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight \
	--repo abhimehro/personal-config --repo-path "${PF_SKIP_REPO}" --skip-fetch
check_grep "preflight --skip-fetch reports git_fetch=skipped" "^git_fetch=skipped$" "${TEST_DIR}/check.log"
check_grep "preflight --skip-fetch reports preflight=PASS" "^preflight=PASS$" "${TEST_DIR}/check.log"

# 13b. --auto-heal repairs missing origin/HEAD and prunes merged worktrees for that repo only
PF_HEAL_WT_ROOT="${TEST_DIR}/pf_heal_wt"
mkdir -p "${PF_HEAL_WT_ROOT}"
PF_HEAL_REPO="${TEST_DIR}/pf_heal_repos/personal-config"
mkdir -p "${TEST_DIR}/pf_heal_repos"
git clone -q "${PRUNE_BARE}" "${PF_HEAL_REPO}"
git -C "${PF_HEAL_REPO}" remote set-head origin -a >/dev/null 2>&1
WT_HEAL_MERGED="$("${TARGET_SCRIPT}" prepare --repo-path "${PF_HEAL_REPO}" --lens bolt --worktree-root "${PF_HEAL_WT_ROOT}")"
printf 'merged candidate\n' >"${WT_HEAL_MERGED}/pf_heal_merged.txt"
git -C "${WT_HEAL_MERGED}" add pf_heal_merged.txt
git -C "${WT_HEAL_MERGED}" -c user.email="test@example.com" -c user.name="Test" commit -q -m "candidate commit merged upstream"
PF_HEAL_UPDATER="${TEST_DIR}/pf_heal_updater"
git clone -q "${PRUNE_BARE}" "${PF_HEAL_UPDATER}"
git -C "${PF_HEAL_UPDATER}" config user.email "test@example.com"
git -C "${PF_HEAL_UPDATER}" config user.name "Test"
git -C "${PF_HEAL_UPDATER}" fetch -q "${WT_HEAL_MERGED}" "$(git -C "${WT_HEAL_MERGED}" rev-parse HEAD)"
git -C "${PF_HEAL_UPDATER}" merge --ff-only -q FETCH_HEAD
git -C "${PF_HEAL_UPDATER}" push -q origin main
WT_FRESH_ZERO="$("${TARGET_SCRIPT}" prepare --repo-path "${PF_HEAL_REPO}" --lens code-health --worktree-root "${PF_HEAL_WT_ROOT}")"
WT_HEAL_OTHER="$("${TARGET_SCRIPT}" prepare --repo-path "${PRUNE_CLONE}" --lens bolt --worktree-root "${PF_HEAL_WT_ROOT}")"
# Delete origin/HEAD to verify --auto-heal restores it
git -C "${PF_HEAL_REPO}" remote set-head origin -d >/dev/null 2>&1
check_exit "preflight --auto-heal passes and heals repo state" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight \
	--repo abhimehro/personal-config --repo-path "${PF_HEAL_REPO}" --worktree-root "${PF_HEAL_WT_ROOT}" --auto-heal
check_grep "preflight --auto-heal reports repo" "^repo=abhimehro/personal-config$" "${TEST_DIR}/check.log"
check_grep "preflight --auto-heal reports git_fetch=ok" "^git_fetch=ok$" "${TEST_DIR}/check.log"
check_grep "preflight --auto-heal reports fetch_transport" "^fetch_transport=direct$" "${TEST_DIR}/check.log"
check_grep "preflight --auto-heal reports gh_auth=ok" "^gh_auth=ok$" "${TEST_DIR}/check.log"
check_grep "preflight --auto-heal reports toolchain=ok" "^toolchain=ok$" "${TEST_DIR}/check.log"
check_grep "preflight --auto-heal reports merged_worktrees_pruned=1" "^merged_worktrees_pruned=1$" "${TEST_DIR}/check.log"
check_grep "preflight --auto-heal reports preflight=PASS" "^preflight=PASS$" "${TEST_DIR}/check.log"
check "preflight --auto-heal restored origin/HEAD" \
	git -C "${PF_HEAL_REPO}" symbolic-ref --quiet refs/remotes/origin/HEAD
check "preflight --auto-heal pruned personal-config merged worktree" test ! -d "${WT_HEAL_MERGED}"
check "preflight --auto-heal preserved zero-commit fresh worktree" test -d "${WT_FRESH_ZERO}"
check "preflight --auto-heal left other repo worktree untouched" test -d "${WT_HEAL_OTHER}"

# 13c. All 7 repository toolchains + unmapped repo (PASS and FAIL exit 7)
PF_REPOS_DIR="${TEST_DIR}/pf_all_repos"
mkdir -p "${PF_REPOS_DIR}"

make_pf_repo() {
	local rname="$1"
	local rdir="${PF_REPOS_DIR}/${rname}"
	git clone -q "${PRUNE_BARE}" "${rdir}"
	git -C "${rdir}" remote set-head origin -a >/dev/null 2>&1
	printf '%s' "${rdir}"
}

# (1) ctrld-sync: uv + uv.lock + ruff F82
PF_CTRLD="$(make_pf_repo "ctrld-sync")"
check_exit "preflight ctrld-sync fails exit 7 when uv.lock is missing" 7 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/ctrld-sync --repo-path "${PF_CTRLD}"
check_grep "preflight ctrld-sync missing prints toolchain=missing" "^toolchain=missing$" "${TEST_DIR}/check.log"
check_grep "preflight ctrld-sync missing prints remediation" "^remediation=" "${TEST_DIR}/check.log"
check_grep "preflight ctrld-sync missing prints preflight=FAIL" "^preflight=FAIL$" "${TEST_DIR}/check.log"
touch "${PF_CTRLD}/uv.lock"
check_exit "preflight ctrld-sync passes with uv + uv.lock + ruff" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/ctrld-sync --repo-path "${PF_CTRLD}"
check_grep "preflight ctrld-sync reports toolchain=ok" "^toolchain=ok$" "${TEST_DIR}/check.log"
PF_UV_FAIL_FLAG="${TEST_DIR}/pf_uv_fail"
touch "${PF_UV_FAIL_FLAG}"
check_exit "preflight ctrld-sync fails exit 7 when uv run ruff fails" 7 \
	env PATH="${PF_MOCK_BIN}:${PATH}" PF_UV_FAIL="${PF_UV_FAIL_FLAG}" \
	"${TARGET_SCRIPT}" preflight --repo abhimehro/ctrld-sync --repo-path "${PF_CTRLD}"
rm -f "${PF_UV_FAIL_FLAG}"

# (2) personal-config: make, bash, python3
PF_PC="$(make_pf_repo "personal-config")"
check_exit "preflight personal-config passes with make/bash/python3" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/personal-config --repo-path "${PF_PC}"
PF_NO_MAKE_BIN="${TEST_DIR}/pf_no_make_bin"
mkdir -p "${PF_NO_MAKE_BIN}"
for b in env git bash cat grep sed mktemp dirname pwd rm touch uname tr cut head wc tee ln mkdir date sort awk find xargs basename expr test gh; do
	if p="$(PATH="${PF_MOCK_BIN}:${PATH}" command -v "${b}" 2>/dev/null)"; then
		ln -sf "${p}" "${PF_NO_MAKE_BIN}/${b}"
	fi
done
cat >"${PF_NO_MAKE_BIN}/python3" <<MOCK
#!/usr/bin/env bash
if [[ "\$1" == "-m" && "\$2" == "pytest" && "\$3" == "--version" ]]; then
	if [[ -n "\${PF_PYTEST_FAIL:-}" && -f "\${PF_PYTEST_FAIL}" ]]; then
		exit 1
	fi
	echo "pytest 8.0.0"
	exit 0
fi
if [[ "\$1" == "-c" && "\$2" == *"import pyflakes"* ]]; then
	exit 1
fi
exec "${REAL_PY3_PATH}" "\$@"
MOCK
chmod +x "${PF_NO_MAKE_BIN}/python3"
check_exit "preflight personal-config fails exit 7 when make is missing" 7 \
	env PATH="${PF_NO_MAKE_BIN}" "${TARGET_SCRIPT}" preflight --repo abhimehro/personal-config --repo-path "${PF_PC}"

# (3) email-security-pipeline: pytest + F82
PF_ESP="$(make_pf_repo "email-security-pipeline")"
check_exit "preflight email-security-pipeline passes with pytest + F82" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/email-security-pipeline --repo-path "${PF_ESP}"
PF_PYTEST_FAIL_FLAG="${TEST_DIR}/pf_pytest_fail"
touch "${PF_PYTEST_FAIL_FLAG}"
check_exit "preflight email-security-pipeline fails exit 7 without pytest" 7 \
	env PATH="${PF_MOCK_BIN}:${PATH}" PF_PYTEST_FAIL="${PF_PYTEST_FAIL_FLAG}" \
	"${TARGET_SCRIPT}" preflight --repo abhimehro/email-security-pipeline --repo-path "${PF_ESP}"
rm -f "${PF_PYTEST_FAIL_FLAG}"
check_exit "preflight email-security-pipeline fails exit 7 without F82 checker" 7 \
	env PATH="${PF_NO_MAKE_BIN}" "${TARGET_SCRIPT}" preflight --repo abhimehro/email-security-pipeline --repo-path "${PF_ESP}"

# (4) Hydrograph_Versus_Seatek_Sensors_Project: pytest + flake8 + F82
PF_HYDRO="$(make_pf_repo "Hydrograph_Versus_Seatek_Sensors_Project")"
check_exit "preflight Hydrograph passes with pytest + flake8 + F82" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/Hydrograph_Versus_Seatek_Sensors_Project --repo-path "${PF_HYDRO}"
check_exit "preflight Hydrograph fails exit 7 without flake8" 7 \
	env PATH="${PF_NO_MAKE_BIN}" "${TARGET_SCRIPT}" preflight --repo abhimehro/Hydrograph_Versus_Seatek_Sensors_Project --repo-path "${PF_HYDRO}"

# (5) series_correction_project_updated: pytest + scripts/tests/ + F82
PF_SERIES="$(make_pf_repo "series_correction_project_updated")"
check_exit "preflight series_correction fails exit 7 without scripts/tests/" 7 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/series_correction_project_updated --repo-path "${PF_SERIES}"
mkdir -p "${PF_SERIES}/scripts/tests"
check_exit "preflight series_correction passes with scripts/tests/ + pytest + F82" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/series_correction_project_updated --repo-path "${PF_SERIES}"

# (6) Seatek_Analysis: Rscript + testthat
PF_SEATEK="$(make_pf_repo "Seatek_Analysis")"
check_exit "preflight Seatek_Analysis passes when Rscript loads testthat" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/Seatek_Analysis --repo-path "${PF_SEATEK}"
PF_RSCRIPT_FAIL_FLAG="${TEST_DIR}/pf_rscript_fail"
touch "${PF_RSCRIPT_FAIL_FLAG}"
check_exit "preflight Seatek_Analysis fails exit 7 when testthat cannot load" 7 \
	env PATH="${PF_MOCK_BIN}:${PATH}" PF_RSCRIPT_FAIL="${PF_RSCRIPT_FAIL_FLAG}" \
	"${TARGET_SCRIPT}" preflight --repo abhimehro/Seatek_Analysis --repo-path "${PF_SEATEK}"
rm -f "${PF_RSCRIPT_FAIL_FLAG}"

# (7) repoprompt-ce: executable .agents/skills/rpce-contribution-check/scripts/preflight.sh
PF_RPCE="$(make_pf_repo "repoprompt-ce")"
check_exit "preflight repoprompt-ce fails exit 7 when rpce preflight.sh is missing" 7 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/repoprompt-ce --repo-path "${PF_RPCE}"
mkdir -p "${PF_RPCE}/.agents/skills/rpce-contribution-check/scripts"
printf '#!/usr/bin/env bash\nexit 0\n' >"${PF_RPCE}/.agents/skills/rpce-contribution-check/scripts/preflight.sh"
chmod +x "${PF_RPCE}/.agents/skills/rpce-contribution-check/scripts/preflight.sh"
check_exit "preflight repoprompt-ce passes when rpce preflight.sh is executable" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/repoprompt-ce --repo-path "${PF_RPCE}"

# (8) unmapped repo: python3 -m pytest --version
PF_UNMAPPED="$(make_pf_repo "some-unmapped-repo")"
check_exit "preflight unmapped repo passes with pytest" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight --repo abhimehro/some-unmapped-repo --repo-path "${PF_UNMAPPED}"
touch "${PF_PYTEST_FAIL_FLAG}"
check_exit "preflight unmapped repo fails exit 7 without pytest" 7 \
	env PATH="${PF_MOCK_BIN}:${PATH}" PF_PYTEST_FAIL="${PF_PYTEST_FAIL_FLAG}" \
	"${TARGET_SCRIPT}" preflight --repo abhimehro/some-unmapped-repo --repo-path "${PF_UNMAPPED}"
rm -f "${PF_PYTEST_FAIL_FLAG}"

# 14. Squash/patch-id false-positive guard on identical repeated blocks (D1)
DUP_BARE="${TEST_DIR}/dup-remote.git"
DUP_SEED="${TEST_DIR}/dup-seed"
DUP_CLONE="${TEST_DIR}/dup-repo"
DUP_WT_ROOT="${TEST_DIR}/dup-wt"
mkdir -p "${DUP_SEED}" "${DUP_WT_ROOT}"
git init -q --bare "${DUP_BARE}"
git init -q "${DUP_SEED}"
git -C "${DUP_SEED}" config user.email "test@example.com"
git -C "${DUP_SEED}" config user.name "Test"
cat >"${DUP_SEED}/dup.py" <<'EOF'
# Header one
alpha = 1
beta = 2
TARGET = "old"
gamma = 3
delta = 4
epsilon = 5

# Spacer 1
# Spacer 2
# Spacer 3
# Spacer 4
# Spacer 5
# Spacer 6
# Spacer 7
# Spacer 8

# Header two
alpha = 1
beta = 2
TARGET = "old"
gamma = 3
delta = 4
epsilon = 5
EOF
git -C "${DUP_SEED}" add dup.py
git -C "${DUP_SEED}" commit -q -m "base with repeated identical blocks"
git -C "${DUP_SEED}" branch -M main
git -C "${DUP_SEED}" remote add origin "${DUP_BARE}"
git -C "${DUP_SEED}" push -q -u origin main
git --git-dir="${DUP_BARE}" symbolic-ref HEAD refs/heads/main
git clone -q "${DUP_BARE}" "${DUP_CLONE}"
git -C "${DUP_CLONE}" remote set-head origin -a >/dev/null 2>&1

WT_DUP="$("${TARGET_SCRIPT}" prepare --repo abhimehro/dup-repo --repo-path "${DUP_CLONE}" --lens bolt --worktree-root "${DUP_WT_ROOT}")"
DUP_BRANCH="$(git -C "${WT_DUP}" symbolic-ref --quiet --short HEAD)"
python3 - "${WT_DUP}/dup.py" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
parts = text.rsplit('TARGET = "old"', 1)
assert len(parts) == 2
p.write_text(parts[0] + 'TARGET = "new"' + parts[1], encoding="utf-8")
PY
git -C "${WT_DUP}" add dup.py
git -C "${WT_DUP}" -c user.email="test@example.com" -c user.name="Test" commit -q -m "bolt: update second identical block"

# Upstream independently modifies ONLY the first identical block with the same line change.
UP_CLONE="${TEST_DIR}/dup-upstream"
git clone -q "${DUP_BARE}" "${UP_CLONE}"
git -C "${UP_CLONE}" config user.email "maintainer@example.com"
git -C "${UP_CLONE}" config user.name "Maintainer"
python3 - "${UP_CLONE}/dup.py" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
parts = text.split('TARGET = "old"', 1)
assert len(parts) == 2
p.write_text(parts[0] + 'TARGET = "new"' + parts[1], encoding="utf-8")
PY
git -C "${UP_CLONE}" add dup.py
git -C "${UP_CLONE}" commit -q -m "feat: update first identical block upstream"
git -C "${UP_CLONE}" push -q origin main
git -C "${DUP_CLONE}" fetch -q origin

PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-throttle retains candidate when upstream matched only another identical block" 5 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/dup-repo --worktree-root "${DUP_WT_ROOT}" --include-worktrees --repo-path "${DUP_CLONE}" --max-open 1
PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-collisions detects unmerged candidate despite repeated-block patch-id match" 4 \
	"${TARGET_SCRIPT}" check-collisions --repo abhimehro/dup-repo --file "dup.py" --include-worktrees --repo-path "${DUP_CLONE}"
check_exit "cleanup --prune-merged runs safely on repeated-block candidate" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${DUP_WT_ROOT}" --prune-merged
check "cleanup --prune-merged preserves unmerged repeated-block worktree" test -d "${WT_DUP}"
check "cleanup --prune-merged preserves unmerged repeated-block branch" \
	git -C "${DUP_CLONE}" rev-parse --verify --quiet "${DUP_BRANCH}"
check_exit "preflight --auto-heal passes without pruning unmerged repeated-block candidate" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight \
	--repo abhimehro/dup-repo --repo-path "${DUP_CLONE}" --worktree-root "${DUP_WT_ROOT}" --auto-heal
check "preflight --auto-heal preserved unmerged worktree after repeated-block edit" test -d "${WT_DUP}"

# 15. Explicit --repo identity in prepare for renamed checkouts (D2)
RENAMED_SEATEK="${TEST_DIR}/custom-clones/seatek-local"
mkdir -p "${TEST_DIR}/custom-clones"
git clone -q "${PRUNE_BARE}" "${RENAMED_SEATEK}"
git -C "${RENAMED_SEATEK}" remote set-head origin -a >/dev/null 2>&1
check_exit "prepare --repo rejects palette on renamed Seatek_Analysis checkout" 3 \
	"${TARGET_SCRIPT}" prepare --repo abhimehro/Seatek_Analysis --repo-path "${RENAMED_SEATEK}" --lens palette --worktree-root "${DUP_WT_ROOT}"
WT_RENAMED_SEATEK="$("${TARGET_SCRIPT}" prepare --repo abhimehro/Seatek_Analysis --repo-path "${RENAMED_SEATEK}" --lens code-health --worktree-root "${DUP_WT_ROOT}")"
check "prepare --repo names worktree slug after explicit repo identity" \
	test "$(basename "${WT_RENAMED_SEATEK}")" != "" -a -z "${WT_RENAMED_SEATEK##*/proactive-Seatek_Analysis-code-health-*}"
check "prepare --repo writes canonical repo_name into proactive-meta.json" python3 - "${WT_RENAMED_SEATEK}" <<'PY'
import json, pathlib, subprocess, sys
git_dir = subprocess.check_output(["git", "-C", sys.argv[1], "rev-parse", "--git-dir"], text=True).strip()
meta = json.loads((pathlib.Path(git_dir) / "proactive-meta.json").read_text(encoding="utf-8"))
assert meta["repo_name"] == "Seatek_Analysis", meta
PY

# 16. Host-scoped gh auth status ignores unrelated expired hosts (D5)
HOST_GH_BIN="${TEST_DIR}/host_gh_bin"
HOST_GH_LOG="${TEST_DIR}/host_gh_args.log"
mkdir -p "${HOST_GH_BIN}"
cat >"${HOST_GH_BIN}/gh" <<MOCK
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"${HOST_GH_LOG}"
if [[ "\$1" == "auth" && "\$2" == "status" ]]; then
	if [[ "\$3" == "--hostname" && "\$4" == "github.com" ]]; then
		echo "Logged in to github.com"
		exit 0
	fi
	if [[ "\$3" == "--hostname" && "\$4" == "ghe.example.com" ]]; then
		echo "Logged in to ghe.example.com"
		exit 0
	fi
	echo "Failed logging in to unrelated.example.invalid" >&2
	exit 1
fi
exit 0
MOCK
chmod +x "${HOST_GH_BIN}/gh"
HOST_REPO_GH="${TEST_DIR}/host_repo_gh"
git clone -q "${PRUNE_BARE}" "${HOST_REPO_GH}"
git -C "${HOST_REPO_GH}" remote set-url origin "git@github.com:abhimehro/email-security-pipeline.git"
: >"${HOST_GH_LOG}"
check_exit "preflight scopes gh auth status to origin hostname (github.com)" 0 \
	env PATH="${HOST_GH_BIN}:${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight \
	--repo abhimehro/email-security-pipeline --repo-path "${HOST_REPO_GH}" --skip-fetch
check_grep "preflight invoked gh auth status --hostname github.com" "^auth status --hostname github.com$" "${HOST_GH_LOG}"

git -C "${HOST_REPO_GH}" remote set-url origin "https://ghe.example.com/org/email-security-pipeline.git"
: >"${HOST_GH_LOG}"
check_exit "preflight scopes gh auth status to GHE origin hostname" 0 \
	env PATH="${HOST_GH_BIN}:${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight \
	--repo org/email-security-pipeline --repo-path "${HOST_REPO_GH}" --skip-fetch
check_grep "preflight invoked gh auth status --hostname ghe.example.com" "^auth status --hostname ghe.example.com$" "${HOST_GH_LOG}"

git -C "${HOST_REPO_GH}" remote set-url origin "git@github-proton:abhimehro/email-security-pipeline.git"
: >"${HOST_GH_LOG}"
check_exit "preflight maps github-proton SSH alias to github.com for gh auth" 0 \
	env PATH="${HOST_GH_BIN}:${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight \
	--repo abhimehro/email-security-pipeline --repo-path "${HOST_REPO_GH}" --skip-fetch
check_grep "preflight checked github.com for github-proton remote" "^auth status --hostname github.com$" "${HOST_GH_LOG}"

# 17. run_with_timeout terminates full process group on timeout (D6)
TIMEOUT_MARKER="${TEST_DIR}/pg_child_escaped.marker"
rc_pg=0
bash -c 'source "$1"; run_with_timeout 0.3 bash -c '\''sleep 1 && touch "$1" & wait'\'' _ "$2"' _ "${TARGET_SCRIPT}" "${TIMEOUT_MARKER}" 2>"${TEST_DIR}/pg_timeout.err" || rc_pg=$?
check "run_with_timeout returns 124 when terminating process group" test "${rc_pg}" -eq 124
sleep 1.4
check "run_with_timeout terminated child background subprocess before marker write" test ! -e "${TIMEOUT_MARKER}"

# 18. Additional hardening regressions ([3], [6], [11]/[16]/[21], [20], [25])

# [3] preflight --auto-heal repairs dangling refs/remotes/origin/HEAD
DANGLE_CLONE="${TEST_DIR}/dangle_clone/personal-config"
mkdir -p "${TEST_DIR}/dangle_clone"
git clone -q "${PRUNE_BARE}" "${DANGLE_CLONE}"
git -C "${DANGLE_CLONE}" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/deleted-branch
check "dangling origin/HEAD does not resolve before auto-heal" bash -c \
	"! git -C '${DANGLE_CLONE}' rev-parse --verify --quiet 'refs/remotes/origin/HEAD^{commit}' >/dev/null 2>&1"
check_exit "preflight --auto-heal repairs dangling origin/HEAD" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight \
	--repo abhimehro/personal-config --repo-path "${DANGLE_CLONE}" --worktree-root "${PF_HEAL_WT_ROOT}" --auto-heal
check "preflight --auto-heal restores valid origin/HEAD target" \
	git -C "${DANGLE_CLONE}" rev-parse --verify --quiet "refs/remotes/origin/HEAD^{commit}"

# [6] TTL cleanup preserves expired squash-merged worktree when offline, removes once reachable
TTL_WT_ROOT="${TEST_DIR}/ttl_offline_wt"
TTL_CLONE="${TEST_DIR}/ttl_offline_clone"
TTL_UPDATER="${TEST_DIR}/ttl_offline_updater"
mkdir -p "${TTL_WT_ROOT}"
git clone -q "${PRUNE_BARE}" "${TTL_CLONE}"
git -C "${TTL_CLONE}" remote set-head origin -a >/dev/null 2>&1
WT_TTL_SQ="$("${TARGET_SCRIPT}" prepare --repo abhimehro/ttl-repo --repo-path "${TTL_CLONE}" --lens bolt --worktree-root "${TTL_WT_ROOT}")"
printf 'squash change\n' >"${WT_TTL_SQ}/ttl_feature.txt"
git -C "${WT_TTL_SQ}" add ttl_feature.txt
git -C "${WT_TTL_SQ}" -c user.email="test@example.com" -c user.name="Test" commit -q -m "ttl feature"
SQ_COMMIT="$(git -C "${WT_TTL_SQ}" rev-parse HEAD)"

git clone -q "${PRUNE_BARE}" "${TTL_UPDATER}"
git -C "${TTL_UPDATER}" config user.email "test@example.com"
git -C "${TTL_UPDATER}" config user.name "Test"
git -C "${TTL_UPDATER}" fetch -q "${WT_TTL_SQ}" "${SQ_COMMIT}"
git -C "${TTL_UPDATER}" merge --squash -q "${SQ_COMMIT}"
git -C "${TTL_UPDATER}" commit -q -m "squash merge ttl feature"
git -C "${TTL_UPDATER}" push -q origin main

python3 - "${WT_TTL_SQ}" <<'PY'
import os, sys, time
old = time.time() - (30 * 86400)
os.utime(sys.argv[1], (old, old))
PY
git -C "${TTL_CLONE}" remote set-url origin "${TEST_DIR}/offline-ttl-remote.git"
check_exit "TTL cleanup completes safely offline" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${TTL_WT_ROOT}" --ttl-days 21
check "TTL cleanup preserves expired squash-merged worktree when origin fetch fails" test -d "${WT_TTL_SQ}"

git -C "${TTL_CLONE}" remote set-url origin "${PRUNE_BARE}"
check_exit "TTL cleanup succeeds when origin is reachable" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${TTL_WT_ROOT}" --ttl-days 21
check "TTL cleanup removes expired squash-merged worktree once origin fetch succeeds" test ! -d "${WT_TTL_SQ}"

# [11], [16], [21] Broken base_sha preservation, sibling prefix isolation, and git-common-dir isolation
ISO_WT_ROOT="${TEST_DIR}/iso_wt_root"
mkdir -p "${ISO_WT_ROOT}" "${TEST_DIR}/iso_main" "${TEST_DIR}/iso_other" "${TEST_DIR}/iso_sib"
ISO_MAIN="${TEST_DIR}/iso_main/proj"
ISO_OTHER="${TEST_DIR}/iso_other/proj"
ISO_SIB="${TEST_DIR}/iso_sib/proj-tools"
git clone -q "${PRUNE_BARE}" "${ISO_MAIN}"
git clone -q "${PRUNE_BARE}" "${ISO_OTHER}"
git clone -q "${PRUNE_BARE}" "${ISO_SIB}"
git -C "${ISO_MAIN}" remote set-head origin -a >/dev/null 2>&1
git -C "${ISO_OTHER}" remote set-head origin -a >/dev/null 2>&1
git -C "${ISO_SIB}" remote set-head origin -a >/dev/null 2>&1

WT_BROKEN_BASE="$("${TARGET_SCRIPT}" prepare --repo abhimehro/proj --repo-path "${ISO_MAIN}" --lens bolt --worktree-root "${ISO_WT_ROOT}")"
WT_BROKEN_GIT_DIR="$(git -C "${WT_BROKEN_BASE}" rev-parse --git-dir)"
python3 - "${WT_BROKEN_GIT_DIR}/proactive-meta.json" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
doc = json.loads(p.read_text(encoding="utf-8"))
doc["base_sha"] = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
PY
python3 - "${WT_BROKEN_BASE}" <<'PY'
import os, sys, time
old = time.time() - (30 * 86400)
os.utime(sys.argv[1], (old, old))
PY
check_exit "TTL cleanup handles corrupt base_sha safely" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${ISO_WT_ROOT}" --ttl-days 21
check "TTL cleanup preserves expired worktree whose base_sha is missing" test -d "${WT_BROKEN_BASE}"

WT_ISO_THIS="$("${TARGET_SCRIPT}" prepare --repo abhimehro/proj --repo-path "${ISO_MAIN}" --lens code-health --worktree-root "${ISO_WT_ROOT}")"
printf 'iso merged\n' >"${WT_ISO_THIS}/iso_merged.txt"
git -C "${WT_ISO_THIS}" add iso_merged.txt
git -C "${WT_ISO_THIS}" -c user.email="test@example.com" -c user.name="Test" commit -q -m "iso candidate commit"
ISO_UPDATER="${TEST_DIR}/iso_updater"
git clone -q "${PRUNE_BARE}" "${ISO_UPDATER}"
git -C "${ISO_UPDATER}" config user.email "test@example.com"
git -C "${ISO_UPDATER}" config user.name "Test"
git -C "${ISO_UPDATER}" fetch -q "${WT_ISO_THIS}" "$(git -C "${WT_ISO_THIS}" rev-parse HEAD)"
git -C "${ISO_UPDATER}" merge --ff-only -q FETCH_HEAD
git -C "${ISO_UPDATER}" push -q origin main
WT_ISO_OTHER="$("${TARGET_SCRIPT}" prepare --repo abhimehro/proj --repo-path "${ISO_OTHER}" --lens bolt --worktree-root "${ISO_WT_ROOT}")"
WT_ISO_SIB="$("${TARGET_SCRIPT}" prepare --repo abhimehro/proj-tools --repo-path "${ISO_SIB}" --lens bolt --worktree-root "${ISO_WT_ROOT}")"
git -C "${WT_BROKEN_BASE}" -c user.email="test@example.com" -c user.name="Test" commit --allow-empty -q -m "keep unmerged broken-base candidate distinct"

check_exit "preflight --auto-heal isolates pruning to matching clone only" 0 \
	env PATH="${PF_MOCK_BIN}:${PATH}" "${TARGET_SCRIPT}" preflight \
	--repo abhimehro/proj --repo-path "${ISO_MAIN}" --worktree-root "${ISO_WT_ROOT}" --auto-heal
check_grep "preflight --auto-heal pruned only the matching clone merged worktree" "^merged_worktrees_pruned=1$" "${TEST_DIR}/check.log"
check "preflight --auto-heal removed matching clone merged worktree" test ! -d "${WT_ISO_THIS}"
check "preflight --auto-heal preserved same-named worktree from different clone" test -d "${WT_ISO_OTHER}"
check "preflight --auto-heal preserved sibling proj-tools worktree" test -d "${WT_ISO_SIB}"

# [20] run_with_timeout SIGKILLs lingering child that ignores SIGTERM after leader exits
TRAPPED_MARKER="${TEST_DIR}/pg_trapped_child.marker"
rc_trap=0
bash -c 'source "$1"; run_with_timeout 0.3 bash -c '\''(trap "" TERM; sleep 1.2 && touch "$1") & sleep 0.6'\'' _ "$2"' _ "${TARGET_SCRIPT}" "${TRAPPED_MARKER}" 2>"${TEST_DIR}/pg_trap_timeout.err" || rc_trap=$?
check "run_with_timeout returns 124 for SIGTERM-ignoring child group" test "${rc_trap}" -eq 124
sleep 1.5
check "run_with_timeout SIGKILLs child that ignored SIGTERM after leader died" test ! -e "${TRAPPED_MARKER}"

# [25] Failing uv with pyproject.toml consistently falls back to repo .venv/bin/ruff in preflight and verify
UV_FB_BARE="${TEST_DIR}/uv_fb_remote.git"
UV_FB_SEED="${TEST_DIR}/uv_fb_seed"
UV_FB_CLONE="${TEST_DIR}/uv_fb_repos/email-security-pipeline"
UV_FB_WT_ROOT="${TEST_DIR}/uv_fb_wt"
UV_FB_LOG="${TEST_DIR}/uv_fb_ruff.log"
UV_FB_BIN="${TEST_DIR}/uv_fb_bin"
mkdir -p "${TEST_DIR}/uv_fb_repos" "${UV_FB_WT_ROOT}" "${UV_FB_BIN}" "${UV_FB_SEED}"
for b in env bash git python3 make cat grep sed mktemp dirname pwd rm touch uname tr cut head wc tee ln mkdir date sort awk find xargs basename expr test gh; do
	if p="$(PATH="${PF_MOCK_BIN}:${PATH}" command -v "${b}" 2>/dev/null)"; then
		ln -sf "${p}" "${UV_FB_BIN}/${b}"
	fi
done
cat >"${UV_FB_BIN}/uv" <<'MOCK'
#!/usr/bin/env bash
exit 1
MOCK
chmod +x "${UV_FB_BIN}/uv"
git init -q --bare "${UV_FB_BARE}"
git init -q "${UV_FB_SEED}"
git -C "${UV_FB_SEED}" config user.email "test@example.com"
git -C "${UV_FB_SEED}" config user.name "Test"
cat >"${UV_FB_SEED}/pyproject.toml" <<'EOF'
[project]
name = "uv-fallback-demo"
version = "0.1.0"
EOF
git -C "${UV_FB_SEED}" add pyproject.toml
git -C "${UV_FB_SEED}" commit -q -m "add pyproject"
git -C "${UV_FB_SEED}" branch -M main
git -C "${UV_FB_SEED}" remote add origin "${UV_FB_BARE}"
git -C "${UV_FB_SEED}" push -q -u origin main
git --git-dir="${UV_FB_BARE}" symbolic-ref HEAD refs/heads/main
git clone -q "${UV_FB_BARE}" "${UV_FB_CLONE}"
git -C "${UV_FB_CLONE}" remote set-head origin -a >/dev/null 2>&1
mkdir -p "${UV_FB_CLONE}/.venv/bin"
cat >"${UV_FB_CLONE}/.venv/bin/ruff" <<MOCK
#!/usr/bin/env bash
printf '%s\n' "\$*" >>"${UV_FB_LOG}"
exit 0
MOCK
cat >"${UV_FB_CLONE}/.venv/bin/python3" <<MOCK
#!/usr/bin/env bash
if [[ "\$1" == "-m" && "\$2" == "pytest" && "\$3" == "--version" ]]; then
	echo "pytest 8.0.0"
	exit 0
fi
exec "${REAL_PY3_PATH}" "\$@"
MOCK
chmod +x "${UV_FB_CLONE}/.venv/bin/ruff" "${UV_FB_CLONE}/.venv/bin/python3"

check_exit "preflight falls back to .venv/bin/ruff when uv fails despite pyproject.toml" 0 \
	env PATH="${UV_FB_BIN}" "${TARGET_SCRIPT}" preflight \
	--repo abhimehro/email-security-pipeline --repo-path "${UV_FB_CLONE}" --skip-fetch
WT_UV_FB="$("${TARGET_SCRIPT}" prepare --repo abhimehro/email-security-pipeline --repo-path "${UV_FB_CLONE}" --lens code-health --worktree-root "${UV_FB_WT_ROOT}")"
printf 'def ok():\n    return 1\n' >"${WT_UV_FB}/ok_mod.py"
: >"${UV_FB_LOG}"
check_exit "verify also falls back to .venv/bin/ruff when uv fails despite pyproject.toml" 0 \
	env PATH="${UV_FB_BIN}" "${TARGET_SCRIPT}" verify \
	--worktree "${WT_UV_FB}" --lens code-health --test-cmd "true"
check_grep "verify executed repo .venv/bin/ruff F82 fallback" "check --select=F82" "${UV_FB_LOG}"

# [BUG_0001] Squash merge followed by overlapping upstream edit stays recognized as merged
SQ_OVER_BARE="${TEST_DIR}/sq_over_remote.git"
SQ_OVER_SEED="${TEST_DIR}/sq_over_seed"
SQ_OVER_CLONE="${TEST_DIR}/sq_over_clone"
SQ_OVER_UPD="${TEST_DIR}/sq_over_updater"
SQ_OVER_WT_ROOT="${TEST_DIR}/sq_over_wt"
mkdir -p "${SQ_OVER_SEED}" "${SQ_OVER_WT_ROOT}"
git init -q --bare "${SQ_OVER_BARE}"
git init -q "${SQ_OVER_SEED}"
git -C "${SQ_OVER_SEED}" config user.email "test@example.com"
git -C "${SQ_OVER_SEED}" config user.name "Test"
printf 'limit = 10\n' >"${SQ_OVER_SEED}/cfg.py"
git -C "${SQ_OVER_SEED}" add cfg.py
git -C "${SQ_OVER_SEED}" commit -q -m "base limit"
git -C "${SQ_OVER_SEED}" branch -M main
git -C "${SQ_OVER_SEED}" remote add origin "${SQ_OVER_BARE}"
git -C "${SQ_OVER_SEED}" push -q -u origin main
git --git-dir="${SQ_OVER_BARE}" symbolic-ref HEAD refs/heads/main
git clone -q "${SQ_OVER_BARE}" "${SQ_OVER_CLONE}"
git -C "${SQ_OVER_CLONE}" remote set-head origin -a >/dev/null 2>&1

WT_SQ_OVER="$("${TARGET_SCRIPT}" prepare --repo abhimehro/sq-over --repo-path "${SQ_OVER_CLONE}" --lens bolt --worktree-root "${SQ_OVER_WT_ROOT}")"
printf 'limit = 20\n' >"${WT_SQ_OVER}/cfg.py"
git -C "${WT_SQ_OVER}" add cfg.py
git -C "${WT_SQ_OVER}" -c user.email="test@example.com" -c user.name="Test" commit -q -m "bolt: raise limit to 20"

git clone -q "${SQ_OVER_BARE}" "${SQ_OVER_UPD}"
git -C "${SQ_OVER_UPD}" config user.email "test@example.com"
git -C "${SQ_OVER_UPD}" config user.name "Test"
git -C "${SQ_OVER_UPD}" fetch -q "${WT_SQ_OVER}" "$(git -C "${WT_SQ_OVER}" rev-parse HEAD)"
git -C "${SQ_OVER_UPD}" merge --squash -q FETCH_HEAD
git -C "${SQ_OVER_UPD}" commit -q -m "squash merge limit 20"
printf 'limit = 30\n' >"${SQ_OVER_UPD}/cfg.py"
git -C "${SQ_OVER_UPD}" add cfg.py
git -C "${SQ_OVER_UPD}" commit -q -m "follow-up overlapping edit limit 30"
git -C "${SQ_OVER_UPD}" push -q origin main
git -C "${SQ_OVER_CLONE}" fetch -q origin

PATH="${MOCK_BIN_EMPTY}:${PATH}" check_exit "check-throttle recognizes squash merge despite later overlapping upstream edit" 0 \
	"${TARGET_SCRIPT}" check-throttle --repo abhimehro/sq-over --worktree-root "${SQ_OVER_WT_ROOT}" --include-worktrees --repo-path "${SQ_OVER_CLONE}" --max-open 1
check_exit "cleanup --prune-merged runs on squash-then-edited candidate" 0 \
	"${TARGET_SCRIPT}" cleanup --worktree-root "${SQ_OVER_WT_ROOT}" --prune-merged
check "cleanup --prune-merged removed squash-then-edited worktree" test ! -d "${WT_SQ_OVER}"

echo ""
echo "Summary: PASS=${PASS} FAIL=${FAIL}"
[[ ${FAIL} -eq 0 ]]
