#!/usr/bin/env bash
#
# Unit tests for scripts/git-hooks/pre-commit-credential-scan.sh
#
# Covers the hook's control flow with a mock gitleaks (discovery via GITLEAKS_BIN
# and via PATH, staged/no-staged short-circuit, finding vs tool-error exit codes,
# both bypass aliases, strict vs skip-with-warning when the tool is absent) plus
# the Trunk action wiring that makes the hook fire at all.
#
# One case runs the REAL gitleaks end to end; it prints SKIP: and continues when
# the binary is not installed (Cursor Cloud and Devin hosts do not ship it).
#
# "gitleaks absent" cannot be simulated by PATH injection alone: the hook falls
# back to absolute Homebrew paths. Per docs/TESTING.md, that case runs a
# sed-patched copy of the hook with the fallback list rewritten.
#
# No test ever writes a real credential. The positive control is a synthetic
# high-entropy string assembled at runtime from two fragments, so this file
# itself stays clean under the very scanner it is testing.

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HOOK="${REPO_ROOT}/scripts/git-hooks/pre-commit-credential-scan.sh"
HOOK_REL="scripts/git-hooks/pre-commit-credential-scan.sh"
TRUNK_YAML="${REPO_ROOT}/.trunk/trunk.yaml"

TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'test-credential-scan')"
trap 'rm -rf "${TEST_DIR}"' EXIT

ORIG_PATH="${PATH}"
BASH_BIN="$(command -v bash)"
MOCK_BIN="${TEST_DIR}/bin"
GITLEAKS_LOG="${TEST_DIR}/gitleaks-argv.log"
FAKE_HOME="${TEST_DIR}/home"
mkdir -p "${MOCK_BIN}" "${FAKE_HOME}" "${TEST_DIR}/absent"

PASS=0
FAIL=0
SKIP=0

ok() {
	echo "✓ $*"
	PASS=$((PASS + 1))
}
bad() {
	echo "✗ $*"
	FAIL=$((FAIL + 1))
}
skipped() {
	echo "SKIP: $*"
	SKIP=$((SKIP + 1))
}

expect_status() {
	local name="$1" expected="$2" actual="$3"
	if [[ ${actual} -eq ${expected} ]]; then
		ok "${name} (exit ${actual})"
	else
		bad "${name} (expected exit ${expected}, got ${actual})"
	fi
}

output_has() {
	local name="$1" needle="$2"
	# Here-string, not a pipe: `grep -q` exits on first match, which SIGPIPEs the
	# writer, and pipefail would report that as a failed match.
	if grep -qF -- "${needle}" <<<"${HOOK_OUTPUT}"; then
		ok "${name}"
	else
		bad "${name} (output lacks: ${needle})"
	fi
}

log_has() {
	local name="$1" needle="$2"
	if grep -qF -- "${needle}" "${GITLEAKS_LOG}" 2>/dev/null; then
		ok "${name}"
	else
		bad "${name} (gitleaks argv lacks: ${needle})"
	fi
}

log_lacks() {
	local name="$1" needle="$2"
	if grep -qF -- "${needle}" "${GITLEAKS_LOG}" 2>/dev/null; then
		bad "${name} (gitleaks argv unexpectedly has: ${needle})"
	else
		ok "${name}"
	fi
}

log_empty() {
	local name="$1"
	if [[ -s ${GITLEAKS_LOG} ]]; then
		bad "${name} (gitleaks was invoked: $(wc -l <"${GITLEAKS_LOG}" | tr -d ' ') call(s))"
	else
		ok "${name}"
	fi
}

reset_log() { : >"${GITLEAKS_LOG}"; }

# write_mock_gitleaks <exit-status>
write_mock_gitleaks() {
	local status="$1"
	cat >"${MOCK_BIN}/gitleaks" <<EOF
#!/usr/bin/env bash
echo "ARGV: \$*" >>"${GITLEAKS_LOG}"
exit ${status}
EOF
	chmod +x "${MOCK_BIN}/gitleaks"
}

