#!/bin/bash
# Script to resolve conflicts for ctrld-sync PRs
# Usage: ./resolve_ctrld_conflicts.sh

CTRLD_DIR="../ctrld-sync"
PR_IDS=(44 40 37)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting conflict resolution for ctrld-sync...${NC}"

if [ ! -d "$CTRLD_DIR" ]; then
    echo -e "${RED}Error: Directory $CTRLD_DIR not found.${NC}"
    exit 1
fi

cd "$CTRLD_DIR" || exit 1

for PR_ID in "${PR_IDS[@]}"; do
    echo -e "\n${GREEN}Processing PR #$PR_ID...${NC}"
    
    # Get branch name
    BRANCH_NAME=$(gh pr view $PR_ID --json headRefName -q .headRefName)
    if [ -z "$BRANCH_NAME" ]; then
        echo -e "${RED}Could not find branch for PR #$PR_ID${NC}"
        continue
    fi
    
    echo "Branch: $BRANCH_NAME"
    
    # Fetch and Checkout
    git fetch origin "$BRANCH_NAME"
    git checkout "$BRANCH_NAME"
    
    # Attempt Merge
    echo "Merging main into $BRANCH_NAME..."
    if git merge origin/main; then
        echo -e "${GREEN}Merge successful (no conflicts).${NC}"
    else
        echo -e "${RED}Merge conflict detected!${NC}"
        echo "Please resolve the conflicts in '$CTRLD_DIR' manually."
        echo "1. Fix the files."
        echo "2. 'git add <file>'"
        echo "3. 'git commit'"
        echo "4. Then press ENTER here to continue."
        read -p "Press ENTER after resolving conflicts..."
    fi
    
    # Push
    echo "Pushing changes..."
    if git push origin "$BRANCH_NAME"; then
        echo -e "${GREEN}Successfully pushed changes to PR #$PR_ID${NC}"
        echo "Attempting to merge PR..."
        gh pr merge $PR_ID --merge --delete-branch
    else
        echo -e "${RED}Failed to push. Please check permissions or manual status.${NC}"
    fi
    
    # Return to main for next iteration
    git checkout main
done

echo -e "\n${GREEN}Done!${NC}"
