#!/usr/bin/env bash
set -euo pipefail

gh_token_env_path="${GH_TOKEN_ENV_PATH:-../email-security-pipeline/GH_TOKEN.env}"

# SECURITY: Fail closed if the token env file is missing or unreadable so we
# do not continue into destructive GitHub CLI operations with an uninitialized
# environment.
if [ ! -r "$gh_token_env_path" ]; then
  echo "Error: GitHub token env file is missing or unreadable: $gh_token_env_path" >&2
  exit 1
fi

source "$gh_token_env_path"

close_pr() {
  local repo=$1
  local pr=$2
  local reason=$3
  echo "Closing $repo#$pr ($reason)..."
  gh pr close $pr -R $repo -c "Automated triage: $reason"
}

close_pr "abhimehro/ctrld-sync" "702" "Semantic duplicate of a newer automated PR (#707)"
close_pr "abhimehro/ctrld-sync" "697" "Semantic duplicate of a newer automated PR (#706)"
close_pr "abhimehro/personal-config" "732" "Semantic duplicate of a newer automated PR (#744)"
close_pr "abhimehro/personal-config" "724" "Semantic duplicate of a newer automated PR (#744)"