make_repo() {
	local dir="$1"
	mkdir -p "${dir}"
	git -C "${dir}" init --quiet
	git -C "${dir}" config user.email "test@example.invalid"
	git -C "${dir}" config user.name "Credential Scan Test"
	git -C "${dir}" config commit.gpgsign false
	# Never inherit a developer's core.hooksPath; this fixture must not fire hooks.
	git -C "${dir}" config core.hooksPath "${dir}/.no-hooks"
	printf 'seed\n' >"${dir}/seed.txt"
	git -C "${dir}" add seed.txt
	git -C "${dir}" commit --quiet -m "seed"
}

stage_clean() {
	local dir="$1"
	printf 'greeting = "hello"\n' >"${dir}/clean.py"
	git -C "${dir}" add clean.py
}

HOOK_STATUS=0
HOOK_OUTPUT=""
RUN_HOOK="${HOOK}"
RUN_PATH="${ORIG_PATH}"

# run_hook [VAR=value ...] -- executes the hook inside REPO with a clean env.
run_hook() {
	local repo="${REPO}"
	HOOK_STATUS=0
	HOOK_OUTPUT="$(
		cd "${repo}" &&
			env -i \
				HOME="${FAKE_HOME}" \
				PATH="${RUN_PATH}" \
				"$@" \
				"${BASH_BIN}" "${RUN_HOOK}" 2>&1
	)" || HOOK_STATUS=$?
}

# ---------------------------------------------------------------- static checks

if [[ ! -f ${HOOK} ]]; then
	echo "FAIL: hook missing: ${HOOK}"
	exit 1
fi

if [[ -x ${HOOK} ]]; then
	ok "hook is executable"
else
	bad "hook is not executable (git cannot run a non-executable hook)"
fi

if [[ $(head -n1 "${HOOK}") == "#!/usr/bin/env bash" ]]; then
	ok "hook shebang is bash"
else
	bad "hook shebang is not bash: $(head -n1 "${HOOK}")"
fi

# Regression guard: .gitignore has a broad `*secret*` rule, so a hook named
# *secret* would be silently uncommittable and the gate would never ship.
if git -C "${REPO_ROOT}" rev-parse --git-dir >/dev/null 2>&1; then
	ign=0
	git -C "${REPO_ROOT}" check-ignore -q "${HOOK_REL}" || ign=$?
	if [[ ${ign} -eq 1 ]]; then
		ok "hook path is not gitignored"
	elif [[ ${ign} -eq 0 ]]; then
		bad "hook path IS gitignored - the gate would never be committed"
	else
		skipped "git check-ignore errored (${ign})"
	fi
else
	skipped "not a git repository; cannot check ignore status"
fi

# ------------------------------------------------------------- Trunk wiring

if [[ ! -f ${TRUNK_YAML} ]]; then
	bad "missing .trunk/trunk.yaml"
