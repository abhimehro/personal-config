#!/usr/bin/env bash
#
# Git LFS Setup Script
# This script sets up Git LFS for the repository and tracks large files.
#
# Usage: ./setup_git_lfs.sh

set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Setting up Git LFS for personal-config repository..."

# Check if git-lfs is installed
if ! command -v git-lfs >/dev/null 2>&1; then
    echo "Error: git-lfs is not installed."
    echo "Please install Git LFS first:"
    echo "  macOS: brew install git-lfs"
    echo "  Linux: sudo apt-get install git-lfs (Debian/Ubuntu)"
    echo "  Windows: Download from https://git-lfs.com/"
    exit 1
fi

echo "✓ Git LFS is installed"

# Initialize Git LFS
git lfs install

echo "✓ Git LFS initialized"

# Track large files with Git LFS
echo "Tracking large files with Git LFS..."

# Track Raycast configuration files
git lfs track "configs/Raycast_*.rayconfig"

# Track patch files
git lfs track "*.patch"

# Track binary files
git lfs track "*.bin"
git lfs track "*.dat"

# Track archive files
git lfs track "*.tar.gz"
git lfs track "*.zip"

# Track database files
git lfs track "*.db"
git lfs track "*.sqlite"

echo "✓ Large file patterns configured"

# Show current Git LFS tracking
echo "Current Git LFS tracking:"
git lfs track

# Migrate existing large files to Git LFS
echo "Migrating existing large files to Git LFS..."
git lfs migrate import --include="configs/Raycast_*.rayconfig,*.patch,*.bin,*.dat,*.tar.gz,*.zip,*.db,*.sqlite" --above=10KB

echo "✓ Git LFS setup complete!"
echo ""
echo "Next steps:"
echo "1. Commit the .gitattributes file"
echo "2. Push to GitHub"
echo "3. The large files will be stored in Git LFS"