#!/usr/bin/env bash
set -Eeuo pipefail

expected_config="$HOME/Documents/dev/personal-config/configs/ssh/config"
expected_agent="$HOME/Documents/dev/personal-config/configs/ssh/agent.toml"
control_dir="$HOME/.ssh/control"
verify="$HOME/Documents/dev/personal-config/scripts/verify_ssh_config.sh"

ensure_link () {
  local link="$1" target="$2" name="$3"
  if [ -L "$link" ] && [ "$(readlink "$link")" = "$target" ]; then
    echo "OK: $name symlink is intact"
    return 0
  fi
  echo "Recreating $name symlink -> $target"
  mkdir -p "$(dirname "$link")"
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    mv -v "$link" "$link.broken.$(date +%Y%m%d_%H%M%S)"
  else
    rm -f "$link"
  fi
  ln -s "$target" "$link"
}

ensure_link "$HOME/.ssh/config" "$expected_config" "~/.ssh/config"
ensure_link "$HOME/.ssh/agent.toml" "$expected_agent" "~/.ssh/agent.toml"

mkdir -p "$control_dir"
chmod 700 "$control_dir"

# Permissions hygiene
chmod 700 "$HOME/.ssh"
chmod 600 "$HOME/.ssh/known_hosts" 2>/dev/null || true
chmod 600 "$HOME/.ssh/known_hosts.old" 2>/dev/null || true

if [ -x "$verify" ]; then
  echo "Running verification..."
  "$verify"
else
  echo "WARN: Verification script not found or not executable: $verify"
fi
