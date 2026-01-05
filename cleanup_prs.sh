#!/bin/bash

# Function to close PRs
close_prs() {
    local repo=$1
    local prs=$2
    local comment=$3

    echo "Processing $repo..."
    for pr in $prs; do
        echo "Closing PR #$pr in $repo..."
        gh pr close $pr --repo $repo -c "$comment" || echo "Failed to close #$pr"
    done
}

# Personal Config
# Closing #90 as well (empty/incomplete)
close_prs "abhimehro/personal-config" "90" "Closing incomplete PR (missing script changes)."
close_prs "abhimehro/personal-config" "78 74 72 69 65 76 70 64" "Closing as duplicate/superseded."

# Ctrld Sync
close_prs "abhimehro/ctrld-sync" "59 48 68 64 61 58 55 49 45 66 65 62 56 46 43 63 60 57 54 51 47 42 39" "Closing as duplicate/superseded."

# Email Security Pipeline
close_prs "abhimehro/email-security-pipeline" "55 59 53 50 48 45 43 41 37 34 51 47 38 54 49 40" "Closing as duplicate/superseded."

echo "Cleanup complete."
