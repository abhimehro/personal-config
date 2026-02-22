#!/bin/bash
#
# Network Mode Manager (Refactored)
# Implements the "Separation Strategy" for Control D and Windscribe.
#
# USAGE: ./scripts/network-mode-manager.sh {controld|windscribe|status} [profile]

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source Core Library
LIB_PATH="$SCRIPT_DIR/lib/network-core.sh"
if [[ -f "$LIB_PATH" ]]; then
    # shellcheck source=scripts/lib/network-core.sh
    source "$LIB_PATH"
else
    echo "Error: Network core library not found at $LIB_PATH" >&2
    exit 1
fi

# Source optional shared libraries
for _lib in "$SCRIPT_DIR/lib/network-utils.sh" "$SCRIPT_DIR/lib/dns-utils.sh"; do
    if [[ -f "$_lib" ]]; then
        # shellcheck source=/dev/null
        source "$_lib"
    fi
done
unset _lib

# --- Configuration ---
DEFAULT_PROFILE="browsing"
IPV6_MANAGER="$SCRIPT_DIR/macos/ipv6-manager.sh"

# --- Logic ---

validate_protocol() {
  case "$1" in
    ""|doh|doh3) return 0 ;;
    *) error "Invalid protocol: '$1'. Must be empty (default) or 'doh' or 'doh3'." ;;
  esac
}

ensure_prereqs() {
  ensure_not_root
  check_cmd "ctrld"
  check_cmd "networksetup"

  if [[ ! -x "$IPV6_MANAGER" ]]; then
    error "IPv6 Manager not found or not executable at $IPV6_MANAGER"
  fi
}

set_ipv6() {
  local state=$1
  log "Setting IPv6 state to: $state..."
  sudo "$IPV6_MANAGER" "$state" >/dev/null
  success "IPv6 state set to $state."
}

stop_controld() {
  log "Stopping Control D service and cleaning up DNS configuration..."
  reset_system_dns
  sudo ctrld service stop 2>/dev/null || true
  sudo pkill -f "ctrld" 2>/dev/null || true
  success "Control D stopped and system DNS reset to DHCP."
}

start_controld() {
  local profile_key=$1
  local force_proto=$2

  case "$profile_key" in
    "privacy")  log "Selecting ${E_PRIVACY} PRIVACY profile..." ;;
    "browsing") log "Selecting ${E_BROWSING} BROWSING profile..." ;;
    "gaming")   log "Selecting ${E_GAMING} GAMING profile..." ;;
    *)          error "Unknown profile '$profile_key'. Available profiles: privacy, browsing, gaming." ;;
  esac

  log "Starting Control D (profile=$profile_key) via controld-manager..."

  local controld_manager="/usr/local/bin/controld-manager"
  if [[ ! -x "$controld_manager" ]]; then
    controld_manager="$REPO_ROOT/controld-system/scripts/controld-manager"
    if [[ ! -x "$controld_manager" ]]; then
      error "controld-manager script not found in /usr/local/bin or at $controld_manager"
    fi
    log "Using local controld-manager: $controld_manager"
  fi

  # Call switch with profile and optional protocol override
  if sudo env CTRLD_PRIVACY_PROFILE="${CTRLD_PRIVACY_PROFILE:-}" \
          CTRLD_GAMING_PROFILE="${CTRLD_GAMING_PROFILE:-}" \
          CTRLD_BROWSING_PROFILE="${CTRLD_BROWSING_PROFILE:-}" \
          CTR_PROFILE_PRIVACY_ID="${CTR_PROFILE_PRIVACY_ID:-${CTRLD_PRIVACY_PROFILE:-}}" \
          CTR_PROFILE_GAMING_ID="${CTR_PROFILE_GAMING_ID:-${CTRLD_GAMING_PROFILE:-}}" \
          CTR_PROFILE_BROWSING_ID="${CTR_PROFILE_BROWSING_ID:-${CTRLD_BROWSING_PROFILE:-}}" \
          "$controld_manager" switch "$profile_key" "$force_proto"; then
    success "Control D active (profile: $profile_key, protocol: ${force_proto:-default})."
  else
    error "controld-manager failed to switch to profile '$profile_key'."
  fi
}

