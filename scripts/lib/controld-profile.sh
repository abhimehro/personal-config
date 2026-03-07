#!/bin/bash
#
# Control D Profile Management Library
# Functions for profile setup, validation, and config generation.
#
# Usage: source "scripts/lib/controld-profile.sh"

# Source Guard
if [[ "${_CONTROLD_PROFILE_SH_:-}" == "true" ]]; then
    return
fi
_CONTROLD_PROFILE_SH_="true"

# Validate DNS protocol.
validate_protocol() {
    local proto="$1"
    case "$proto" in
        doh|doh3) return 0 ;;
        *) return 1 ;;
    esac
}

# Redact profile ID for safe logging.
redact_profile_id() {
    local profile_id="$1"
    if [[ -z "$profile_id" ]]; then
        echo "(empty)"
        return
    fi
    local len=${#profile_id}
    if [[ $len -le 5 ]]; then
        # For short IDs (5 chars or less), mask completely
        echo "***...**"
    else
        echo "${profile_id:0:3}...${profile_id: -2}"
    fi
}

# Resolve profile name to profile ID.
get_profile_id() {
    local profile_name="$1"
    local profile_id=""

    case "$profile_name" in
        "privacy") profile_id="${CTR_PROFILE_PRIVACY_ID:-${CTRLD_PRIVACY_PROFILE:-6m971e9jaf}}" ;;
        "gaming") profile_id="${CTR_PROFILE_GAMING_ID:-${CTRLD_GAMING_PROFILE:-1xfy57w34t7}}" ;;
        "browsing") profile_id="${CTR_PROFILE_BROWSING_ID:-${CTRLD_BROWSING_PROFILE:-rcnz7qgvwg}}" ;;
        *) echo ""; return 0 ;;
    esac

    # Validate the resolved profile ID
    if [[ -n "$profile_id" ]]; then
        # Use validate_profile_id from network-common.sh (assumes it's loaded)
        if command -v validate_profile_id >/dev/null 2>&1; then
            if ! validate_profile_id "$profile_id"; then
                echo ""
                return 0
            fi
        fi
    fi

    echo "$profile_id"
    return 0
}

# Get the preferred protocol for a profile name.
get_profile_protocol() {
    case "$1" in
        "gaming") echo "doh3" ;;
        "privacy") echo "doh3" ;;
        "browsing") echo "doh3" ;;
        *) echo "doh3" ;;
    esac
}

# Get list of all supported profiles.
get_all_profiles() {
    echo "privacy gaming browsing"
}

# Generate configuration for a profile.
# Usage: generate_profile_config <profile_name> <profile_id> <protocol> <profiles_dir>
generate_profile_config() {
    local profile_name="$1"
    local profile_id="$2"
    local protocol="$3"
    local profiles_dir="$4"
    local config_file="$profiles_dir/ctrld.$profile_name.toml"

    # Input Validation
    if command -v validate_profile_id >/dev/null 2>&1; then
        if ! validate_profile_id "$profile_id"; then
            return 1
        fi
    fi

    # Ensure destination directory exists
    mkdir -p "$profiles_dir"

    # Use local variable and ensure cleanup
    local TEMP_CONFIG
    TEMP_CONFIG=$(mktemp "${TMPDIR:-/tmp}/ctrld_temp.toml.XXXXXX")

    # NOTE: trap ... RETURN is process-global; save and restore any existing handler.
    local previous_return_trap
    previous_return_trap=$(trap -p RETURN 2>/dev/null || true)
    trap '
        rm -f "${TEMP_CONFIG:-}"
        # Remove this temporary RETURN trap so it does not affect other functions.
        trap - RETURN
        # Restore any previously configured RETURN trap, if one existed.
        if [[ -n ${previous_return_trap:-} ]]; then
            eval "${previous_return_trap}"
        fi
    ' RETURN
    local ctrld_pid
    if [[ "$protocol" == "doh3" ]]; then
        ctrld run --cd "$profile_id" --proto doh3 --config="$TEMP_CONFIG" --skip_self_checks >/dev/null 2>&1 &
        ctrld_pid=$!
    else
        ctrld run --cd "$profile_id" --config="$TEMP_CONFIG" --skip_self_checks >/dev/null 2>&1 &
        ctrld_pid=$!
    fi

    # Wait for config file to be created (optimized)
    local max_retries=50
    local count=0
    while [[ ! -f "$TEMP_CONFIG" ]] && [[ $count -lt $max_retries ]]; do
        # If process died prematurely, stop waiting
        if ! kill -0 "$ctrld_pid" 2>/dev/null; then
            break
        fi
        sleep 0.1
        count=$((count + 1))
    done

    # Ensure file has content
    if [[ -f "$TEMP_CONFIG" ]]; then
        sleep 0.1
    fi

    # Cleanup background process
    kill "$ctrld_pid" 2>/dev/null || true
    wait "$ctrld_pid" 2>/dev/null || true

    if [[ -f "$TEMP_CONFIG" ]]; then
        # Atomic copy+permission setting
        install -m 600 "$TEMP_CONFIG" "$config_file"
        rm -f "$TEMP_CONFIG"

        # Hardening against Open Resolver
        sed -i '' -e "s/ip = ['\"]0.0.0.0['\"]/ip = \"127.0.0.1\"/g" \
                  -e "s/ip = ['\"]::['\"]/ip = \"127.0.0.1\"/g" \
                  -e 's/, "::\/0"//g' \
                  -e 's/"::\/0", //g' \
                  -e "s/timeout = 5000/timeout = 3000/g" \
                  "$config_file" 2>/dev/null || true

        # Verification
        if grep -qE "ip = ['\"]?0\.0\.0\.0['\"]?|ip = ['\"]?::['\"]?" "$config_file"; then
             rm -f "$config_file"
             return 1
        fi
        return 0
    else
        rm -f "$TEMP_CONFIG"
        return 1
    fi
}

# Test connection specific to a profile (checks filtering rules).
# Usage: test_profile_connection <profile_name> [resolver_ip]
test_profile_connection() {
    local profile_name="$1"
    local resolver="${2:-127.0.0.1}"

    # Check basic resolution
    if command -v test_dns_resolution >/dev/null 2>&1; then
        test_dns_resolution "$resolver" "google.com" || return 1
        test_dns_resolution "$resolver" "p.controld.com" || return 1
    else
        dig @"$resolver" google.com +short +time=5 >/dev/null 2>&1 || return 1
        dig @"$resolver" p.controld.com +short +time=5 >/dev/null 2>&1 || return 1
    fi

    # Test profile filtering rules
    local block_test
    block_test=$(dig @"$resolver" doubleclick.net +short 2>/dev/null | wc -l)

    if [[ "$block_test" -eq 0 ]]; then
        # Ads blocked, working for privacy/browsing
        return 0
    elif [[ "$block_test" -gt 0 ]]; then
        if [[ "$profile_name" == "gaming" ]]; then
            # Gaming profile allows ads for compatibility
            return 0
        else
            # Warning: Ads not blocked for privacy profile
            return 2 # special exit code for "working but not blocking"
        fi
    fi

    return 0
}

# Self-execution guard for testing
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Return 0 when executed directly
    return 0 2>/dev/null
fi
