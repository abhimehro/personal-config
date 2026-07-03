#!/usr/bin/env bash

source ../email-security-pipeline/GH_TOKEN.env

close_pr() {
  local repo=$1
  local pr=$2
  local reason=$3
  echo "Closing $repo#$pr ($reason)..."
  gh pr close $pr -R $repo -c "Automated triage: $reason"
}

# SUPERSEDED
close_pr "abhimehro/personal-config" "739" "Superseded / Zero-diff PR"
close_pr "abhimehro/email-security-pipeline" "641" "Superseded / Zero-diff PR"
close_pr "abhimehro/email-security-pipeline" "636" "Superseded / Zero-diff PR"
close_pr "abhimehro/email-security-pipeline" "631" "Superseded / Zero-diff PR"

# EXACT DUPLICATE (from script)
close_pr "abhimehro/ctrld-sync" "701" "Duplicate of a newer automated PR"
close_pr "abhimehro/email-security-pipeline" "634" "Duplicate of a newer automated PR"
close_pr "abhimehro/Seatek_Analysis" "124" "Duplicate of a newer automated PR"

# SEMANTIC DUPLICATE
close_pr "abhimehro/Seatek_Analysis" "126" "Semantic duplicate of a newer automated PR (#127)"
close_pr "abhimehro/personal-config" "735" "Semantic duplicate of a newer automated PR (#741)"
close_pr "abhimehro/email-security-pipeline" "635" "Semantic duplicate of a newer automated PR (#642)"
close_pr "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project" "105" "Semantic duplicate of a newer automated PR (#108)"
close_pr "abhimehro/Hydrograph_Versus_Seatek_Sensors_Project" "101" "Semantic duplicate of a newer automated PR (#108)"
