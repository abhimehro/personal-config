#!/bin/bash
#
# Unit tests for scripts/lib/network-utils.sh
# Tests function availability and basic behaviour using mocks

set -euo pipefail

# Setup
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-network-utils')
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
trap 'rm -rf "$TEST_DIR"' EXIT

# --- Mocks ---
cat > "$MOCK_BIN/networksetup" << 'EOF'
#!/bin/bash
case "$1" in
    -listallnetworkservices)
        printf 'An asterisk (*) denotes that a network service is disabled.\nWi-Fi\nEthernet\nBluetooth PAN\n'
        ;;
    -listallhardwareports)
        printf 'Hardware Port: Wi-Fi\nDevice: en0\nEthernet Address: aa:bb:cc:dd:ee:ff\n\n'
        ;;
    -getairportnetwork)
        printf 'Current Wi-Fi Network: TestSSID\n'
        ;;
    *)
        echo "MOCK networksetup: $*"
        ;;
esac
EOF
chmod +x "$MOCK_BIN/networksetup"

cat > "$MOCK_BIN/route" << 'EOF'
#!/bin/bash
if [[ "$*" == "get default" ]]; then
    printf '   route to: default\ndestination: default\n     gateway: 192.168.1.1\n   interface: en0\n'
fi
EOF
chmod +x "$MOCK_BIN/route"

export PATH="$MOCK_BIN:$PATH"

# Source the library (network-core.sh is sourced internally)
# shellcheck source=scripts/lib/network-utils.sh
source "$REPO_ROOT/scripts/lib/network-utils.sh"

PASS=0
FAIL=0

check() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

check_false() {
    local name="$1"; shift
    if ! "$@" >/dev/null 2>&1; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

check_output() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (expected '$expected', got '$actual')"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Testing scripts/lib/network-utils.sh ==="

# --- get_active_interface ---
echo ""
echo "-- get_active_interface --"
IFACE=$(get_active_interface)
check_output "get_active_interface returns en0" "en0" "$IFACE"

# --- list_network_services ---
echo ""
echo "-- list_network_services --"
SERVICES=$(list_network_services)
check "list_network_services returns non-empty output" test -n "$SERVICES"
# Should NOT include the header line
check_false "list_network_services strips header" bash -c '[[ "'"$SERVICES"'" == *"asterisk"* ]]'
check "list_network_services includes Wi-Fi entry" bash -c 'echo "'"$SERVICES"'" | grep -q "Wi-Fi"'

# --- get_wifi_interface ---
echo ""
echo "-- get_wifi_interface --"
WIFI_IF=$(get_wifi_interface)
check_output "get_wifi_interface returns en0" "en0" "$WIFI_IF"

# --- get_wifi_ssid ---
echo ""
echo "-- get_wifi_ssid --"
SSID=$(get_wifi_ssid)
check_output "get_wifi_ssid returns TestSSID" "TestSSID" "$SSID"

# --- is_wifi_connected ---
echo ""
echo "-- is_wifi_connected --"
check "is_wifi_connected returns true when SSID is set" is_wifi_connected

# --- Source guard ---
echo ""
echo "-- source guard --"
# Re-sourcing should be a no-op (guard prevents re-execution)
OLD_PASS=$PASS
source "$REPO_ROOT/scripts/lib/network-utils.sh"
check "source guard prevents duplicate initialisation" test "$_NETWORK_UTILS_SH_" = "true"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
