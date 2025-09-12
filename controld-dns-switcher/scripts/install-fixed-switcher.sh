#!/bin/bash
# DNS Switcher Installation Script
# Installs the working DNS profile switcher and fixes configuration issues
# 
# Usage: sudo ./install-fixed-switcher.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔧 Installing fixed DNS switcher..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Error: This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p /opt/controld-switcher/etc
mkdir -p /var/run/ctrld-switcher
mkdir -p /var/log/ctrld-switcher

# Install working script
echo "📋 Installing working DNS switcher script..."
if [[ -f "$REPO_ROOT/bin/quick-dns-switch-working" ]]; then
    cp "$REPO_ROOT/bin/quick-dns-switch-working" /usr/local/bin/quick-dns-switch-simple
    chmod +x /usr/local/bin/quick-dns-switch-simple
    echo "✅ Working script installed as /usr/local/bin/quick-dns-switch-simple"
else
    echo "❌ Error: Working script not found at $REPO_ROOT/bin/quick-dns-switch-working"
    exit 1
fi

# Backup and replace original if it exists
if [[ -f /usr/local/bin/quick-dns-switch ]]; then
    if [[ ! -L /usr/local/bin/quick-dns-switch ]]; then
        echo "🔄 Backing up original script..."
        mv /usr/local/bin/quick-dns-switch /usr/local/bin/quick-dns-switch-original
    else
        echo "🗑️  Removing existing symlink..."
        rm /usr/local/bin/quick-dns-switch
    fi
fi

# Create symlink
echo "🔗 Creating symlink..."
ln -s /usr/local/bin/quick-dns-switch-simple /usr/local/bin/quick-dns-switch

# Create configuration file
echo "⚙️  Creating configuration file..."
cat > /opt/controld-switcher/etc/config.json << 'EOF'
{
  "version": "3.0.0",
  "profiles": {
    "privacy": {
      "id": "2eoeqoo9ib9",
      "endpoint": "https://dns.controld.com/2eoeqoo9ib9",
      "description": "Enhanced security and privacy filtering"
    },
    "gaming": {
      "id": "1igcvpwtsfg", 
      "endpoint": "https://dns.controld.com/1igcvpwtsfg",
      "description": "Low latency gaming optimization"
    }
  },
  "network": {
    "timeout": 5000,
    "retries": 3
  }
}
EOF

# Set proper permissions
echo "🔐 Setting permissions..."
chown root:wheel /usr/local/bin/quick-dns-switch-simple
chown root:wheel /opt/controld-switcher/etc/config.json
chmod 644 /opt/controld-switcher/etc/config.json

# Clean up any stale lock files
echo "🧹 Cleaning up stale files..."
rm -f /var/run/ctrld-switcher/switcher.lock

echo ""
echo "✅ DNS switcher installation completed successfully!"
echo ""
echo "Usage:"
echo "  sudo quick-dns-switch gaming   # Switch to gaming profile"
echo "  sudo quick-dns-switch privacy  # Switch to privacy profile"  
echo "  quick-dns-switch status        # Check current status"
echo ""
echo "Test the installation:"
echo "  sudo quick-dns-switch gaming && quick-dns-switch status"
echo ""