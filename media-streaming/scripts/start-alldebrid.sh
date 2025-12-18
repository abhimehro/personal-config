#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOUNT_DIR="${ALD_MOUNT_DIR:-$HOME/mnt/alldebrid}"
mkdir -p "$MOUNT_DIR"

echo "🚀 Starting Alldebrid + Infuse Setup..."

# Check if already mounted
if mount | grep -q "alldebrid:links"; then
    echo "✅ Rclone already mounted"
else
    echo "📁 Mounting Alldebrid via rclone..."
    rclone mount alldebrid:links "$MOUNT_DIR" \
        --dir-cache-time 10s \
        --multi-thread-streams=0 \
        --cutoff-mode=cautious \
        --vfs-cache-mode minimal \
        --buffer-size=0 \
        --read-only \
        --daemon

    # Wait a moment for mount to be ready
    sleep 3

    if mount | grep -q "alldebrid:links"; then
        echo "✅ Rclone mounted successfully"
    else
        echo "❌ Failed to mount rclone"
        exit 1
    fi
fi

echo "🌐 Starting HTTP server for Infuse..."
echo "🎬 Once started, add this to Infuse:"
echo "   Server: http://$(ipconfig getifaddr en0):8080"
echo "   (or http://localhost:8080 for local testing)"
echo ""
echo "Note: Basic Authentication is now enabled. Check the output for credentials."
echo "Note: Default binding is now localhost. Use --public for LAN access."
echo ""

# By default, run securely on localhost.
# Users should uncomment the --public line or pass it manually if they need LAN access for Infuse.
# Or, check if an environment variable is set to enable public access.
if [ "$ENABLE_PUBLIC_ACCESS" = "true" ]; then
    echo "⚠️  Public access enabled (LAN)."
    python3 "$SCRIPT_DIR/alldebrid-server.py" 8080 --public
else
    echo "🔒 Running on localhost only. To enable LAN access for Infuse, run:"
    echo "   ENABLE_PUBLIC_ACCESS=true ./start-alldebrid.sh"
    echo "   OR edit this script to add --public"
    python3 "$SCRIPT_DIR/alldebrid-server.py" 8080
fi
