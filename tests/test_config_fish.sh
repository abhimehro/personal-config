#!/usr/bin/env bash
# Simple syntax check for config.fish
set -euo pipefail

# Check if the Fish shell is installed; skip on platforms where it is unavailable (e.g. Linux CI)
command -v fish >/dev/null 2>&1 || { echo "SKIP: fish shell not available"; exit 77; }
# Determine repository root and config path (support both repo and configs path)
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$REPO_ROOT/configs/.config/fish/config.fish"

# Backward-compat fallback (older layout)
if [ ! -f "$CONFIG_FILE" ]; then
  CONFIG_FILE="$REPO_ROOT/configs/fish/config.fish"
fi

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Config file not found: $CONFIG_FILE" >&2
  exit 1
fi

fish --no-execute "$CONFIG_FILE"
