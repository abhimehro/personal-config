#!/usr/bin/env bash
#
# Install All Configs - Master Installation Script
# Sets up all configuration symlinks and verifies the installation
#
# Usage: ./scripts/install_all_configs.sh

set -Eeuo pipefail

# Repository root (absolute path)
REPO_ROOT="${REPO_ROOT:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions (Palette 🎨 UX enhanced)
log()      { echo -e "${BLUE}ℹ️  [INFO]${NC}  $*"; }
success()  { echo -e "${GREEN}✅ [OK]${NC}    $*"; }
warn()     { echo -e "${YELLOW}⚠️  [WARN]${NC}  $*"; }
error()    { echo -e "${RED}❌ [ERROR]${NC} $*" >&2; }
step()     { echo -e "${BLUE}==>${NC} ${1}"; }
substep()  { echo -e "  ${BLUE}->${NC} ${1}"; }

# Ensure we're in the repo root
if [[ ! -d "$REPO_ROOT" ]]; then
    error "Repository root not found: $REPO_ROOT"
    exit 1
fi

cd "$REPO_ROOT"

# Script paths
SYNC_SCRIPT="$REPO_ROOT/scripts/sync_all_configs.sh"
VERIFY_SCRIPT="$REPO_ROOT/scripts/verify_all_configs.sh"

echo "=========================================="
echo -e "${BLUE}🎨 Personal Config Installer${NC}"
echo "=========================================="
echo ""
step "Plan of Action:"
substep "Link SSH Configs    (${YELLOW}~/.ssh/config${NC})"
substep "Link Fish Configs   (${YELLOW}~/.config/fish${NC})"
substep "Link Editor Configs (${YELLOW}~/.cursor, ~/.vscode${NC})"
substep "Backup existing files automatically"
substep "Verify all symlinks"
echo ""
read -p "Ready to proceed? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Installation cancelled"
    exit 0
fi

echo ""

# Step 1: Sync all configs
if [[ ! -x "$SYNC_SCRIPT" ]]; then
    error "Sync script not found or not executable: $SYNC_SCRIPT"
    exit 1
fi

step "Creating symlinks..."
"$SYNC_SCRIPT"
sync_exit=$?

if [[ $sync_exit -ne 0 ]]; then
    error "Failed to sync configuration files"
    exit 1
fi

echo ""

# Step 2: Verify installation
if [[ ! -x "$VERIFY_SCRIPT" ]]; then
    error "Verify script not found or not executable: $VERIFY_SCRIPT"
    exit 1
fi

step "Verifying installation..."
"$VERIFY_SCRIPT"
verify_exit=$?

echo ""

# Summary
if [[ $sync_exit -eq 0 ]] && [[ $verify_exit -eq 0 ]]; then
    echo -e "${GREEN}✨ Installation completed successfully!${NC}"
    echo "=========================================="
    echo ""
    step "Next steps:"
    substep "Reload shell: ${YELLOW}exec fish${NC}"
    substep "Test Network: ${YELLOW}nm-status${NC}"
    substep "Verify SSH:   ${YELLOW}./scripts/verify_ssh_config.sh${NC}"
    echo ""
    exit 0
else
    error "Installation completed with errors"
    echo "=========================================="
    echo ""
    step "Troubleshooting:"
    substep "Run sync manually:   ${YELLOW}./scripts/sync_all_configs.sh${NC}"
    substep "Run verify manually: ${YELLOW}./scripts/verify_all_configs.sh${NC}"
    echo ""
    exit 1
fi
