# Minimal Zsh compatibility shim
export PATH="$HOME/.local/bin:$PATH"

# Emergency DNS recovery function for Control D
# Force-kills ctrld, clears static DNS entries on ALL interfaces, and flushes DNS cache
# Uses dynamic interface detection to work with any network configuration
fix-dns() {
  sudo pkill -9 -f "ctrld run" 2>/dev/null
  sudo launchctl unload /Library/LaunchDaemons/ctrld.plist 2>/dev/null
  # Dynamically get all network services and clear DNS on each
  # Uses same pattern as scripts/lib/network-utils.sh
  local services
  services=$(networksetup -listallnetworkservices | grep -v "^An asterisk")
  if [[ -n "$services" ]]; then
    while IFS= read -r iface; do
      [[ -n "$iface" ]] && sudo networksetup -setdnsservers "$iface" Empty 2>/dev/null
    done <<< "$services"
  fi
  sudo dscacheutil -flushcache
  sudo killall -HUP mDNSResponder
  echo "DNS restored to DHCP on all interfaces"
}

# 1Password CLI shell plugins (agent/CI/non-TTY gated inside plugins.sh)
# SECURITY: Do not bypass OP_AGENT_SKIP / CURSOR_AGENT gates in plugins.sh.
if [[ -f "$HOME/.config/op/plugins.sh" ]]; then
  source "$HOME/.config/op/plugins.sh"
fi
