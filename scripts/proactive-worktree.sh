#!/usr/bin/env bash
#
# Isolated Git Worktree & Verification Runner for Antigravity Proactive Sweeps.
# Protects primary checkouts, disables push remotes in local-only mode, enforces
# tamper-evident checks on build/lock/script/test harnesses before running gates,
# enforces numeric-equivalence checks on research repositories, checks open-PR
# file collisions plus local/remote candidate throttles, and prunes stale
# empty worktrees past their 21-day TTL while preserving unmerged candidates.

set -Eeuo pipefail

DEFAULT_WT_ROOT="${HOME}/.gemini/antigravity/worktrees"

usage() {
	cat <<'EOF'
Usage:
  proactive-worktree.sh prepare --repo-path <dir> --lens <lens> [--worktree-root <dir>] [--mode <local|draft-pr>]
  proactive-worktree.sh verify --worktree <dir> [--lens <lens>] [--test-cmd <cmd>] [--numeric-check-cmd <cmd>] [--allow-harness-changes] [--allow-test-edits]
  proactive-worktree.sh check-collisions --repo <owner/name> --file <relpath> [--file <relpath> ...]
  proactive-worktree.sh check-throttle --repo <owner/name> [--worktree-root <dir>] [--max-open <n>] [--max-age-days <days>] [--now-epoch <sec>]
  proactive-worktree.sh cleanup [--worktree-root <dir>] [--ttl-days <days>]
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

cmd_verify() {
	local wt_path=""
	local lens_override=""
	local test_cmd=""
	local numeric_cmd=""
	local allow_harness=0
	local allow_tests=0

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
		*)
			echo "[ERROR] Unknown flag for verify: $1" >&2
			exit 1
			;;
		esac
	done

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

	local prs_json
	# changedFiles lets us detect truncation: gh caps the per-PR files list, so a
	# large PR could otherwise hide a colliding path and let the gate pass.
	prs_json="$(gh pr list --repo "${repo}" --state open --limit 100 --json number,title,isDraft,createdAt,files,changedFiles)"

	python3 - "${prs_json}" "${target_files[@]}" <<'PY'
import json
import os
import sys

prs = json.loads(sys.argv[1])
targets = {os.path.normpath(t.strip()) for t in sys.argv[2:] if t.strip()}
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
            collisions.append((pr.get("number"), pr.get("title", ""), path))

if collisions:
    for num, title, path in collisions:
        sys.stderr.write(f"COLLISION: Open PR #{num} ({title}) already touches {path}\n")
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

	local repo_short="${repo##*/}"
	if [[ -d ${wt_root} ]]; then
		local local_candidates=0
		local candidate_dir=""
		for candidate_dir in "${wt_root}/proactive-${repo_short}-"*; do
			[[ -d ${candidate_dir} ]] || continue
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
