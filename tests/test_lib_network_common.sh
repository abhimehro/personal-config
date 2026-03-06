#!/bin/bash
#
# Unit tests for scripts/lib/network-common.sh
# Covers: validate_dns_protocol, validate_profile_id, redact_profile_id,
#         backup_dns_settings, restore_dns_settings, source guard
# Mocks: networksetup

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-lib-network-common')
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
trap 'rm -rf "$TEST_DIR"' EXIT

# --- Mocks ---
# networksetup mock: simulates -getdnsservers and -setdnsservers.
NS_LOG="$TEST_DIR/networksetup.log"
cat > "$MOCK_BIN/networksetup" << MOCK
#!/bin/bash
echo "networksetup \$*" >> "$NS_LOG"
case "\$1" in
    -getdnsservers) echo "8.8.8.8" ;;
    -setdnsservers) exit 0 ;;
    *) echo "MOCK networksetup: \$*" ;;
esac
MOCK
chmod +x "$MOCK_BIN/networksetup"

export PATH="$MOCK_BIN:$PATH"
export HOME="$TEST_DIR/home"
mkdir -p "$HOME"

# Source the library under test.
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

check_grep() {
    local name="$1"
    local pattern="$2"
    local file="$3"
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (pattern '$pattern' not found in $file)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Testing scripts/lib/network-common.sh ==="

# --- validate_dns_protocol ---
echo ""
echo "-- validate_dns_protocol --"
check       "validate_dns_protocol accepts doh"          validate_dns_protocol "doh"
check       "validate_dns_protocol accepts doh3"         validate_dns_protocol "doh3"
check_false "validate_dns_protocol rejects empty"        validate_dns_protocol ""
check_false "validate_dns_protocol rejects dot3"         validate_dns_protocol "dot3"
check_false "validate_dns_protocol rejects arbitrary"    validate_dns_protocol "udp"

# --- validate_profile_id ---
echo ""
echo "-- validate_profile_id --"
check       "validate_profile_id accepts lowercase-alphanumeric ID" validate_profile_id "abc123xyz0"
check       "validate_profile_id accepts single-char ID"            validate_profile_id "a"
check_false "validate_profile_id rejects empty string"              validate_profile_id ""
check_false "validate_profile_id rejects ID with uppercase"         validate_profile_id "ABC123"
check_false "validate_profile_id rejects ID with hyphen"            validate_profile_id "abc-123"
check_false "validate_profile_id rejects ID with space"             validate_profile_id "abc 123"

# --- redact_profile_id ---
echo ""
echo "-- redact_profile_id --"
REDACTED=$(redact_profile_id "abcde12345")
check_output "redact_profile_id shows first-3 and last-2 for long ID" "abc...45" "$REDACTED"

SHORT_REDACTED=$(redact_profile_id "abc")
check_output "redact_profile_id fully masks short ID (<=5 chars)" "***...**" "$SHORT_REDACTED"

EMPTY_REDACTED=$(redact_profile_id "")
check_output "redact_profile_id returns (empty) for empty input" "(empty)" "$EMPTY_REDACTED"

# Exactly 5 chars should also be masked completely
FIVE_REDACTED=$(redact_profile_id "abcde")
check_output "redact_profile_id fully masks exactly 5-char ID" "***...**" "$FIVE_REDACTED"

# --- backup_dns_settings ---
echo ""
echo "-- backup_dns_settings --"
BACKUP_DIR="$TEST_DIR/dns_backup"
mkdir -p "$BACKUP_DIR"

backup_dns_settings "$BACKUP_DIR"

check "backup_dns_settings creates original_dns.txt" test -f "$BACKUP_DIR/original_dns.txt"
check "original_dns.txt is non-empty" test -s "$BACKUP_DIR/original_dns.txt"
check_grep "networksetup -getdnsservers was invoked" "getdnsservers" "$NS_LOG"

# --- restore_dns_settings ---
echo ""
echo "-- restore_dns_settings (from backup file) --"
NS_LOG2="$TEST_DIR/networksetup2.log"
cat > "$MOCK_BIN/networksetup" << MOCK2
#!/bin/bash
echo "networksetup \$*" >> "$NS_LOG2"
case "\$1" in
    -setdnsservers) exit 0 ;;
    *) exit 0 ;;
esac
MOCK2
chmod +x "$MOCK_BIN/networksetup"

# Backup contains a real DNS address
RESTORE_DIR="$TEST_DIR/dns_restore"
mkdir -p "$RESTORE_DIR"
echo "1.1.1.1" > "$RESTORE_DIR/original_dns.txt"

restore_dns_settings "$RESTORE_DIR"
check_grep "restore invokes networksetup -setdnsservers" "setdnsservers" "$NS_LOG2"

# --- restore_dns_settings (no backup file) ---
echo ""
echo "-- restore_dns_settings (no backup file – fallback) --"
NS_LOG3="$TEST_DIR/networksetup3.log"
cat > "$MOCK_BIN/networksetup" << MOCK3
#!/bin/bash
echo "networksetup \$*" >> "$NS_LOG3"
exit 0
MOCK3
chmod +x "$MOCK_BIN/networksetup"

NOBACKUP_DIR="$TEST_DIR/dns_nobackup"
mkdir -p "$NOBACKUP_DIR"
# No original_dns.txt created — simulate missing backup.

restore_dns_settings "$NOBACKUP_DIR"
check_grep "restore falls back to public DNS when no backup" "setdnsservers" "$NS_LOG3"

# --- Source guard ---
echo ""
echo "-- source guard --"
# shellcheck source=scripts/lib/network-common.sh
source "$REPO_ROOT/scripts/lib/network-common.sh"
check_output "source guard variable is set to 'true'" "true" "$_NETWORK_COMMON_SH_"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
