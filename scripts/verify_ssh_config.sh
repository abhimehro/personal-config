#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

expected_config="$REPO_ROOT/configs/ssh/config"
expected_agent="$REPO_ROOT/configs/ssh/agent.toml"
control_dir="$HOME/.ssh/control"
op_sock="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"

fail=0

echo "== Symlinks =="
if [ -L "$HOME/.ssh/config" ] && [ "$(readlink "$HOME/.ssh/config")" = "$expected_config" ]; then
  echo "OK: ~/.ssh/config -> $expected_config"
else
  echo "ERROR: ~/.ssh/config is missing or not pointing to $expected_config"
  fail=1
fi

if [ -L "$HOME/.ssh/agent.toml" ] && [ "$(readlink "$HOME/.ssh/agent.toml")" = "$expected_agent" ]; then
  echo "OK: ~/.ssh/agent.toml -> $expected_agent"
else
  echo "ERROR: ~/.ssh/agent.toml is missing or not pointing to $expected_agent"
  fail=1
fi

echo "== Control directory =="
if [ -d "$control_dir" ]; then
  perms=$(stat -f %Mp%Lp "$control_dir")
  if [ "$perms" = "700" ]; then
    echo "OK: ~/.ssh/control exists with perms 700"
  else
    echo "WARN: ~/.ssh/control perms are $perms (fixing to 700)"
    chmod 700 "$control_dir" || true
  fi
else
  echo "ERROR: ~/.ssh/control does not exist"
  fail=1
fi

echo "== 1Password agent socket =="
if [ -S "$op_sock" ]; then
  echo "OK: 1Password agent socket present: $op_sock"
else
  echo "WARN: Socket not found at $op_sock (ensure 1Password is unlocked and SSH agent integration is enabled)"
fi

echo "== SSH config parse =="
if ssh -G github.com >/dev/null 2>&1; then
  echo "OK: ssh config parses (ssh -G github.com)"
else
  echo "ERROR: ssh -G github.com failed to parse"
  fail=1
fi

echo "== ssh-agent connectivity =="
if ssh-add -l >/dev/null 2>&1; then
  echo "OK: ssh-agent reachable and identities present"
else
  rc=$?
  if [ $rc -eq 1 ]; then
    echo "OK: ssh-agent reachable but no identities loaded (may be normal until you approve keys in 1Password)"
  else
    echo "ERROR: ssh-agent not reachable (ssh-add -l exit code $rc)"
    fail=1
  fi
fi

exit $fail
