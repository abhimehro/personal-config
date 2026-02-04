#!/bin/bash
#
# Network Mode Manager
# Implements the "Separation Strategy" for Control D and Windscribe.
#
# MODES:
#   controld   -> Enables Control D (DoH3 via cloud profile), enables IPv6
#   windscribe -> Disables Control D, disables IPv6 (leak protection), resets DNS
#   status     -> Shows current network state
#
# USAGE: ./scripts/network-mode-manager.sh {controld|windscribe|status} [profile]

set -euo pipefail

# --- Configuration ---

# Default profile if none specified
DEFAULT_PROFILE="browsing"

# IP where ctrld listens. Recommended: 127.0.0.1 (localhost)
# CRITICAL: This MUST match the IP that macOS DNS points to.
LISTENER_IP="127.0.0.1"

# Path to existing macOS-specific IPv6 manager (relative to repo root)
IPV6_MANAGER="./scripts/macos/ipv6-manager.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'
BOLD='\033[1m'

# Emojis 🎨
E_PASS="✅"
E_FAIL="❌"
E_WARN="⚠️"
E_INFO="ℹ️"
E_PRIVACY="🛡️"
E_GAMING="🎮"
E_BROWSING="🌐"
E_VPN="🔐"
E_NETWORK="🛜"

# --- Helpers ---

log()      { echo -e "${BLUE}${E_INFO} [INFO]${NC} $@"; }
success()  { echo -e "${GREEN}${E_PASS} [OK]${NC} $@"; }
error()    { echo -e "${RED}${E_FAIL} [ERR]${NC} $@" >&2; exit 1; }

ensure_prereqs() {
  # Least privilege: refuse to run as root
  if [[ $EUID -eq 0 ]]; then
    error "Please run as your normal user (not root). The script will ask for sudo when needed."
  fi

  command -v ctrld >/dev/null 2>&1       || error "ctrld utility not found in PATH"
  command -v networksetup >/dev/null 2>&1 || error "networksetup not found (macOS required)"

  if [[ ! -x "$IPV6_MANAGER" ]]; then
    error "IPv6 Manager not found or not executable at $IPV6_MANAGER"
  fi
}

flush_dns() {
  log "Flushing DNS caches..."
  sudo dscacheutil -flushcache || true
  sudo killall -HUP mDNSResponder 2>/dev/null || true
}

# --- Core Logic ---

set_ipv6() {
  local state=$1  # "enable" or "disable"
  log "Setting IPv6 state to: $state..."
  sudo "$IPV6_MANAGER" "$state" >/dev/null
  success "IPv6 state set to $state."
}

stop_controld() {
  log "Stopping Control D service and cleaning up DNS configuration..."

  # ⚡ Bolt Optimization: Reset DNS first to restore internet immediately via router,
  # minimizing downtime while the service stops (which can take seconds).
  sudo networksetup -setdnsservers "Wi-Fi" "Empty" 2>/dev/null || true

  # Graceful stop
  sudo ctrld service stop 2>/dev/null || true
  # Kill any lingering processes
  sudo pkill -f "ctrld" 2>/dev/null || true

  flush_dns
  success "Control D stopped and system DNS reset to DHCP."
}

start_controld() {
  local profile_key=$1
  local force_proto=$2

  case "$profile_key" in
    "privacy")
      log "Selecting ${E_PRIVACY} PRIVACY profile..."
      ;;
    "browsing")
      log "Selecting ${E_BROWSING} BROWSING profile..."
      ;;
    "gaming")
      log "Selecting ${E_GAMING} GAMING profile..."
      ;;
    *)
      error "Unknown profile '$profile_key'. Available profiles: privacy, browsing, gaming."
      ;;
  esac

  log "Starting Control D (profile=$profile_key) via controld-manager..."

  # Delegate profile + protocol management to the proven controld-manager script.
  # This script:
  #   - Generates/uses per-profile configs under /etc/controld/profiles
  #   - Starts ctrld with --skip_self_checks
  #   - Points macOS Wi‑Fi DNS at the local resolver
  #   - Verifies Control D connectivity and filtering

  # Find the script location regardless of current working directory
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  # 🛡️ Sentinel: Prefer installed, root-owned binary if available (Defense in Depth)
  local controld_manager="/usr/local/bin/controld-manager"

  if [[ ! -x "$controld_manager" ]]; then
    # Fallback to local script (Dev mode / Pre-install)
    controld_manager="$script_dir/../controld-system/scripts/controld-manager"
    if [[ ! -x "$controld_manager" ]]; then
      error "controld-manager script not found in /usr/local/bin or at $controld_manager"
    fi
    log "Using local controld-manager: $controld_manager"
  else
    # Verify we are using the secure installed version
    log "Using system controld-manager: $controld_manager"
  fi

  # Call switch with profile and optional protocol override
  if sudo env CTRLD_PRIVACY_PROFILE="${CTRLD_PRIVACY_PROFILE:-}" \
          CTRLD_GAMING_PROFILE="${CTRLD_GAMING_PROFILE:-}" \
          CTRLD_BROWSING_PROFILE="${CTRLD_BROWSING_PROFILE:-}" \
          CTR_PROFILE_PRIVACY_ID="${CTR_PROFILE_PRIVACY_ID:-${CTRLD_PRIVACY_PROFILE:-}}" \
          CTR_PROFILE_GAMING_ID="${CTR_PROFILE_GAMING_ID:-${CTRLD_GAMING_PROFILE:-}}" \
          CTR_PROFILE_BROWSING_ID="${CTR_PROFILE_BROWSING_ID:-${CTRLD_BROWSING_PROFILE:-}}" \
          "$controld_manager" switch "$profile_key" "$force_proto"; then
    success "Control D active via controld-manager (profile: $profile_key, protocol: ${force_proto:-default})."
  else
    error "controld-manager failed to switch to profile '$profile_key'. See /var/log/controld_manager.log for details."
  fi
}

