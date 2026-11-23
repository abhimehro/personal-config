#!/usr/bin/env bash
#
# Isolated Git Worktree & Verification Runner for Antigravity Proactive Sweeps.
# Protects primary checkouts, disables push remotes in local-only mode, enforces
# tamper-evident checks on build/lock/script/test harnesses before running gates,
# enforces a base-relative semantic test-coverage gate (AST diff + test count +
# static checks) so silently dropped coverage cannot ride a green suite,
# enforces numeric-equivalence checks on research repositories, checks file
# collisions against both open PRs and live candidate worktrees, enforces
# local/remote candidate throttles across every registered worktree, and prunes
# stale empty worktrees past their 21-day TTL while preserving unmerged
# candidates.

set -Eeuo pipefail

DEFAULT_WT_ROOT="${HOME}/.gemini/antigravity/worktrees"
PATCH_ID_CACHE_DIR=""
VERBATIM_PATCH_ID_CHECKED=0
VERBATIM_PATCH_ID_OK=0
LAST_FETCH_TRANSPORT=""
FETCH_FAILURE_SUMMARY=""
FETCH_ERR_TMP=""
GH_OUT_TMP=""
GH_ERR_TMP=""
PRUNED_MERGED_COUNT=0

cleanup_runtime_temps() {
	if [[ -n ${PATCH_ID_CACHE_DIR} ]] && [[ -d ${PATCH_ID_CACHE_DIR} ]]; then
		rm -rf "${PATCH_ID_CACHE_DIR}"
	fi
	if [[ -n ${FETCH_ERR_TMP} ]] && [[ -f ${FETCH_ERR_TMP} ]]; then
		rm -f "${FETCH_ERR_TMP}"
	fi
	if [[ -n ${GH_OUT_TMP} ]] && [[ -f ${GH_OUT_TMP} ]]; then
		rm -f "${GH_OUT_TMP}"
	fi
	if [[ -n ${GH_ERR_TMP} ]] && [[ -f ${GH_ERR_TMP} ]]; then
		rm -f "${GH_ERR_TMP}"
	fi
}

usage() {
	cat <<'EOF'
Usage:
  proactive-worktree.sh prepare --repo-path <dir> --lens <lens> [--worktree-root <dir>] [--mode <local|draft-pr>]
  proactive-worktree.sh verify --worktree <dir> [--lens <lens>] [--test-cmd <cmd>] [--numeric-check-cmd <cmd>] [--allow-harness-changes] [--allow-test-edits] [--expected-test-count <n>]
  proactive-worktree.sh check-collisions --repo <owner/name> --file <relpath> [--file <relpath> ...] [--repo-path <dir>] [--include-worktrees]
  proactive-worktree.sh check-throttle --repo <owner/name> [--worktree-root <dir>] [--max-open <n>] [--max-age-days <days>] [--now-epoch <sec>] [--repo-path <dir>] [--include-worktrees]
  proactive-worktree.sh cleanup [--worktree-root <dir>] [--ttl-days <days>] [--prune-merged]
  proactive-worktree.sh preflight --repo <owner/name> --repo-path <dir> [--worktree-root <dir>] [--auto-heal] [--skip-fetch]
  proactive-worktree.sh print-test-cmd --repo-name <name>

verify exit codes:
  0 clean, 1 usage, 2 BLOCKED (path policy or semantic test-coverage gate),
  3 BLOCKED (lens policy), 6 could not establish a fresh origin ref

check-collisions exit codes:
  0 clean, 1 usage, 4 COLLISION (open PR or live candidate worktree),
  5 UNVERIFIABLE (truncated PR listing), 6 could not enumerate worktrees or
  establish a fresh origin ref

check-throttle exit codes:
  0 clean, 1 usage, 5 THROTTLED/UNVERIFIABLE, 6 could not establish a fresh
  origin ref

preflight exit codes:
  0 PASS, 1 usage or invalid repo-path, 6 git fetch or gh auth failure,
  7 missing verification toolchain
EOF
}

is_research_repo() {
	local name="$1"
	case "${name}" in
	Hydrograph_Versus_Seatek_Sensors_Project | Seatek_Analysis | series_correction_project_updated)
		return 0
		;;
	*)
		return 1
		;;
	esac
}

default_test_cmd_for_repo() {
	local name="$1"
	case "${name}" in
	personal-config)
		printf '%s' "make lint-errors && bash tests/test_lib_common.sh && bash tests/test_lib_dns_utils.sh && python3 -m unittest tests.test_path_validation"
		;;
	ctrld-sync)
		printf '%s' "uv run --frozen --all-extras pytest tests/ test_main.py -q && uv run --frozen --all-extras ruff check ."
		;;
	email-security-pipeline)
		printf '%s' "python3 -m pytest -q"
		;;
	Hydrograph_Versus_Seatek_Sensors_Project)
		printf '%s' "MPLBACKEND=Agg python3 -m pytest tests/ -q && flake8 src/ tests/"
		;;
	series_correction_project_updated)
		printf '%s' "MPLBACKEND=Agg python3 -m pytest scripts/tests/ -q"
		;;
	Seatek_Analysis)
		printf '%s' "Rscript -e \"library(testthat); source('Updated_Seatek_Analysis.R', local = TRUE); testthat::test_dir('tests/testthat', reporter = 'summary')\""
		;;
	repoprompt-ce)
		printf '%s' ".agents/skills/rpce-contribution-check/scripts/preflight.sh commit"
		;;
	*)
		printf '%s' "python3 -m pytest -q"
		;;
	esac
}

resolve_int_env() {
	local var_name="$1"
	local raw_val="$2"
	local default_val="$3"
	local min_val="$4"

	if [[ -z ${raw_val} ]]; then
		printf '%s' "${default_val}"
		return 0
	fi
	if [[ ! ${raw_val} =~ ^[0-9]+$ ]]; then
		echo "[WARN] Ignoring invalid ${var_name}=${raw_val}; using default ${default_val}" >&2
		printf '%s' "${default_val}"
		return 0
	fi
	local num_val=""
	num_val="$((10#${raw_val}))"
	if [[ ${num_val} -lt ${min_val} ]]; then
		echo "[WARN] Ignoring invalid ${var_name}=${raw_val}; using default ${default_val}" >&2
		printf '%s' "${default_val}"
		return 0
	fi
	printf '%s' "${num_val}"
}

