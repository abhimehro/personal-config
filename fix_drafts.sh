#!/usr/bin/env bash
# Mark draft pull requests ready and merge them using a safely loaded GH_TOKEN.
set -euo pipefail

if [[ ${1-} != "--yes" ]]; then
	echo "This script marks ready and merges 3 hardcoded PRs from an April 2026 triage run." >&2
	echo "Re-run with --yes if that is still what you want." >&2
	exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# SECURITY: execute the token helper and capture stdout; do not source it.
GH_TOKEN="$(bash "${SCRIPT_DIR}/scripts/ensure_gh_token.sh")"
if [[ -z ${GH_TOKEN} ]]; then
	echo "error: ensure_gh_token.sh returned an empty token" >&2
	exit 1
fi
export GH_TOKEN

fix_and_merge() {
  local repo="$1"
  local pr="$2"
  echo "Marking ${repo}#${pr} ready and merging..."
  gh pr ready "${pr}" --repo "${repo}"
  gh pr merge "${pr}" --repo "${repo}" --squash --delete-branch
}

fix_and_merge "abhimehro/email-security-pipeline" "632"
fix_and_merge "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project" "102"
fix_and_merge "abhimehro/personal-config" "743"
