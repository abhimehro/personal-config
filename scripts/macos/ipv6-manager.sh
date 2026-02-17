#!/bin/bash
# IPv6 Manager for macOS
# Disables/Enables IPv6 to prevent issues with IPv4-only VPN tunnels

set -e

# --- UX Definitions ---
# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Emojis 🎨
E_PASS="✅"
E_FAIL="❌"
E_WARN="⚠️"
E_INFO="ℹ️"
E_IPV6="🌐"

# Helpers
log()      { echo -e "${BLUE}${E_INFO} [INFO]${NC}" "$@"; }
success()  { echo -e "${GREEN}${E_PASS} [OK]${NC}" "$@"; }
error()    { echo -e "${RED}${E_FAIL} [ERR]${NC}" "$@" >&2; exit 1; }
warn()     { echo -e "${YELLOW}${E_WARN} [WARN]${NC}" "$@"; }
header() {
    # Print a blank line, then a bold blue header built from all arguments.
    # We avoid $* to preserve argument boundaries and any embedded whitespace.
    printf '\n%s' "${BOLD}${BLUE}"
    if [ "$#" -gt 0 ]; then
        # Print the first argument without a leading space...
        printf '%s' "$1"
        shift
        # ...then print remaining arguments each preceded by a single space.
        for arg in "$@"; do
            printf ' %s' "$arg"
        done
    fi
    # Reset color and finish with a newline.
    printf '%s\n' "${NC}"
}

# --- Core Logic ---

# Get all network services
get_network_services() {
    networksetup -listallnetworkservices | grep -v "^An asterisk"
}

# ⚡ Bolt Optimization: Parallel fetcher for service info
# Fetches info for all services in parallel background jobs to save time.
# Then iterates results sequentially to perform logic safely.
process_services_parallel() {
    local callback_func="$1"
    local tmp_dir
    tmp_dir=$(mktemp -d)

    # Cleanup temp dir on return
    trap 'rm -rf "$tmp_dir"' RETURN

    local pids=()
    local services=()
    local i=0

    # 1. Launch background jobs for all services
    local all_services=()
    while IFS= read -r service; do
        [[ -n "$service" ]] && all_services+=("$service")
    done < <(get_network_services)

    for service in "${all_services[@]}"; do
        services+=("$service")

        # Use index for filename to avoid collision and overhead
        (networksetup -getinfo "$service" 2>/dev/null > "$tmp_dir/$i") &
        pids+=($!)
        ((i+=1))
    done

    # 2. Wait for all fetches to complete
    wait "${pids[@]}" 2>/dev/null || true

    # 3. Process results sequentially
    i=0
    for service in "${services[@]}"; do
        local info_file="$tmp_dir/$i"

        # Invoke callback with service name and path to info file
        "$callback_func" "$service" "$info_file"
        ((i+=1))
    done
}

# Disable IPv6 on all interfaces
disable_ipv6() {
    header "${E_IPV6} Disabling IPv6 on all network interfaces..."
    
    # 1. Standard networksetup method (Parallel Read / Sequential Write)
    _disable_callback() {
        local service="$1"
        local info_file="$2"
        if grep -q "IPv6: Off" "$info_file"; then
            echo -e "   ${YELLOW}•${NC} $service: already disabled"
        else
            echo -e "   ${RED}↓${NC} Disabling IPv6 on: $service"
            sudo networksetup -setv6off "$service" 2>/dev/null || warn "   (skipped: $service)"
        fi
    }
    process_services_parallel _disable_callback

    # 2. Sysctl method (Disable Router Advertisements globally)
    echo -e "   ${RED}↓${NC} Disabling IPv6 Router Advertisements (sysctl)..."
    sudo sysctl -w net.inet6.ip6.accept_rtadv=0 2>/dev/null || true
    
    success "IPv6 disabled on all interfaces"
    check_ipv6_status
}

# Enable IPv6 on all interfaces
enable_ipv6() {
    header "${E_IPV6} Enabling IPv6 on all network interfaces..."
    
    # 1. Standard networksetup method (Parallel Read / Sequential Write)
    _enable_callback() {
        local service="$1"
        local info_file="$2"
        if grep -q "IPv6: Automatic" "$info_file"; then
             echo -e "   ${GREEN}•${NC} $service: already enabled"
        else
            echo -e "   ${GREEN}↑${NC} Enabling IPv6 on: $service"
            sudo networksetup -setv6automatic "$service" 2>/dev/null || warn "   (skipped: $service)"
        fi
    }
    process_services_parallel _enable_callback

    # 2. Sysctl method (Re-enable Router Advertisements)
    echo -e "   ${GREEN}↑${NC} Enabling IPv6 Router Advertisements (sysctl)..."
    sudo sysctl -w net.inet6.ip6.accept_rtadv=1 2>/dev/null || true
    
    success "IPv6 enabled on all interfaces"
    check_ipv6_status
}

# Check IPv6 status
check_ipv6_status() {
    header "Current IPv6 configuration:"
    
    _status_callback() {
        local service="$1"
        local info_file="$2"
        local ipv6_config
        ipv6_config=$(grep "IPv6:" "$info_file" || echo "IPv6: Unknown")

        # Formatting status
        if [[ "$ipv6_config" == *"IPv6: Automatic"* ]]; then
             printf "   %-25s %b\n" "$service" "${GREEN}● ENABLED${NC} (Automatic)"
        elif [[ "$ipv6_config" == *"IPv6: Off"* ]]; then
             printf "   %-25s %b\n" "$service" "${RED}○ DISABLED${NC} (Off)"
        else
             # Extract status value after "IPv6: " prefix
             local status_value="${ipv6_config#*IPv6: }"
             printf "   %-25s %b\n" "$service" "${YELLOW}UNKNOWN${NC} ($status_value)"
        fi
    }
    process_services_parallel _status_callback
    
    header "Active IPv6 addresses:"
    local ipv6_addrs
    ipv6_addrs=$(ifconfig | grep "inet6" | grep -v "::1" | grep -v "fe80::" || true)

    if [[ -z "$ipv6_addrs" ]]; then
        echo -e "   ${YELLOW}No global IPv6 addresses found${NC}"
    else
        echo "$ipv6_addrs"
    fi
    echo ""
}

# Main
case "${1:-}" in
    "disable")
        disable_ipv6
        ;;
    "enable")
        enable_ipv6
        ;;
    "status")
        check_ipv6_status
        ;;
    *)
        echo -e "${BOLD}${BLUE}IPv6 Manager for macOS${NC}"
        echo -e "Usage: $0 <command>"
        echo ""
        echo -e "${BOLD}Commands:${NC}"
        echo -e "  ${GREEN}disable${NC}   Disable IPv6 on all network interfaces"
        echo -e "  ${GREEN}enable${NC}    Enable IPv6 on all network interfaces"
        echo -e "  ${GREEN}status${NC}    Check current IPv6 configuration"
        echo ""
        echo -e "${BOLD}Why disable IPv6?${NC}"
        echo -e "  - Windscribe VPN only supports IPv4"
        echo -e "  - Apps attempting IPv6 connections will timeout/fail"
        echo -e "  - Causes Raycast updates and other services to fail"
        echo ""
        echo -e "${BOLD}Examples:${NC}"
        echo -e "  sudo $0 disable    # Disable IPv6 (recommended with Windscribe)"
        echo -e "  $0 status          # Check current status"
        echo -e "  sudo $0 enable     # Re-enable IPv6 (if needed)"
        ;;
esac
