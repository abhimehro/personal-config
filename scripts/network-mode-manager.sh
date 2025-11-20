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
BLUE='\033[0;34m'
NC='\033[0m'

# --- Helpers ---

log()      { echo -e "${BLUE}[INFO]${NC} $*"; }
success()  { echo -e "${GREEN}[OK]${NC} $*"; }
error()    { echo -e "${RED}[ERR]${NC} $*" >&2; exit 1; }

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
      ;;
    "browsing")
      uid="rcnz7qgvwg"
      ;;
    "gaming")
      uid="1xfy57w34t7"
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
  if sudo ./controld-system/scripts/controld-manager switch "$profile_key"; then
    success "Control D active via controld-manager (profile: $profile_key)."
  else
    error "controld-manager failed to switch to profile '$profile_key'. See /var/log/controld_manager.log for details."
  fi
}

print_status() {
  echo -e "${BLUE}=== Network Status ===${NC}"

  echo -n "Control D process: "
  if pgrep -x "ctrld" >/dev/null 2>&1; then
    echo -e "${GREEN}RUNNING${NC}"
    # Best-effort resolver ID extraction (may not be supported on all ctrld versions)
    local running_uid
    running_uid=$(sudo ctrld status 2>/dev/null | grep 'Resolver ID' | awk '{print $NF}' 2>/dev/null || echo "N/A")
    echo -e "  Resolver ID: ${GREEN}$running_uid${NC}"
  else
    echo -e "${RED}STOPPED${NC}"
  fi

  echo -n "System DNS (Wi‑Fi): "
  networksetup -getdnsservers "Wi-Fi" 2>/dev/null || echo "Unknown"

  echo -n "IPv6 Status (Wi‑Fi): "
  if networksetup -getinfo "Wi-Fi" 2>/dev/null | grep -q "IPv6: Automatic"; then
    echo -e "${GREEN}ENABLED (Automatic)${NC}"
  else
    echo -e "${RED}DISABLED/Manual${NC}"
  fi
}

# --- Main Dispatcher ---

main() {
  ensure_prereqs

  local mode="${1:-}"
  local profile="${2:-$DEFAULT_PROFILE}"

  case "$mode" in
    windscribe)
      echo -e "${BLUE}>>> Switching to WINDSCRIBE (VPN) MODE${NC}"
      stop_controld
      set_ipv6 "disable"
      success "System is now configured for Windscribe VPN (IPv6 disabled, DNS reset)."
      print_status
      # Run tight verification for Windscribe-ready state
      if [[ -x ./scripts/network-mode-verify.sh ]]; then
        ./scripts/network-mode-verify.sh windscribe || echo -e "${RED}[WARN] Windscribe-ready verification reported issues${NC}"
      fi
      ;;

    controld)
      echo -e "${BLUE}>>> Switching to CONTROL D (DNS) MODE${NC}"
      set_ipv6 "enable"
      stop_controld
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
      echo "Usage: $0 {controld|windscribe|status} [profile_name]"
      echo "Available profiles: privacy, browsing, gaming"
      exit 1
      ;;
  esac
}

main "$@"