print_status() {
  # Header
  echo -e "\n${BOLD}${BLUE}   NETWORK STATUS${NC}"
  echo -e "${BLUE}   ──────────────${NC}"

  # --- Control D Status ---
  local cd_status
  local cd_display

  if pgrep -x "ctrld" >/dev/null 2>&1; then
    cd_status="${GREEN}● ACTIVE${NC}"

    # ⚡ Bolt Optimization: Read config symlink instead of expensive 'sudo ctrld status'
    # This avoids spawning a process and potential sudo prompt.
    local config_link="/etc/controld/ctrld.toml"
    local profile_name="Unknown"

    if sudo test -L "$config_link"; then
      local target
      target=$(sudo readlink "$config_link" || echo "")
      # Extract profile name from filename (e.g., ctrld.privacy.toml -> privacy)
      local extracted_name
      # Optimization: Use Bash parameter expansion to avoid basename overhead
      extracted_name="${target##*/}"
      extracted_name="${extracted_name#ctrld.}"
      extracted_name="${extracted_name%.toml}"

      case "$extracted_name" in
        "privacy")  profile_name="Privacy" ;;
        "browsing") profile_name="Browsing" ;;
        "gaming")   profile_name="Gaming" ;;
        *)          profile_name="$extracted_name" ;;
      esac
    fi

    cd_display="$cd_status (${YELLOW}$profile_name${NC})"
  else
    cd_display="${RED}○ STOPPED${NC}"
  fi

  printf "   %s  %-13s %b\n" "🤖" "Control D" "$cd_display"

  # --- VPN Status ---
  local vpn_status
  # Check for utun interface with an IP address (standard for VPNs on macOS)
  if ifconfig | grep -A5 "utun" | grep "inet " | grep -v "127.0.0.1" >/dev/null 2>&1; then
    vpn_status="${GREEN}CONNECTED${NC}"
  else
    vpn_status="${RED}DISCONNECTED${NC}"
  fi

  printf "   %s  %-13s %b\n" "🔐" "VPN Tunnel" "$vpn_status"

  # --- Fetch Network Info (Parallelized) ---
  # ⚡ Bolt Optimization: Run networksetup commands in parallel to reduce wait time
  local dns_temp
  dns_temp=$(mktemp)
  local info_temp
  info_temp=$(mktemp)

  (networksetup -getdnsservers "Wi-Fi" 2>/dev/null || echo "Unknown") > "$dns_temp" &
  local pid1=$!

  (networksetup -getinfo "Wi-Fi" 2>/dev/null || echo "") > "$info_temp" &
  local pid2=$!

  wait $pid1 $pid2

  local dns_servers
  dns_servers=$(cat "$dns_temp")
  local wifi_info
  wifi_info=$(cat "$info_temp")

  rm -f "$dns_temp" "$info_temp"

  # --- System DNS Status ---
  local dns_status

  # ⚡ Bolt Optimization: Use Bash string matching instead of 'grep' pipelines
  if [[ "$dns_servers" == *"There aren't any DNS Servers"* ]]; then
    dns_status="${YELLOW}DHCP (ISP/Router)${NC}"
  elif [[ "$dns_servers" == *"127.0.0.1"* ]]; then
    dns_status="${GREEN}127.0.0.1 (Localhost)${NC}"
  else
    # ⚡ Bolt Optimization: Use Bash parameter expansion instead of 'tr | sed' pipeline
    local cleaner_dns="${dns_servers//$'\n'/, }" # Replace newlines with ", "
    cleaner_dns="${cleaner_dns%, }"             # Remove trailing ", "
    dns_status="${RED}$cleaner_dns${NC}"
  fi

  printf "   %s  %-13s %b\n" "📡" "System DNS" "$dns_status"

  # --- IPv6 Status ---
  local ipv6_status
  # ⚡ Bolt Optimization: Captured output via parallel execution above
  if [[ "$wifi_info" == *"IPv6: Automatic"* ]]; then
    ipv6_status="${GREEN}ENABLED${NC} (Automatic)"
  else
    ipv6_status="${RED}DISABLED${NC} (Manual/Off)"
  fi

  printf "   %s  %-13s %b\n" "🌐" "IPv6 Mode" "$ipv6_status"

  echo -e "\n"
}

