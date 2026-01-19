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

# Map profiles to Control D Resolver UIDs (from the Control D dashboard)

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
  # Graceful stop
  sudo ctrld service stop 2>/dev/null || true
  # Kill any lingering processes
  sudo pkill -f "ctrld" 2>/dev/null || true
  # Reset Wi‑Fi DNS to DHCP/router (Empty)
  sudo networksetup -setdnsservers "Wi-Fi" "Empty" 2>/dev/null || true
  flush_dns
  success "Control D stopped and system DNS reset to DHCP."
}

start_controld() {
  local profile_key=$1
  local uid

  case "$profile_key" in
    "privacy")
      uid="6m971e9jaf"
      log "Selecting ${E_PRIVACY} PRIVACY profile..."
      ;;
    "browsing")
      uid="rcnz7qgvwg"
      log "Selecting ${E_BROWSING} BROWSING profile..."
      ;;
    "gaming")
      uid="1xfy57w34t7"
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
  local controld_manager="$script_dir/../controld-system/scripts/controld-manager"

  if [[ ! -x "$controld_manager" ]]; then
    error "controld-manager script not found or not executable at $controld_manager"
  fi

  if sudo "$controld_manager" switch "$profile_key"; then
    success "Control D active via controld-manager (profile: $profile_key)."
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

    if [[ -L "$config_link" ]]; then
      local target
      target=$(readlink "$config_link" || echo "")
      # Extract profile name from filename (e.g., ctrld.privacy.toml -> privacy)
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

    cd_display="$cd_status (${YELLOW}$profile_name${NC})"
  else
    cd_display="${RED}○ STOPPED${NC}"
  fi

  printf "   %s  %-13s %b\n" "🤖" "Control D" "$cd_display"

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

# --- Main Dispatcher ---

main() {
  ensure_prereqs

  local mode="${1:-}"
  local profile="${2:-$DEFAULT_PROFILE}"

  case "$mode" in
    windscribe)
      echo -e "${BLUE}>>> ${E_VPN} Switching to WINDSCRIBE (VPN) MODE${NC}"
      stop_controld
      set_ipv6 "disable"
      success "System is now configured for ${E_VPN} Windscribe VPN (IPv6 disabled, DNS reset)."
      print_status
      # Run tight verification for Windscribe-ready state
      if [[ -x ./scripts/network-mode-verify.sh ]]; then
        ./scripts/network-mode-verify.sh windscribe || echo -e "${RED}[WARN] Windscribe-ready verification reported issues${NC}"
      fi
      ;;

    controld)
      echo -e "${BLUE}>>> ${E_BROWSING} Switching to CONTROL D (DNS) MODE${NC}"
      set_ipv6 "enable"
      # ⚡ Bolt Optimization: Skip redundant stop_controld to prevent DNS flap (Empty -> 127.0.0.1)
      # start_controld delegates to controld-manager which safely handles cleanup and handover.
      start_controld "$profile"
      success "System is now protected by Control D (profile: $profile). Ensure Windscribe is disconnected."
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