else
	ACTIONS_SECTION="$(awk '/^actions:$/{f=1;next} f&&/^[A-Za-z]/{f=0} f' "${TRUNK_YAML}")"
	CREDENTIAL_BLOCK="$(awk '/^    - id: credential-scan$/{f=1;next} f&&/^    - id: /{f=0} f' <<<"${ACTIONS_SECTION}")"
	ENABLED_LIST="$(awk '/^  enabled:$/{f=1;next} f&&/^  [A-Za-z]/{f=0} f' <<<"${ACTIONS_SECTION}")"
	DISABLED_LIST="$(awk '/^  disabled:$/{f=1;next} f&&/^  [A-Za-z]/{f=0} f' <<<"${ACTIONS_SECTION}")"

	if grep -qF "run: ${HOOK_REL}" <<<"${CREDENTIAL_BLOCK}"; then
		ok "trunk.yaml defines credential-scan -> ${HOOK_REL}"
	else
		bad "trunk.yaml has no credential-scan action running ${HOOK_REL}"
	fi

	if grep -qE 'git_hooks: \[pre-commit\]' <<<"${CREDENTIAL_BLOCK}"; then
		ok "credential-scan triggers on pre-commit"
	else
		bad "credential-scan is not wired to the pre-commit git hook"
	fi

	if grep -qxE '[[:space:]]*- credential-scan' <<<"${ENABLED_LIST}"; then
		ok "credential-scan is in actions.enabled"
	else
		bad "credential-scan is missing from actions.enabled (hook will never be synced)"
	fi

	if grep -qxE '[[:space:]]*- trufflehog-pre-commit' <<<"${DISABLED_LIST}"; then
		ok "trufflehog-pre-commit stays disabled (one scanner per trigger)"
	else
		bad "trufflehog-pre-commit is no longer disabled - two scanners on pre-commit"
	fi
fi

# ------------------------------------------------- sed-patched "absent" variant

HOOK_NOABS="${TEST_DIR}/hook-no-abs-fallback.sh"
sed -E 's|^([[:space:]]*)for candidate in .*$|\1for candidate in /nonexistent-gitleaks-candidate; do|' \
	"${HOOK}" >"${HOOK_NOABS}"
chmod +x "${HOOK_NOABS}"

if grep -qF '/nonexistent-gitleaks-candidate' "${HOOK_NOABS}" &&
	! grep -qF '/opt/homebrew/bin/gitleaks' "${HOOK_NOABS}"; then
	PATCH_VARIANT_OK=1
	ok "absent-tool variant patched the absolute fallback list"
else
	PATCH_VARIANT_OK=0
	bad "could not patch the absolute gitleaks fallback list; hook resolver changed shape"
fi

# --------------------------------------------------------------- behavior tests

REPO="${TEST_DIR}/repo"
make_repo "${REPO}"

# 1. Nothing staged: short-circuit before ever resolving gitleaks.
write_mock_gitleaks 0
reset_log
RUN_PATH="${MOCK_BIN}:/usr/bin:/bin"
run_hook
expect_status "nothing staged exits 0" 0 "${HOOK_STATUS}"
log_empty "nothing staged does not invoke gitleaks"

# 2. Staged clean content: scan runs, with --staged and --redact.
stage_clean "${REPO}"
write_mock_gitleaks 0
reset_log
run_hook "GITLEAKS_BIN=${MOCK_BIN}/gitleaks"
expect_status "staged clean content exits 0" 0 "${HOOK_STATUS}"
log_has "invokes the git subcommand" "ARGV: git"
log_has "scans staged blobs only" "--staged"
log_has "always redacts its own output" "--redact"
log_lacks "does not scan full history" "--log-opts"

# 3. A finding (exit 1) blocks the commit.
write_mock_gitleaks 1
reset_log
run_hook "GITLEAKS_BIN=${MOCK_BIN}/gitleaks"
expect_status "a finding blocks the commit" 1 "${HOOK_STATUS}"
output_has "reports the block" "Commit blocked"
output_has "points at the 1Password remediation" "op://"

# 4. A tool error (any other non-zero) fails closed, not open.
write_mock_gitleaks 2
reset_log
run_hook "GITLEAKS_BIN=${MOCK_BIN}/gitleaks"
expect_status "tool error fails closed" 1 "${HOOK_STATUS}"
output_has "distinguishes tool error from finding" "tool error"

# 5. Both bypass aliases short-circuit without scanning.
write_mock_gitleaks 1
reset_log
run_hook "SKIP_CREDENTIAL_SCAN=1" "GITLEAKS_BIN=${MOCK_BIN}/gitleaks"
expect_status "SKIP_CREDENTIAL_SCAN=1 bypasses" 0 "${HOOK_STATUS}"
log_empty "SKIP_CREDENTIAL_SCAN=1 does not invoke gitleaks"

