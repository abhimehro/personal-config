# Minimal Zsh compatibility shim
export PATH="$HOME/.local/bin:$PATH"

# Emergency DNS recovery function for Control D
# Force-kills ctrld, clears static DNS entries on ALL interfaces, and flushes DNS cache
# Uses dynamic interface detection to work with any network configuration
fix-dns() {
  sudo pkill -9 -f "ctrld run" 2>/dev/null
  sudo launchctl unload /Library/LaunchDaemons/ctrld.plist 2>/dev/null
  # Dynamically get all network services and clear DNS on each
  networksetup -listallnetworkservices | tail -n +2 | awk '{print $NF}' | while read -r iface; do
    [[ -n "$iface" ]] && sudo networksetup -setdnsservers "$iface" Empty 2>/dev/null
  done
  sudo dscacheutil -flushcache
  sudo killall -HUP mDNSResponder
  echo "DNS restored to DHCP on all interfaces"
}
alias fix-dns='fix-dns'
