#!/bin/bash
# SSH Configuration Installation Script for Cursor IDE + 1Password
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# UX Helpers
RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m' BLUE='\033[0;34m' BOLD='\033[1m' NC='\033[0m'
log() { echo -e "${BLUE}ℹ️  [INFO]${NC} $*"; }
success() { echo -e "${GREEN}✅ [OK]${NC}   $*"; }
error() { echo -e "${RED}❌ [ERR]${NC}  $*" >&2; exit 1; }

echo -e "\n${BOLD}${BLUE}🔧 SSH Configuration Setup${NC}\n"

[[ "$OSTYPE" != "darwin"* ]] && error "This configuration is designed for macOS only."

# Plan & Confirmation
echo -e "${BOLD}Actions:${NC}"
echo -e "  1. ${YELLOW}OVERWRITE${NC} ~/.ssh/config & agent.toml"
echo -e "  2. ${YELLOW}CREATE${NC}    ~/.ssh/control/ & scripts/"
read -p "Proceed? [y/N] " -n 1 -r REPLY; echo ""
[[ ! $REPLY =~ ^[Yy]$ ]] && { log "Cancelled."; exit 0; }

# Backup
if [ -f ~/.ssh/config ]; then
    TS=$(date +%Y%m%d_%H%M%S)
    cp ~/.ssh/config "${HOME}/.ssh/config.backup.$TS"
    success "Backup: ~/.ssh/config.backup.$TS"
fi

mkdir -p ~/.ssh/{control,scripts} && chmod 700 ~/.ssh ~/.ssh/control
log "Installing config files..."
cp "$REPO_ROOT/configs/ssh/config" ~/.ssh/config
cp "$REPO_ROOT/configs/ssh/agent.toml" ~/.ssh/agent.toml
chmod 600 ~/.ssh/config ~/.ssh/agent.toml

log "Installing scripts..."
cp "$REPO_ROOT/scripts/ssh"/*.sh ~/.ssh/scripts/
chmod +x ~/.ssh/scripts/*.sh

# Symlinks
for script in smart_connect check_connections setup_verification diagnose_vpn setup_aliases; do
    ln -sf ~/.ssh/scripts/$script.sh ~/.ssh/$script.sh
done
chmod +x ~/.ssh/*.sh

echo -e "\n${GREEN}✅ Installation Complete!${NC}"
echo -e "${BOLD}Next:${NC} Enable 1Password SSH Agent -> Verify with ${BOLD}~/.ssh/setup_verification.sh${NC}"
