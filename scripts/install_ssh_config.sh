#!/bin/bash
# SSH Configuration Installation Script
# This script installs the SSH configuration for Cursor IDE and 1Password integration

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🔧 Installing SSH Configuration for Cursor IDE + 1Password..."
echo ""

# Check if we're on macOS
if [[ $OSTYPE != "darwin"* ]]; then
	echo "❌ This configuration is designed for macOS"
	exit 1
fi

# Backup existing SSH config
if [ -f ~/.ssh/config ]; then
	echo "📦 Backing up existing SSH config..."
	cp ~/.ssh/config ~/.ssh/config.backup."$(date +%Y%m%d_%H%M%S)"
	echo "✅ Backup created"
fi

# Create SSH directory if it doesn't exist securely (avoids TOCTOU)
install -d -m 700 ~/.ssh

# Copy configuration files atomically with secure permissions
echo "📁 Installing SSH configuration files..."
install -m 600 "$REPO_ROOT/configs/ssh/config" ~/.ssh/config
install -m 600 "$REPO_ROOT/configs/ssh/agent.toml" ~/.ssh/agent.toml

# Create control directory securely (avoids TOCTOU)
install -d -m 700 ~/.ssh/control

# Copy and make scripts executable
echo "📜 Installing SSH scripts..."
mkdir -p ~/.ssh/scripts
cp "$REPO_ROOT/scripts/ssh"/*.sh ~/.ssh/scripts/
chmod +x ~/.ssh/scripts/*.sh

# Create symlinks for easy access
ln -sf ~/.ssh/scripts/smart_connect.sh ~/.ssh/smart_connect.sh
ln -sf ~/.ssh/scripts/check_connections.sh ~/.ssh/check_connections.sh
ln -sf ~/.ssh/scripts/setup_verification.sh ~/.ssh/setup_verification.sh
ln -sf ~/.ssh/scripts/diagnose_vpn.sh ~/.ssh/diagnose_vpn.sh
ln -sf ~/.ssh/scripts/setup_aliases.sh ~/.ssh/setup_aliases.sh

chmod +x ~/.ssh/*.sh

echo ""
echo "✅ SSH Configuration installed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Make sure 1Password SSH agent is enabled:"
echo "   - Open 1Password → Settings → Developer → SSH Agent → Enable"
echo "2. Verify your setup:"
echo "   ~/.ssh/setup_verification.sh"
echo "3. Test connection:"
echo "   ~/.ssh/smart_connect.sh"
echo ""
echo "🎯 For Cursor IDE:"
echo "   - Use host: cursor-mdns (recommended)"
echo "   - Alternative: cursor-local or cursor-auto"
echo ""
echo "📚 Documentation available in:"
echo "   - docs/ssh/README.md"
echo "   - docs/ssh/iTerm2_setup_guide.md"
