#!/bin/bash
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
echo "   Address: http://192.168.0.199:8088"
echo "   Username: infuse"
echo "   Password: mediaserver123"
echo "   Path: /"
echo
echo "Press Ctrl+C to stop server"
echo

rclone serve webdav media: \
    --addr 0.0.0.0:8088 \
    --user infuse \
    --pass mediaserver123 \
    --dir-cache-time 30m \
    --read-only \
    --verbose
