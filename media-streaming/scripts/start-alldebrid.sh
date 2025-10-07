#!/bin/bash

echo "🚀 Starting Alldebrid + Infuse Setup..."

# Check if already mounted
if mount | grep -q "alldebrid:links"; then
    echo "✅ Rclone already mounted"
else
    echo "📁 Mounting Alldebrid via rclone..."
    rclone mount alldebrid:links ~/mnt/alldebrid \
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
python3 ~/alldebrid-server.py 8080
