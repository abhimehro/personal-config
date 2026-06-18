#!/bin/bash
# Watches for network interface state changes and validates ctrld health
# on every transition. Falls back to DHCP DNS if ctrld is unresponsive.
# Dynamically detects available network interfaces.
#
# REQUIREMENT: Passwordless sudo must be configured for the following commands:
#   - networksetup -setdnsservers *
#   - dscacheutil -flushcache
#   - killall -HUP mDNSResponder
#   - ctrld service restart
#
# To configure, add to /etc/sudoers (use visudo):
#   username ALL=(ALL) NOPASSWD: /usr/sbin/networksetup,/usr/bin/dscacheutil,/usr/bin/killall,/usr/local/bin/ctrld

LOG="$HOME/Public/Scripts/controld_monitor.log"

# Function to get all active network services dynamically
# Uses the same pattern as scripts/lib/network-utils.sh
get_network_services() {
  networksetup -listallnetworkservices | grep -v "^An asterisk"
}

# Function to set DNS servers for all active interfaces
set_dns_all_interfaces() {
  local dns_value="$1"
  local services
  services=$(get_network_services)
  
  if [[ -z "$services" ]]; then
    echo "$(date): No network services found" >> "$LOG"
    return 1
  fi
  
  while IFS= read -r iface; do
    [[ -z "$iface" ]] && continue
    sudo networksetup -setdnsservers "$iface" "$dns_value" 2>/dev/null
  done <<< "$services"
  return 0
}

scutil --watch | while read -r line; do
  if echo "$line" | grep -qE "State:/Network/Interface/.*/IPv4|State:/Network/Global/IPv4"; then
    sleep 3  # allow interface to stabilize
    
    if ! dig +time=3 +tries=1 @127.0.0.1 verify.controld.com &>/dev/null; then
      echo "$(date): ctrld unresponsive after network event — falling back to DHCP" >> "$LOG"
      set_dns_all_interfaces "Empty"
      sudo dscacheutil -flushcache
      sudo killall -HUP mDNSResponder
      # Attempt service recovery
      sudo ctrld service restart &
      sleep 5
      # Re-enforce DNS if ctrld recovered
      if dig +time=3 +tries=1 @127.0.0.1 verify.controld.com &>/dev/null; then
        echo "$(date): ctrld recovered — re-enforcing 127.0.0.1 DNS" >> "$LOG"
        set_dns_all_interfaces "127.0.0.1"
      else
        echo "$(date): ctrld failed to recover — DHCP DNS remains active" >> "$LOG"
      fi
    fi
  fi
done
