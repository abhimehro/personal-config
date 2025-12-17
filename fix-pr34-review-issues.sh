#!/bin/bash
# Fix PR #34 Review Issues - personal-config
# This script addresses all review feedback for PR #34 in one automated run
# 
# Author: Abhi Mehrotra
# Repository: abhimehro/personal-config
# Branch: normalize-gitignore-eol
# Date: 2025-12-17

set -e  # Exit on any error
set -u  # Exit on undefined variables
set -o pipefail  # Exit on pipe failures

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BRANCH_NAME="normalize-gitignore-eol"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo '')"
COMMIT_MESSAGE="fix: address PR review feedback"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Safety checks
check_prerequisites() {
    log_info "Running prerequisite checks..."
    
    # Check if we're in a git repository
    if [ -z "$REPO_ROOT" ]; then
        log_error "Not in a git repository. Please run this script from within the personal-config repository."
        exit 1
    fi
    
    log_success "Repository root: $REPO_ROOT"
    
    # Navigate to repository root
    cd "$REPO_ROOT"
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        log_warning "You have uncommitted changes. This script will modify files."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Aborted by user."
            exit 0
        fi
    fi
    
    # Check if branch exists
    if ! git rev-parse --verify "$BRANCH_NAME" >/dev/null 2>&1; then
        log_error "Branch '$BRANCH_NAME' does not exist."
        exit 1
    fi
    
    log_success "All prerequisite checks passed."
}

# Checkout the correct branch
checkout_branch() {
    log_info "Checking out branch '$BRANCH_NAME'..."
    
    current_branch=$(git branch --show-current)
    
    if [ "$current_branch" = "$BRANCH_NAME" ]; then
        log_success "Already on branch '$BRANCH_NAME'."
    else
        git checkout "$BRANCH_NAME"
        log_success "Switched to branch '$BRANCH_NAME'."
    fi
}

# Fix 1 & 2: Delete duplicate files
delete_duplicate_files() {
    log_info "Deleting duplicate files..."
    
    local files=(
        "scripts/protondrive_backup.sh"
        "scripts/protondrive_backup.exclude"
    )
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            git rm "$file"
            log_success "Deleted: $file"
        else
            log_warning "File not found (may already be deleted): $file"
        fi
    done
}

# Fix 3: Fix .gitignore - remove duplicate Cursor terminal block (lines 170-172) and fish_variables line
fix_gitignore() {
    log_info "Fixing .gitignore..."
    
    if [ ! -f ".gitignore" ]; then
        log_error ".gitignore not found."
        return 1
    fi
    
    # Create a temporary file
    temp_file=$(mktemp)
    
    # Remove duplicate Cursor terminal block (lines 170-172) and fish_variables line
    # This uses sed to remove the second occurrence of the Cursor terminal block
    # and the fish_variables line
    awk '
    /^# Cursor terminal state$/ {
        cursor_count++
        if (cursor_count == 2) {
            # Skip this line and the next two lines (the duplicate block)
            getline; getline; next
        }
    }
    /^configs\/fish\/fish_variables$/ { next }
    { print }
    ' .gitignore > "$temp_file"
    
    # Replace original file
    mv "$temp_file" .gitignore
    
    log_success "Fixed .gitignore (removed duplicate Cursor block and fish_variables line)"
}

# Fix 4: Add .fish_history to maintenance/conf/protondrive_backup.exclude after .zsh_history
add_fish_history_to_exclude() {
    log_info "Adding .fish_history to protondrive_backup.exclude..."
    
    local exclude_file="maintenance/conf/protondrive_backup.exclude"
    
    if [ ! -f "$exclude_file" ]; then
        log_error "$exclude_file not found."
        return 1
    fi
    
    # Check if .fish_history already exists
    if grep -q "^\.fish_history$" "$exclude_file"; then
        log_success ".fish_history already in $exclude_file (idempotent check passed)"
        return 0
    fi
    
    # Add .fish_history after .zsh_history
    temp_file=$(mktemp)
    awk '
    /^\.zsh_history$/ { print; print ".fish_history"; next }
    { print }
    ' "$exclude_file" > "$temp_file"
    
    mv "$temp_file" "$exclude_file"
    
    log_success "Added .fish_history to $exclude_file"
}

# Fix 5: Fix 'Github' -> 'GitHub' in docs/POST_RESET_GUIDE.md
fix_github_capitalization() {
    log_info "Fixing GitHub capitalization in POST_RESET_GUIDE.md..."
    
    local doc_file="docs/POST_RESET_GUIDE.md"
    
    if [ ! -f "$doc_file" ]; then
        log_error "$doc_file not found."
        return 1
    fi
    
    # Replace all occurrences of 'Github' with 'GitHub' (case-sensitive)
    sed -i.bak 's/Github/GitHub/g' "$doc_file"
    rm -f "${doc_file}.bak"
    
    log_success "Fixed GitHub capitalization in $doc_file"
}

# Fix 6: Remove duplicate --no-delete in macos/com.abhimehrotra.protondrive-backup.plist
fix_plist_duplicate() {
    log_info "Removing duplicate --no-delete from plist file..."
    
    local plist_file="macos/com.abhimehrotra.protondrive-backup.plist"
    
    if [ ! -f "$plist_file" ]; then
        log_error "$plist_file not found."
        return 1
    fi
    
    # Remove duplicate --no-delete entries
    # Keep only the first occurrence
    temp_file=$(mktemp)
    awk '
    /<string>--no-delete<\/string>/ {
        if (!seen) {
            seen = 1
            print
            next
        }
        next
    }
    { print }
    ' "$plist_file" > "$temp_file"
    
    mv "$temp_file" "$plist_file"
    
    log_success "Removed duplicate --no-delete from $plist_file"
}

# Show diff before committing
show_diff() {
    log_info "Showing changes to be committed..."
    echo -e "${YELLOW}========================================${NC}"
    git diff --cached
    echo -e "${YELLOW}========================================${NC}"
}

# Commit changes
commit_changes() {
    log_info "Staging all changes..."
    
    # Stage all modified and deleted files
    git add -A
    
    # Show diff
    if git diff --cached --quiet; then
        log_warning "No changes to commit (all fixes may have already been applied)."
        return 0
    fi
    
    show_diff
    
    # Ask for confirmation
    read -p "Commit these changes? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_info "Commit aborted by user."
        exit 0
    fi
    
    git commit -m "$COMMIT_MESSAGE"
    log_success "Changes committed: $COMMIT_MESSAGE"
}

# Push to origin
push_changes() {
    log_info "Pushing changes to origin/$BRANCH_NAME..."
    
    read -p "Push to remote? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_info "Push aborted by user. You can push manually later with:"
        echo "  git push origin $BRANCH_NAME"
        exit 0
    fi
    
    git push origin "$BRANCH_NAME"
    log_success "Changes pushed to origin/$BRANCH_NAME"
}

# Main execution
main() {
    echo -e "${BLUE}╔═════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Fix PR #34 Review Issues - personal-config               ${NC}"
    echo -e "${BLUE}${NC}"
    echo
    
    check_prerequisites
    checkout_branch
    
    echo
    log_info "Applying all fixes..."
    echo
    
    delete_duplicate_files
    fix_gitignore
    add_fish_history_to_exclude
    fix_github_capitalization
    fix_plist_duplicate
    
    echo
    commit_changes
    push_changes
    
    echo
    echo -e "${GREEN}${NC}"
    echo -e "${GREEN}  All PR #34 review issues have been fixed!               ${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
}

# Run main function
main