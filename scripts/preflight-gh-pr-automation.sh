#!/usr/bin/env bash
set -euo pipefail

# Preflight for multi-repo PR automation capabilities.
# Default mode is read-only capability verification.
# Optional write-probe mode performs real PR mutations on dedicated probe PRs.

SCRIPT_NAME="$(basename "$0")"

readonly DEFAULT_REPOS=(
  "abhimehro/personal-config"
  "abhimehro/email-security-pipeline"
  "abhimehro/ctrld-sync"
)

declare -a REPOS=()
declare -A PROBE_PRS=()
REQUIRE_WRITE_PROBES=false
CONFIG_FILE=""

usage() {
  cat <<'USAGE'
Usage:
  preflight-gh-pr-automation.sh [options]

Options:
  --config PATH                 Load repos from YAML config (path to pr-review-agent.config.yaml).
  --repo OWNER/REPO             Add repository to check (repeatable).
  --require-write-probes        Enable mutation probes for review/comment/close/reopen.
  --probe-pr OWNER/REPO#NUMBER  Probe PR mapping (repeatable, required with --require-write-probes).
  -h, --help                    Show this help.

Examples:
  # Read-only preflight (repos from config)
  bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml

  # Read-only preflight (explicit repos)
  bash scripts/preflight-gh-pr-automation.sh \
    --repo abhimehro/personal-config \
    --repo abhimehro/email-security-pipeline \
    --repo abhimehro/ctrld-sync

  # Full capability probe (mutating) on dedicated probe PRs
  bash scripts/preflight-gh-pr-automation.sh \
    --repo abhimehro/personal-config \
    --repo abhimehro/email-security-pipeline \
    --repo abhimehro/ctrld-sync \
    --require-write-probes \
    --probe-pr abhimehro/personal-config#123 \
    --probe-pr abhimehro/email-security-pipeline#456 \
    --probe-pr abhimehro/ctrld-sync#789
USAGE
}

log() { printf '[INFO] %s\n' "$*"; }
pass() { printf '[PASS] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; }
fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || fail "Missing required command: $cmd"
}

