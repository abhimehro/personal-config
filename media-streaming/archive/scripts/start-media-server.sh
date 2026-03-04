#!/bin/bash
# Credential file format: shell-quoted assignment (KEY='value')
# Example:
#   MEDIA_WEBDAV_USER='infuse'
#   MEDIA_WEBDAV_PASS='generated-secret'
# Consumers: strip surrounding single quotes when parsing values
#   raw=$(grep '^KEY=' file | cut -d'=' -f2-)
#   [[ $raw == \'*\' ]] && value=${raw:1:-1} || value=$raw
#   (tr -d "'" also works but removes embedded quotes; prefer the form above)
# See: start-media-server-fast.sh (generates this format)
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "WARNING: start-media-server.sh is deprecated."
echo "Use start-media-server-fast.sh instead."

echo "Delegating to start-media-server-fast.sh..."
exec "$SCRIPT_DIR/start-media-server-fast.sh" "$@"
