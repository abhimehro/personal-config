#!/usr/bin/env bash
set -euo pipefail

# Install Control D configuration from repo to /etc/controld/ctrld.toml
# Requires: sudo, env CTRLD_PROFILE_ID

if [ -z "${CTRLD_PROFILE_ID:-}" ]; then
  echo "Error: CTRLD_PROFILE_ID environment variable is not set." >&2
  echo "Set it, e.g.: export CTRLD_PROFILE_ID=xxxxxxxxxx" >&2
  exit 1
fi

SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$SRC_DIR/configs/ctrld-enhanced-split-dns.toml"
DEST_DIR="/etc/controld"
DEST_FILE="$DEST_DIR/ctrld.toml"

if ! sudo -n true 2>/dev/null; then
  echo "This script requires sudo privileges." >&2
  exit 1
fi

tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT

# Substitute environment variables into template safely
envsubst < "$TEMPLATE" > "$tmpfile"

sudo mkdir -p "$DEST_DIR"
if [ -f "$DEST_FILE" ]; then
  sudo cp "$DEST_FILE" "$DEST_FILE.bak.$(date +%Y%m%d_%H%M%S)"
fi
sudo install -m 0644 "$tmpfile" "$DEST_FILE"

echo "Installed Control D configuration to $DEST_FILE"