reset_log
run_hook "CREDENTIAL_SCAN_SKIP=1" "GITLEAKS_BIN=${MOCK_BIN}/gitleaks"
expect_status "CREDENTIAL_SCAN_SKIP=1 bypasses" 0 "${HOOK_STATUS}"
log_empty "CREDENTIAL_SCAN_SKIP=1 does not invoke gitleaks"

# 6. Discovery order: explicit GITLEAKS_BIN wins when gitleaks is not on PATH.
write_mock_gitleaks 0
reset_log
RUN_PATH="/usr/bin:/bin"
run_hook "GITLEAKS_BIN=${MOCK_BIN}/gitleaks"
expect_status "GITLEAKS_BIN override is honored" 0 "${HOOK_STATUS}"
log_has "GITLEAKS_BIN target was executed" "ARGV: git"

# 7. Discovery order: PATH lookup works when GITLEAKS_BIN is unset.
RUN_PATH="${MOCK_BIN}:/usr/bin:/bin"
reset_log
run_hook
expect_status "PATH-discovered gitleaks is honored" 0 "${HOOK_STATUS}"
log_has "PATH gitleaks was executed" "ARGV: git"

# 8/9. Tool absent: skip-with-warning by default, fail under STRICT.
if [[ ${PATCH_VARIANT_OK} -eq 1 ]]; then
	RUN_HOOK="${HOOK_NOABS}"
	RUN_PATH="/usr/bin:/bin"

	reset_log
	run_hook
	expect_status "absent gitleaks exits 0 by default" 0 "${HOOK_STATUS}"
	output_has "absent gitleaks warns it skipped" "SKIPPED"
	log_empty "absent gitleaks is not invoked"

	reset_log
	run_hook "STRICT_CREDENTIAL_SCAN=1"
	expect_status "STRICT_CREDENTIAL_SCAN=1 fails when gitleaks is absent" 1 "${HOOK_STATUS}"
	output_has "strict mode names the variable" "STRICT_CREDENTIAL_SCAN=1"

	RUN_HOOK="${HOOK}"
else
	skipped "absent-tool cases (fallback list could not be patched)"
	skipped "absent-tool strict case (fallback list could not be patched)"
fi

# 10. End-to-end with the real scanner: a staged high-entropy credential blocks,
#     clean staged content passes. Fragments are concatenated at runtime so this
#     committed file contains no string gitleaks would flag.
REAL_GITLEAKS="$(PATH="${ORIG_PATH}" command -v gitleaks 2>/dev/null || true)"
if [[ -z ${REAL_GITLEAKS} ]]; then
	skipped "real-gitleaks end-to-end detection (gitleaks not installed)"
	skipped "real-gitleaks end-to-end clean pass (gitleaks not installed)"
else
	INT_REPO="${TEST_DIR}/repo-int"
	make_repo "${INT_REPO}"
	REPO="${INT_REPO}"
	RUN_PATH="${ORIG_PATH}"

	printf 'api_key = "%s%s"\n' 'aB3xK9mQ2pL7' 'vR5nT8wY1zC4' >"${INT_REPO}/leak.py"
	git -C "${INT_REPO}" add leak.py
	run_hook
	expect_status "real gitleaks blocks a staged credential" 1 "${HOOK_STATUS}"

	git -C "${INT_REPO}" reset --quiet leak.py
	rm -f "${INT_REPO}/leak.py"
	stage_clean "${INT_REPO}"
	run_hook
	expect_status "real gitleaks passes clean staged content" 0 "${HOOK_STATUS}"

	REPO="${TEST_DIR}/repo"
fi

echo ""
echo "Passed: ${PASS}  Failed: ${FAIL}  Skipped: ${SKIP}"
if [[ ${FAIL} -gt 0 ]]; then
	exit 1
fi
exit 0
