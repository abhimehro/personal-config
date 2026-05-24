#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${ROOT}/scripts/ensure_gh_token.sh"

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

