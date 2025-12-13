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

# Helper functions
log()      { echo -e "${BLUE}[INFO]${NC} $@"; }
success()  { echo -e "${GREEN}[OK]${NC} $@"; }
warn()     { echo -e "${YELLOW}[WARN]${NC} $@"; }
error()    { echo -e "${RED}[ERROR]${NC} $@" >&2; }

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
echo "Installing All Configuration Files"
echo "=========================================="
echo ""
echo "This will:"
echo "  1. Create symlinks from repository to home directory"
echo "  2. Backup any existing configuration files"
echo "  3. Verify all symlinks are correctly established"
echo ""
read -p "Continue? (y/N) " -n 1 -r
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

log "Step 1: Creating symlinks..."
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

log "Step 2: Verifying installation..."
"$VERIFY_SCRIPT"
verify_exit=$?

echo ""

# Summary
echo "=========================================="
if [[ $sync_exit -eq 0 ]] && [[ $verify_exit -eq 0 ]]; then
    success "Installation completed successfully!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Reload your fish shell to use new functions:"
    echo "   exec fish"
    echo ""
    echo "2. Test Control D functions:"
    echo "   nm-status          # Check network status"
    echo "   nm-browse          # Switch to browsing mode"
    echo "   nm-privacy         # Switch to privacy mode"
    echo "   nm-gaming          # Switch to gaming mode"
    echo "   nm-vpn             # Switch to Windscribe VPN mode"
    echo ""
    echo "3. Verify SSH configuration:"
    echo "   ./scripts/verify_ssh_config.sh"
    echo ""
    echo "4. Documentation:"
    echo "   - Control D usage: controld-system/docs/Control D DNS Daily Usage Guide.md"
    echo "   - Network modes: scripts/network-mode-manager.sh --help"
    echo ""
    exit 0
else
    error "Installation completed with errors"
    echo "=========================================="
    echo ""
    echo "Please review the errors above and run:"
    echo "  ./scripts/sync_all_configs.sh"
    echo "  ./scripts/verify_all_configs.sh"
    echo ""
    exit 1
fi
