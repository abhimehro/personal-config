#!/bin/bash
# Final resolution script for ctrld-sync PR #37

CTRLD_DIR="../ctrld-sync"
PR_ID=37

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting final resolution for ctrld-sync PR #$PR_ID...${NC}"

if [ ! -d "$CTRLD_DIR" ]; then
    echo -e "${RED}Error: Directory $CTRLD_DIR not found.${NC}"
    exit 1
fi

cd "$CTRLD_DIR" || exit 1

# Get branch name
BRANCH_NAME=$(gh pr view $PR_ID --json headRefName -q .headRefName)
if [ -z "$BRANCH_NAME" ]; then
    echo -e "${RED}Could not find branch for PR #$PR_ID${NC}"
    exit 1
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
    echo "Attempting to merge PR via admin..."
    gh pr merge $PR_ID --repo abhimehro/ctrld-sync --merge --delete-branch --admin
else
    echo -e "${RED}Failed to push.${NC}"
fi

# Return to main
git checkout main
echo -e "\n${GREEN}Done!${NC}"
