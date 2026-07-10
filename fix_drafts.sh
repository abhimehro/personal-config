#!/usr/bin/env bash
# Mark draft pull requests ready and merge them using a safely loaded GH_TOKEN.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/ensure_gh_token.sh
source "${SCRIPT_DIR}/scripts/ensure_gh_token.sh"

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
