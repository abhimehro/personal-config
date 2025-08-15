#!/bin/bash
# 1Password SSH Setup Verification Script

echo "🔧 Setting up 1Password SSH integration..."
echo ""

# Make sure the control directory exists
echo "1. Creating SSH control directory..."
mkdir -p ~/.ssh/control
chmod 700 ~/.ssh/control
echo "✅ SSH control directory ready"
echo ""

# Check 1Password SSH agent
echo "2. Testing 1Password SSH agent..."
export SSH_AUTH_SOCK=~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock

if [ -S "$SSH_AUTH_SOCK" ]; then
    echo "✅ 1Password SSH agent socket found"
    
    # Test if agent responds
    if ssh-add -l >/dev/null 2>&1; then
        echo "✅ 1Password SSH agent is responding"
        echo "Available keys:"
        ssh-add -l
    else
        echo "⚠️  1Password SSH agent not responding"
        echo "   → Open 1Password → Settings → Developer → SSH Agent → Enable"
    fi
else
    echo "❌ 1Password SSH agent socket not found"
    echo "   → Make sure 1Password SSH agent is enabled"
fi
echo ""

# Test SSH config syntax
echo "3. Validating SSH configuration..."
if ssh -G cursor-local >/dev/null 2>&1; then
    echo "✅ SSH configuration is valid"
else
    echo "❌ SSH configuration has errors"
fi
echo ""

# Test connection to cursor-local
echo "4. Testing connection to cursor-local..."
echo "   (This may prompt for 1Password authentication)"
if timeout 10 ssh -o ConnectTimeout=5 -o BatchMode=yes cursor-local echo "Hello from cursor-local" 2>/dev/null; then
    echo "✅ SSH connection to cursor-local successful!"
else
    echo "⚠️  SSH connection to cursor-local failed"
    echo "   → Make sure the host is reachable and keys are correct"
fi
echo ""

echo "🎉 Setup verification complete!"
echo ""
echo "To use with Cursor IDE:"
echo "1. Open Cursor"
echo "2. Use Remote-SSH extension"
echo "3. Connect to 'cursor-local'"
echo ""
echo "For iTerm/terminal usage:"
echo "ssh cursor-local"