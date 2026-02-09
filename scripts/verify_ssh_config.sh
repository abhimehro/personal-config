#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- UX Helpers ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

E_OK="✅"
E_ERR="❌"
E_WARN="⚠️"

header() { echo -e "\n${BOLD}${BLUE}=== $* ===${NC}"; }
ok()     { echo -e "${GREEN}${E_OK} [OK]${NC}    $*"; }
warn()   { echo -e "${YELLOW}${E_WARN} [WARN]${NC}  $*"; }
err()    { echo -e "${RED}${E_ERR} [ERR]${NC}   $*"; }

# --- Configs ---
expected_config="$REPO_ROOT/configs/ssh/config"
expected_agent="$REPO_ROOT/configs/ssh/agent.toml"
control_dir="$HOME/.ssh/control"
op_sock="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"

fail=0

echo -e "${BOLD}SSH Configuration Verification${NC}"

header "Symlinks"
if [ -L "$HOME/.ssh/config" ] && [ "$(readlink "$HOME/.ssh/config")" = "$expected_config" ]; then
  ok "~/.ssh/config -> $expected_config"
else
  err "~/.ssh/config is missing or not pointing to $expected_config"
  fail=1
fi

if [ -L "$HOME/.ssh/agent.toml" ] && [ "$(readlink "$HOME/.ssh/agent.toml")" = "$expected_agent" ]; then
  ok "~/.ssh/agent.toml -> $expected_agent"
else
  err "~/.ssh/agent.toml is missing or not pointing to $expected_agent"
  fail=1
fi

header "Control Directory"
if [ -d "$control_dir" ]; then
  perms=$(stat -f %Mp%Lp "$control_dir")
  if [ "$perms" = "700" ]; then
    ok "~/.ssh/control exists with perms 700"
  else
    warn "~/.ssh/control perms are $perms (fixing to 700)"
    chmod 700 "$control_dir" || true
  fi
else
  err "~/.ssh/control does not exist"
  fail=1
fi

header "1Password Agent"
if [ -S "$op_sock" ]; then
  ok "1Password agent socket present"
else
  warn "Socket not found at $op_sock (ensure 1Password is unlocked)"
fi

header "SSH Config Parse"
if ssh -G github.com >/dev/null 2>&1; then
  ok "ssh config parses (ssh -G github.com)"
else
  err "ssh -G github.com failed to parse"
  fail=1
fi

header "SSH Agent Connectivity"
if ssh-add -l >/dev/null 2>&1; then
  ok "ssh-agent reachable and identities present"
else
  rc=$?
  if [ $rc -eq 1 ]; then
    ok "ssh-agent reachable but no identities loaded (normal if unlocked but no keys used yet)"
  else
    err "ssh-agent not reachable (ssh-add -l exit code $rc)"
    fail=1
  fi
fi

echo ""
if [ $fail -eq 0 ]; then
  echo -e "${GREEN}${E_OK} All SSH checks passed.${NC}"
else
  echo -e "${RED}${E_ERR} Some checks failed.${NC}"
fi

exit $fail