run_with_timeout() {
	local timeout_s="$1"
	shift
	if [[ $# -eq 0 ]]; then
		echo "[ERROR] run_with_timeout requires a command" >&2
		return 1
	fi
	local rc=0
	python3 - "${timeout_s}" "$@" <<'PY' || rc=$?
import subprocess
import sys

try:
    timeout_val = float(sys.argv[1])
except ValueError:
    sys.stderr.write(f"[ERROR] Invalid timeout value: {sys.argv[1]}\n")
    sys.exit(1)

cmd = sys.argv[2:]
try:
    proc = subprocess.run(cmd, timeout=timeout_val)
    sys.exit(proc.returncode)
except subprocess.TimeoutExpired:
    sys.stderr.write(f"[ERROR] Command timed out after {sys.argv[1]}s: {cmd[0]}\n")
    sys.exit(124)
except FileNotFoundError:
    sys.stderr.write(f"[ERROR] Command not found: {cmd[0]}\n")
    sys.exit(127)
PY
	return "${rc}"
}

is_github_ssh_url() {
	local url="$1"
	case "${url}" in
	git@github.com:* | ssh://git@github.com/*)
		return 0
		;;
	*)
		return 1
		;;
	esac
}

run_fetch_attempts() {
	local label="$1"
	local retries="$2"
	local backoff_s="$3"
	local timeout_s="$4"
	shift 4

	local attempt=1
	local last_err=""
	local rc=0
	local sleep_s=0

	FETCH_ERR_TMP="$(mktemp "${TMPDIR:-/tmp}/proactive-fetch-err.XXXXXX")"

	while [[ ${attempt} -le ${retries} ]]; do
		: >"${FETCH_ERR_TMP}"
		rc=0
		run_with_timeout "${timeout_s}" "$@" >/dev/null 2>"${FETCH_ERR_TMP}" || rc=$?
		if [[ ${rc} -eq 0 ]]; then
			rm -f "${FETCH_ERR_TMP}"
			FETCH_ERR_TMP=""
			LAST_FETCH_TRANSPORT="${label}"
			return 0
		fi
		last_err="$(awk '{ gsub(/\r/, "") } NF { line = $0 } END { print line }' "${FETCH_ERR_TMP}" 2>/dev/null || true)"
		if [[ -z ${last_err} ]]; then
			last_err="exit ${rc}"
		fi
		if [[ ${attempt} -lt ${retries} ]] && [[ ${backoff_s} -gt 0 ]]; then
			sleep_s=$((backoff_s * attempt))
			sleep "${sleep_s}"
		fi
		attempt=$((attempt + 1))
	done

	rm -f "${FETCH_ERR_TMP}"
	FETCH_ERR_TMP=""
	if [[ -n ${FETCH_FAILURE_SUMMARY} ]]; then
		FETCH_FAILURE_SUMMARY="${FETCH_FAILURE_SUMMARY}; ${label}: ${last_err}"
	else
		FETCH_FAILURE_SUMMARY="${label}: ${last_err}"
	fi
	return 1
}

fetch_origin_resilient() {
	local repo_path="$1"
	LAST_FETCH_TRANSPORT=""
	FETCH_FAILURE_SUMMARY=""

	local retries=""
	local backoff_s=""
	local timeout_s=""
	local force_ssh=""
	retries="$(resolve_int_env "PROACTIVE_FETCH_RETRIES" "${PROACTIVE_FETCH_RETRIES:-}" 2 1)"
	backoff_s="$(resolve_int_env "PROACTIVE_FETCH_BACKOFF_S" "${PROACTIVE_FETCH_BACKOFF_S:-}" 2 0)"
	timeout_s="$(resolve_int_env "PROACTIVE_FETCH_TIMEOUT_S" "${PROACTIVE_FETCH_TIMEOUT_S:-}" 30 1)"
	force_ssh="${PROACTIVE_FETCH_FORCE_SSH:-0}"
	if [[ -n ${force_ssh} ]] && [[ ${force_ssh} != "0" ]] && [[ ${force_ssh} != "1" ]]; then
		echo "[WARN] Ignoring invalid PROACTIVE_FETCH_FORCE_SSH=${force_ssh}; using default 0" >&2
		force_ssh="0"
	fi

	local origin_url=""
	origin_url="$(git -C "${repo_path}" remote get-url origin 2>/dev/null || true)"

	if is_github_ssh_url "${origin_url}"; then
		if [[ ${force_ssh} != "1" ]]; then
			if command -v gh >/dev/null 2>&1; then
				if run_fetch_attempts "https-gh" "${retries}" "${backoff_s}" "${timeout_s}" \
					env GIT_TERMINAL_PROMPT=0 \
					git -C "${repo_path}" \
					-c credential.helper= \
					-c "credential.helper=!gh auth git-credential" \
					-c "url.https://github.com/.insteadOf=git@github.com:" \
					-c "url.https://github.com/.insteadOf=ssh://git@github.com/" \
					fetch --prune --quiet origin; then
					return 0
				fi
			fi
			if run_fetch_attempts "https-anon" "${retries}" "${backoff_s}" "${timeout_s}" \
				env GIT_TERMINAL_PROMPT=0 \
				git -C "${repo_path}" \
				-c credential.helper= \
				-c "url.https://github.com/.insteadOf=git@github.com:" \
				-c "url.https://github.com/.insteadOf=ssh://git@github.com/" \
				fetch --prune --quiet origin; then
				return 0
			fi
		fi
		run_fetch_attempts "ssh-batch" "${retries}" "${backoff_s}" "${timeout_s}" \
			env GIT_TERMINAL_PROMPT=0 \
			GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10" \
			git -C "${repo_path}" fetch --prune --quiet origin
		return $?
	fi

	run_fetch_attempts "direct" "${retries}" "${backoff_s}" "${timeout_s}" \
		env GIT_TERMINAL_PROMPT=0 \
		GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10" \
		git -C "${repo_path}" fetch --prune --quiet origin
}

run_gh_resilient() {
	local retries=""
	local backoff_s=""
	local timeout_s=""
	retries="$(resolve_int_env "PROACTIVE_GH_RETRIES" "${PROACTIVE_GH_RETRIES:-}" 3 1)"
	backoff_s="$(resolve_int_env "PROACTIVE_GH_BACKOFF_S" "${PROACTIVE_GH_BACKOFF_S:-}" 2 0)"
	timeout_s="$(resolve_int_env "PROACTIVE_GH_TIMEOUT_S" "${PROACTIVE_GH_TIMEOUT_S:-}" 30 1)"

	local wants_json=0
	local arg=""
	for arg in "$@"; do
		if [[ ${arg} == "--json" ]] || [[ ${arg} == --json=* ]]; then
			wants_json=1
			break
		fi
	done

	local cmd_desc="$*"
	GH_OUT_TMP="$(mktemp "${TMPDIR:-/tmp}/proactive-gh-out.XXXXXX")"
	GH_ERR_TMP="$(mktemp "${TMPDIR:-/tmp}/proactive-gh-err.XXXXXX")"

	local attempt=1
	local rc=0
	local err_text=""
	local sleep_s=0
	local permanent_re='not logged into any GitHub hosts|HTTP 401|HTTP 404|Could not resolve to a Repository|unknown flag'

	while [[ ${attempt} -le ${retries} ]]; do
		: >"${GH_OUT_TMP}"
		: >"${GH_ERR_TMP}"
		rc=0
		run_with_timeout "${timeout_s}" gh "$@" >"${GH_OUT_TMP}" 2>"${GH_ERR_TMP}" || rc=$?

		if [[ ${rc} -eq 0 ]]; then
			if [[ ${wants_json} -eq 1 ]]; then
				if python3 -c 'import json, sys; json.load(open(sys.argv[1], encoding="utf-8"))' "${GH_OUT_TMP}" 2>/dev/null; then
					cat "${GH_OUT_TMP}"
					rm -f "${GH_OUT_TMP}" "${GH_ERR_TMP}"
					GH_OUT_TMP=""
					GH_ERR_TMP=""
					return 0
				fi
				rc=1
				printf '%s\n' "invalid JSON output from gh" >>"${GH_ERR_TMP}"
			else
				cat "${GH_OUT_TMP}"
				rm -f "${GH_OUT_TMP}" "${GH_ERR_TMP}"
				GH_OUT_TMP=""
				GH_ERR_TMP=""
				return 0
			fi
		fi

		err_text="$(awk '{ gsub(/\r/, ""); gsub(/^[[:space:]]+|[[:space:]]+$/, "") } NF { out = (out ? out "; " $0 : $0) } END { print out }' "${GH_ERR_TMP}" 2>/dev/null || true)"
		if [[ -z ${err_text} ]]; then
			err_text="exit ${rc}"
		fi

		if [[ ${rc} -eq 127 ]] || grep -qE "${permanent_re}" "${GH_ERR_TMP}" 2>/dev/null; then
			rm -f "${GH_OUT_TMP}" "${GH_ERR_TMP}"
			GH_OUT_TMP=""
			GH_ERR_TMP=""
			echo "[ERROR] gh ${cmd_desc} failed after ${attempt} attempt(s): ${err_text}" >&2
			exit 6
		fi

		if [[ ${attempt} -lt ${retries} ]] && [[ ${backoff_s} -gt 0 ]]; then
			sleep_s=$((backoff_s * attempt))
			sleep "${sleep_s}"
		fi
		attempt=$((attempt + 1))
	done

	local total_attempts=$((attempt - 1))
	rm -f "${GH_OUT_TMP}" "${GH_ERR_TMP}"
	GH_OUT_TMP=""
	GH_ERR_TMP=""
	echo "[ERROR] gh ${cmd_desc} failed after ${total_attempts} attempt(s): ${err_text}" >&2
	exit 6
}

resolve_verify_path() {
	local wt_path="$1"
	local repo_path="$2"
	local test_cmd="$3"
	local out_path="${PATH}"
	if [[ ${test_cmd} != *"uv run"* ]]; then
		if [[ -d "${wt_path}/.venv/bin" ]]; then
			out_path="${wt_path}/.venv/bin:${out_path}"
		elif [[ -n ${repo_path} ]] && [[ -d "${repo_path}/.venv/bin" ]]; then
			out_path="${repo_path}/.venv/bin:${out_path}"
		fi
	fi
	printf '%s' "${out_path}"
}

resolve_default_branch() {
	local repo_path="$1"
	local sym=""
	sym="$(git -C "${repo_path}" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
	if [[ -n ${sym} ]]; then
		printf '%s' "${sym#origin/}"
		return 0
	fi
	if command -v gh >/dev/null 2>&1; then
		local gh_branch=""
		gh_branch="$(cd "${repo_path}" && gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null || true)"
		if [[ -n ${gh_branch} ]]; then
			printf '%s' "${gh_branch}"
			return 0
		fi
	fi
	printf '%s' "main"
}

cmd_prepare() {
	local repo_path=""
	local lens=""
	local wt_root="${DEFAULT_WT_ROOT}"
	local mode="local"

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--repo-path)
			repo_path="$2"
			shift 2
			;;
		--lens)
			lens="$2"
			shift 2
			;;
		--worktree-root)
			wt_root="$2"
			shift 2
			;;
		--mode)
			mode="$2"
			shift 2
			;;
		*)
			echo "[ERROR] Unknown flag for prepare: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -z ${repo_path} ]] || [[ -z ${lens} ]]; then
		echo "[ERROR] prepare requires --repo-path and --lens" >&2
		exit 1
	fi

	# Allowlists, not denylists: the research-repo gates compare lens by exact
	# string and only mode "local" disables the push URL, so a typo such as
	# "Palette" or "perf" would otherwise silently skip a safety boundary.
	case "${lens}" in
	sentinel | bolt | palette | code-health) ;;
	*)
		echo "[ERROR] Unknown lens: ${lens} (expected sentinel|bolt|palette|code-health)" >&2
		exit 1
		;;
	esac
	case "${mode}" in
	local | draft-pr) ;;
	*)
		echo "[ERROR] Unknown mode: ${mode} (expected local|draft-pr)" >&2
		exit 1
		;;
	esac

	mkdir -p "${wt_root}"
	wt_root="$(cd "${wt_root}" 2>/dev/null && pwd)"

	# Canonicalize so basename never yields "." or "..", and so the path stored in
	# proactive-meta.json stays valid when cleanup runs from another directory.
	# Logical pwd (not -P) keeps a symlinked repo's own name for is_research_repo.
	local canonical_repo_path=""
	canonical_repo_path="$(cd "${repo_path}" 2>/dev/null && pwd)" || canonical_repo_path=""
	if [[ -z ${canonical_repo_path} ]]; then
		echo "[ERROR] Not a git repository: ${repo_path}" >&2
		exit 1
	fi
	repo_path="${canonical_repo_path}"
	if [[ ! -d "${repo_path}/.git" ]] && ! git -C "${repo_path}" rev-parse --git-dir >/dev/null 2>&1; then
		echo "[ERROR] Not a git repository: ${repo_path}" >&2
		exit 1
	fi

	local repo_name
	repo_name="$(basename "${repo_path}")"
	if is_research_repo "${repo_name}" && [[ ${lens} == "palette" ]]; then
		echo "[ERROR] Palette lens is disabled for research repository ${repo_name}" >&2
		exit 3
	fi

	if ! fetch_origin_resilient "${repo_path}"; then
		echo "[WARN] prepare: could not refresh origin for ${repo_path}; falling back to existing local ref (${FETCH_FAILURE_SUMMARY})" >&2
	fi

	local default_branch
	default_branch="$(resolve_default_branch "${repo_path}")"
	local base_ref="origin/${default_branch}"
	if ! git -C "${repo_path}" rev-parse --verify --quiet "${base_ref}" >/dev/null; then
		base_ref="${default_branch}"
	fi
	local base_sha
	base_sha="$(git -C "${repo_path}" rev-parse "${base_ref}")"

	local ts
	ts="$(date -u +%Y%m%dT%H%M%SZ)"
	local nonce="${RANDOM}"
	local slug="proactive-${repo_name}-${lens}-${ts}-$$-${nonce}"
	local branch_name="proactive/${lens}-${ts}-$$-${nonce}"
	local wt_path="${wt_root}/${slug}"

	mkdir -p "${wt_root}"
	chmod 700 "${wt_root}" 2>/dev/null || true
	git -C "${repo_path}" worktree add --quiet -b "${branch_name}" "${wt_path}" "${base_sha}"

	if [[ ${mode} == "local" ]]; then
		git -C "${repo_path}" config extensions.worktreeConfig true
		git -C "${wt_path}" config --worktree remote.origin.pushurl "DISABLED"
		# Prevent 1Password op-ssh-sign Touch ID hangs during unattended 2B
		# candidate commits without touching ~/.gitconfig or primary checkouts.
		git -C "${wt_path}" config --worktree commit.gpgsign false
	fi

	local wt_git_dir
	wt_git_dir="$(git -C "${wt_path}" rev-parse --git-dir)"
	python3 - "${wt_git_dir}/proactive-meta.json" "${repo_name}" "${repo_path}" "${base_sha}" "${default_branch}" "${lens}" "${mode}" "${ts}" <<'PY'
