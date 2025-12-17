#!/usr/bin/env bash
set -Eeuo pipefail

# Smart connect helper for Cursor host entries.
# Tries the most reliable host first and falls back.

hosts=("cursor-mdns" "cursor-local" "cursor-auto" "cursor-vpn")

for h in "${hosts[@]}"; do
  if ssh -G "$h" >/dev/null 2>&1; then
    exec ssh "$h" "$@"
  fi
done

echo "ERROR: No Cursor SSH hosts found (expected one of: ${hosts[*]})." >&2
exit 1
