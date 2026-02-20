#!/bin/bash
#
# Network Utilities Library
# Helpers for network interface enumeration and status on macOS
#
# Usage: source "scripts/lib/network-utils.sh"

# Source Guard
if [[ "${_NETWORK_UTILS_SH_:-}" == "true" ]]; then
    return
fi
_NETWORK_UTILS_SH_="true"

# Source network-core for shared infrastructure (if not already loaded)
_NETWORK_UTILS_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${_NETWORK_CORE_SH_:-}" != "true" && -f "$_NETWORK_UTILS_LIB_DIR/network-core.sh" ]]; then
    # shellcheck source=scripts/lib/network-core.sh
    source "$_NETWORK_UTILS_LIB_DIR/network-core.sh"
fi

# --- Network Interface Enumeration ---

# Return the name of the default network interface (e.g. "en0")
get_active_interface() {
    route get default 2>/dev/null | awk '/interface:/{print $2}' | head -1
}

# List all network services, one per line (strips the header from networksetup output)
list_network_services() {
    networksetup -listallnetworkservices 2>/dev/null | tail -n +2
}

# Return the Hardware Port device name for the first Wi-Fi interface (e.g. "en0")
get_wifi_interface() {
    networksetup -listallhardwareports 2>/dev/null \
        | awk '/Wi-Fi/{found=1} found && /Device:/{print $2; exit}'
}

# Return the current Wi-Fi SSID, or empty string if not connected
get_wifi_ssid() {
    local iface
    iface=$(get_wifi_interface)
    if [[ -z "$iface" ]]; then
        echo ""
        return 0
    fi
    networksetup -getairportnetwork "$iface" 2>/dev/null \
        | awk -F': ' '/Current Wi-Fi Network:/{print $2}'
}

# Return 0 if Wi-Fi is associated with a network, non-zero otherwise
is_wifi_connected() {
    local ssid
    ssid=$(get_wifi_ssid)
    [[ -n "$ssid" ]]
}
