#!/bin/bash
#
# Network Common Library
# Shared helpers for DNS protocol validation, profile ID handling,
# and Wi-Fi DNS state backup/restore.
#
# Usage: source "scripts/lib/network-common.sh"

# Source Guard
if [[ "${_NETWORK_COMMON_SH_:-}" == "true" ]]; then
    return
fi
_NETWORK_COMMON_SH_="true"

# Source supporting libraries when available (not present in standalone installs)
_NETWORK_COMMON_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for _nclib in \
    "$_NETWORK_COMMON_LIB_DIR/common.sh" \
    "$_NETWORK_COMMON_LIB_DIR/network-core.sh"; do
    if [[ -f "$_nclib" ]]; then
        # shellcheck source=/dev/null
        source "$_nclib"
    fi
done
unset _nclib _NETWORK_COMMON_LIB_DIR

# --- Protocol Validation ---

# Return 0 if <proto> is a recognised DNS-over-HTTPS protocol (doh or doh3).
# Usage: validate_dns_protocol <proto>
validate_dns_protocol() {
    local proto="$1"
    case "$proto" in
        doh|doh3) return 0 ;;
        *) return 1 ;;
    esac
}

# --- Profile ID Validation ---

# Return 0 if <profile_id> is a valid ControlD profile ID.
# Valid IDs are non-empty strings containing only lowercase alphanumeric characters.
# Usage: validate_profile_id <profile_id>
validate_profile_id() {
    local profile_id="$1"
    if [[ -z "$profile_id" ]]; then
        return 1
    fi
    # Only lowercase letters and digits are permitted (typical 10-char ControlD IDs)
    if [[ ! "$profile_id" =~ ^[a-z0-9]+$ ]]; then
        return 1
    fi
    return 0
}

# Return a redacted form of <profile_id> safe for logging (shows first 3 and last 2 chars).
# Short IDs (5 chars or fewer) are masked entirely.
# Usage: redact_profile_id <profile_id>
redact_profile_id() {
    local profile_id="$1"
    if [[ -z "$profile_id" ]]; then
        echo "(empty)"
        return
    fi
    local len="${#profile_id}"
    if [[ $len -le 5 ]]; then
        # Mask completely – too short to safely show any characters
        echo "***...**"
    else
        echo "${profile_id:0:3}...${profile_id: -2}"
    fi
}

# --- DNS State Backup / Restore ---

# Save the current Wi-Fi DNS server list to <backup_dir>/original_dns.txt.
# Usage: backup_dns_settings <backup_dir>
backup_dns_settings() {
    local backup_dir="$1"
    networksetup -getdnsservers Wi-Fi > "$backup_dir/original_dns.txt" 2>/dev/null \
        || echo "No DNS servers" > "$backup_dir/original_dns.txt"
}

# Restore Wi-Fi DNS settings from <backup_dir>/original_dns.txt.
# Falls back to public DNS (1.1.1.1 8.8.8.8) if the backup file is missing.
# Usage: restore_dns_settings <backup_dir>
restore_dns_settings() {
    local backup_dir="$1"
    if [[ -f "$backup_dir/original_dns.txt" ]]; then
        local original_dns
        original_dns=$(cat "$backup_dir/original_dns.txt")
        if [[ "$original_dns" == "No DNS servers" ]] \
            || [[ "$original_dns" == *"There aren't any DNS Servers"* ]]; then
            networksetup -setdnsservers Wi-Fi "Empty"
        else
            # Restore the first listed DNS server
            while IFS= read -r dns_server; do
                if [[ -n "$dns_server" ]]; then
                    networksetup -setdnsservers Wi-Fi "$dns_server"
                    break
                fi
            done < "$backup_dir/original_dns.txt"
        fi
    else
        # No backup available – fall back to well-known public resolvers
        networksetup -setdnsservers Wi-Fi 1.1.1.1 8.8.8.8
    fi
}
