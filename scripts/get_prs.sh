#!/usr/bin/env bash
set -euo pipefail

# List open PRs across configured repos for PR-review / agent workflows.
#
# Unlike filtering by --author bot only, this script lists *all* open PRs, then
# adds heuristic "automation hints" (branch/title/body/bot flag) so an agent can
# infer automation vs human follow-up.
#
# USAGE:
#   ./scripts/get_prs.sh
#   ./scripts/get_prs.sh --config tasks/pr-review-agent.config.yaml
#   ./scripts/get_prs.sh --repo owner/a --repo owner/b --limit 50
#   ./scripts/get_prs.sh --details   # extra gh calls: review/comment snippets per PR
#   ./scripts/get_prs.sh --bots-only # legacy: only gh pr list --author <bot> (comparison)
#   ./scripts/get_prs.sh --compare-bots  # full inventory, then append legacy bots-only section
#
# REQUIRES: gh (authenticated), python3. Markdown formatting lives in
# scripts/get_prs_summarize.py (lintable/testable; not embedded here).
# Optional: PyYAML (`pip install pyyaml`) for robust --config parsing; else regex fallback.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CONFIG_FILE=""
CONFIG_PATH_RESOLVED="" # set when repos were loaded from default or explicit config
LIMIT=100
INCLUDE_DETAILS=false
BOTS_ONLY=false
COMPARE_BOTS=false
REPOS=()
BOT_AUTHORS=()

declare -a _GET_PRS_TEMP_FILES=()
cleanup_get_prs_temp() {
	rm -f "${_GET_PRS_TEMP_FILES[@]-}"
}
trap cleanup_get_prs_temp EXIT

register_get_prs_temp() {
	_GET_PRS_TEMP_FILES+=("$1")
}

usage() {
	cat <<'USAGE'
Usage: get_prs.sh [options]

  --config PATH   Load repo list from tasks/pr-review-agent.config.yaml-style file
  --repo O/R      Add a repository (repeatable; overrides default when set)
  --limit N       Max open PRs per repo (default: 100)
  --details       Fetch reviews + issue comments per PR (slower; one gh pr view
                  per PR — watch rate limits on repos with many open PRs)
  --bots-only     Legacy mode: only list PRs where GitHub author matches bot_authors
                  (same idea as the original script; misses Jules-on-human-account PRs)
  --compare-bots  After the full open-PR inventory, append the legacy bots-only tables
  -h, --help      Show this help

Environment:
  GH_REPO         If set, only query this single repo (same as one --repo).

Output:
  Markdown-friendly tables per repo. Check rollup is summarized from
  statusCheckRollup[] (conclusion/status), not .statusCheckRollup.state (invalid).

bot_authors:
  Loaded from the same YAML as repos when using --config or the default
  tasks/pr-review-agent.config.yaml (top-level bot_authors: list). Otherwise:
  dependabot[bot], renovate[bot], google-labs-jules[bot].

  With PyYAML installed, config is parsed properly; otherwise a line-based
  fallback is used (same style as preflight-gh-pr-automation.sh).
USAGE
}

