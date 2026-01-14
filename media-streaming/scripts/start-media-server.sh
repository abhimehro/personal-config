#!/bin/bash
set -euo pipefail

echo "🚀 Starting Unified Media WebDAV Server..."
echo

# Load Credentials
CRED_FILE="$HOME/.config/media-server/credentials"

if [[ -f "$CRED_FILE" ]]; then
    source "$CRED_FILE"
fi

# Validate credentials
if [[ -z "${MEDIA_USER:-}" ]] || [[ -z "${MEDIA_PASS:-}" ]]; then
    echo "❌ Missing credentials!"
    echo "Please create $CRED_FILE with MEDIA_USER and MEDIA_PASS"
    echo "Example template available in media-streaming/configs/media-credentials.example"
    echo "Or set MEDIA_USER and MEDIA_PASS environment variables."
    exit 1
fi

# Check if union remote exists
if ! command -v rclone >/dev/null 2>&1; then
    echo "❌ rclone not found. Please install rclone."
    exit 1
fi

if ! rclone listremotes | grep -q "^media:$"; then
    echo "❌ 'media' remote not found. Please run setup-media-library.sh first."
    exit 1
fi

echo "📡 Starting WebDAV server on port 8088..."
echo "🎬 Add this to Infuse:"
echo "   Protocol: WebDAV"
echo "   Address: http://HOST_IP:8088"
echo "   Username: $MEDIA_USER"
echo "   Password: (hidden)"
echo "   Path: /"
echo
echo "Press Ctrl+C to stop server"
echo

rclone serve webdav media: \
    --addr 0.0.0.0:8088 \
    --user "$MEDIA_USER" \
    --pass "$MEDIA_PASS" \
    --dir-cache-time 30m \
    --read-only \
    --verbose
