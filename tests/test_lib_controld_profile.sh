#!/bin/bash
#
# NOTE: This file previously contained unit tests for scripts/lib/controld-profile.sh.
# The tests have been consolidated into tests/test_controld_profile.sh to avoid
# duplication and redundant execution. This script is retained as a no-op shim
# for backwards compatibility with any tooling that still references it.

set -euo pipefail

# Intentionally do nothing; all relevant tests live in tests/test_controld_profile.sh.
exit 0
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
