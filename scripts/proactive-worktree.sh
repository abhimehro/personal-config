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

usage() {
	cat <<'EOF'
Usage:
  proactive-worktree.sh prepare --repo-path <dir> --lens <lens> [--worktree-root <dir>] [--mode <local|draft-pr>]
  proactive-worktree.sh verify --worktree <dir> [--lens <lens>] [--test-cmd <cmd>] [--numeric-check-cmd <cmd>] [--allow-harness-changes] [--allow-test-edits] [--expected-test-count <n>]
  proactive-worktree.sh check-collisions --repo <owner/name> --file <relpath> [--file <relpath> ...] [--repo-path <dir>] [--include-worktrees]
  proactive-worktree.sh check-throttle --repo <owner/name> [--worktree-root <dir>] [--max-open <n>] [--max-age-days <days>] [--now-epoch <sec>] [--repo-path <dir>] [--include-worktrees]
  proactive-worktree.sh cleanup [--worktree-root <dir>] [--ttl-days <days>]
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
		printf '%s' "uv run --all-extras pytest tests/ test_main.py -q && uv run --all-extras ruff check ."
		;;
	email-security-pipeline)
		printf '%s' "python3 -m pytest -q"
		;;
	Hydrograph_Versus_Seatek_Sensors_Project)
		printf '%s' "MPLBACKEND=Agg python3 -m pytest tests/ -q && flake8 src/ tests/"
		;;
	series_correction_project_updated)
		printf '%s' "MPLBACKEND=Agg python3 -m pytest tests/ -q"
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

	git -C "${repo_path}" fetch --prune --quiet origin 2>/dev/null || true

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
	if ! git -C "${repo_path}" fetch --prune --quiet origin; then
		echo "[ERROR] git fetch failed for ${repo_path}; refusing to emit a ref-based verdict from a possibly stale origin/* (offline or no 'origin'?)" >&2
		exit 6
	fi
}

# Static checks on touched Python files. Two tiers:
#   1. AST parse - dependency-free floor, catches files that do not even parse.
#      Uses ast rather than py_compile so no __pycache__ is written into the
#      worktree under verification.
#   2. Undefined-name (F82) - ruff when present, pyflakes otherwise. ruff's F82
#      is the same check Seatek_Analysis CI already runs
#      (pr-validation.yml: ruff --select=E9,F63,F7,F82).
run_python_static_checks() {
	local wt_path="$1"
	shift

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

	if command -v ruff >/dev/null 2>&1; then
		(cd "${wt_path}" && ruff check --select=F82 --no-cache --quiet "$@")
	elif python3 -c 'import pyflakes' >/dev/null 2>&1; then
		(cd "${wt_path}" && python3 -m pyflakes "$@")
	else
		echo "[WARN] Neither ruff nor pyflakes is available; ran the AST parse floor only, so undefined names in untested code paths are not covered" >&2
		return 0
	fi
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

	local repo_name base_sha meta_lens
	repo_name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repo_name"])' "${meta_file}")"
	base_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_sha"])' "${meta_file}")"
	meta_lens="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lens"])' "${meta_file}")"

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
		if ! run_python_static_checks "${wt_path}" "${touched_py_present[@]}"; then
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

	(
		cd "${wt_path}"
		SSH_AUTH_SOCK="" GH_TOKEN="" GITHUB_TOKEN="" bash -c "${test_cmd}"
		if [[ -n ${numeric_cmd} ]]; then
			SSH_AUTH_SOCK="" GH_TOKEN="" GITHUB_TOKEN="" bash -c "${numeric_cmd}"
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

	local prs_json
	# changedFiles lets us detect truncation: gh caps the per-PR files list, so a
	# large PR could otherwise hide a colliding path and let the gate pass.
	prs_json="$(gh pr list --repo "${repo}" --state open --limit 100 --json number,title,isDraft,createdAt,files,changedFiles)"

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
		if git -C "${wt_dir}" merge-base --is-ancestor HEAD "origin/${default_branch}" 2>/dev/null; then
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

	local prs_json
	prs_json="$(gh pr list --repo "${repo}" --state open --limit 100 --json number,title,isDraft,createdAt)"

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

cmd_cleanup() {
	local wt_root="${DEFAULT_WT_ROOT}"
	local ttl_days=21

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
		*)
			echo "[ERROR] Unknown flag for cleanup: $1" >&2
			exit 1
			;;
		esac
	done

	if [[ ! -d ${wt_root} ]]; then
		return 0
	fi

	local stale_dirs
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

main "$@"
