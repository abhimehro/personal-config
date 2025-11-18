#!/bin/bash

# Control D Baseline Tests
# Quick validation suite for post-change verification

echo "=== Control D Baseline Tests ==="
echo ""

failed=0

# Test 1: Service running
echo -n "1. Service status... "
if sudo ctrld service status &>/dev/null; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

# Test 2: DNS resolution
echo -n "2. DNS resolution... "
if dig @127.0.0.1 example.com +short +timeout=5 | grep -q "^[0-9]"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

# Test 3: DoH encryption active
echo -n "3. DoH encryption... "
if sudo tail -10 /var/log/ctrld.log | grep -q "REPLY.*upstream"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

# Test 4: Firewall exception
echo -n "4. Firewall exception... "
if sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep -q ctrld; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

# Test 5: Launch daemon loaded
echo -n "5. Launch daemon... "
if sudo launchctl list | grep -q ctrld; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

# Test 6: Config file valid
echo -n "6. Config file syntax... "
if [ -f ~/.config/controld/ctrld.toml ] && grep -q "\[upstream\.0\]" ~/.config/controld/ctrld.toml; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
    failed=$((failed + 1))
fi

echo ""
if [ $failed -eq 0 ]; then
    echo "Result: ALL TESTS PASSED ✓"
    exit 0
else
    echo "Result: $failed test(s) FAILED ✗"
    echo "Run full health check: ~/.config/controld/health-check.sh"
    exit 1
fi
