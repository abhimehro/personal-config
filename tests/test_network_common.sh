#!/bin/bash
#
# Unit tests for scripts/lib/network-common.sh
# Tests validate_dns_protocol, validate_profile_id, redact_profile_id,
# backup_dns_settings, restore_dns_settings, and the source guard.

set -euo pipefail

# Setup
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-network-common')
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
trap 'rm -rf "$TEST_DIR"' EXIT

# --- Mocks ---
# Record calls to networksetup so we can assert on them in tests
NETWORKSETUP_CALLS="$TEST_DIR/networksetup.calls"

cat > "$MOCK_BIN/networksetup" << 'EOF'
#!/bin/bash
printf '%s\n' "$*" >> "$NETWORKSETUP_CALLS_FILE"
case "$1" in
    -getdnsservers)
        echo "192.168.1.1"
        ;;
    -setdnsservers)
        ;;
    *)
        echo "MOCK networksetup: $*"
        ;;
esac
EOF
chmod +x "$MOCK_BIN/networksetup"
export NETWORKSETUP_CALLS_FILE="$NETWORKSETUP_CALLS"
export PATH="$MOCK_BIN:$PATH"

# Source the library under test
# shellcheck source=scripts/lib/network-common.sh
source "$REPO_ROOT/scripts/lib/network-common.sh"

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
        echo "FAIL: $name (expected='$expected', got='$actual')"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Testing scripts/lib/network-common.sh ==="

# --- validate_dns_protocol ---
echo ""
echo "-- validate_dns_protocol --"
check "accepts 'doh'"  validate_dns_protocol "doh"
check "accepts 'doh3'" validate_dns_protocol "doh3"
check_false "rejects empty string"   validate_dns_protocol ""
check_false "rejects 'https'"        validate_dns_protocol "https"
check_false "rejects 'DOH3'"         validate_dns_protocol "DOH3"
check_false "rejects 'doh '"         validate_dns_protocol "doh "

# --- validate_profile_id ---
echo ""
echo "-- validate_profile_id --"
check       "accepts lowercase alphanumeric"   validate_profile_id "abc123"
check       "accepts 10-char id"               validate_profile_id "a1b2c3d4e5"
check_false "rejects empty string"             validate_profile_id ""
check_false "rejects uppercase letters"        validate_profile_id "ABC123"
check_false "rejects whitespace"               validate_profile_id "abc 123"
check_false "rejects special characters"       validate_profile_id "abc-123"
check_false "rejects id with newline"          validate_profile_id $'abc\n123'

# --- redact_profile_id ---
echo ""
echo "-- redact_profile_id --"
check_output "redacts long id (shows 3+2)"  "abc...56"    "$(redact_profile_id "abcde56")"
check_output "redacts short id (<= 5)"      "***...**"    "$(redact_profile_id "abc12")"
check_output "redacts empty id"             "(empty)"     "$(redact_profile_id "")"
# Exactly 6 chars: shows first 3 + last 2
check_output "redacts 6-char id"            "abc...45"    "$(redact_profile_id "abc345")"

# --- backup_dns_settings ---
echo ""
echo "-- backup_dns_settings --"
BACKUP_DIR="$TEST_DIR/backup"
mkdir -p "$BACKUP_DIR"
: > "$NETWORKSETUP_CALLS"
backup_dns_settings "$BACKUP_DIR"
check "backup creates original_dns.txt" test -f "$BACKUP_DIR/original_dns.txt"
check "backup file is non-empty"        test -s "$BACKUP_DIR/original_dns.txt"
check "networksetup -getdnsservers was called" \
    grep -q "\-getdnsservers" "$NETWORKSETUP_CALLS"

# --- restore_dns_settings: from backup file ---
echo ""
echo "-- restore_dns_settings (from backup) --"
: > "$NETWORKSETUP_CALLS"
restore_dns_settings "$BACKUP_DIR"
check "networksetup -setdnsservers was called" \
    grep -q "\-setdnsservers" "$NETWORKSETUP_CALLS"

# --- restore_dns_settings: missing backup (fallback to public DNS) ---
echo ""
echo "-- restore_dns_settings (no backup → public fallback) --"
EMPTY_BACKUP="$TEST_DIR/empty_backup"
mkdir -p "$EMPTY_BACKUP"
: > "$NETWORKSETUP_CALLS"
restore_dns_settings "$EMPTY_BACKUP"
check "networksetup -setdnsservers called with public fallback" \
    grep -q "1.1.1.1" "$NETWORKSETUP_CALLS"

# --- restore_dns_settings: DHCP (empty) backup ---
echo ""
echo "-- restore_dns_settings (DHCP backup → Empty) --"
DHCP_BACKUP="$TEST_DIR/dhcp_backup"
mkdir -p "$DHCP_BACKUP"
echo "No DNS servers" > "$DHCP_BACKUP/original_dns.txt"
: > "$NETWORKSETUP_CALLS"
restore_dns_settings "$DHCP_BACKUP"
check "restore DHCP uses Empty keyword" \
    grep -q "Empty" "$NETWORKSETUP_CALLS"

# --- Source guard ---
echo ""
echo "-- source guard --"
source "$REPO_ROOT/scripts/lib/network-common.sh"
check "source guard is set" test "$_NETWORK_COMMON_SH_" = "true"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
