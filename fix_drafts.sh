#!/usr/bin/env bash
set -euo pipefail

gh_token_env_path="${GH_TOKEN_ENV_PATH:-../email-security-pipeline/GH_TOKEN.env}"

# SECURITY: Fail closed if the token env file is missing or unreadable.
if [ ! -r "$gh_token_env_path" ]; then
  echo "Error: GH token env file is missing or unreadable: $gh_token_env_path" >&2
  exit 1
fi

source "$gh_token_env_path"

fix_and_merge() {
  local repo=$1
  local pr=$2
  echo "Marking $repo#$pr ready and merging..."
  # Tolerate individual failures so one bad PR does not abort the batch.
  # `set -e` still applies to setup above.
  if ! gh pr ready "$pr" -R "$repo"; then
    echo "  -> WARNING: failed to mark $repo#$pr ready; skipping." >&2
    return
  fi
  if ! gh pr merge "$pr" -R "$repo" --squash --delete-branch; then
    echo "  -> WARNING: failed to merge $repo#$pr; continuing." >&2
  fi
}

fix_and_merge "abhimehro/email-security-pipeline" "632"
fix_and_merge "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project" "102"
fix_and_merge "abhimehro/personal-config" "743"

