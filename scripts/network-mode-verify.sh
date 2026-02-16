#!/bin/bash
#
# Network Mode Verification
# Runs tight checks for:
#   - Control D Active state ("controld")
#   - Windscribe Ready state ("windscribe")
# and prints a single PASS/FAIL summary.
#
# USAGE: ./scripts/network-mode-verify.sh {controld|windscribe}

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

LISTENER_IP="127.0.0.1"  # must match LISTENER_IP in network-mode-manager.sh

log()   { echo -e "${BLUE}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
pass()  { echo -e "${GREEN}[PASS]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }

ensure_prereqs_verify() {
  if [[ $EUID -eq 0 ]]; then
    echo -e "${RED}[ERR]${NC} Please run as your normal user; this script will use sudo where needed." >&2
    exit 1
  fi
  command -v networksetup >/dev/null 2>&1 || { echo "networksetup not found" >&2; exit 1; }
  command -v scutil >/dev/null 2>&1 || { echo "scutil not found" >&2; exit 1; }
  command -v dig >/dev/null 2>&1 || { echo "dig not found" >&2; exit 1; }
}

check_controld_active() {
  local expected_profile="${1:-}"
  local ok=0

  echo -e "${BLUE}=== Verifying CONTROL D ACTIVE state ===${NC}"

  # Initialize PIDs to prevent unbound variable errors on cleanup
  local pid_dns="" pid_conn="" pid_who="" pid_aaaa=""

  # Start network checks in background (Parallelization)
  local tmp_who tmp_aaaa
  # 🛡️ Sentinel: Use -t template for macOS compatibility
  tmp_who=$(mktemp -t nmv_who.XXXXXX)
  tmp_aaaa=$(mktemp -t nmv_aaaa.XXXXXX)

  # 3) Basic DNS checks (Background)
  dig @"$LISTENER_IP" example.com +short +time=5 >/dev/null 2>&1 &
  pid_dns=$!

  # 4) Connectivity checks (Background)
  dig @"$LISTENER_IP" p.controld.com +short +time=5 >/dev/null 2>&1 &
  pid_conn=$!

  # 5) whoami checks (Background)
  (dig @"$LISTENER_IP" +short +time=5 whoami.control-d.net 2>/dev/null | head -n1 || true) > "$tmp_who" &
  pid_who=$!

  # 6) IPv6 checks (Background)
  (dig @"$LISTENER_IP" +short +time=5 AAAA example.com 2>/dev/null | head -n1 || true) > "$tmp_aaaa" &
  pid_aaaa=$!

  # Set up cleanup trap for both background processes and temporary files
  trap 'kill ${pid_dns:-} ${pid_conn:-} ${pid_who:-} ${pid_aaaa:-} 2>/dev/null || true; rm -f "${tmp_who:-}" "${tmp_aaaa:-}"' RETURN

  # 1) LaunchDaemon / process (Local Check)
  if sudo launchctl list | grep -q "ctrld"; then
    pass "ctrld LaunchDaemon is loaded (launchctl list | grep ctrld)."
  else
    fail "ctrld LaunchDaemon is NOT loaded."
    ok=1
  fi

  if sudo lsof -nPi :53 2>/dev/null | grep -q "ctrld"; then
    pass "ctrld is bound to port 53 (UDP/TCP)."
  else
    fail "No ctrld listener detected on port 53."
    ok=1
  fi

  # 2) DNS points at local listener (Local Check)
  # On macOS, when ctrld is running, at least one resolver should be 127.0.0.1
  # This is more permissive since resolver ordering can vary
  local dns_check
  dns_check=$(scutil --dns | grep "nameserver" | grep "$LISTENER_IP" || true)
  if [[ -n "$dns_check" ]]; then
    pass "Primary resolver nameserver includes $LISTENER_IP."
  else
    fail "Resolver configuration does not include $LISTENER_IP. Check: scutil --dns"
    ok=1
  fi

  # Collect Background Results

  # 3) Basic DNS
  if wait "$pid_dns"; then
    pass "Basic DNS resolution via Control D (example.com) is working."
  else
    fail "Basic DNS resolution via Control D (example.com) failed."
    ok=1
  fi

  # 4) Connectivity
  if wait "$pid_conn"; then
    pass "Control D connectivity confirmed via p.controld.com."
  else
    fail "Control D connectivity check (p.controld.com) failed."
    ok=1
  fi

  # 4) whoami.control-d.net resolution (soft check)
  wait "$pid_who" || true
  local who
  who=$(cat "$tmp_who")
  # File cleanup handled by trap
  if [[ -n "$who" ]]; then
    pass "whoami.control-d.net resolved to '$who'."
  else
    warn "whoami.control-d.net did not resolve (or timed out). This does not block CONTROL D ACTIVE but indicates a potential dashboard/config issue."
  fi

  # 5) IPv6 AAAA query (soft check – IPv6 optional)
  wait "$pid_aaaa" || true
  local aaaa
  aaaa=$(cat "$tmp_aaaa")
  # File cleanup handled by trap
  if [[ -n "$aaaa" ]]; then
    pass "IPv6 AAAA lookup for example.com returned '$aaaa'."
  else
    warn "IPv6 AAAA lookup for example.com returned no result. IPv6 path may be disabled or unavailable; this is treated as a warning."
  fi

  # 7) Profile & DoH3 checks
  if [[ -n "$expected_profile" ]]; then
    # Try to infer active profile from /etc/controld/ctrld.toml symlink
    local active_profile=""
    local active_config=""
    if [[ -L "/etc/controld/ctrld.toml" ]]; then
      local target
      target=$(readlink "/etc/controld/ctrld.toml" 2>/dev/null || true)
      active_config="$target"
      active_profile=$(basename "$target" | sed "s/^ctrld\.//; s/\.toml$//")
    fi

    if [[ -z "$active_profile" ]]; then
      warn "Unable to determine active Control D profile from /etc/controld/ctrld.toml; profile-aware validation is partial."
    elif [[ "$active_profile" == "$expected_profile" ]]; then
      pass "Active Control D profile matches expected: $expected_profile."
    else
      fail "Active Control D profile is '$active_profile', expected '$expected_profile'."
      ok=1
    fi

    # Enforce DoH3 at config level when we have a readable config file.
    if [[ -n "$active_config" && -f "$active_config" ]]; then
      # ⚡ Bolt Optimization: Use single-pass grep with precise regex to avoid
      # reading file into memory and spawning subshells/pipes.
      # Regex matches lines where type is bare 'doh' or 'doh' followed by a non-'3' character
      # (e.g., "type = 'doh'", "type = 'doh2'", "type = 'doha'"), while excluding "type = 'doh3'".
      if grep -Eq '^[[:space:]]*type = '\''(doh'\''|doh[^3])' "$active_config" 2>/dev/null; then
        fail "Active profile config ($active_config) contains non-DoH3 DoH upstreams (legacy 'doh' or variants like 'doh2')."
        ok=1
      elif grep -Eq '^[[:space:]]*type = '\''doh3'\''' "$active_config" 2>/dev/null; then
        pass "Active profile config ($active_config) uses DoH3-only upstreams."
      else
        warn "Could not find any upstream type=\"doh*\" entries in $active_config; DoH3 validation is partial."
      fi
    else
      warn "Active Control D config file could not be read; skipping DoH3 validation."
    fi
  else
    warn "No profile hint provided; skipping profile-specific and DoH3 validation."
  fi

  local result
  if [[ $ok -eq 0 ]]; then
    echo -e "${GREEN}=== CONTROL D ACTIVE verification: PASSED ===${NC}"
    result="PASS"
  else
    echo -e "${RED}=== CONTROL D ACTIVE verification: FAILED ===${NC}"
    result="FAIL"
  fi
  # Machine-friendly one-line summary for logging/automation
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "SUMMARY TS=${ts} MODE=controld RESULT=${result}"
  return $ok
}

check_windscribe_ready() {
  local ok=0

  echo -e "${BLUE}=== Verifying WINDSCRIBE READY state ===${NC}"

  # 1) No ctrld LaunchDaemon / process
  if sudo launchctl list | grep -q "ctrld"; then
    fail "ctrld LaunchDaemon is still loaded (launchctl list | grep ctrld)."
    ok=1
  else
    pass "No ctrld LaunchDaemon loaded."
  fi

  if sudo lsof -nPi :53 2>/dev/null | grep -q "ctrld"; then
    fail "ctrld is still bound to port 53."
    ok=1
  else
    pass "No ctrld listener on port 53 (port is free)."
  fi

  # 2) DNS no longer points to local listener
  local ns
  ns=$(scutil --dns | awk '/^resolver #1/{f=1} f && /nameserver\[0\]/{print $3; exit}' || true)
  if [[ "$ns" == "$LISTENER_IP" ]]; then
    fail "Primary resolver nameserver is still $LISTENER_IP; expected DHCP/VPN-provided DNS."
    ok=1
  else
    pass "Primary resolver nameserver is '$ns' (not $LISTENER_IP)."
  fi

  # 3) IPv6 should be disabled for Wi‑Fi
  local ipv6_line
  ipv6_line=$(networksetup -getinfo "Wi-Fi" 2>/dev/null | grep "IPv6:" || true)
  if echo "$ipv6_line" | grep -q "Off"; then
    pass "IPv6 reported as Off for Wi‑Fi ($ipv6_line)."
  else
    fail "IPv6 does not appear to be Off for Wi‑Fi (line: '$ipv6_line')."
    ok=1
  fi

  warn "Windscribe DNS (ROBERT/custom) behavior must be validated after connecting the VPN client."

  local result
  if [[ $ok -eq 0 ]]; then
    echo -e "${GREEN}=== WINDSCRIBE READY verification: PASSED ===${NC}"
    result="PASS"
  else
    echo -e "${RED}=== WINDSCRIBE READY verification: FAILED ===${NC}"
    result="FAIL"
  fi
  # Machine-friendly one-line summary for logging/automation
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "SUMMARY TS=${ts} MODE=windscribe RESULT=${result}"
  return $ok
}

main() {
  ensure_prereqs_verify

  local mode="${1:-}"
  local profile_hint="${2:-}"

  if [[ -n "$profile_hint" ]]; then
    log "Profile hint for verification: $profile_hint"
  fi

  case "$mode" in
    controld)
      check_controld_active "$profile_hint"
      ;;
    windscribe)
      check_windscribe_ready
      ;;
    *)
      echo "Usage: $0 {controld|windscribe} [profile]" >&2
      exit 1
      ;;
  esac
}

main "$@"
