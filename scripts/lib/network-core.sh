#!/bin/bash
#
# Network Core Library
# Shared functions for DNS and VPN management
#
# Usage: source "scripts/lib/network-core.sh"

# Source Guard
if [[ "${_NETWORK_CORE_SH_:-}" == "true" ]]; then
    return
fi
_NETWORK_CORE_SH_="true"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# --- Emojis ---
E_PASS="✅"
E_FAIL="❌"
E_INFO="ℹ️"
E_PRIVACY="🛡️"
E_GAMING="🎮"
E_BROWSING="🌐"
E_VPN="🔐"

# --- Logging ---
log()      { echo -e "${BLUE}${E_INFO} [INFO]${NC}" "$@"; }
success()  { echo -e "${GREEN}${E_PASS} [OK]${NC}" "$@"; }
warn()     { echo -e "${YELLOW}⚠️ [WARN]${NC}" "$@"; }
error()    { echo -e "${RED}${E_FAIL} [ERR]${NC}" "$@" >&2; exit 1; }

# --- Modern Tooling Wrappers ---
smart_grep() {
    if command -v rg >/dev/null 2>&1; then
        rg "$@"
    else
        grep "$@"
    fi
}

smart_find() {
    if command -v fd >/dev/null 2>&1; then
        # When fd is available, defer completely to it so that callers can
        # use the full fd CLI (flags, multiple args, etc.).
        fd "$@"
    else
        # Fallback interface: smart_find <pattern> [path]
        #   - pattern: required for name matching
        #   - path:    optional, defaults to current directory
        #
        # We intentionally interpret only the first two positional arguments
        # here to avoid trying to emulate all fd flags with find.
        local pattern path
        pattern="$1"
        path="${2:-.}"

        if [[ -z "$pattern" ]]; then
            # If no pattern is provided, approximate `fd`'s "list everything"
            # behavior by running a plain find on the target path.
            find "$path"
        else
            # Normal case: search under "$path" for entries matching "$pattern".
            find "$path" -name "$pattern"
        fi
    fi
}

# --- Environment ---
load_network_env() {
    local env_file="/etc/controld/controld.env"
    if [[ -f "$env_file" ]]; then
        # shellcheck source=/dev/null
        source "$env_file"
    fi
}

# --- Core DNS Actions ---
flush_dns_cache() {
    log "Flushing DNS caches..."
    sudo dscacheutil -flushcache || true
    sudo killall -HUP mDNSResponder 2>/dev/null || true
}

reset_system_dns() {
    log "Resetting system DNS to DHCP defaults..."
    sudo networksetup -setdnsservers "Wi-Fi" "Empty" 2>/dev/null || true
    flush_dns_cache
}

# --- Core VPN Actions ---
is_vpn_connected() {
    # Check for utun interface with an IP address
    ifconfig | awk '/^utun/ {s=1; next} s && /inet / && !/127\.0\.0\.1/ {f=1; exit} s && /^[^ 	]/ {s=0} END {exit !f}' >/dev/null 2>&1
}

# --- Utilities ---
ensure_not_root() {
    if [[ "${EUID}" -eq 0 ]]; then
        error "Please run as your normal user (not root). The script will ask for sudo when needed."
    fi
}

check_cmd() {
    local cmd="$1"
    command -v "$cmd" >/dev/null 2>&1 || error "$cmd utility not found in PATH"
}
