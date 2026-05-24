# shellcheck source=scripts/ensure_gh_token.sh
source "$(dirname "$0")/scripts/ensure_gh_token.sh"

fix_and_merge() {
  local repo=$1
  local pr=$2
  echo "Marking $repo#$pr ready and merging..."
  gh pr ready $pr -R $repo
  gh pr merge $pr -R $repo --squash --delete-branch
}

fix_and_merge "abhimehro/email-security-pipeline" "632"
fix_and_merge "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project" "102"
fix_and_merge "abhimehro/personal-config" "743"

