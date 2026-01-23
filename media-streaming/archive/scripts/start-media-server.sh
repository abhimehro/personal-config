#!/bin/bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "WARNING: start-media-server.sh is deprecated."
echo "Use start-media-server-fast.sh instead."

echo "Delegating to start-media-server-fast.sh..."
exec "$SCRIPT_DIR/start-media-server-fast.sh" "$@"
