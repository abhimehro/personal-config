#!/bin/bash

echo "🛑 Stopping Alldebrid setup..."

# Kill HTTP server if running
if pgrep -f "alldebrid-server.py" > /dev/null; then
    echo "🌐 Stopping HTTP server..."
    pkill -f "alldebrid-server.py"
fi

# Unmount rclone
if mount | grep -q "alldebrid:links"; then
    echo "📁 Unmounting rclone..."
    umount ~/mnt/alldebrid
    if [ $? -eq 0 ]; then
        echo "✅ Unmounted successfully"
    else
        echo "⚠️  Force unmounting..."
        umount -f ~/mnt/alldebrid
    fi
else
    echo "ℹ️  Rclone not mounted"
fi

echo "✅ Cleanup complete"
