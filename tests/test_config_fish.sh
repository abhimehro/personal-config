#!/usr/bin/env bash
# Simple syntax check for config.fish
set -euo pipefail

# Check if the Fish shell is installed
if ! command -v fish >/dev/null; then
  echo "Error: Fish shell is not installed or not in PATH." >&2
  exit 1
fi
# Determine repository root and config path
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_FILE="$REPO_ROOT/.config/fish/config.fish"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Config file not found: $CONFIG_FILE" >&2
  exit 1
fi

fish --no-execute "$CONFIG_FILE"
