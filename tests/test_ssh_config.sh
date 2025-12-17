#!/usr/bin/env bash
# SSH Configuration Test Script
# Validates repo-managed SSH config and helper scripts.

set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🧪 Testing SSH Configuration..."
echo ""

TESTS_PASSED=0
TESTS_TOTAL=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -n "Testing $test_name... "
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo "✅"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo "❌"
        return 1
    fi
}

# Test SSH config syntax
run_test "SSH config syntax" "ssh -F \"$REPO_ROOT/configs/ssh/config\" -G cursor-mdns"

# Test SSH config file exists
run_test "SSH config file exists" "[ -f \"$REPO_ROOT/configs/ssh/config\" ]"

# Test 1Password agent config exists
run_test "1Password agent config exists" "[ -f \"$REPO_ROOT/configs/ssh/agent.toml\" ]"

# Test repo helper scripts exist and are executable
run_test "smart_connect.sh exists" "[ -x \"$REPO_ROOT/scripts/ssh/smart_connect.sh\" ]"
run_test "check_connections.sh exists" "[ -x \"$REPO_ROOT/scripts/ssh/check_connections.sh\" ]"
run_test "setup_verification.sh exists" "[ -x \"$REPO_ROOT/scripts/ssh/setup_verification.sh\" ]"
run_test "diagnose_vpn.sh exists" "[ -x \"$REPO_ROOT/scripts/ssh/diagnose_vpn.sh\" ]"
run_test "setup_aliases.sh exists" "[ -x \"$REPO_ROOT/scripts/ssh/setup_aliases.sh\" ]"

# Test 1Password SSH agent socket
run_test "1Password SSH agent socket exists" "[ -S ~/Library/Group\\ Containers/2BUA8C4S2C.com.1password/t/agent.sock ]"

# Test 1Password SSH agent responds
run_test "1Password SSH agent responds" "SSH_AUTH_SOCK=~/Library/Group\\ Containers/2BUA8C4S2C.com.1password/t/agent.sock ssh-add -l"

# Test SSH host configurations
run_test "cursor-mdns config valid" "ssh -F \"$REPO_ROOT/configs/ssh/config\" -G cursor-mdns | grep -qi 'hostname .*\\.local'"
run_test "cursor-local config valid" "ssh -F \"$REPO_ROOT/configs/ssh/config\" -G cursor-local | grep -qi 'hostname'"
run_test "cursor-auto config valid" "ssh -F \"$REPO_ROOT/configs/ssh/config\" -G cursor-auto | grep -qi 'hostname .*\\.local'"

echo ""
echo "📊 Test Results: $TESTS_PASSED/$TESTS_TOTAL tests passed"

if [ $TESTS_PASSED -eq $TESTS_TOTAL ]; then
    echo "🎉 All tests passed! SSH configuration is ready."
    exit 0
elif [ $TESTS_PASSED -gt $((TESTS_TOTAL * 3 / 4)) ]; then
    echo "⚠️  Most tests passed. Minor issues may need attention."
    exit 1
else
    echo "❌ Multiple tests failed. Configuration needs fixing."
    echo ""
    echo "🔧 Troubleshooting steps:"
    echo "1. Run the installation script: ./scripts/install_ssh_config.sh"
    echo "2. Enable 1Password SSH agent: 1Password → Settings → Developer → SSH Agent"
    echo "3. Run setup verification: ~/.ssh/setup_verification.sh"
    exit 2
fi