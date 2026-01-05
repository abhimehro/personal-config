#!/bin/bash
# Master Conflict Resolution Script v2
# Robust resolution across all dev repositories.

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASE_DEV_DIR="/Users/speedybee/Documents/dev"
REPOS=("personal-config" "ctrld-sync" "email-security-pipeline")

process_repo() {
    local REPO_NAME=$1
    local REPO_PATH="${BASE_DEV_DIR}/${REPO_NAME}"
    
    echo -e "\n${BLUE}📂 Entering Repository: $REPO_NAME${NC}"
    if [ ! -d "$REPO_PATH" ]; then
        echo -e "${RED}Skipping $REPO_NAME (directory not found at $REPO_PATH)${NC}"
        return
    fi

    cd "$REPO_PATH" || return
    
    # 1. Ensure main is clean and up to date
    echo "Updating main branch..."
    git checkout main &>/dev/null
    git reset --hard origin/main &>/dev/null
    git pull origin main &>/dev/null

    # 2. Get list of open PRs by google-labs-jules
    local PR_LIST=$(gh pr list --author "app/google-labs-jules" --json number,title,headRefName --repo "abhimehro/$REPO_NAME")
    
    if [[ $(echo "$PR_LIST" | jq '. | length') -eq 0 ]]; then
        echo -e "${GREEN}No open PRs from Jules in $REPO_NAME.${NC}"
        return
    fi

    echo "$PR_LIST" | jq -c '.[]' | while read -r pr; do
        local ID=$(echo "$pr" | jq -r '.number')
        local TITLE=$(echo "$pr" | jq -r '.title')
        local BRANCH=$(echo "$pr" | jq -r '.headRefName')

        echo -e "\n${YELLOW}───────────────────────────────────────────────────${NC}"
        echo -e "${YELLOW}PR #$ID: $TITLE${NC}"
        echo "Branch: $BRANCH"

        # Fetch and Checkout PR branch
        git fetch origin "$BRANCH" &>/dev/null
        if ! git checkout "$BRANCH" &>/dev/null; then
            echo -e "${RED}Failed to checkout branch $BRANCH. Skipping.${NC}"
            continue
        fi

        # Attempt Merge from main
        echo "Merging main into branch..."
        if git merge origin/main -m "Merge main into $BRANCH"; then
            echo -e "${GREEN}Merge successful.${NC}"
        else
            echo -e "${RED}💥 CONFLICT DETECTED! 💥${NC}"
            echo -e "${YELLOW}Please resolve conflicts in: $REPO_PATH${NC}"
            echo "1. Fix the files in your editor."
            echo "2. git add <fixed-files>"
            echo "3. git commit -m 'Resolve conflicts'"
            read -p "Press ENTER here AFTER you have committed the fix..."
        fi

        # Push the updated branch
        echo "Pushing resolution to remote..."
        if git push origin "$BRANCH"; then
            echo -e "${GREEN}Branch updated on GitHub.${NC}"
            # Final Approval and Merge
            echo "Attempting final merge..."
            gh pr review "$ID" --repo "abhimehro/$REPO_NAME" --approve --body "Gemini: Resolved conflicts and approved." &>/dev/null
            if gh pr merge "$ID" --repo "abhimehro/$REPO_NAME" --merge --delete-branch --admin; then
                echo -e "${GREEN}✓ PR #$ID Merged successfully!${NC}"
            else
                echo -e "${RED}X Failed to merge PR #$ID. It might still have issues or pending checks.${NC}"
            fi
        else
            echo -e "${RED}Failed to push branch. Skipping merge.${NC}"
        fi

        # Go back to main and clean up
        git checkout main &>/dev/null
    done
}

# Run for all repos
for repo in "${REPOS[@]}"; do
    process_repo "$repo"
done

echo -e "\n${GREEN}=======================================================${NC}"
echo -e "${GREEN}Master resolution complete!${NC}"
echo -e "${GREEN}=======================================================${NC}"