print_help() {
  echo -e "${BOLD}${BLUE}Network Mode Manager${NC}"
  echo -e "Usage: $0 {controld|windscribe|status} [profile_name]"
  echo -e ""
  echo -e "${BOLD}Commands:${NC}"
  echo -e "  ${GREEN}controld${NC}    Enable Control D (DNS) mode"
  echo -e "              Arguments: [privacy|browsing|gaming]"
  echo -e "  ${GREEN}windscribe${NC}  Enable Windscribe (VPN) mode"
  echo -e "  ${GREEN}status${NC}      Show current network status"
  echo -e ""
  echo -e "${BOLD}Profiles:${NC}"
  echo -e "  ${YELLOW}privacy${NC}     Maximum security"
  echo -e "  ${YELLOW}browsing${NC}    Balanced (Default)"
  echo -e "  ${YELLOW}gaming${NC}      Low latency"
  echo -e ""
}

interactive_menu() {
  echo -e "\n${BOLD}${BLUE}🎨 Network Mode Manager${NC}"
  echo -e "${BLUE}   Select a mode to apply:${NC}\n"

  echo -e "   1) ${E_PRIVACY} Control D (Privacy)"
  echo -e "   2) ${E_BROWSING} Control D (Browsing) ${YELLOW}[Default]${NC}"
  echo -e "   3) ${E_GAMING} Control D (Gaming)"
  echo -e "   4) ${E_VPN} Windscribe (VPN)"
  echo -e "   5) ${E_INFO} Show Status"
  echo -e "   0) 🚪 Exit"

  echo -ne "\n${BOLD}Select an option [1-5]: ${NC}"
  read -r choice

  case "$choice" in
    1)    main "controld" "privacy" ;;
    2|"") main "controld" "browsing" ;;
    3)    main "controld" "gaming" ;;
    4)    main "windscribe" ;;
    5)    main "status" ;;
    0)    echo -e "${BLUE}Exiting...${NC}"; exit 0 ;;
    *)    error "Invalid option" ;;
  esac
}

# --- Main Dispatcher ---

main() {
  local mode="${1:-}"
  local profile="${2:-$DEFAULT_PROFILE}"

  # UX: Check for help flags before prereqs so help is always accessible
  if [[ "$mode" == "-h" || "$mode" == "--help" || "$mode" == "help" ]]; then
    print_help
    exit 0
  fi

  # Interactive Menu if no arguments
  if [[ -z "$mode" ]]; then
    interactive_menu
    exit 0
  fi

  ensure_prereqs

  case "$mode" in
    windscribe)
      local profile="${2:-}"
      if [[ -n "$profile" ]]; then
        echo -e "${BLUE}>>> ${E_VPN} Switching to WINDSCRIBE + CONTROL D ($profile) MODE${NC}"
        # We force 'doh' (TCP) for VPN mode to prevent connection failures
        # caused by DoH3/QUIC inside the encrypted tunnel.
        start_controld "$profile" "doh"
        success "System is now configured for ${E_VPN} Windscribe VPN with local Control D ($profile, DoH)."
      else
        echo -e "${BLUE}>>> ${E_VPN} Switching to STANDALONE WINDSCRIBE (VPN) MODE${NC}"
        stop_controld
        success "System is now configured for ${E_VPN} Windscribe VPN (IPv6 disabled, DNS reset)."
      fi
      set_ipv6 "disable"
      print_status
      # Run tight verification for Windscribe-ready state
      if [[ -x ./scripts/network-mode-verify.sh ]]; then
        # If profile provided, use controld verify instead of windscribe verify
        if [[ -n "$profile" ]]; then
          ./scripts/network-mode-verify.sh controld "$profile" || echo -e "${RED}[WARN] Control D verification reported issues${NC}"
        else
          ./scripts/network-mode-verify.sh windscribe || echo -e "${RED}[WARN] Windscribe-ready verification reported issues${NC}"
        fi
      fi
      ;;

    controld)
      local proto="${3:-}"
      echo -e "${BLUE}>>> ${E_BROWSING} Switching to CONTROL D (DNS) MODE${NC}"
      set_ipv6 "enable"
      # ⚡ Bolt Optimization: Skip redundant stop_controld to prevent DNS flap (Empty -> 127.0.0.1)
      # start_controld delegates to controld-manager which safely handles cleanup and handover.
      start_controld "$profile" "$proto"
      success "System is now protected by Control D (profile: $profile, protocol: ${proto:-default}). Ensure Windscribe is disconnected."
      print_status
      # Run tight verification for Control D active state (profile-aware)
      if [[ -x ./scripts/network-mode-verify.sh ]]; then
        ./scripts/network-mode-verify.sh controld "$profile" || echo -e "${RED}[WARN] Control D verification reported issues${NC}"
      fi
      ;;

    status)
      print_status
      ;;

    *)
      print_help
      exit 1
      ;;
  esac
}

main "$@"
