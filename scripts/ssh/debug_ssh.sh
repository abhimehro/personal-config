#!/bin/bash

echo "=== SSH Configuration Debug Script ==="
echo ""

echo "1. Checking 1Password SSH agent..."
export SSH_AUTH_SOCK=~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock
echo "SSH_AUTH_SOCK: $SSH_AUTH_SOCK"
echo ""

echo "2. Testing if 1Password SSH agent is running..."
if [ -S "$SSH_AUTH_SOCK" ]; then
    echo "✅ 1Password SSH agent socket exists"
else
    echo "❌ 1Password SSH agent socket not found"
fi
echo ""

echo "3. Listing available SSH keys from 1Password..."
ssh-add -l 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ 1Password SSH agent is working"
else
    echo "❌ 1Password SSH agent not responding - check if 1Password SSH agent is enabled"
fi
echo ""

echo "4. Testing SSH connection to cursor-local..."
ssh -o ConnectTimeout=5 -o BatchMode=yes cursor-local echo "Connection successful" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ SSH connection to cursor-local works"
else
    echo "❌ SSH connection to cursor-local failed"
fi
echo ""

echo "5. Checking SSH config syntax..."
ssh -G cursor-local > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ SSH config syntax is valid"
else
    echo "❌ SSH config has syntax errors"
fi
echo ""

echo "6. Checking 1Password config file..."
if [ -f ~/.ssh/1Password/config ] && [ -s ~/.ssh/1Password/config ]; then
    echo "✅ 1Password config file exists and has content"
    echo "Content:"
    cat ~/.ssh/1Password/config | grep -v "^#" | grep -v "^$"
else
    echo "❌ 1Password config file is empty or missing"
fi
echo ""

echo "7. Checking if SSH keys are in 1Password..."
ls -la ~/.ssh/1Password/*.pub 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Found SSH public keys in 1Password directory"
else
    echo "❌ No SSH public keys found in 1Password directory"
    echo "This means 1Password hasn't generated SSH keys yet"
fi
echo ""

echo "=== Recommendations ==="
echo "If you see issues above:"
echo "1. Open 1Password app → Settings → Developer → SSH Agent → Enable"
echo "2. Make sure you have SSH keys stored in your 1Password vault"
echo "3. Restart 1Password and try again"
echo "4. If still not working, try: killall ssh-agent && eval \$(ssh-agent)"