print_status() {
  echo -e "\n${BOLD}${BLUE}   NETWORK STATUS${NC}"
  echo -e "${BLUE}   ──────────────${NC}"

  # Control D
  local cd_display
  if pgrep -x "ctrld" >/dev/null 2>&1; then
    local config_link="/etc/controld/ctrld.toml"
    local profile_name="Unknown"
    if sudo test -L "$config_link"; then
      local target
      target=$(sudo readlink "$config_link" || echo "")
      local extracted_name
      extracted_name=$(basename "$target")
      extracted_name="${extracted_name#ctrld.}"
      extracted_name="${extracted_name%.toml}"
      case "$extracted_name" in
        "privacy")  profile_name="Privacy" ;;
        "browsing") profile_name="Browsing" ;;
        "gaming")   profile_name="Gaming" ;;
        *)          profile_name="$extracted_name" ;;
      esac
    fi
    cd_display="${GREEN}● ACTIVE${NC} (${YELLOW}$profile_name${NC})"
  else
    cd_display="${RED}○ STOPPED${NC}"
  fi
  printf "   %s  %-13s %b\n" "🤖" "Control D" "$cd_display"

  # VPN
  local vpn_status="${RED}DISCONNECTED${NC}"
  if is_vpn_connected; then
    vpn_status="${GREEN}CONNECTED${NC}"
  fi
  printf "   %s  %-13s %b\n" "🔐" "VPN Tunnel" "$vpn_status"

  # Network Info (Parallel)
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

  # DNS Status
  local dns_status
  if [[ "$dns_servers" == *"There aren't any DNS Servers"* ]]; then
    dns_status="${YELLOW}DHCP (ISP/Router)${NC}"
  elif [[ "$dns_servers" == *"127.0.0.1"* ]]; then
    dns_status="${GREEN}127.0.0.1 (Localhost)${NC}"
  else
    local cleaner_dns="${dns_servers//$'\n'/, }"
    dns_status="${RED}${cleaner_dns%, }${NC}"
  fi
  printf "   %s  %-13s %b\n" "📡" "System DNS" "$dns_status"

  # IPv6 Status
  local ipv6_status="${RED}DISABLED${NC}"
  if [[ "$wifi_info" == *"IPv6: Automatic"* ]]; then
    ipv6_status="${GREEN}ENABLED${NC} (Automatic)"
  fi
  printf "   %s  %-13s %b\n" "🌐" "IPv6 Mode" "$ipv6_status"
  echo -e "\n"
}

interactive_menu() {
  while true; do
    clear

    local active_mode="none"
    if pgrep -x "ctrld" >/dev/null 2>&1; then
      local config_link="/etc/controld/ctrld.toml"
      if sudo test -L "$config_link"; then
        local target
        target=$(sudo readlink "$config_link" || echo "")
        if [[ "$target" == *"privacy"* ]]; then active_mode="privacy"; fi
        if [[ "$target" == *"browsing"* ]]; then active_mode="browsing"; fi
        if [[ "$target" == *"gaming"* ]]; then active_mode="gaming"; fi
      fi
    elif is_vpn_connected; then
      active_mode="vpn"
    fi

    local m_priv="  " m_brow="  " m_game="  " m_vpn="  "
    case "$active_mode" in
      privacy)  m_priv="${GREEN}✅${NC}" ;;
      browsing) m_brow="${GREEN}✅${NC}" ;;
      gaming)   m_game="${GREEN}✅${NC}" ;;
      vpn)      m_vpn="${GREEN}✅${NC}" ;;
    esac

    echo -e "\n${BOLD}${BLUE}🎨 Network Mode Manager${NC}"
    echo -e "${BLUE}   ────────────────────${NC}"
    echo -e "   1) ${E_PRIVACY} Control D (Privacy)          $m_priv"
    echo -e "   2) ${E_BROWSING} Control D (Browsing)         $m_brow"
    echo -e "   3) ${E_GAMING} Control D (Gaming)           $m_game"
    echo -e "   4) ${E_VPN} Windscribe (VPN)             $m_vpn"
    echo -e "   5) ${E_INFO} Show Status                  ${YELLOW}[Default]${NC}"
    echo -e "   0) 🚪 Exit"

    echo -ne "\n${BOLD}Select option [0-5]: ${NC}"
    read -r choice
    choice="${choice:-5}"

    case "$choice" in
      1) (main "controld" "privacy") || true ;;
      2) (main "controld" "browsing") || true ;;
      3) (main "controld" "gaming") || true ;;
      4) (main "windscribe") || true ;;
      5) (main "status") || true ;;
      0) echo "Goodbye!"; exit 0 ;;
      *) echo -e "${RED}Invalid option${NC}" ;;
    esac

    echo -e "\n${BOLD}Press any key to continue...${NC}"
    read -n 1 -s -r
  done
}

main() {
  local mode="${1:-}"
  local profile="${2:-$DEFAULT_PROFILE}"

  if [[ "$mode" == "-h" || "$mode" == "--help" || "$mode" == "help" ]]; then
    echo "Usage: $0 {controld|windscribe|status} [profile]"
    exit 0
  fi

  if [[ -z "$mode" ]]; then
    interactive_menu
    exit 0
  fi

  ensure_prereqs
  load_network_env

  case "$mode" in
    windscribe)
      local profile="${2:-}"
      if [[ -n "$profile" ]]; then
        log "Switching to WINDSCRIBE + CONTROL D ($profile) MODE..."
        start_controld "$profile" "doh"
      else
        log "Switching to STANDALONE WINDSCRIBE (VPN) MODE..."
        stop_controld
      fi
      set_ipv6 "disable"
      print_status
      ;;
    controld)
      local proto="${3:-}"
      validate_protocol "$proto"
      log "Switching to CONTROL D (DNS) MODE..."
      set_ipv6 "enable"
      start_controld "$profile" "$proto"
      print_status
      ;;
    status)
      print_status
      ;;
    *)
      error "Invalid mode '$mode'"
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
