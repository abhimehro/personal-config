#!/bin/bash
# Control D Baseline Tests (Separation Strategy aware)
# Quick wrapper around network-mode-verify for CONTROL D ACTIVE.

set -euo pipefail

VERIFY_SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/scripts/network-mode-verify.sh"

if [[ ! -x "$VERIFY_SCRIPT" ]]; then
  echo "network-mode-verify.sh not found or not executable at $VERIFY_SCRIPT" >&2
  exit 1
fi

echo "=== Control D Baseline Tests (Separation Strategy) ==="

echo "Running CONTROL D ACTIVE verification..."

if "$VERIFY_SCRIPT" controld; then
  echo "Result: ALL TESTS PASSED ✓"
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "SUMMARY TS=${ts} MODE=baseline-test RESULT=PASS"
  exit 0
else
  echo "Result: Baseline verification FAILED ✗"
  echo "See details above from network-mode-verify.sh."
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "SUMMARY TS=${ts} MODE=baseline-test RESULT=FAIL"
  exit 1
fi
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
