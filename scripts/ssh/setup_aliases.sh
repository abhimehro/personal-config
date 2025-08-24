#!/bin/bash
# SSH Connection Aliases Setup

echo "🔧 Setting up convenient SSH aliases..."
echo ""

# Create aliases for shell (you can add these to your .bashrc, .zshrc, or .config/fish/config.fish)
cat > ~/.ssh/ssh_aliases.sh << 'EOF'
# SSH Connection Aliases for Cursor IDE

# Smart connection (auto-detects best method)
alias cursor='~/.ssh/smart_connect.sh'

# Specific connection methods
alias cursor-vpn='ssh cursor-vpn'      # When VPN is ON
alias cursor-local='ssh cursor-local'  # When VPN is OFF  
alias cursor-mdns='ssh cursor-mdns'    # Fallback mDNS

# Quick status check
alias cursor-status='~/.ssh/check_connections.sh'
EOF

echo "Created SSH aliases file: ~/.ssh/ssh_aliases.sh"
echo ""
echo "To use these aliases, add this line to your shell config:"
echo ""

# Detect shell and provide appropriate instructions
if [ -n "$FISH_VERSION" ]; then
    echo "For Fish shell, add to ~/.config/fish/config.fish:"
    echo "source ~/.ssh/ssh_aliases.sh"
elif [ -n "$ZSH_VERSION" ]; then
    echo "For Zsh, add to ~/.zshrc:"
    echo "source ~/.ssh/ssh_aliases.sh"
elif [ -n "$BASH_VERSION" ]; then
    echo "For Bash, add to ~/.bashrc:"
    echo "source ~/.ssh/ssh_aliases.sh"
else
    echo "Add to your shell config file:"
    echo "source ~/.ssh/ssh_aliases.sh"
fi

echo ""
echo "After adding the source line, restart your terminal or run:"
echo "source ~/.ssh/ssh_aliases.sh"
echo ""
echo "Then you can use these commands:"
echo "  cursor           # Smart auto-connect"
echo "  cursor-vpn       # Force VPN connection"
echo "  cursor-local     # Force local connection"
echo "  cursor-mdns      # Force mDNS connection"
echo "  cursor-status    # Check all connection methods"