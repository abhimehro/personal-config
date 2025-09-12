#!/usr/bin/env bash
set -euo pipefail

# DNS Scripts Deployment Script
# Deploys Control D DNS switching scripts to ~/bin

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/bin"
SCRIPTS=("dns-privacy" "dns-gaming")

echo "🔧 DNS Scripts Deployment"
echo "========================="
echo "Source: $SCRIPT_DIR"
echo "Target: $TARGET_DIR"
echo ""

# Create ~/bin if it doesn't exist
if [[ ! -d "$TARGET_DIR" ]]; then
    echo "📁 Creating $TARGET_DIR"
    mkdir -p "$TARGET_DIR"
fi

# Check if ~/bin is in PATH
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    echo "⚠️  Warning: $TARGET_DIR is not in PATH"
    echo "   Add this to your ~/.bash_profile:"
    echo "   export PATH=\"$TARGET_DIR:\$PATH\""
fi

# Deploy scripts
echo "📋 Deploying scripts:"
for script in "${SCRIPTS[@]}"; do
    if [[ -f "$SCRIPT_DIR/$script" ]]; then
        echo "   ✅ $script"
        cp "$SCRIPT_DIR/$script" "$TARGET_DIR/$script"
        chmod +x "$TARGET_DIR/$script"
    else
        echo "   ❌ $script (not found)"
        exit 1
    fi
done

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Usage:"
echo "   sudo dns-privacy    # Switch to privacy mode"
echo "   sudo dns-gaming     # Switch to gaming mode"
echo ""
echo "Verification:"
echo "   command -v dns-privacy"
echo "   command -v dns-gaming"
echo ""
echo "For help, see: $SCRIPT_DIR/README.md"

# Test if commands are accessible
echo "🧪 Testing deployment:"
for script in "${SCRIPTS[@]}"; do
    if command -v "$script" >/dev/null 2>&1; then
        echo "   ✅ $script command available"
    else
        echo "   ❌ $script command not found in PATH"
        echo "      Try: source ~/.bash_profile"
    fi
done

echo ""
echo "✨ Ready to use! Remember to run scripts with sudo."