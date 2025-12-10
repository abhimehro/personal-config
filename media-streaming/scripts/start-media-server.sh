#!/bin/bash
#
# Unified Media WebDAV Server
# Serves cloud media library to Infuse via WebDAV
#
# Environment variables (optional):
#   MEDIA_WEBDAV_USER        - WebDAV username (default: infuse)
#   MEDIA_WEBDAV_PASS        - WebDAV password (default: from ~/.config/media-server/credentials)
#   MEDIA_CACHE_DIR          - Local cache dir (default: ~/Library/Application Support/MediaCache)
#   MEDIA_CREDENTIALS_FILE   - Override credentials file path
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load credentials
MEDIA_WEBDAV_USER="${MEDIA_WEBDAV_USER:-infuse}"
MEDIA_WEBDAV_PASS="${MEDIA_WEBDAV_PASS:-}"
CREDS_FILE="${MEDIA_CREDENTIALS_FILE:-$HOME/.config/media-server/credentials}"

# If no password set, try to load from credentials file
if [[ -z "$MEDIA_WEBDAV_PASS" ]]; then
    if [[ -f "$CREDS_FILE" ]]; then
        # shellcheck disable=SC1090
        source "$CREDS_FILE"
    else
        echo "⚠️  No password configured. Creating credentials file..."
        mkdir -p "$(dirname "$CREDS_FILE")"
        # Generate a random password (alnum only for easier input)
        MEDIA_WEBDAV_PASS=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9')
        {
          echo "MEDIA_WEBDAV_USER='${MEDIA_WEBDAV_USER}'"
          echo "MEDIA_WEBDAV_PASS='${MEDIA_WEBDAV_PASS}'"
        } > "$CREDS_FILE"
        chmod 600 "$CREDS_FILE"
        echo "✓ Generated password saved to $CREDS_FILE"
    fi
fi

# Cache directory lives outside iCloud to avoid sync churn
CACHE_DIR="${MEDIA_CACHE_DIR:-$HOME/Library/Application Support/MediaCache}"
mkdir -p "$CACHE_DIR"

echo "🚀 Starting Unified Media WebDAV Server..."
echo

# Check if union remote exists
if ! rclone listremotes | grep -q "^media:$"; then
    echo "❌ 'media' remote not found. Please run setup-media-library.sh first."
    exit 1
fi

echo "📡 Starting WebDAV server on port 8088..."
echo "🎬 Add this to Infuse:"
echo "   Protocol: WebDAV"
echo "   Address: http://$(ipconfig getifaddr en0 2>/dev/null || echo 'localhost'):8088"
echo "   Username: $MEDIA_WEBDAV_USER"
echo "   Password: $MEDIA_WEBDAV_PASS"
echo "   Path: /"
echo
echo "Press Ctrl+C to stop server"
echo

# Bind to 0.0.0.0 for access from all devices (macOS, iOS, tvOS)
RCLONE_CACHE_DIR="$CACHE_DIR" \
rclone serve webdav media: \
    --addr 0.0.0.0:8088 \
    --user "$MEDIA_WEBDAV_USER" \
    --pass "$MEDIA_WEBDAV_PASS" \
    --dir-cache-time 30m \
    --poll-interval 1m \
    --vfs-cache-mode minimal \
    --read-only \
    --verbose
