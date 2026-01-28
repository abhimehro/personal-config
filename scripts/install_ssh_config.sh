#!/bin/bash
# SSH Configuration Installation Script
# This script installs the SSH configuration for Cursor IDE and 1Password integration

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- UX Helpers ---

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Emojis
E_INFO="ℹ️"
E_OK="✅"
E_WARN="⚠️"
E_ERR="❌"
E_FILE="📁"
E_BACKUP="📦"
E_SCRIPT="📜"
E_LINK="🔗"

log()     { echo -e "${BLUE}${E_INFO}  [INFO]${NC}  $*"; }
success() { echo -e "${GREEN}${E_OK} [OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}${E_WARN}  [WARN]${NC}  $*"; }
error()   { echo -e "${RED}${E_ERR} [ERR]${NC}   $*" >&2; exit 1; }
header()  { echo -e "\n${BOLD}${BLUE}$*${NC}\n"; }

# --- Checks ---

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    error "This configuration is designed for macOS"
fi

# --- Plan of Execution ---

header "SSH Configuration Installer"

echo -e "This script will configure your SSH environment for Cursor + 1Password."
echo -e "${RED}${BOLD}WARNING: This operation is destructive for existing configs!${NC}\n"

echo -e "${BOLD}Plan of Execution:${NC}"
echo -e "  1. ${E_BACKUP} Backup existing ${BOLD}~/.ssh/config${NC}"
echo -e "  2. ${E_WARN} ${RED}Overwrite${NC} ${BOLD}~/.ssh/config${NC} with repo version"
echo -e "  3. ${E_WARN} ${RED}Overwrite${NC} ${BOLD}~/.ssh/agent.toml${NC} with repo version"
echo -e "  4. ${E_FILE} Create/Update ${BOLD}~/.ssh/scripts/${NC} and ${BOLD}~/.ssh/control/${NC}"
echo -e "  5. ${E_LINK} Install helper aliases (smart_connect, etc.)"

echo ""
read -p "Are you sure you want to proceed? [y/N] " -n 1 -r REPLY
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Operation cancelled by user."
    exit 0
fi

# --- Execution ---

# Backup existing SSH config
if [ -f ~/.ssh/config ]; then
    BACKUP_FILE=~/.ssh/config.backup.$(date +%Y%m%d_%H%M%S)
    log "Backing up existing SSH config..."
    cp ~/.ssh/config "$BACKUP_FILE"
    success "Backup created at $BACKUP_FILE"
fi

# Create SSH directory if it doesn't exist
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Copy configuration files
log "Installing SSH configuration files..."
cp "$REPO_ROOT/configs/ssh/config" ~/.ssh/config
cp "$REPO_ROOT/configs/ssh/agent.toml" ~/.ssh/agent.toml

# Set proper permissions
chmod 600 ~/.ssh/config
chmod 600 ~/.ssh/agent.toml

# Create control directory
mkdir -p ~/.ssh/control
chmod 700 ~/.ssh/control

# Copy and make scripts executable
log "Installing SSH scripts..."
mkdir -p ~/.ssh/scripts
cp "$REPO_ROOT/scripts/ssh"/*.sh ~/.ssh/scripts/
chmod +x ~/.ssh/scripts/*.sh

# Create symlinks for easy access
log "Creating symlinks..."
ln -sf ~/.ssh/scripts/smart_connect.sh ~/.ssh/smart_connect.sh
ln -sf ~/.ssh/scripts/check_connections.sh ~/.ssh/check_connections.sh
ln -sf ~/.ssh/scripts/setup_verification.sh ~/.ssh/setup_verification.sh
ln -sf ~/.ssh/scripts/diagnose_vpn.sh ~/.ssh/diagnose_vpn.sh
ln -sf ~/.ssh/scripts/setup_aliases.sh ~/.ssh/setup_aliases.sh

chmod +x ~/.ssh/*.sh

header "Installation Complete"

echo -e "${BOLD}Next steps:${NC}"
echo -e "1. ${BOLD}Enable 1Password SSH Agent${NC}:"
echo "   - Open 1Password → Settings → Developer → SSH Agent → Enable"
echo -e "2. ${BOLD}Verify your setup${NC}:"
echo "   ~/.ssh/setup_verification.sh"
echo -e "3. ${BOLD}Test connection${NC}:"
echo "   ~/.ssh/smart_connect.sh"

echo ""
echo -e "${BOLD}For Cursor IDE:${NC}"
echo "   - Use host: cursor-mdns (recommended)"
echo "   - Alternative: cursor-local or cursor-auto"
echo ""
echo -e "${BOLD}Documentation:${NC}"
echo "   - docs/ssh/README.md"
echo "   - docs/ssh/iTerm2_setup_guide.md"