import json
import pathlib
import sys

meta_path = pathlib.Path(sys.argv[1])
meta = {
    "repo_name": sys.argv[2],
    "repo_path": sys.argv[3],
    "base_sha": sys.argv[4],
    "default_branch": sys.argv[5],
    "lens": sys.argv[6],
    "mode": sys.argv[7],
    "created_at": sys.argv[8],
}
meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
PY

	printf '%s\n' "${wt_path}"
}

is_protected_harness_path() {
	local path="$1"
	case "${path}" in
	Makefile | GNUmakefile | Justfile | pyproject.toml | uv.lock | setup.py | setup.cfg | tox.ini | noxfile.py | pytest.ini | .ruff.toml | ruff.toml | .python-version | conftest.py | package.json | package-lock.json | .pre-commit-config.yaml | renv.lock | .Rprofile | .Renviron | DESCRIPTION | NAMESPACE | AGENTS.md | GEMINI.md | CLAUDE.md | .jules/sentinel.md | .gitignore | .gitattributes)
		return 0
		;;
	requirements*.txt | */requirements*.txt)
		return 0
		;;
	.trunk/* | .github/* | .agents/* | scripts/* | Scripts/* | */scripts/* | */Scripts/*)
		return 0
		;;
	*/Makefile | */pyproject.toml | */uv.lock | */conftest.py | */pytest.ini | */AGENTS.md | */GEMINI.md | */CLAUDE.md | */.gitignore | */.gitattributes | */setup.py | */setup.cfg | */tox.ini | */noxfile.py | */package.json)
		return 0
		;;
	*)
		return 1
		;;
	esac
}

is_protected_test_path() {
	local path="$1"
	case "${path}" in
	tests/* | */tests/* | Tests/* | */Tests/* | test/* | */test/* | test_*.py | */test_*.py | test-*.R | */test-*.R | *_test.py | run_tests.sh | */run_tests.sh)
		return 0
		;;
	*)
		return 1
		;;
	esac
}

is_python_test_path() {
	local path="$1"
	# Mirrors pytest's own discovery convention (test_*.py or *_test.py). In a
	# case pattern '*' also matches '/', so *_test.py already covers nested
	# paths while test_*.py needs the explicit */ variant.
	case "${path}" in
	test_*.py | */test_*.py | *_test.py)
		return 0
		;;
	*)
		return 1
		;;
	esac
}

# A verdict that compares HEAD against origin/<branch> is only as true as the
# remote-tracking ref it reads. A stale ref turns "already merged" into a false
# pass, so refresh first and fail closed when we cannot. Deliberately NOT called
# from has_unreviewed_worktree_commits: that helper also serves cleanup, where a
# network outage must not block pruning (its safe default is to preserve).
require_fresh_origin_ref() {
	local repo_path="$1"
	if [[ -z ${repo_path} ]] || [[ ! -d ${repo_path} ]]; then
		echo "[ERROR] Cannot refresh origin refs: no resolvable repository path for a ref-based verdict" >&2
		exit 6
	fi
	if ! fetch_origin_resilient "${repo_path}"; then
		echo "[ERROR] git fetch failed for ${repo_path} (tried: ${FETCH_FAILURE_SUMMARY}); refusing to emit a ref-based verdict from a possibly stale origin/*" >&2
		exit 6
	fi
}

# Static checks on touched Python files. Two tiers:
#   1. AST parse - dependency-free floor, catches files that do not even parse.
#      Uses ast rather than py_compile so no __pycache__ is written into the
#      worktree under verification.
#   2. Undefined-name (F82) - ruff when present, pyflakes otherwise, and a
#      FAIL-CLOSED exit when neither is. ruff's F82 is the same check
#      Seatek_Analysis CI already runs
#      (pr-validation.yml: ruff --select=E9,F63,F7,F82).
run_python_static_checks() {
	local wt_path="$1"
	local repo_path="$2"
	shift 2

	if ! (
		cd "${wt_path}" && python3 - "$@" <<'PY'
import ast
import sys

failed = False
for rel in sys.argv[1:]:
    try:
        with open(rel, encoding="utf-8", errors="replace") as handle:
            ast.parse(handle.read(), filename=rel)
    except SyntaxError as exc:
        sys.stderr.write(f"SYNTAX: {rel}:{exc.lineno}: {exc.msg}\n")
        failed = True
sys.exit(1 if failed else 0)
PY
	); then
		return 1
	fi

	# Resolve the undefined-name checker. uv-managed repos (ctrld-sync) ship ruff
	# through their own lockfile rather than onto PATH, so `uv run ruff` counts as
	# present - without it this gate would falsely block the best-provisioned repos.
	local -a f82_cmd=()
	if command -v ruff >/dev/null 2>&1; then
		f82_cmd=(ruff check --select=F82 --no-cache --quiet)
	elif command -v uv >/dev/null 2>&1 && [[ -f ${wt_path}/pyproject.toml ]]; then
		if [[ -f ${wt_path}/uv.lock ]]; then
			f82_cmd=(uv run --frozen --all-extras ruff check --select=F82 --no-cache --quiet)
		else
			f82_cmd=(uv run --all-extras ruff check --select=F82 --no-cache --quiet)
		fi
	elif [[ -n ${repo_path} ]] && [[ -x "${repo_path}/.venv/bin/ruff" ]]; then
		f82_cmd=("${repo_path}/.venv/bin/ruff" check --select=F82 --no-cache --quiet)
	elif [[ -n ${repo_path} ]] && [[ -x "${repo_path}/.venv/bin/python3" ]] && "${repo_path}/.venv/bin/python3" -c 'import pyflakes' >/dev/null 2>&1; then
		f82_cmd=("${repo_path}/.venv/bin/python3" -m pyflakes)
	elif python3 -c 'import pyflakes' >/dev/null 2>&1; then
		f82_cmd=(python3 -m pyflakes)
	else
		# Fail closed. This tier is a required gate, not an advisory: an AST parse
		# proves a file is syntactically valid, not that its names resolve, so
		# passing on the floor alone would let an undefined name through in any
		# path the tests do not reach. A missing linter is an environment defect,
		# and silently degrading a required check to cover it is how the gate
		# becomes decorative. ruff is pinned in requirements.txt precisely so this
		# branch is unreachable in a provisioned environment.
		echo "[ERROR] No undefined-name checker available (tried ruff, uv run ruff, repo .venv, pyflakes); refusing to emit a pass from the AST parse floor alone. Install the pinned linter (python3 -m pip install -r requirements.txt, which carries ruff) and re-run." >&2
		return 2
	fi
	(cd "${wt_path}" && "${f82_cmd[@]}" "$@")
}

