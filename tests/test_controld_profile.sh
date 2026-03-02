#!/bin/bash
# Tests for controld-profile.sh

set -eo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_ROOT/scripts/lib/controld-profile.sh"

test_failed=0


test_validate_protocol() {
    if ! validate_protocol "doh"; then echo "Fail: doh should be valid"; return 1; fi
    if ! validate_protocol "doh3"; then echo "Fail: doh3 should be valid"; return 1; fi
    if validate_protocol "dot"; then echo "Fail: dot should be invalid"; return 1; fi
    return 0
}

test_redact_profile_id() {
    local res
    res=$(redact_profile_id "abc")
    if [[ "$res" != "***...**" ]]; then echo "Fail: abc should be fully redacted"; return 1; fi

    res=$(redact_profile_id "1234567890")
    if [[ "$res" != "123...90" ]]; then echo "Fail: 1234567890 should be partially redacted, got $res"; return 1; fi

    return 0
}

test_get_profile_id() {
    local id

    export CTR_PROFILE_GAMING_ID="test_game_123"
    id=$(get_profile_id "gaming")
    if [[ "$id" != "test_game_123" ]]; then echo "Fail: gaming should return test_game_123, got $id"; return 1; fi

    id=$(get_profile_id "unknown_profile")
    if [[ -n "$id" ]]; then echo "Fail: unknown_profile should return empty, got $id"; return 1; fi

    return 0
}

if ! test_validate_protocol; then echo "test_validate_protocol failed"; test_failed=1; fi
if ! test_redact_profile_id; then echo "test_redact_profile_id failed"; test_failed=1; fi
if ! test_get_profile_id; then echo "test_get_profile_id failed"; test_failed=1; fi

if [[ $test_failed -eq 0 ]]; then
    echo "test_controld_profile.sh passed!"
    true
else
    false
fi
