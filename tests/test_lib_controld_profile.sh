#!/bin/bash
#
# Unit tests for scripts/lib/controld-profile.sh
# Covers: validate_protocol, redact_profile_id, get_profile_id,
#         get_profile_protocol, get_all_profiles, source guard
# Mocks: ctrld (records invocations), networksetup

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-lib-controld-profile')
MOCK_BIN="$TEST_DIR/bin"
mkdir -p "$MOCK_BIN"
trap 'rm -rf "$TEST_DIR"' EXIT

# --- Mocks ---
# ctrld mock: records every invocation.
CTRLD_LOG="$TEST_DIR/ctrld.log"
cat > "$MOCK_BIN/ctrld" << MOCK
#!/bin/bash
echo "ctrld \$*" >> "$CTRLD_LOG"
exit 0
MOCK
chmod +x "$MOCK_BIN/ctrld"

# networksetup mock: returns a plausible DNS value.
cat > "$MOCK_BIN/networksetup" << 'MOCK'
#!/bin/bash
echo "1.1.1.1"
MOCK
chmod +x "$MOCK_BIN/networksetup"

export PATH="$MOCK_BIN:$PATH"
export HOME="$TEST_DIR/home"
mkdir -p "$HOME"

# Source network-common.sh first so validate_profile_id is available.
# shellcheck source=scripts/lib/network-common.sh
source "$REPO_ROOT/scripts/lib/network-common.sh"

# Source the library under test.
# shellcheck source=scripts/lib/controld-profile.sh
source "$REPO_ROOT/scripts/lib/controld-profile.sh"

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

echo "=== Testing scripts/lib/controld-profile.sh ==="

# --- validate_protocol ---
echo ""
echo "-- validate_protocol --"
check       "validate_protocol accepts doh"          validate_protocol "doh"
check       "validate_protocol accepts doh3"         validate_protocol "doh3"
check_false "validate_protocol rejects empty string" validate_protocol ""
check_false "validate_protocol rejects dot3"         validate_protocol "dot3"
check_false "validate_protocol rejects arbitrary"    validate_protocol "tcp"

# --- redact_profile_id (from controld-profile.sh) ---
echo ""
echo "-- redact_profile_id --"
REDACTED=$(redact_profile_id "abcde12345")
check_output "redact_profile_id shows first-3 and last-2 for long ID" "abc...45" "$REDACTED"

SHORT_REDACTED=$(redact_profile_id "abc")
check_output "redact_profile_id fully masks short ID (<=5 chars)" "***...**" "$SHORT_REDACTED"

EMPTY_REDACTED=$(redact_profile_id "")
check_output "redact_profile_id returns (empty) for empty input" "(empty)" "$EMPTY_REDACTED"

# --- get_profile_id ---
echo ""
echo "-- get_profile_id --"

# Default IDs from the library
PRIVACY_ID=$(get_profile_id "privacy")
check "get_profile_id returns non-empty ID for 'privacy'" test -n "$PRIVACY_ID"

GAMING_ID=$(get_profile_id "gaming")
check "get_profile_id returns non-empty ID for 'gaming'" test -n "$GAMING_ID"

BROWSING_ID=$(get_profile_id "browsing")
check "get_profile_id returns non-empty ID for 'browsing'" test -n "$BROWSING_ID"

UNKNOWN_ID=$(get_profile_id "unknown_profile")
check_output "get_profile_id returns empty for unknown profile" "" "$UNKNOWN_ID"

# Override via environment variable
CTR_PROFILE_PRIVACY_ID="test123abc" PRIVACY_OVERRIDE=$(get_profile_id "privacy")
check_output "get_profile_id uses CTR_PROFILE_PRIVACY_ID env override" "test123abc" "$PRIVACY_OVERRIDE"

# --- get_profile_protocol ---
echo ""
echo "-- get_profile_protocol --"
check_output "get_profile_protocol returns doh3 for gaming"   "doh3" "$(get_profile_protocol gaming)"
check_output "get_profile_protocol returns doh3 for privacy"  "doh3" "$(get_profile_protocol privacy)"
check_output "get_profile_protocol returns doh3 for browsing" "doh3" "$(get_profile_protocol browsing)"
check_output "get_profile_protocol returns doh3 as default"   "doh3" "$(get_profile_protocol unknown)"

# --- get_all_profiles ---
echo ""
echo "-- get_all_profiles --"
ALL_PROFILES=$(get_all_profiles)
check "get_all_profiles includes 'privacy'"  bash -c '[[ "'"$ALL_PROFILES"'" == *"privacy"* ]]'
check "get_all_profiles includes 'gaming'"   bash -c '[[ "'"$ALL_PROFILES"'" == *"gaming"* ]]'
check "get_all_profiles includes 'browsing'" bash -c '[[ "'"$ALL_PROFILES"'" == *"browsing"* ]]'

# --- Source guard ---
echo ""
echo "-- source guard --"
# shellcheck source=scripts/lib/controld-profile.sh
source "$REPO_ROOT/scripts/lib/controld-profile.sh"
check_output "source guard variable is set to 'true'" "true" "$_CONTROLD_PROFILE_SH_"

# --- Summary ---
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