load_repos_from_config_bash() {
	local config_file="$1"
	[[ -f $config_file ]] || {
		echo "ERROR: config not found: $config_file" >&2
		exit 1
	}
	REPOS=()
	local in_repos=false
	local line normalized
	while IFS= read -r line || [[ -n $line ]]; do
		normalized="${line%$'\r'}"
		if [[ $normalized =~ ^repos:[[:space:]]*$ ]]; then
			in_repos=true
			continue
		fi
		if [[ $in_repos == true ]]; then
			if [[ $normalized =~ ^[a-zA-Z_][a-zA-Z0-9_]*:[[:space:]]*$ ]]; then
				break
			fi
			if [[ $normalized =~ ^[[:space:]]*-[[:space:]]+(.+)$ ]]; then
				REPOS+=("${BASH_REMATCH[1]}")
			fi
		fi
	done <"$config_file"
	[[ ${#REPOS[@]} -gt 0 ]] || {
		echo "ERROR: no repos in config: $config_file" >&2
		exit 1
	}
}

# Load bot_authors: lines under "bot_authors:" until next top-level "word:" key.
load_bot_authors_from_config_bash() {
	local config_file="$1"
	[[ -f $config_file ]] || return 1
	BOT_AUTHORS=()
	local in_bots=false
	local line normalized
	while IFS= read -r line || [[ -n $line ]]; do
		normalized="${line%$'\r'}"
		if [[ $normalized =~ ^bot_authors:[[:space:]]*$ ]]; then
			in_bots=true
			continue
		fi
		if [[ $in_bots == true ]]; then
			if [[ $normalized =~ ^[a-zA-Z_][a-zA-Z0-9_]*:[[:space:]]*$ ]]; then
				break
			fi
			if [[ $normalized =~ ^[[:space:]]*-[[:space:]]+(.+)$ ]]; then
				# Strip inline YAML comments (e.g. " # note")
				local ent="${BASH_REMATCH[1]%%#*}"
				ent="${ent%"${ent##*[![:space:]]}"}"
				[[ -n $ent ]] && BOT_AUTHORS+=("$ent")
			fi
		fi
	done <"$config_file"
	[[ ${#BOT_AUTHORS[@]} -gt 0 ]]
}

# Prefer PyYAML via helper script; exit 2 from helper means "no PyYAML, use bash".
load_pr_review_agent_config() {
	local config_file="$1"
	[[ -f $config_file ]] || {
		echo "ERROR: config not found: $config_file" >&2
		exit 1
	}
	REPOS=()
	BOT_AUTHORS=()
	local py_out py_status
	py_out="$(python3 "$SCRIPT_DIR/_load_pr_review_agent_config.py" "$config_file" 2>/dev/null)" && py_status=0 || py_status=$?
	if [[ $py_status -eq 2 ]]; then
		load_repos_from_config_bash "$config_file"
		load_bot_authors_from_config_bash "$config_file" || true
	elif [[ $py_status -eq 0 ]]; then
		local key val
		while IFS=$'\t' read -r key val; do
			[[ -z ${key-} ]] && continue
			case "$key" in
			repo) REPOS+=("$val") ;;
			bot) BOT_AUTHORS+=("$val") ;;
			esac
		done < <(printf '%s\n' "$py_out")
	else
		echo "ERROR: could not parse $config_file (install PyYAML or fix YAML)" >&2
		exit 1
	fi
	[[ ${#REPOS[@]} -gt 0 ]] || {
		echo "ERROR: no repos in config: $config_file" >&2
		exit 1
	}
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--config)
		[[ $# -ge 2 ]] || {
			echo "ERROR: --config needs a path" >&2
			exit 1
		}
		CONFIG_FILE="$2"
		shift 2
		;;
	--repo)
		[[ $# -ge 2 ]] || {
			echo "ERROR: --repo needs owner/name" >&2
			exit 1
		}
		REPOS+=("$2")
		shift 2
		;;
	--limit)
		[[ $# -ge 2 ]] || {
			echo "ERROR: --limit needs a number" >&2
			exit 1
		}
		LIMIT="$2"
		shift 2
		;;
	--details)
		INCLUDE_DETAILS=true
		shift
		;;
	--bots-only)
		BOTS_ONLY=true
		shift
		;;
	--compare-bots)
		COMPARE_BOTS=true
		shift
		;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		echo "ERROR: unknown argument: $1" >&2
		usage >&2
		exit 1
		;;
	esac
done

if [[ $BOTS_ONLY == true && $COMPARE_BOTS == true ]]; then
	echo "ERROR: use only one of --bots-only or --compare-bots" >&2
	exit 1
fi

if [[ -n ${GH_REPO-} ]]; then
	REPOS=("$GH_REPO")
fi

if [[ -n $CONFIG_FILE ]]; then
	load_pr_review_agent_config "$CONFIG_FILE"
elif [[ ${#REPOS[@]} -eq 0 ]]; then
	default_config="$REPO_ROOT/tasks/pr-review-agent.config.yaml"
	if [[ -f $default_config ]]; then
		load_pr_review_agent_config "$default_config"
	else
		echo "ERROR: No repositories specified. Use --repo or provide a config file." >&2
		exit 1
	fi
fi

if [[ ${#BOT_AUTHORS[@]} -eq 0 ]]; then
	BOT_AUTHORS=(
		"dependabot[bot]"
		"renovate[bot]"
		"google-labs-jules[bot]"
	)
fi

command -v gh >/dev/null 2>&1 || {
	echo "ERROR: gh CLI not found" >&2
	exit 1
}
command -v python3 >/dev/null 2>&1 || {
	echo "ERROR: python3 not found" >&2
	exit 1
}

# Summarize PR list JSON to stdout (markdown table + automation hints).
summarize_prs_py() {
	local detail_flag="$1"
	local json_path="$2"
	python3 "$SCRIPT_DIR/get_prs_summarize.py" "$detail_flag" "$json_path"
}

# Shared: gh pr list → temp JSON → Python summarizer (trap cleans temp files).
summarize_pr_json_for_repo() {
	local repo="$1"
	shift
	local json_raw json_file
	if ! json_raw="$(gh pr list --repo "$repo" "$@" --state open --limit "$LIMIT" --json \
		number,title,author,isDraft,headRefName,body,createdAt,updatedAt,mergeable,mergeStateStatus,url,statusCheckRollup \
		2>&1)"; then
		printf '%s\n' "$json_raw" >&2
		echo "_Failed to list PRs for ${repo} (gh exited non-zero)._"
		echo ""
		return 0
	fi
	if [[ -z $json_raw ]] || [[ ${json_raw:0:1} != "[" ]]; then
		printf '%s\n' "$json_raw" >&2
		echo "_Unexpected gh output for ${repo} (expected JSON array)._"
		echo ""
		return 0
	fi
	json_file="$(mktemp "${TMPDIR:-/tmp}/get_prs.XXXXXX.json")"
	register_get_prs_temp "$json_file"
	printf '%s' "$json_raw" >"$json_file"
	export GH_DETAIL_REPO="$repo"
	if [[ $INCLUDE_DETAILS == true ]]; then
		summarize_prs_py true "$json_file"
	else
		summarize_prs_py false "$json_file"
	fi
	echo ""
}

run_full_inventory() {
	for repo in "${REPOS[@]}"; do
		echo "## ${repo}"
		echo ""
		summarize_pr_json_for_repo "$repo"
	done
}

# Legacy comparison: original script behavior (per-repo × per-bot --author filter).
run_legacy_bots_only() {
	echo ""
	# shellcheck disable=SC2016
	echo '## Legacy comparison: `gh pr list --author` (bots only)'
	echo ""
	# shellcheck disable=SC2016
	printf '_Bot logins: `%s`._\n' "${BOT_AUTHORS[*]}"
	echo "_Misses automation opened under a human GitHub user (common for Jules UI) even when the body or commits reference a bot._"
	echo ""
	for repo in "${REPOS[@]}"; do
		for author in "${BOT_AUTHORS[@]}"; do
			echo "### ${repo} — \`${author}\`"
			echo ""
			summarize_pr_json_for_repo "$repo" --author "$author"
		done
	done
}

export GH_DETAIL_REPO=""

if [[ $BOTS_ONLY == true ]]; then
	# shellcheck disable=SC2016
	echo '# Open PR inventory (legacy: `--bots-only`)'
	echo ""
	# shellcheck disable=SC2016
	echo '_Only PRs whose GitHub **author** matches `bot_authors`. Use default mode or `--compare-bots` for the full open list._'
	echo ""
	run_legacy_bots_only
	echo "---"
	echo "Done."
	exit 0
fi

echo "# Open PR inventory"
echo ""
echo "_Generated for agent triage: lists **all** open PRs; automation is inferred from metadata and optional review/comment fetch._"
if [[ $COMPARE_BOTS == true ]]; then
	# shellcheck disable=SC2016
	echo '_Also appending a **legacy bots-only** section at the end (`--compare-bots`)._'
fi
echo ""

run_full_inventory

if [[ $COMPARE_BOTS == true ]]; then
	run_legacy_bots_only
fi

echo "---"
echo "Done."