# Semantic test-coverage gate: a hunk that applies cleanly can still delete
# coverage as collateral, and losing a test does not fail a suite. Compare the
# AST of every touched Python test file against the pinned base and fail on any
# lost class/method or any drop in test count, even when the suite is green.
run_semantic_test_gate() {
	local wt_path="$1"
	local base_sha="$2"
	local expected_count="$3"
	shift 3

	if [[ $# -eq 0 ]]; then
		return 0
	fi

	local rc=0
	python3 - "${wt_path}" "${base_sha}" "${expected_count}" "$@" <<'PY' || rc=$?
import ast
import subprocess
import sys

wt_path, base_sha, expected_raw = sys.argv[1], sys.argv[2], sys.argv[3].strip()
rels = sys.argv[4:]
expected = int(expected_raw) if expected_raw else None


def base_source(rel):
    probe = subprocess.run(
        ["git", "-C", wt_path, "cat-file", "-e", f"{base_sha}:{rel}"],
        capture_output=True,
    )
    if probe.returncode != 0:
        return ""
    shown = subprocess.run(
        ["git", "-C", wt_path, "show", f"{base_sha}:{rel}"],
        capture_output=True,
        text=True,
    )
    return shown.stdout


def current_source(rel):
    try:
        with open(f"{wt_path}/{rel}", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except FileNotFoundError:
        # Deleted test file: every test it held is lost coverage.
        return ""


def test_index(source):
    """Map container -> sorted test names, plus a total count.

    Covers unittest (TestCase subclasses and Test* classes) and pytest
    (module-level test_* functions), so the count is framework-independent and
    needs no suite run against the base revision.
    """
    tree = ast.parse(source)
    index = {}
    module_fns = [
        n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test")
    ]
    if module_fns:
        index["<module>"] = sorted(module_fns)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        if not (node.name.startswith("Test") or "TestCase" in bases):
            continue
        index[node.name] = sorted(
            n.name for n in node.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test")
        )
    return index, sum(len(v) for v in index.values())


total_before = 0
total_after = 0
lost_report = []
added_report = []
parse_errors = []

for rel in rels:
    try:
        base_index, base_count = test_index(base_source(rel))
    except SyntaxError as exc:
        parse_errors.append(f"{rel}: base revision does not parse ({exc})")
        continue
    try:
        cur_index, cur_count = test_index(current_source(rel))
    except SyntaxError as exc:
        parse_errors.append(f"{rel}: worktree revision does not parse ({exc})")
        continue

    total_before += base_count
    total_after += cur_count

    for cls in sorted(set(base_index) - set(cur_index)):
        lost_report.append(f"{rel}: removed test container {cls} ({len(base_index[cls])} tests)")
    for cls in sorted(set(base_index) & set(cur_index)):
        for name in sorted(set(base_index[cls]) - set(cur_index[cls])):
            lost_report.append(f"{rel}: lost test {cls}.{name}")
        for name in sorted(set(cur_index[cls]) - set(base_index[cls])):
            added_report.append(f"{rel}: added test {cls}.{name}")
    for cls in sorted(set(cur_index) - set(base_index)):
        added_report.append(f"{rel}: added test container {cls} ({len(cur_index[cls])} tests)")

for err in parse_errors:
    sys.stderr.write(f"BLOCKED: semantic test gate could not parse {err}\n")
if parse_errors:
    sys.exit(2)

sys.stderr.write(
    f"semantic-gate: touched Python test files={len(rels)} "
    f"tests_before={total_before} tests_after={total_after}\n"
)
for item in added_report:
    sys.stderr.write(f"semantic-gate: ADDED {item}\n")
for item in lost_report:
    sys.stderr.write(f"semantic-gate: LOST {item}\n")

if expected is not None:
    if total_after != expected:
        sys.stderr.write(
            f"BLOCKED: --expected-test-count {expected} but the worktree has {total_after} tests\n"
        )
        sys.exit(2)
    sys.exit(0)

if total_after < total_before:
    sys.stderr.write(
        f"BLOCKED: test count dropped {total_before} -> {total_after}. A drop fails the gate "
        "even when the suite passes; if the reduction is intentional, re-run with "
        f"--expected-test-count {total_after}\n"
    )
    sys.exit(2)
if lost_report:
    sys.stderr.write(
        "BLOCKED: test coverage was lost. If that is the intended diff, re-run with "
        f"--expected-test-count {total_after}\n"
    )
    sys.exit(2)
PY
	return "${rc}"
}

cmd_verify() {
	local wt_path=""
	local lens_override=""
	local test_cmd=""
	local numeric_cmd=""
	local allow_harness=0
	local allow_tests=0
	local expected_test_count=""

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--worktree)
			wt_path="$2"
			shift 2
			;;
		--lens)
			lens_override="$2"
			shift 2
			;;
		--test-cmd)
			test_cmd="$2"
			shift 2
			;;
		--numeric-check-cmd)
			numeric_cmd="$2"
			shift 2
			;;
		--allow-harness-changes)
			allow_harness=1
			shift
			;;
		--allow-test-edits)
			allow_tests=1
			shift
			;;
		--expected-test-count)
			expected_test_count="$2"
			shift 2
			;;
		*)
			echo "[ERROR] Unknown flag for verify: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -n ${expected_test_count} ]] && ! [[ ${expected_test_count} =~ ^[0-9]+$ ]]; then
		echo "[ERROR] --expected-test-count requires a non-negative integer, got: ${expected_test_count}" >&2
		exit 1
	fi

	if [[ -z ${wt_path} ]] || [[ ! -d ${wt_path} ]]; then
		echo "[ERROR] verify requires an existing --worktree directory" >&2
		exit 1
	fi

	local wt_git_dir
	wt_git_dir="$(git -C "${wt_path}" rev-parse --git-dir)"
	local meta_file="${wt_git_dir}/proactive-meta.json"
	if [[ ! -f ${meta_file} ]]; then
		echo "[ERROR] Missing proactive-meta.json in ${wt_git_dir}" >&2
		exit 1
	fi

	local repo_name="" base_sha="" meta_lens="" repo_path=""
	repo_name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repo_name"])' "${meta_file}")"
	base_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_sha"])' "${meta_file}")"
	meta_lens="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lens"])' "${meta_file}")"
	repo_path="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo_path",""))' "${meta_file}" 2>/dev/null || true)"

	local lens="${lens_override:-${meta_lens}}"

	local changed_files
	changed_files="$({
		git -C "${wt_path}" diff --no-renames --name-only "${base_sha}"
		git -C "${wt_path}" ls-files --others --exclude-standard
	} | sort -u)"

	local touched_py_present=()
	local touched_test_py=()

	if [[ -n ${changed_files} ]]; then
		local rel=""
		while IFS= read -r rel; do
			[[ -z ${rel} ]] && continue
			if [[ ${allow_harness} -eq 0 ]] && is_protected_harness_path "${rel}"; then
				echo "BLOCKED: protected build/harness/policy file modified without --allow-harness-changes: ${rel}" >&2
				exit 2
			fi
			if [[ ${allow_tests} -eq 0 ]] && is_protected_test_path "${rel}"; then
				echo "BLOCKED: protected test file modified without --allow-test-edits: ${rel}" >&2
				exit 2
			fi
			if [[ ${rel} == *.py ]]; then
				# A deleted path still needs coverage accounting but has no file
				# to lint, so the static checks get only present paths.
				if [[ -f ${wt_path}/${rel} ]]; then
					touched_py_present+=("${rel}")
				fi
				if is_python_test_path "${rel}"; then
					touched_test_py+=("${rel}")
				fi
			fi
		done <<<"${changed_files}"
	fi

	if is_research_repo "${repo_name}"; then
		# A --lens override must never relax a gate the worktree was prepared
		# under, so research-repo gates fire if EITHER lens requires them.
		if [[ ${lens} == "palette" ]] || [[ ${meta_lens} == "palette" ]]; then
			echo "BLOCKED: Palette lens is disabled on research repository ${repo_name}" >&2
			exit 3
		fi
		if [[ ${lens} == "bolt" || ${meta_lens} == "bolt" ]] && [[ -z ${numeric_cmd} ]]; then
			echo "BLOCKED: Bolt lens on research repository ${repo_name} requires --numeric-check-cmd tolerance check" >&2
			exit 3
		fi
	fi

	# Semantic gates run before the suite: they are cheap, deterministic, and
	# catch the defect class a green suite cannot (silently dropped coverage).
	if [[ ${#touched_py_present[@]} -gt 0 ]]; then
		if ! run_python_static_checks "${wt_path}" "${repo_path}" "${touched_py_present[@]}"; then
			echo "BLOCKED: static check failed on touched Python files" >&2
			exit 2
		fi
	fi
	if [[ ${#touched_test_py[@]} -gt 0 ]]; then
		run_semantic_test_gate "${wt_path}" "${base_sha}" "${expected_test_count}" "${touched_test_py[@]}"
	elif [[ -n ${expected_test_count} ]]; then
		echo "[WARN] --expected-test-count given but no Python test file changed; the semantic gate had nothing to enforce" >&2
	fi

	if [[ -z ${test_cmd} ]]; then
		test_cmd="$(default_test_cmd_for_repo "${repo_name}")"
	fi

	local verify_path=""
	verify_path="$(resolve_verify_path "${wt_path}" "${repo_path}" "${test_cmd}")"

	(
		cd "${wt_path}"
		env -u SSH_AUTH_SOCK -u GH_TOKEN -u GITHUB_TOKEN -u VIRTUAL_ENV PATH="${verify_path}" bash -c "${test_cmd}"
		if [[ -n ${numeric_cmd} ]]; then
			env -u SSH_AUTH_SOCK -u GH_TOKEN -u GITHUB_TOKEN -u VIRTUAL_ENV PATH="${verify_path}" bash -c "${numeric_cmd}"
		fi
	)
}

cmd_check_collisions() {
	local repo=""
	local repo_path=""
	local include_worktrees=0
	local target_files=()

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--repo)
			repo="$2"
			shift 2
			;;
		--file)
			target_files+=("$2")
			shift 2
			;;
		--repo-path)
			repo_path="$2"
			shift 2
			;;
		--include-worktrees)
			include_worktrees=1
			shift
			;;
		*)
			echo "[ERROR] Unknown flag for check-collisions: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -z ${repo} ]] || [[ ${#target_files[@]} -eq 0 ]]; then
		echo "[ERROR] check-collisions requires --repo and at least one --file" >&2
		exit 1
	fi

	if [[ ${include_worktrees} -eq 1 ]] && [[ -z ${repo_path} ]]; then
		echo "[ERROR] --include-worktrees requires --repo-path so git worktree list can be resolved" >&2
		exit 1
	fi

	local prs_json=""
	# changedFiles lets us detect truncation: gh caps the per-PR files list, so a
	# large PR could otherwise hide a colliding path and let the gate pass.
	prs_json="$(run_gh_resilient pr list --repo "${repo}" --state open --limit 100 --json number,title,isDraft,createdAt,files,changedFiles)" || exit $?

	# Open PRs are only half the collision surface. In 2B local-first mode there
	# are no bot PRs at all, so a PR-only gate is a no-op for exactly the class
	# that stranded real work: two sessions editing the same file in the same
	# burst. Union in the changed paths of every live local candidate worktree.
	local wt_records=""
	if [[ ${include_worktrees} -eq 1 ]]; then
		local main_top="" wt_list="" wt_line="" candidate_dir="" wt_git_dir="" wt_branch=""
		local is_candidate=0
		local candidate_dirs=()

		main_top="$(git -C "${repo_path}" rev-parse --show-toplevel 2>/dev/null || true)"
		# Enumerate first and check the status: a silently empty list would
		# under-report collisions, which is the unsafe direction.
		if ! wt_list="$(git -C "${repo_path}" worktree list --porcelain)"; then
			echo "[ERROR] --include-worktrees could not enumerate worktrees for ${repo_path}; refusing to under-report collisions" >&2
			exit 6
		fi

		while IFS= read -r wt_line; do
			[[ ${wt_line} == worktree\ * ]] || continue
			candidate_dir="${wt_line#worktree }"
			[[ -n ${candidate_dir} ]] || continue
			[[ ${candidate_dir} == "${main_top}" ]] && continue
			is_candidate=0
			wt_git_dir="$(git -C "${candidate_dir}" rev-parse --git-dir 2>/dev/null || true)"
			if [[ -n ${wt_git_dir} ]] && [[ -f ${wt_git_dir}/proactive-meta.json ]]; then
				is_candidate=1
			fi
			wt_branch="$(git -C "${candidate_dir}" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
			if [[ ${wt_branch} == proactive/* ]]; then
				is_candidate=1
			fi
			[[ ${is_candidate} -eq 1 ]] || continue
			candidate_dirs+=("${candidate_dir}")
		done <<<"${wt_list}"

		# Liveness is judged against origin/<default_branch>, so refresh first and
		# fail closed. This subcommand already needs the network for gh pr list, so
		# the fetch adds no new dependency.
		if [[ ${#candidate_dirs[@]} -gt 0 ]]; then
			require_fresh_origin_ref "${repo_path}"
		fi

		local cand="" cand_base="" cand_paths="" cand_rel="" cand_dirty="" cand_branch=""
		for cand in ${candidate_dirs[@]+"${candidate_dirs[@]}"}; do
			cand_dirty="$(git -C "${cand}" status --porcelain 2>/dev/null | head -1)"
			# A candidate whose work already merged is not a collision: its paths
			# are on the base branch now, and counting it would block that file for
			# up to the 21-day TTL. Uncommitted edits do count, so check dirtiness
			# before the commit-ancestry test.
			if [[ -z ${cand_dirty} ]] && ! has_unreviewed_worktree_commits "${cand}"; then
				continue
			fi
			cand_base=""
			cand_branch="$(git -C "${cand}" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
			wt_git_dir="$(git -C "${cand}" rev-parse --git-dir 2>/dev/null || true)"
			if [[ -n ${wt_git_dir} ]] && [[ -f ${wt_git_dir}/proactive-meta.json ]]; then
				cand_base="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("base_sha",""))' "${wt_git_dir}/proactive-meta.json" 2>/dev/null || true)"
			fi
			if [[ -z ${cand_base} ]]; then
				echo "[ERROR] candidate worktree ${cand} has no recorded base_sha; refusing to under-report collisions" >&2
				exit 6
			fi
			cand_paths="$({
				git -C "${cand}" diff --no-renames --name-only "${cand_base}" 2>/dev/null
				git -C "${cand}" ls-files --others --exclude-standard 2>/dev/null
			} | sort -u)"
			while IFS= read -r cand_rel; do
				[[ -n ${cand_rel} ]] || continue
				wt_records+="${cand_rel}"$'\t'"${cand}"$'\t'"${cand_branch}"$'\n'
			done <<<"${cand_paths}"
		done
	fi

	python3 - "${prs_json}" "${wt_records}" "${target_files[@]}" <<'PY'
import json
import os
import sys

prs = json.loads(sys.argv[1])
wt_blob = sys.argv[2]
targets = {os.path.normpath(t.strip()) for t in sys.argv[3:] if t.strip()}
collisions = []

# Fail closed when the listing may be incomplete: hitting the --limit cap or a
# truncated per-PR files list means a collision could be invisible.
if len(prs) >= 100:
    sys.stderr.write("UNVERIFIABLE: open PR list reached the 100 PR limit; refusing to pass the collision gate\n")
    sys.exit(5)
for pr in prs:
    files = pr.get("files", [])
    if len(files) < pr.get("changedFiles", len(files)):
        sys.stderr.write(
            f"UNVERIFIABLE: Open PR #{pr.get('number')} lists {len(files)} of "
            f"{pr.get('changedFiles')} changed files; refusing to pass the collision gate\n"
        )
        sys.exit(5)

for pr in prs:
    for fobj in pr.get("files", []):
        path = os.path.normpath(fobj.get("path", "").strip())
        if path in targets:
            collisions.append(f"COLLISION: Open PR #{pr.get('number')} ({pr.get('title', '')}) already touches {path}")

for line in wt_blob.splitlines():
    if not line.strip():
        continue
    parts = line.split("\t")
    if len(parts) != 3:
        continue
    rel, wt_dir, branch = parts[0].strip(), parts[1].strip(), parts[2].strip()
    if os.path.normpath(rel) in targets:
        label = f"branch {branch}" if branch else "detached HEAD"
        collisions.append(f"COLLISION: live candidate worktree {wt_dir} ({label}) already touches {os.path.normpath(rel)}")

if collisions:
    for message in collisions:
        sys.stderr.write(f"{message}\n")
    sys.exit(4)
PY
}

ensure_patch_id_cache_dir() {
	if [[ -z ${PATCH_ID_CACHE_DIR} ]] || [[ ! -d ${PATCH_ID_CACHE_DIR} ]]; then
		PATCH_ID_CACHE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/proactive-patch-id-cache.XXXXXX")"
	fi
}

require_verbatim_patch_id() {
	if [[ ${VERBATIM_PATCH_ID_CHECKED} -eq 1 ]]; then
		[[ ${VERBATIM_PATCH_ID_OK} -eq 1 ]]
		return $?
	fi
	VERBATIM_PATCH_ID_CHECKED=1
	if git patch-id --verbatim </dev/null >/dev/null 2>&1; then
		VERBATIM_PATCH_ID_OK=1
		return 0
	fi
	VERBATIM_PATCH_ID_OK=0
	echo "[WARN] git patch-id --verbatim is unavailable; squash-merge detection degraded to ancestry-only" >&2
	return 1
}

collect_upstream_patch_ids() {
	local wt_dir="$1"
	local merge_base="$2"
	local upstream_ref="$3"

	UPSTREAM_PATCH_IDS_FILE=""
	if ! require_verbatim_patch_id; then
		return 1
	fi
	local upstream_sha=""
	upstream_sha="$(git -C "${wt_dir}" rev-parse --verify --quiet "${upstream_ref}" 2>/dev/null || true)"
	if [[ -z ${upstream_sha} ]]; then
		return 1
	fi

	local common_dir=""
	local common_rel=""
	common_rel="$(git -C "${wt_dir}" rev-parse --git-common-dir 2>/dev/null || true)"
	if [[ -n ${common_rel} ]]; then
		common_dir="$(cd "${wt_dir}" 2>/dev/null && cd "${common_rel}" 2>/dev/null && pwd || true)"
	fi
	if [[ -z ${common_dir} ]]; then
		common_dir="${wt_dir}"
	fi

	local lookback="${PROACTIVE_SQUASH_LOOKBACK:-0}"
	if [[ ! ${lookback} =~ ^[0-9]+$ ]]; then
		echo "[WARN] Ignoring invalid PROACTIVE_SQUASH_LOOKBACK=${lookback}; scanning full range" >&2
		lookback="0"
	fi

	ensure_patch_id_cache_dir
	local cache_key=""
	cache_key="$(python3 -c 'import hashlib, sys; print(hashlib.sha256("|".join(sys.argv[1:]).encode()).hexdigest())' "${common_dir}" "${merge_base}" "${upstream_sha}" "${lookback}")"
	local cache_file="${PATCH_ID_CACHE_DIR}/${cache_key}"

	if [[ ! -f ${cache_file} ]]; then
		local -a log_args=(git -C "${wt_dir}" log -p --no-merges --no-renames)
		if [[ ${lookback} -gt 0 ]]; then
			log_args+=("--max-count=${lookback}")
		fi
		log_args+=("${merge_base}..${upstream_ref}")

		local tmp_cache="${cache_file}.tmp.$$"
		{
			"${log_args[@]}" 2>/dev/null || true
		} | git patch-id --verbatim 2>/dev/null | awk '{ print $1 }' >"${tmp_cache}" || true
		mv -f "${tmp_cache}" "${cache_file}"
	fi

	if [[ ! -s ${cache_file} ]]; then
		return 1
	fi
	UPSTREAM_PATCH_IDS_FILE="${cache_file}"
	return 0
}

all_linear_commits_in_patch_ids() {
	local wt_dir="$1"
	local upstream_ref="$2"
	local cache_file="$3"

	local commit_count="0"
	commit_count="$(git -C "${wt_dir}" rev-list --no-merges --count "${upstream_ref}..HEAD" 2>/dev/null || echo "0")"
	if [[ ${commit_count} -le 0 ]]; then
		return 1
	fi

	local cand_pids=""
	cand_pids="$(
		{
			git -C "${wt_dir}" log -p --no-merges --no-renames "${upstream_ref}..HEAD" 2>/dev/null || true
		} | git patch-id --verbatim 2>/dev/null | awk '{ print $1 }' || true
	)"

	local pid=""
	local matched=0
	while IFS= read -r pid; do
		[[ -n ${pid} ]] || continue
		if ! grep -qxF "${pid}" "${cache_file}"; then
			return 1
		fi
		matched=$((matched + 1))
	done <<<"${cand_pids}"

	[[ ${matched} -eq ${commit_count} ]]
}

is_worktree_merged_into_upstream() {
	local wt_dir="$1"
	local upstream_ref="$2"

	if git -C "${wt_dir}" merge-base --is-ancestor HEAD "${upstream_ref}" 2>/dev/null; then
		return 0
	fi

	local merge_base=""
	merge_base="$(git -C "${wt_dir}" merge-base "${upstream_ref}" HEAD 2>/dev/null || true)"
	if [[ -z ${merge_base} ]]; then
		return 1
	fi

	if ! collect_upstream_patch_ids "${wt_dir}" "${merge_base}" "${upstream_ref}"; then
		return 1
	fi

	# Multi-commit (and single-commit) squash merges produce one upstream commit whose
	# verbatim patch-id matches the combined branch diff.
	local branch_patch_id=""
	branch_patch_id="$(
		{
			git -C "${wt_dir}" diff --no-renames "${merge_base}..HEAD" 2>/dev/null || true
		} | git patch-id --verbatim 2>/dev/null | awk 'NR == 1 { print $1 }' || true
	)"
	if [[ -n ${branch_patch_id} ]] && grep -qxF "${branch_patch_id}" "${UPSTREAM_PATCH_IDS_FILE}"; then
		return 0
	fi

	# For non-squashed rebased/cherry-picked commits, preserve linear-history safety:
	# skip per-commit matching if upstream..HEAD contains merge commits whose conflict
	# resolutions git log --no-merges / git cherry would not verify.
	local merge_commits="1"
	merge_commits="$(git -C "${wt_dir}" rev-list --merges --count "${upstream_ref}..HEAD" 2>/dev/null || echo "1")"
	if [[ ${merge_commits} -ne 0 ]]; then
		return 1
	fi

	all_linear_commits_in_patch_ids "${wt_dir}" "${upstream_ref}" "${UPSTREAM_PATCH_IDS_FILE}"
}

has_unreviewed_worktree_commits() {
	local wt_dir="$1"
	local wt_git_dir=""
	wt_git_dir="$(git -C "${wt_dir}" rev-parse --git-dir 2>/dev/null || true)"
	local base_sha=""
	local default_branch="main"
	if [[ -n ${wt_git_dir} ]] && [[ -f "${wt_git_dir}/proactive-meta.json" ]]; then
		base_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("base_sha",""))' "${wt_git_dir}/proactive-meta.json" 2>/dev/null || true)"
		default_branch="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("default_branch","main"))' "${wt_git_dir}/proactive-meta.json" 2>/dev/null || echo "main")"
	fi

	if [[ -z ${base_sha} ]]; then
		return 1
	fi

	local ahead="0"
	ahead="$(git -C "${wt_dir}" rev-list --count "${base_sha}..HEAD" 2>/dev/null || echo "0")"
	if [[ ${ahead} -le 0 ]]; then
		return 1
	fi

	if git -C "${wt_dir}" rev-parse --verify --quiet "origin/${default_branch}" >/dev/null 2>&1; then
		if is_worktree_merged_into_upstream "${wt_dir}" "origin/${default_branch}"; then
			return 1
		fi
	fi
	return 0
}

cmd_check_throttle() {
	local repo=""
	local wt_root="${DEFAULT_WT_ROOT}"
	local max_open=2
	local max_age_days=7
	local now_epoch=""
	local repo_path=""
	local include_worktrees=0

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--repo)
			repo="$2"
			shift 2
			;;
		--worktree-root)
			wt_root="$2"
			shift 2
			;;
		--max-open)
			max_open="$2"
			shift 2
			;;
		--max-age-days)
			max_age_days="$2"
			shift 2
			;;
		--now-epoch)
			now_epoch="$2"
			shift 2
			;;
		--repo-path)
			repo_path="$2"
			shift 2
			;;
		--include-worktrees)
			include_worktrees=1
			shift
			;;
		*)
			echo "[ERROR] Unknown flag for check-throttle: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -z ${repo} ]]; then
		echo "[ERROR] check-throttle requires --repo" >&2
		exit 1
	fi

	if [[ ${include_worktrees} -eq 1 ]] && [[ -z ${repo_path} ]]; then
		echo "[ERROR] --include-worktrees requires --repo-path so git worktree list can be resolved" >&2
		exit 1
	fi

	local repo_short="${repo##*/}"
	local candidates=()
	local seen_keys=()
	local candidate_dir=""

	add_candidate() {
		local dir="$1"
		[[ -d ${dir} ]] || return 0
		# Dedupe on git identity, not on the path string: the worktree root may
		# be reached through a symlink (macOS /var -> /private/var) and the same
		# directory must not be counted twice against the cap.
		local key=""
		key="$(git -C "${dir}" rev-parse --absolute-git-dir 2>/dev/null || true)"
		[[ -n ${key} ]] || return 0
		local seen=""
		for seen in ${seen_keys[@]+"${seen_keys[@]}"}; do
			[[ ${seen} == "${key}" ]] && return 0
		done
		seen_keys+=("${key}")
		candidates+=("${dir}")
	}

	if [[ -d ${wt_root} ]]; then
		for candidate_dir in "${wt_root}/proactive-${repo_short}-"*; do
			[[ -d ${candidate_dir} ]] || continue
			add_candidate "${candidate_dir}"
		done
	fi

	if [[ ${include_worktrees} -eq 1 ]]; then
		# The glob above only sees the worktree root this invocation was told
		# about, so a candidate prepared under a different root is invisible to
		# the cap. Union in every git-registered worktree this tool created,
		# identified by proactive metadata or a proactive/* branch. Human
		# worktrees match neither and stay out of the count.
		local main_top=""
		main_top="$(git -C "${repo_path}" rev-parse --show-toplevel 2>/dev/null || true)"
		# Enumerate first and check the status: a silently empty list would
		# under-count the cap and let extra candidates through.
		local wt_list=""
		if ! wt_list="$(git -C "${repo_path}" worktree list --porcelain)"; then
			echo "[ERROR] --include-worktrees could not enumerate worktrees for ${repo_path}; refusing to under-count the cap" >&2
			exit 6
		fi
		local wt_branch="" wt_git_dir="" is_candidate=0 wt_line=""
		while IFS= read -r wt_line; do
			[[ ${wt_line} == worktree\ * ]] || continue
			candidate_dir="${wt_line#worktree }"
			[[ -n ${candidate_dir} ]] || continue
			[[ ${candidate_dir} == "${main_top}" ]] && continue
			is_candidate=0
			wt_git_dir="$(git -C "${candidate_dir}" rev-parse --git-dir 2>/dev/null || true)"
			if [[ -n ${wt_git_dir} ]] && [[ -f ${wt_git_dir}/proactive-meta.json ]]; then
				is_candidate=1
			fi
			wt_branch="$(git -C "${candidate_dir}" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
			if [[ ${wt_branch} == proactive/* ]]; then
				is_candidate=1
			fi
			[[ ${is_candidate} -eq 1 ]] || continue
			add_candidate "${candidate_dir}"
		done <<<"${wt_list}"
	fi

	# The ancestry comparison below reads origin/<default_branch>, so a stale
	# remote-tracking ref would render a false verdict. Refresh first and fail
	# closed; with zero candidates there is no ref-based verdict to render.
	# Eager rather than lazy is deliberate: this subcommand already requires the
	# network for gh pr list, so a per-candidate fetch would add latency without
	# buying offline capability.
	if [[ ${#candidates[@]} -gt 0 ]]; then
		local fetch_source="${repo_path}"
		if [[ -z ${fetch_source} ]]; then
			local first_git_dir=""
			first_git_dir="$(git -C "${candidates[0]}" rev-parse --git-dir 2>/dev/null || true)"
			if [[ -n ${first_git_dir} ]] && [[ -f ${first_git_dir}/proactive-meta.json ]]; then
				fetch_source="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo_path",""))' "${first_git_dir}/proactive-meta.json" 2>/dev/null || true)"
			fi
		fi
		require_fresh_origin_ref "${fetch_source}"
	fi

	if [[ ${#candidates[@]} -gt 0 ]]; then
		local local_candidates=0
		for candidate_dir in "${candidates[@]}"; do
			local dirty=""
			dirty="$(git -C "${candidate_dir}" status --porcelain 2>/dev/null || true)"
			if [[ -n ${dirty} ]] || has_unreviewed_worktree_commits "${candidate_dir}"; then
				local_candidates=$((local_candidates + 1))
				local wt_git_dir=""
				wt_git_dir="$(git -C "${candidate_dir}" rev-parse --git-dir 2>/dev/null || true)"
				if [[ -n ${wt_git_dir} ]] && [[ -f "${wt_git_dir}/proactive-meta.json" ]]; then
					python3 - "${wt_git_dir}/proactive-meta.json" "${max_age_days}" "${now_epoch}" "${candidate_dir}" <<'PY'
import datetime as dt
import json
import sys

meta = json.loads(open(sys.argv[1], encoding="utf-8").read())
max_age = int(sys.argv[2])
now_ts = int(sys.argv[3]) if sys.argv[3] else int(dt.datetime.now(dt.timezone.utc).timestamp())
created_raw = meta.get("created_at", "")
if created_raw:
    created_dt = dt.datetime.strptime(created_raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    age_days = (now_ts - int(created_dt.timestamp())) / 86400.0
    if age_days > max_age:
        sys.stderr.write(f"THROTTLED: Unreviewed local candidate worktree {sys.argv[4]} is {age_days:.1f} days old (> {max_age}d)\n")
        sys.exit(5)
PY
				fi
			fi
		done

		if [[ ${local_candidates} -ge ${max_open} ]]; then
			echo "THROTTLED: ${local_candidates} unreviewed local candidate worktrees for ${repo_short} (cap=${max_open})" >&2
			exit 5
		fi
	fi

	local prs_json=""
	prs_json="$(run_gh_resilient pr list --repo "${repo}" --state open --limit 100 --json number,title,isDraft,createdAt)" || exit $?

	python3 - "${prs_json}" "${max_open}" "${max_age_days}" "${now_epoch}" <<'PY'
import datetime as dt
import json
import sys

prs = json.loads(sys.argv[1])
max_open = int(sys.argv[2])
max_age_days = int(sys.argv[3])
now_epoch = int(sys.argv[4]) if sys.argv[4] else int(dt.datetime.now(dt.timezone.utc).timestamp())

prefixes = ("⚡bolt", "🎨palette", "chore(qa)", "chore(proactive)", "repo-health/")
bot_drafts = []

for pr in prs:
    if not pr.get("isDraft"):
        continue
    title = (pr.get("title") or "").strip()
    if any(title.lower().startswith(p.lower()) for p in prefixes):
        created_raw = pr.get("createdAt", "")
        created_ts = int(dt.datetime.fromisoformat(created_raw.replace("Z", "+00:00")).timestamp())
        age_days = (now_epoch - created_ts) / 86400.0
        bot_drafts.append((pr.get("number"), title, age_days))

if len(bot_drafts) >= max_open:
    sys.stderr.write(
        f"THROTTLED: {len(bot_drafts)} open proactive Draft PRs (cap={max_open})\n"
    )
    sys.exit(5)

for num, title, age_days in bot_drafts:
    if age_days > max_age_days:
        sys.stderr.write(
            f"THROTTLED: Open Draft PR #{num} ({title}) is {age_days:.1f} days old (> {max_age_days}d)\n"
        )
        sys.exit(5)
PY
}

prune_merged_worktrees() {
	local wt_root="$1"
	local repo_filter="${2:-}"
	local pre_fetched_repo="${3:-}"

	PRUNED_MERGED_COUNT=0
	if [[ ! -d ${wt_root} ]]; then
		return 0
	fi

	local name_glob="proactive-*"
	if [[ -n ${repo_filter} ]]; then
		name_glob="proactive-${repo_filter}-*"
	fi

	local prune_dirs=""
	prune_dirs="$(find "${wt_root}" -mindepth 1 -maxdepth 1 -type d -name "${name_glob}" 2>/dev/null || true)"
	if [[ -z ${prune_dirs} ]]; then
		return 0
	fi

	local -a fetched_repos=()
	local -a fetched_ok=()
	if [[ -n ${pre_fetched_repo} ]]; then
		fetched_repos+=("${pre_fetched_repo}")
		fetched_ok+=(1)
	fi

	local dir=""
	while IFS= read -r dir; do
		[[ -z ${dir} ]] && continue
		local dirty=""
		dirty="$(git -C "${dir}" status --porcelain 2>/dev/null || echo "UNKNOWN")"
		if [[ -n ${dirty} ]]; then
			echo "[WARN] Preserving dirty or unverified worktree: ${dir}" >&2
			continue
		fi

		local wt_git_dir=""
		wt_git_dir="$(git -C "${dir}" rev-parse --git-dir 2>/dev/null || true)"
		if [[ -z ${wt_git_dir} ]] || [[ ! -f "${wt_git_dir}/proactive-meta.json" ]]; then
			continue
		fi

		local repo_path="" base_sha=""
		repo_path="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo_path",""))' "${wt_git_dir}/proactive-meta.json" 2>/dev/null || true)"
		base_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("base_sha",""))' "${wt_git_dir}/proactive-meta.json" 2>/dev/null || true)"
		if [[ -z ${repo_path} ]] || [[ ! -d ${repo_path} ]] || [[ -z ${base_sha} ]]; then
			continue
		fi

		local idx=0 cache_hit=0 repo_ok=0 seen_repo=""
		for seen_repo in ${fetched_repos[@]+"${fetched_repos[@]}"}; do
			if [[ ${seen_repo} == "${repo_path}" ]]; then
				cache_hit=1
				repo_ok="${fetched_ok[${idx}]}"
				break
			fi
			idx=$((idx + 1))
		done
		if [[ ${cache_hit} -eq 0 ]]; then
			if fetch_origin_resilient "${repo_path}"; then
				repo_ok=1
			else
				repo_ok=0
			fi
			fetched_repos+=("${repo_path}")
			fetched_ok+=("${repo_ok}")
		fi
		if [[ ${repo_ok} -ne 1 ]]; then
			echo "[WARN] Preserving worktree (fetch failed for ${repo_path}): ${dir}" >&2
			continue
		fi

		if has_unreviewed_worktree_commits "${dir}"; then
			echo "[WARN] Preserving worktree with unmerged candidate commits: ${dir}" >&2
			continue
		fi

		local wt_branch=""
		wt_branch="$(git -C "${dir}" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
		if git -C "${repo_path}" worktree remove --force "${dir}" 2>/dev/null; then
			git -C "${repo_path}" worktree prune 2>/dev/null || true
			if [[ ${wt_branch} == proactive/* ]]; then
				git -C "${repo_path}" branch -D "${wt_branch}" >/dev/null 2>&1 || true
			fi
			PRUNED_MERGED_COUNT=$((PRUNED_MERGED_COUNT + 1))
		fi
	done <<<"${prune_dirs}"
}

cmd_cleanup() {
	local wt_root="${DEFAULT_WT_ROOT}"
	local ttl_days=21
	local prune_merged=0

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--worktree-root)
			wt_root="$2"
			shift 2
			;;
		--ttl-days)
			ttl_days="$2"
			shift 2
			;;
		--prune-merged)
			prune_merged=1
			shift
			;;
		*)
			echo "[ERROR] Unknown flag for cleanup: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ ! -d ${wt_root} ]]; then
		return 0
	fi

	if [[ ${prune_merged} -eq 1 ]]; then
		prune_merged_worktrees "${wt_root}" "" ""
		return 0
	fi

	local stale_dirs=""
	stale_dirs="$(find "${wt_root}" -mindepth 1 -maxdepth 1 -type d -name 'proactive-*' -mtime "+${ttl_days}" 2>/dev/null || true)"
	if [[ -z ${stale_dirs} ]]; then
		return 0
	fi

	local dir=""
	while IFS= read -r dir; do
		[[ -z ${dir} ]] && continue
		local dirty=""
		dirty="$(git -C "${dir}" status --porcelain 2>/dev/null || echo "UNKNOWN")"
		if [[ -n ${dirty} ]]; then
			echo "[WARN] Preserving dirty or unverified worktree: ${dir}" >&2
			continue
		fi
		if has_unreviewed_worktree_commits "${dir}"; then
			echo "[WARN] Preserving worktree with unmerged candidate commits: ${dir}" >&2
			continue
		fi
		local wt_git_dir=""
		wt_git_dir="$(git -C "${dir}" rev-parse --git-dir 2>/dev/null || true)"
		local repo_path=""
		if [[ -n ${wt_git_dir} ]] && [[ -f "${wt_git_dir}/proactive-meta.json" ]]; then
			repo_path="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo_path",""))' "${wt_git_dir}/proactive-meta.json" 2>/dev/null || true)"
		fi
		if [[ -n ${repo_path} ]] && [[ -d ${repo_path} ]]; then
			if ! git -C "${repo_path}" worktree remove --force "${dir}" 2>/dev/null; then
				rm -rf "${dir}"
				git -C "${repo_path}" worktree prune 2>/dev/null || true
			fi
		else
			rm -rf "${dir}"
		fi
	done <<<"${stale_dirs}"
}

heal_origin_head() {
	local repo_path="$1"
	if git -C "${repo_path}" symbolic-ref --quiet refs/remotes/origin/HEAD >/dev/null 2>&1; then
		return 0
	fi

	local origin_url=""
	origin_url="$(git -C "${repo_path}" remote get-url origin 2>/dev/null || true)"
	local force_ssh="${PROACTIVE_FETCH_FORCE_SSH:-0}"
	if is_github_ssh_url "${origin_url}" && [[ ${force_ssh} != "1" ]]; then
		if command -v gh >/dev/null 2>&1; then
			run_with_timeout 15 env GIT_TERMINAL_PROMPT=0 \
				git -C "${repo_path}" \
				-c credential.helper= \
				-c "credential.helper=!gh auth git-credential" \
				-c "url.https://github.com/.insteadOf=git@github.com:" \
				-c "url.https://github.com/.insteadOf=ssh://git@github.com/" \
				remote set-head origin -a >/dev/null 2>&1 || true
		fi
		if ! git -C "${repo_path}" symbolic-ref --quiet refs/remotes/origin/HEAD >/dev/null 2>&1; then
			run_with_timeout 15 env GIT_TERMINAL_PROMPT=0 \
				git -C "${repo_path}" \
				-c credential.helper= \
				-c "url.https://github.com/.insteadOf=git@github.com:" \
				-c "url.https://github.com/.insteadOf=ssh://git@github.com/" \
				remote set-head origin -a >/dev/null 2>&1 || true
		fi
	else
		run_with_timeout 15 env GIT_TERMINAL_PROMPT=0 \
			GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10" \
			git -C "${repo_path}" remote set-head origin -a >/dev/null 2>&1 || true
	fi

	if ! git -C "${repo_path}" symbolic-ref --quiet refs/remotes/origin/HEAD >/dev/null 2>&1; then
		if git -C "${repo_path}" rev-parse --verify --quiet refs/remotes/origin/main >/dev/null 2>&1; then
			git -C "${repo_path}" remote set-head origin main >/dev/null 2>&1 || true
		fi
	fi
	return 0
}

has_f82_checker() {
	local repo_path="$1"
	local verify_path="$2"

	if PATH="${verify_path}" command -v ruff >/dev/null 2>&1; then
		return 0
	fi
	if PATH="${verify_path}" command -v uv >/dev/null 2>&1 && [[ -f "${repo_path}/pyproject.toml" ]]; then
		if [[ -f "${repo_path}/uv.lock" ]]; then
			if (cd "${repo_path}" && run_with_timeout 15 env -u VIRTUAL_ENV PATH="${verify_path}" uv run --frozen --all-extras ruff --version >/dev/null 2>&1); then
				return 0
			fi
		else
			if (cd "${repo_path}" && run_with_timeout 15 env -u VIRTUAL_ENV PATH="${verify_path}" uv run --all-extras ruff --version >/dev/null 2>&1); then
				return 0
			fi
		fi
	fi
	if [[ -n ${repo_path} ]] && [[ -x "${repo_path}/.venv/bin/ruff" ]]; then
		return 0
	fi
	if [[ -n ${repo_path} ]] && [[ -x "${repo_path}/.venv/bin/python3" ]] && "${repo_path}/.venv/bin/python3" -c 'import pyflakes' >/dev/null 2>&1; then
		return 0
	fi
	if env -u VIRTUAL_ENV PATH="${verify_path}" python3 -c 'import pyflakes' >/dev/null 2>&1; then
		return 0
	fi
	return 1
}

PREFLIGHT_REMEDIATION=""
PREFLIGHT_MISSING_DETAIL=""

check_preflight_toolchain() {
	local repo_short="$1"
	local repo_path="$2"
	local verify_path="$3"

	PREFLIGHT_REMEDIATION=""
	PREFLIGHT_MISSING_DETAIL=""

	case "${repo_short}" in
	ctrld-sync)
		if ! PATH="${verify_path}" command -v uv >/dev/null 2>&1; then
			PREFLIGHT_MISSING_DETAIL="uv CLI not found on PATH"
			PREFLIGHT_REMEDIATION="Install uv (brew install uv) and run: cd \"${repo_path}\" && uv sync --all-extras"
			return 1
		fi
		if [[ ! -f "${repo_path}/uv.lock" ]]; then
			PREFLIGHT_MISSING_DETAIL="uv.lock missing in ${repo_path}"
			PREFLIGHT_REMEDIATION="cd \"${repo_path}\" && uv lock && uv sync --all-extras"
			return 1
		fi
		if ! (cd "${repo_path}" && run_with_timeout 15 env -u VIRTUAL_ENV PATH="${verify_path}" uv run --frozen --all-extras ruff --version >/dev/null 2>&1); then
			PREFLIGHT_MISSING_DETAIL="ruff F82 unavailable via uv run --frozen"
			PREFLIGHT_REMEDIATION="cd \"${repo_path}\" && uv sync --all-extras"
			return 1
		fi
		;;
	personal-config)
		local tool=""
		for tool in make bash python3; do
			if ! PATH="${verify_path}" command -v "${tool}" >/dev/null 2>&1; then
				PREFLIGHT_MISSING_DETAIL="${tool} not found on PATH"
				PREFLIGHT_REMEDIATION="Install Xcode Command Line Tools (xcode-select --install) and ensure make, bash, and python3 are on PATH"
				return 1
			fi
		done
		;;
	email-security-pipeline)
		if ! (cd "${repo_path}" && env -u VIRTUAL_ENV PATH="${verify_path}" python3 -m pytest --version >/dev/null 2>&1); then
			PREFLIGHT_MISSING_DETAIL="pytest unavailable in ${repo_path}"
			PREFLIGHT_REMEDIATION="python3 -m venv \"${repo_path}/.venv\" && \"${repo_path}/.venv/bin/pip\" install -r \"${repo_path}/requirements-ci.txt\" ruff"
			return 1
		fi
		if ! has_f82_checker "${repo_path}" "${verify_path}"; then
			PREFLIGHT_MISSING_DETAIL="ruff/pyflakes F82 checker unavailable"
			PREFLIGHT_REMEDIATION="\"${repo_path}/.venv/bin/pip\" install ruff"
			return 1
		fi
		;;
	Hydrograph_Versus_Seatek_Sensors_Project)
		if ! (cd "${repo_path}" && env -u VIRTUAL_ENV PATH="${verify_path}" python3 -m pytest --version >/dev/null 2>&1); then
			PREFLIGHT_MISSING_DETAIL="pytest unavailable in ${repo_path}"
			PREFLIGHT_REMEDIATION="python3 -m venv \"${repo_path}/.venv\" && \"${repo_path}/.venv/bin/pip\" install pytest flake8 ruff"
			return 1
		fi
		if ! (cd "${repo_path}" && env -u VIRTUAL_ENV PATH="${verify_path}" flake8 --version >/dev/null 2>&1); then
			PREFLIGHT_MISSING_DETAIL="flake8 unavailable in ${repo_path}"
			PREFLIGHT_REMEDIATION="\"${repo_path}/.venv/bin/pip\" install flake8"
			return 1
		fi
		if ! has_f82_checker "${repo_path}" "${verify_path}"; then
			PREFLIGHT_MISSING_DETAIL="ruff/pyflakes F82 checker unavailable"
			PREFLIGHT_REMEDIATION="\"${repo_path}/.venv/bin/pip\" install ruff"
			return 1
		fi
		;;
	series_correction_project_updated)
		if [[ ! -d "${repo_path}/scripts/tests" ]]; then
			PREFLIGHT_MISSING_DETAIL="scripts/tests/ directory missing in ${repo_path}"
			PREFLIGHT_REMEDIATION="Restore ${repo_path}/scripts/tests/ and run: python3 -m venv \"${repo_path}/.venv\" && \"${repo_path}/.venv/bin/pip\" install -r \"${repo_path}/scripts/requirements-dev.txt\" ruff && \"${repo_path}/.venv/bin/pip\" install -e \"${repo_path}\""
			return 1
		fi
		if ! (cd "${repo_path}" && env -u VIRTUAL_ENV PATH="${verify_path}" python3 -m pytest --version >/dev/null 2>&1); then
			PREFLIGHT_MISSING_DETAIL="pytest unavailable in ${repo_path}"
			PREFLIGHT_REMEDIATION="python3 -m venv \"${repo_path}/.venv\" && \"${repo_path}/.venv/bin/pip\" install -r \"${repo_path}/scripts/requirements-dev.txt\" ruff && \"${repo_path}/.venv/bin/pip\" install -e \"${repo_path}\""
			return 1
		fi
		if ! has_f82_checker "${repo_path}" "${verify_path}"; then
			PREFLIGHT_MISSING_DETAIL="ruff/pyflakes F82 checker unavailable"
			PREFLIGHT_REMEDIATION="\"${repo_path}/.venv/bin/pip\" install ruff"
			return 1
		fi
		;;
	Seatek_Analysis)
		if ! PATH="${verify_path}" command -v Rscript >/dev/null 2>&1; then
			PREFLIGHT_MISSING_DETAIL="Rscript not found on PATH"
			PREFLIGHT_REMEDIATION="Install R and run Rscript -e 'renv::restore()' in \"${repo_path}\""
			return 1
		fi
		if ! (cd "${repo_path}" && run_with_timeout 15 env -u VIRTUAL_ENV PATH="${verify_path}" Rscript -e 'if (!requireNamespace("testthat", quietly = TRUE)) quit(status = 1)' >/dev/null 2>&1); then
			PREFLIGHT_MISSING_DETAIL="R package testthat cannot be loaded"
			PREFLIGHT_REMEDIATION="cd \"${repo_path}\" && Rscript -e 'renv::restore()'"
			return 1
		fi
		;;
	repoprompt-ce)
		if [[ ! -x "${repo_path}/.agents/skills/rpce-contribution-check/scripts/preflight.sh" ]]; then
			PREFLIGHT_MISSING_DETAIL=".agents/skills/rpce-contribution-check/scripts/preflight.sh missing or not executable"
			PREFLIGHT_REMEDIATION="Ensure ${repo_path}/.agents/skills/rpce-contribution-check/scripts/preflight.sh exists and is executable (chmod +x)"
			return 1
		fi
		;;
	*)
		if ! (cd "${repo_path}" && env -u VIRTUAL_ENV PATH="${verify_path}" python3 -m pytest --version >/dev/null 2>&1); then
			PREFLIGHT_MISSING_DETAIL="pytest unavailable in ${repo_path}"
			PREFLIGHT_REMEDIATION="python3 -m venv \"${repo_path}/.venv\" && \"${repo_path}/.venv/bin/pip\" install pytest"
			return 1
		fi
		;;
	esac
	return 0
}

cmd_preflight() {
	local repo=""
	local repo_path=""
	local wt_root="${DEFAULT_WT_ROOT}"
	local auto_heal=0
	local skip_fetch=0

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--repo)
			if [[ $# -lt 2 ]]; then
				echo "[ERROR] preflight: --repo requires a value" >&2
				exit 1
			fi
			repo="$2"
			shift 2
			;;
		--repo-path)
			if [[ $# -lt 2 ]]; then
				echo "[ERROR] preflight: --repo-path requires a value" >&2
				exit 1
			fi
			repo_path="$2"
			shift 2
			;;
		--worktree-root)
			if [[ $# -lt 2 ]]; then
				echo "[ERROR] preflight: --worktree-root requires a value" >&2
				exit 1
			fi
			wt_root="$2"
			shift 2
			;;
		--auto-heal)
			auto_heal=1
			shift
			;;
		--skip-fetch)
			skip_fetch=1
			shift
			;;
		*)
			echo "[ERROR] Unknown flag for preflight: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ -z ${repo} ]] || [[ -z ${repo_path} ]]; then
		echo "[ERROR] preflight requires --repo <owner/name> and --repo-path <dir>" >&2
		exit 1
	fi

	local repo_short="${repo##*/}"
	if [[ -z ${repo_short} ]] || [[ ${repo_short} == "." ]] || [[ ${repo_short} == ".." ]]; then
		echo "[ERROR] preflight: invalid --repo value: ${repo}" >&2
		exit 1
	fi

	local canonical_repo_path=""
	canonical_repo_path="$(cd "${repo_path}" 2>/dev/null && pwd)" || canonical_repo_path=""
	if [[ -z ${canonical_repo_path} ]]; then
		echo "[ERROR] preflight: --repo-path is not a directory: ${repo_path}" >&2
		exit 1
	fi
	repo_path="${canonical_repo_path}"
	if [[ ! -d "${repo_path}/.git" ]] && ! git -C "${repo_path}" rev-parse --git-dir >/dev/null 2>&1; then
		echo "[ERROR] preflight: not a git repository: ${repo_path}" >&2
		exit 1
	fi

	if [[ ${auto_heal} -eq 1 ]]; then
		git -C "${repo_path}" worktree prune 2>/dev/null || true
	fi

	local git_fetch_state="skipped"
	local fetch_transport="none"
	if [[ ${skip_fetch} -eq 0 ]]; then
		if ! fetch_origin_resilient "${repo_path}"; then
			echo "repo=${repo}"
			echo "git_fetch=failed"
			echo "fetch_transport=none"
			echo "preflight=FAIL"
			echo "[ERROR] preflight git fetch failed for ${repo_path}: ${FETCH_FAILURE_SUMMARY}" >&2
			exit 6
		fi
		git_fetch_state="ok"
		fetch_transport="${LAST_FETCH_TRANSPORT:-direct}"
		if [[ ${auto_heal} -eq 1 ]]; then
			heal_origin_head "${repo_path}"
		fi
	fi

	if ! command -v gh >/dev/null 2>&1 || ! run_with_timeout 15 gh auth status >/dev/null 2>&1; then
		echo "repo=${repo}"
		echo "git_fetch=${git_fetch_state}"
		echo "fetch_transport=${fetch_transport}"
		echo "gh_auth=failed"
		echo "preflight=FAIL"
		echo "[ERROR] preflight gh auth check failed (run: gh auth login)" >&2
		exit 6
	fi

	local merged_pruned=0
	if [[ ${auto_heal} -eq 1 ]] && [[ ${skip_fetch} -eq 0 ]]; then
		prune_merged_worktrees "${wt_root}" "${repo_short}" "${repo_path}"
		merged_pruned="${PRUNED_MERGED_COUNT}"
	fi

	local test_cmd=""
	test_cmd="$(default_test_cmd_for_repo "${repo_short}")"
	local verify_path=""
	verify_path="$(resolve_verify_path "${repo_path}" "${repo_path}" "${test_cmd}")"

	if ! check_preflight_toolchain "${repo_short}" "${repo_path}" "${verify_path}"; then
		echo "repo=${repo}"
		echo "git_fetch=${git_fetch_state}"
		echo "fetch_transport=${fetch_transport}"
		echo "gh_auth=ok"
		echo "toolchain=missing"
		echo "toolchain_detail=${PREFLIGHT_MISSING_DETAIL}"
		echo "remediation=${PREFLIGHT_REMEDIATION}"
		echo "merged_worktrees_pruned=${merged_pruned}"
		echo "preflight=FAIL"
		echo "[ERROR] preflight missing verification toolchain for ${repo_short}: ${PREFLIGHT_MISSING_DETAIL}" >&2
		exit 7
	fi

	echo "repo=${repo}"
	echo "git_fetch=${git_fetch_state}"
	echo "fetch_transport=${fetch_transport}"
	echo "gh_auth=ok"
	echo "toolchain=ok"
	echo "merged_worktrees_pruned=${merged_pruned}"
	echo "preflight=PASS"
	return 0
}

# Prints the default test command for a repository so callers outside this script
# (the ctl CLI's base-check) share one mapping instead of duplicating it and
# drifting out of sync with verify.
cmd_print_test_cmd() {
	local repo_name=""
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--repo-name)
			repo_name="${2##*/}"
			shift 2
			;;
		*)
			echo "[ERROR] Unknown flag for print-test-cmd: $1" >&2
			exit 1
			;;
		esac
	done
	if [[ -z ${repo_name} ]]; then
		echo "[ERROR] print-test-cmd requires --repo-name <name>" >&2
		exit 1
	fi
	default_test_cmd_for_repo "${repo_name}"
	echo
}

main() {
	if [[ $# -lt 1 ]]; then
		usage >&2
		exit 1
	fi
	local subcmd="$1"
	shift
	case "${subcmd}" in
	prepare)
		cmd_prepare "$@"
		;;
	verify)
		cmd_verify "$@"
		;;
	check-collisions)
		cmd_check_collisions "$@"
		;;
	check-throttle)
		cmd_check_throttle "$@"
		;;
	cleanup)
		cmd_cleanup "$@"
		;;
	preflight)
		cmd_preflight "$@"
		;;
	print-test-cmd)
		cmd_print_test_cmd "$@"
		;;
	-h | --help | help)
		usage
		;;
	*)
		echo "[ERROR] Unknown subcommand: ${subcmd}" >&2
		usage >&2
		exit 1
		;;
	esac
}

if [[ ${BASH_SOURCE[0]:-$0} == "$0" ]]; then
	trap cleanup_runtime_temps EXIT
	main "$@"
fi
