# Minimal Zsh compatibility shim
export PATH="$HOME/.local/bin:$PATH"

# Emergency DNS recovery function for Control D
# Force-kills ctrld, clears static DNS entries on ALL interfaces, and flushes DNS cache
# Uses dynamic interface detection to work with any network configuration
fix-dns() {
  sudo pkill -9 -f -- "ctrld run" 2>/dev/null
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

# Octopus CLI
export PATH="/Users/speedybee/.octopus/bin:$PATH"

# ============================================
# Proton Pass SSH Agent (auto-select when alive)
# ============================================
# Prefer the Proton Pass SSH agent socket when the agent is actually
# responding; otherwise keep the platform / 1Password default.
# - Dead-socket safe: only claims the socket if `ssh-add -l` answers
#   (exit 0 = keys loaded, exit 1 = agent alive with no identities).
# - Skipped for agent/CI contexts (CURSOR_AGENT, CI, GITHUB_ACTIONS)
#   and when PROTON_AGENT_SKIP=1, matching the 1Password gating pattern.
if [ "${PROTON_AGENT_SKIP:-}" != "1" ] && [ -z "${CURSOR_AGENT:-}" ] && [ -z "${CI:-}" ] && [ -z "${GITHUB_ACTIONS:-}" ] && [ -S "${HOME}/.ssh/proton-pass-ssh-agent.sock" ]; then
  _PROTON_SOCK="${HOME}/.ssh/proton-pass-ssh-agent.sock"
  SSH_AUTH_SOCK="$_PROTON_SOCK" ssh-add -l >/dev/null 2>&1
  _PROTON_PROBE=$?
  if [ "$_PROTON_PROBE" -eq 0 ] || [ "$_PROTON_PROBE" -eq 1 ]; then
    export SSH_AUTH_SOCK="$_PROTON_SOCK"
  fi
  unset _PROTON_SOCK _PROTON_PROBE
fi
