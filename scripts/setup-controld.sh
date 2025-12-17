#!/bin/bash
#
# Control D Setup Script
# Installs controld-manager and initializes Control D configuration
#
# Usage: ./scripts/setup-controld.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROLD_MANAGER_SRC="$REPO_ROOT/controld-system/scripts/controld-manager"
CONTROLD_MANAGER_DEST="/usr/local/bin/controld-manager"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()      { echo -e "${BLUE}[INFO]${NC} $*"; }
success()  { echo -e "${GREEN}[OK]${NC} $*"; }
error()    { echo -e "${RED}[ERR]${NC} $*" >&2; exit 1; }
warn()     { echo -e "${YELLOW}[WARN]${NC} $*"; }

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    error "Please run as your normal user (not root). The script will ask for sudo when needed."
fi

# Check prerequisites
command -v ctrld >/dev/null 2>&1 || error "ctrld not found. Install with: brew install ctrld"

# Install controld-manager
log "Installing controld-manager..."
if [[ ! -f "$CONTROLD_MANAGER_SRC" ]]; then
    error "controld-manager source not found at: $CONTROLD_MANAGER_SRC"
fi

if [[ -f "$CONTROLD_MANAGER_DEST" ]]; then
    warn "controld-manager already installed at $CONTROLD_MANAGER_DEST"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Skipping controld-manager installation"
    else
        sudo cp "$CONTROLD_MANAGER_SRC" "$CONTROLD_MANAGER_DEST"
        sudo chmod +x "$CONTROLD_MANAGER_DEST"
        sudo chown root:wheel "$CONTROLD_MANAGER_DEST"
        success "controld-manager installed"
    fi
else
    sudo cp "$CONTROLD_MANAGER_SRC" "$CONTROLD_MANAGER_DEST"
    sudo chmod +x "$CONTROLD_MANAGER_DEST"
    sudo chown root:wheel "$CONTROLD_MANAGER_DEST"
    success "controld-manager installed"
fi

# Verify installation
if ! command -v controld-manager >/dev/null 2>&1; then
    error "controld-manager installation failed"
fi

success "Setup complete!"
echo ""
log "Next steps:"
echo "  1. Start Control D with browsing profile:"
echo "     cd $REPO_ROOT"
echo "     ./scripts/network-mode-manager.sh controld browsing"
echo ""
echo "  2. Or use your Fish aliases:"
echo "     nm-browse    # Browsing profile"
echo "     nm-privacy   # Privacy profile"
echo "     nm-gaming    # Gaming profile"
echo "     nm-status    # Check status"
echo ""
echo "  3. For Windscribe VPN mode:"
echo "     ./scripts/network-mode-manager.sh windscribe"
echo "     # or: nm-vpn"
