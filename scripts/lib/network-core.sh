#!/bin/bash
#
# Network Core Library
# Shared functions for DNS and VPN management
#
# Usage: source "scripts/lib/network-core.sh"

# Source Guard
if [[ ${_NETWORK_CORE_SH_-} == "true" ]]; then
	return
fi
_NETWORK_CORE_SH_="true"

# Source Common Library (optional – not present in standalone installs)
_NETWORK_CORE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$_NETWORK_CORE_LIB_DIR/common.sh" ]]; then
	# shellcheck source=scripts/lib/common.sh
	source "$_NETWORK_CORE_LIB_DIR/common.sh"
fi

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

# Export for use in scripts that source this library
export RED GREEN YELLOW BLUE BOLD NC
export E_PASS E_FAIL E_INFO E_PRIVACY E_GAMING E_BROWSING E_VPN

# --- Logging ---
log() { printf "${BLUE}${E_INFO} [INFO]${NC} %s\n" "$*"; }
success() { printf "${GREEN}${E_PASS} [OK]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}⚠️ [WARN]${NC} %s\n" "$*"; }
error() {
	printf "${RED}${E_FAIL} [ERR]${NC} %s\n" "$*" >&2
	exit 1
}

# --- Modern Tooling Wrappers ---
smart_grep() {
	if command -v rg >/dev/null 2>&1; then
		rg "$@"
	else
		grep "$@"
	fi
}

# fd -> find
# Usage: smart_find pattern [path]
smart_find() {
	# Define a stable interface: first arg = pattern, second arg (optional) = path.
	# We avoid blindly forwarding "$@" so that fd and find behavior stays consistent.
	if [[ $# -lt 1 ]]; then
		printf 'smart_find: missing required pattern argument\n' >&2
		return 1
	fi

	local pattern path
	pattern=$1
	path="${2:-.}"

	# 🛡️ Sentinel: Sanitize path to prevent argument injection
	# If path starts with '-', prepend './' so it's treated as a path, not an option
	if [[ $path == -* ]]; then
		path="./$path"
	fi

	if command -v fd >/dev/null 2>&1; then
		# Use the same (pattern, path) semantics for fd as for find.
		fd -- "$pattern" "$path"
	else
		# find fallback (basic name search) with stable (pattern, path) semantics
		# 🛡️ Sentinel: Sanitize pattern to prevent argument injection
		if [[ $pattern == -* ]]; then
			pattern="./$pattern"
		fi
		find "$path" -name "$pattern"
	fi
}

# --- Environment ---
load_network_env() {
	local env_file="${CONTROLD_DIR:-/etc/controld}/controld.env"
	if [[ -r $env_file ]]; then
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
	sudo networksetup -setdnsservers "USB 10/100/1000 LAN" "Empty" 2>/dev/null || true
	flush_dns_cache
}

# --- Core VPN Actions ---
is_vpn_connected() {
	# Check for utun interface with an IP address
	ifconfig | awk '/^utun/ {s=1; next} s && /inet / && !/127\.0\.0\.1/ {f=1; exit} s && /^[^ 	]/ {s=0} END {exit !f}' >/dev/null 2>&1
}

# Resolve windscribe CLI binary path (macOS app bundle or PATH).
resolve_windscribe_bin() {
	if [[ -n ${WINDSCRIBE_BIN-} && -x ${WINDSCRIBE_BIN} ]]; then
		echo "$WINDSCRIBE_BIN"
		return 0
	fi
	if command -v windscribe-cli >/dev/null 2>&1; then
		command -v windscribe-cli
		return 0
	fi
	if [[ -x /Applications/Windscribe.app/Contents/MacOS/windscribe-cli ]]; then
		echo "/Applications/Windscribe.app/Contents/MacOS/windscribe-cli"
		return 0
	fi
	if command -v windscribe >/dev/null 2>&1; then
		command -v windscribe
		return 0
	fi
	return 1
}

# Detect whether the active Windscribe tunnel has IPv6 capability.
# Returns 0 when a global (non-link-local) IPv6 address is present on a utun
# interface while VPN appears connected. Static/IPv4-only servers return 1.
# Override with WINDSCRIBE_IPV6=1|0 for forced policy during connect.
vpn_supports_ipv6() {
	case "${WINDSCRIBE_IPV6-}" in
	1 | true | TRUE | yes | YES | on | ON) return 0 ;;
	0 | false | FALSE | no | NO | off | OFF) return 1 ;;
	esac

	is_vpn_connected || return 1

	# Prefer a global inet6 on any utun (Windscribe WireGuard IPv6 egress).
	if ifconfig 2>/dev/null | awk '
		/^utun/ {in_utun=1; next}
		in_utun && /^[a-z]/ {in_utun=0}
		in_utun && /inet6 / && $2 !~ /^fe80:/ && $2 != "::1" {found=1; exit}
		END {exit !found}
	'; then
		return 0
	fi
	return 1
}

# Map a DNS protocol + IPv6 policy to the three supported network profile modes:
#   doh-ipv4   → DoH, IPv6 disabled (leak prevention / IPv4-only VPN)
#   doh3-ipv6  → DoH3, IPv6 enabled (standalone Control D)
#   doh-ipv6   → DoH, IPv6 enabled (Windscribe IPv6-capable servers)
resolve_network_profile_mode() {
	local protocol="${1:-doh3}"
	local ipv6_policy="${2:-enable}" # enable|disable
	case "$protocol:$ipv6_policy" in
	doh:disable) echo "doh-ipv4" ;;
	doh:enable) echo "doh-ipv6" ;;
	doh3:enable | doh3:disable) echo "doh3-ipv6" ;;
	*) echo "doh3-ipv6" ;;
	esac
}

# --- Utilities ---
ensure_not_root() {
	if [[ ${EUID} -eq 0 ]]; then
		error "Please run as your normal user (not root). The script will ask for sudo when needed."
	fi
}

check_cmd() {
	local cmd="$1"
	command -v "$cmd" >/dev/null 2>&1 || error "$cmd utility not found in PATH"
}
