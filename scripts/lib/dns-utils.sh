#!/bin/bash
#
# DNS Utilities Library
# DNS lookup helpers with TTL-aware file-based caching
#
# Usage: source "scripts/lib/dns-utils.sh"

# Source Guard
if [[ "${_DNS_UTILS_SH_:-}" == "true" ]]; then
    return
fi
_DNS_UTILS_SH_="true"

# Cache directory (override via DNS_CACHE_DIR env var before sourcing)
DNS_CACHE_DIR="${DNS_CACHE_DIR:-${TMPDIR:-/tmp}/dns_cache_$$}"

# --- Cache management ---

# Ensure the cache directory exists (created on first use)
dns_cache_init() {
    if [[ ! -d "$DNS_CACHE_DIR" ]]; then
        mkdir -p "$DNS_CACHE_DIR"
    fi
}

# Remove all cached DNS entries
dns_cache_clear() {
    if [[ -d "$DNS_CACHE_DIR" && ! -L "$DNS_CACHE_DIR" ]]; then
        rm -f "$DNS_CACHE_DIR"/*.cache 2>/dev/null || true
    fi
}

# Remove the entire cache directory
dns_cache_destroy() {
    if [[ -d "$DNS_CACHE_DIR" && ! -L "$DNS_CACHE_DIR" ]]; then
        rm -rf "$DNS_CACHE_DIR"
    fi
}

# --- DNS lookup with caching ---

# Perform a DNS A/CNAME lookup with TTL-aware file-based caching.
# Returns the first record from the answer (empty string on failure).
#
# Usage: dns_lookup_cached <hostname> [ttl_seconds]
dns_lookup_cached() {
    local host="$1"
    local ttl="${2:-60}"

    # 🛡️ Sentinel: sanitize hostname to a safe filename
    # Only allow alphanumeric characters, dots, and hyphens
    local safe_host
    safe_host=$(printf '%s' "$host" | tr -cd 'a-zA-Z0-9.-')
    if [[ -z "$safe_host" ]]; then
        return 1
    fi

    dns_cache_init
    local cache_file="$DNS_CACHE_DIR/${safe_host}.cache"

    # Check cache freshness (skip symlinks to prevent symlink attacks)
    if [[ -f "$cache_file" && ! -L "$cache_file" ]]; then
        local cache_time now
        now=$(date +%s)
        # Cache file format: line 1 = Unix epoch when cached, line 2 = result.
        # This avoids relying on filesystem mtime, making it fully cross-platform.
        cache_time=$(head -1 "$cache_file" 2>/dev/null || echo 0)
        # Guard: only use cache_time if it is a plain integer
        if [[ "$cache_time" =~ ^[0-9]+$ ]] && (( now - cache_time < ttl )); then
            tail -1 "$cache_file"
            return 0
        fi
    fi

    # Perform the lookup
    local result
    result=$(dig +short +time=2 +tries=1 "$host" 2>/dev/null \
             | grep -v '^;;' | head -1)

    # Store result in cache only on success
    if [[ -n "$result" ]]; then
        # 🛡️ Sentinel: write to a temp file then atomically rename to prevent
        # partial reads and to avoid following existing symlinks at the target path.
        # Cache file format: line 1 = epoch timestamp, line 2 = resolved value.
        local tmp now
        now=$(date +%s)
        tmp=$(mktemp "$DNS_CACHE_DIR/${safe_host}.XXXXXX")
        printf '%s\n%s\n' "$now" "$result" > "$tmp"
        mv "$tmp" "$cache_file"
    fi

    printf '%s\n' "$result"
}

# --- DNS health checks ---

# Test DNS resolution via an optional resolver IP.
# Returns 0 if the lookup succeeds, non-zero otherwise.
#
# Usage: dns_health_check [resolver_ip] [test_hostname]
dns_health_check() {
    local resolver="${1:-}"
    local test_host="${2:-google.com}"
    if [[ -n "$resolver" ]]; then
        dig "@${resolver}" +short +time=3 +tries=1 "$test_host" >/dev/null 2>&1
    else
        dig +short +time=3 +tries=1 "$test_host" >/dev/null 2>&1
    fi
}

# --- Network settings backup/restore ---

# Backup current network settings
backup_network_settings() {
    local backup_dir="$1"

    # Delegate DNS backup to the shared helper (network-common.sh) if available
    if command -v backup_dns_settings >/dev/null 2>&1; then
        backup_dns_settings "$backup_dir"
    else
        networksetup -getdnsservers Wi-Fi > "$backup_dir/original_dns.txt" 2>/dev/null \
            || echo "No DNS servers" > "$backup_dir/original_dns.txt"
    fi

    # Backup current network configuration
    scutil --dns > "$backup_dir/dns_config.txt" 2>/dev/null || true
}

# Restore network settings (emergency recovery)
restore_network_settings() {
    local backup_dir="$1"

    # Delegate DNS restore to the shared helper (network-common.sh) if available
    if command -v restore_dns_settings >/dev/null 2>&1; then
        restore_dns_settings "$backup_dir"
    else
        if [[ -f "$backup_dir/original_dns.txt" ]]; then
            local original_dns
            original_dns=$(cat "$backup_dir/original_dns.txt")
            if [[ "$original_dns" == "No DNS servers" ]] || [[ "$original_dns" == "There aren't any DNS Servers set on Wi-Fi." ]]; then
                networksetup -setdnsservers Wi-Fi "Empty"
            else
                while IFS= read -r dns_server; do
                    if [[ -n "$dns_server" ]]; then
                        networksetup -setdnsservers Wi-Fi "$dns_server"
                        break
                    fi
                done < "$backup_dir/original_dns.txt"
            fi
        else
            networksetup -setdnsservers Wi-Fi 1.1.1.1 8.8.8.8
        fi
    fi

    # Flush DNS cache
    dscacheutil -flushcache 2>/dev/null || true
    sudo killall -HUP mDNSResponder 2>/dev/null || true
}

# --- DNS Resolution Test ---

# Test generic DNS resolution against a specific resolver
# Returns 0 if successful, 1 if failed
# Usage: test_dns_resolution [resolver_ip] [domain]
test_dns_resolution() {
    local resolver="${1:-127.0.0.1}"
    local domain="${2:-google.com}"

    # Use dns_health_check if available (it is in this file)
    if command -v dns_health_check >/dev/null 2>&1; then
        dns_health_check "$resolver" "$domain"
        return $?
    else
        if dig @"$resolver" "$domain" +short +time=5 >/dev/null 2>&1; then
            return 0
        else
            return 1
        fi
    fi
}
