#!/bin/bash
# Watches for network interface state changes and validates ctrld health
# on every transition. Falls back to DHCP DNS if ctrld is unresponsive.
# Dynamically detects available network interfaces.

LOG="$HOME/Public/Scripts/controld_monitor.log"

# Function to get all active network services dynamically
get_network_services() {
  networksetup -listallnetworkservices | tail -n +2 | awk '{print $NF}' | tr -d '\n*'
}

scutil --watch | while read -r line; do
  if echo "$line" | grep -qE "State:/Network/Interface/.*/IPv4|State:/Network/Global/IPv4"; then
    sleep 3  # allow interface to stabilize
    
    # Get current active interfaces dynamically
    INTERFACES=()
    while IFS= read -r iface; do
      [[ -z "$iface" ]] && continue
      INTERFACES+=("$iface")
    done < <(get_network_services)
    
    if [[ ${#INTERFACES[@]} -eq 0 ]]; then
      echo "$(date): No network interfaces found, skipping DNS check" >> "$LOG"
      continue
    fi
    
    if ! dig +time=3 +tries=1 @127.0.0.1 verify.controld.com &>/dev/null; then
      echo "$(date): ctrld unresponsive after network event — falling back to DHCP" >> "$LOG"
      for iface in "${INTERFACES[@]}"; do
        sudo networksetup -setdnsservers "$iface" Empty 2>/dev/null
      done
      sudo dscacheutil -flushcache
      sudo killall -HUP mDNSResponder
      # Attempt service recovery
      sudo ctrld service restart &
      sleep 5
      # Re-enforce DNS if ctrld recovered
      if dig +time=3 +tries=1 @127.0.0.1 verify.controld.com &>/dev/null; then
        echo "$(date): ctrld recovered — re-enforcing 127.0.0.1 DNS" >> "$LOG"
        for iface in "${INTERFACES[@]}"; do
          sudo networksetup -setdnsservers "$iface" 127.0.0.1 2>/dev/null
        done
      else
        echo "$(date): ctrld failed to recover — DHCP DNS remains active" >> "$LOG"
      fi
    fi
  fi
done
