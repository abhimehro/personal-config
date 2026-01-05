#!/bin/bash

# Ensure gh is installed and authenticated
if ! command -v gh &> /dev/null; then
    echo "Error: 'gh' CLI tool is not installed."
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "Error: You are not logged into GitHub CLI. Please run 'gh auth login' first."
    exit 1
fi

echo "Closing duplicate PRs for personal-config..."
# Duplicate PRs identified for personal-config
gh pr close 78 74 72 69 65 76 70 64 --repo abhimehro/personal-config -c "Closing as duplicate/superseded."

echo "Closing duplicate PRs for ctrld-sync..."
# Duplicate PRs identified for ctrld-sync
gh pr close 59 48 68 64 61 58 55 49 45 66 65 62 56 46 43 63 60 57 54 51 47 42 39 --repo abhimehro/ctrld-sync -c "Closing as duplicate/superseded."

echo "Closing duplicate PRs for email-security-pipeline..."
# Duplicate PRs identified for email-security-pipeline
gh pr close 55 59 53 50 48 45 43 41 37 34 51 47 38 54 49 40 --repo abhimehro/email-security-pipeline -c "Closing as duplicate/superseded."

echo "Batch closure complete."