# Load repos from YAML config. Expects top-level "repos:" list.
# ASSUMES: config has "repos:" followed by "- owner/repo" lines until next top-level key.
load_repos_from_config() {
  local config_file="$1"
  [[ -f "$config_file" ]] || fail "Config file not found: $config_file"
  REPOS=()
  while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*-[[:space:]]+(.+)$ ]]; then
      REPOS+=("${BASH_REMATCH[1]}")
    fi
  done < <(sed -n '/^repos:/,/^[a-zA-Z_][a-zA-Z0-9_]*:/p' "$config_file" | grep '^  - ' | sed 's/^  - //' | tr -d '\r')
  [[ ${#REPOS[@]} -gt 0 ]] || fail "Config file has no repos list: $config_file"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --config)
        [[ $# -ge 2 ]] || fail "--config requires a value"
        CONFIG_FILE="$2"
        shift 2
        ;;
      --repo)
        [[ $# -ge 2 ]] || fail "--repo requires a value"
        REPOS+=("$2")
        shift 2
        ;;
      --require-write-probes)
        REQUIRE_WRITE_PROBES=true
        shift
        ;;
      --probe-pr)
        [[ $# -ge 2 ]] || fail "--probe-pr requires OWNER/REPO#NUMBER"
        local mapping="$2"
        [[ "$mapping" == *"#"* ]] || fail "Invalid --probe-pr value: $mapping"
        local repo="${mapping%%#*}"
        local pr="${mapping##*#}"
        [[ "$repo" == */* ]] || fail "Invalid repo in --probe-pr: $mapping"
        [[ "$pr" =~ ^[0-9]+$ ]] || fail "Invalid PR number in --probe-pr: $mapping"
        PROBE_PRS["$repo"]="$pr"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        fail "Unknown argument: $1"
        ;;
    esac
  done

  if [[ -n "$CONFIG_FILE" ]]; then
    load_repos_from_config "$CONFIG_FILE"
  elif [[ ${#REPOS[@]} -eq 0 ]]; then
    REPOS=("${DEFAULT_REPOS[@]}")
  fi

  if [[ "$REQUIRE_WRITE_PROBES" == true ]]; then
    local repo
    for repo in "${REPOS[@]}"; do
      [[ -n "${PROBE_PRS[$repo]:-}" ]] || fail "Missing --probe-pr for $repo while --require-write-probes is enabled"
    done
  fi
}

auth_preflight() {
  log "Checking GitHub CLI authentication"
  gh auth status >/dev/null 2>&1 || fail "gh is not authenticated. Run: gh auth login"
  pass "gh authentication is active"
}

get_sample_pr() {
  local repo="$1"
  # Prefer bot-authored PRs for realistic automation probing.
  local pr
  pr="$(
    gh pr list --repo "$repo" --state open --limit 50 --json number,author \
      --jq 'map(select(.author.is_bot == true))[0].number // .[0].number // empty' 2>/dev/null || true
  )"
  printf '%s' "$pr"
}

check_repo_readonly() {
  local repo="$1"
  [[ "$repo" == */* ]] || fail "Invalid repo format: $repo (expected OWNER/REPO)"

  log "Read-only checks for $repo"
  gh repo view "$repo" --json nameWithOwner,defaultBranchRef >/dev/null 2>&1 \
    || fail "$repo is not accessible for this token/app installation"
  pass "$repo repository read access OK"

  local pr_number
  pr_number="$(get_sample_pr "$repo")"

  if [[ -z "$pr_number" ]]; then
    warn "$repo has no open PRs; PR-scoped checks skipped"
    return
  fi

  gh pr view "$pr_number" --repo "$repo" \
    --json number,title,mergeable,mergeStateStatus,isDraft >/dev/null 2>&1 \
    || fail "$repo#${pr_number} cannot be read via gh pr view"
  pass "$repo#${pr_number} PR metadata read OK"

  local checks_out=""
  local checks_err=""
  checks_out="$(gh pr checks "$pr_number" --repo "$repo" --json name,state,bucket,workflow 2> >(checks_err="$(cat)"; typeset -p checks_err >/dev/null) || true)"

  if [[ -z "$checks_out" ]]; then
    # Re-run once to capture deterministic stderr content.
    checks_err="$(gh pr checks "$pr_number" --repo "$repo" --json name,state,bucket,workflow 2>&1 >/dev/null || true)"
    fail "$repo#${pr_number} check visibility failed. Details: ${checks_err:-unknown error}"
  fi
  pass "$repo#${pr_number} checks visibility OK"

  local owner="${repo%%/*}"
  local name="${repo##*/}"
  local gql
  gql="$(gh api graphql \
    -f query='query($owner:String!, $name:String!, $number:Int!){ repository(owner:$owner,name:$name){ pullRequest(number:$number){ viewerCanUpdate viewerCanEnableAutoMerge viewerCanDeleteHeadRef mergeable } } }' \
    -f owner="$owner" -f name="$name" -F number="$pr_number" \
    --jq '.data.repository.pullRequest' 2>/dev/null || true)"

  if [[ -z "$gql" ]]; then
    warn "$repo#${pr_number} capability introspection unavailable (GraphQL blocked or query failed)"
  else
    pass "$repo#${pr_number} capability introspection OK"
    local can_update
    local can_auto_merge
    can_update="$(gh api graphql \
      -f query='query($owner:String!, $name:String!, $number:Int!){ repository(owner:$owner,name:$name){ pullRequest(number:$number){ viewerCanUpdate } } }' \
      -f owner="$owner" -f name="$name" -F number="$pr_number" \
      --jq '.data.repository.pullRequest.viewerCanUpdate' 2>/dev/null || true)"
    can_auto_merge="$(gh api graphql \
      -f query='query($owner:String!, $name:String!, $number:Int!){ repository(owner:$owner,name:$name){ pullRequest(number:$number){ viewerCanEnableAutoMerge } } }' \
      -f owner="$owner" -f name="$name" -F number="$pr_number" \
      --jq '.data.repository.pullRequest.viewerCanEnableAutoMerge' 2>/dev/null || true)"

    if [[ "$can_update" != "true" ]]; then
      warn "$repo#${pr_number} viewerCanUpdate=false (close/comment/review likely blocked without higher scope)"
    fi
    if [[ "$can_auto_merge" != "true" ]]; then
      warn "$repo#${pr_number} viewerCanEnableAutoMerge=false (auto-merge enablement likely blocked)"
    fi
  fi
}

check_repo_write_probe() {
  local repo="$1"
  local pr_number="${PROBE_PRS[$repo]}"
  local marker
  marker="[automation-preflight $(date -u +%Y-%m-%dT%H:%M:%SZ)]"

  log "Write probes for $repo using PR #$pr_number"
  gh pr view "$pr_number" --repo "$repo" --json number,state,isDraft >/dev/null 2>&1 \
    || fail "Probe PR $repo#$pr_number is not accessible"

  # Probe review-comment permission.
  gh pr review "$pr_number" --repo "$repo" --comment \
    --body "$marker review-permission-probe" >/dev/null 2>&1 \
    || fail "$repo#$pr_number review probe failed (missing addPullRequestReview scope)"
  pass "$repo#$pr_number review permission OK"

  # Probe issue-comment permission.
  gh pr comment "$pr_number" --repo "$repo" \
    --body "$marker issue-comment-permission-probe" >/dev/null 2>&1 \
    || fail "$repo#$pr_number comment probe failed (missing addComment/issues write scope)"
  pass "$repo#$pr_number issue comment permission OK"

  # Probe close + reopen permission.
  gh pr close "$pr_number" --repo "$repo" >/dev/null 2>&1 \
    || fail "$repo#$pr_number close probe failed (missing closePullRequest scope)"
  pass "$repo#$pr_number close permission OK"

  gh pr reopen "$pr_number" --repo "$repo" >/dev/null 2>&1 \
    || fail "$repo#$pr_number reopen probe failed; repository may now require manual reopen"
  pass "$repo#$pr_number reopen permission OK"
}

main() {
  require_cmd gh
  parse_args "$@"
  auth_preflight

  local repo
  for repo in "${REPOS[@]}"; do
    check_repo_readonly "$repo"
  done

  if [[ "$REQUIRE_WRITE_PROBES" == true ]]; then
    warn "Write probe mode is enabled: this will add comments/reviews and close+reopen designated probe PRs."
    for repo in "${REPOS[@]}"; do
      check_repo_write_probe "$repo"
    done
  fi

  pass "Preflight completed successfully for ${#REPOS[@]} repository/repositories"
}

main "$@"
