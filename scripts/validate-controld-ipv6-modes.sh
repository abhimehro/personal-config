#!/usr/bin/env bash
#
# Live validation checklist for Control D reliability + IPv6 profile modes.
# Run manually (requires sudo + network). Does NOT uninstall Control D.
#
# USAGE: ./scripts/validate-controld-ipv6-modes.sh [profile]
#
set -euo pipefail

PROFILE="${1:-privacy}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; FAILURES=$((FAILURES + 1)); }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
info() { echo -e "${BLUE}[INFO]${NC} $*"; }

FAILURES=0

info "=== Unit tests (no network) ==="
bash tests/test_network_mode_manager_pure.sh || fail "test_network_mode_manager_pure.sh"
bash tests/test_lib_controld_service.sh || fail "test_lib_controld_service.sh"
bash tests/test_lib_controld_profile.sh || fail "test_lib_controld_profile.sh"

info "=== Mode 1: doh3-ipv6 (standalone Control D) ==="
./scripts/network-mode-manager.sh controld "$PROFILE" || fail "switch controld doh3"
./scripts/network-mode-verify.sh controld "$PROFILE" || fail "verify controld doh3"
MODE=$(sudo awk -F= '$1=="PROFILE_MODE"{print $2;exit}' /etc/controld/active_profile 2>/dev/null || echo "")
[[ $MODE == "doh3-ipv6" ]] && pass "PROFILE_MODE=doh3-ipv6" || fail "expected doh3-ipv6 got '$MODE'"

info "=== Mode 2: doh-ipv4 (DoH + IPv6 off) ==="
./scripts/network-mode-manager.sh controld "$PROFILE" doh || fail "switch controld doh"
MODE=$(sudo awk -F= '$1=="PROFILE_MODE"{print $2;exit}' /etc/controld/active_profile 2>/dev/null || echo "")
[[ $MODE == "doh-ipv4" ]] && pass "PROFILE_MODE=doh-ipv4" || fail "expected doh-ipv4 got '$MODE'"
IPV6=$(networksetup -getinfo Wi-Fi | grep IPv6: || true)
echo "$IPV6" | grep -q Off && pass "IPv6 Off for doh-ipv4" || fail "IPv6 not Off: $IPV6"

info "=== Mode 3: doh-ipv6 (DoH + IPv6 on, no VPN) ==="
CONTROLD_IPV6=enable ./scripts/network-mode-manager.sh controld "$PROFILE" doh || fail "switch doh-ipv6"
MODE=$(sudo awk -F= '$1=="PROFILE_MODE"{print $2;exit}' /etc/controld/active_profile 2>/dev/null || echo "")
[[ $MODE == "doh-ipv6" ]] && pass "PROFILE_MODE=doh-ipv6" || fail "expected doh-ipv6 got '$MODE'"
IPV6=$(networksetup -getinfo Wi-Fi | grep IPv6: || true)
echo "$IPV6" | grep -q Automatic && pass "IPv6 Automatic for doh-ipv6" || warn "IPv6 not Automatic yet: $IPV6"

info "=== Reliability: rapid profile switches (no false API fallback) ==="
for p in privacy browsing gaming privacy; do
	./scripts/network-mode-manager.sh controld "$p" || fail "rapid switch $p"
done
if sudo test -f /etc/controld/active_profile && sudo grep -q 'FALLBACK=1' /etc/controld/active_profile 2>/dev/null; then
	warn "Fallback flag set after rapid switches — check API health"
else
	pass "No FALLBACK=1 after rapid switches"
fi
dig @127.0.0.1 google.com +short +time=3 >/dev/null && pass "DNS resolves after rapid switches" || fail "DNS broken after rapid switches"

info "=== Combined Windscribe path (optional; skips if CLI missing) ==="
WS=""
if command -v windscribe-cli >/dev/null 2>&1; then
	WS=windscribe-cli
elif [[ -x /Applications/Windscribe.app/Contents/MacOS/windscribe-cli ]]; then
	WS=/Applications/Windscribe.app/Contents/MacOS/windscribe-cli
fi
if [[ -n $WS ]]; then
	info "Forcing doh-ipv4 combined mode (WINDSCRIBE_IPV6=0)..."
	WINDSCRIBE_IPV6=0 ./scripts/network-mode-manager.sh windscribe "$PROFILE" || fail "windscribe doh-ipv4"
	MODE=$(sudo awk -F= '$1=="PROFILE_MODE"{print $2;exit}' /etc/controld/active_profile 2>/dev/null || echo "")
	[[ $MODE == "doh-ipv4" ]] && pass "combined forced doh-ipv4" || fail "expected doh-ipv4 got '$MODE'"

	info "Forcing doh-ipv6 combined mode (WINDSCRIBE_IPV6=1)..."
	WINDSCRIBE_IPV6=1 ./scripts/network-mode-manager.sh windscribe "$PROFILE" || fail "windscribe doh-ipv6"
	MODE=$(sudo awk -F= '$1=="PROFILE_MODE"{print $2;exit}' /etc/controld/active_profile 2>/dev/null || echo "")
	[[ $MODE == "doh-ipv6" ]] && pass "combined forced doh-ipv6" || fail "expected doh-ipv6 got '$MODE'"

	info "Restore standalone Control D..."
	./scripts/network-mode-manager.sh controld "$PROFILE" || fail "restore controld"
else
	warn "Windscribe CLI not found; skipped combined-mode live checks"
fi

echo
if [[ $FAILURES -eq 0 ]]; then
	pass "ALL VALIDATIONS PASSED"
	exit 0
fi
fail "$FAILURES check(s) failed"
exit 1
