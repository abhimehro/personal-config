#!/bin/bash

echo "🛑 Stopping Alldebrid setup..."

# Kill HTTP server if running
if pgrep -f "alldebrid-server.py" >/dev/null; then
	echo "🌐 Stopping HTTP server..."
	pkill -f "alldebrid-server.py"
fi

# Unmount rclone
MOUNT_DIR="${ALD_MOUNT_DIR:-$HOME/mnt/alldebrid}"
if mount | grep -q "alldebrid:links"; then
	echo "📁 Unmounting rclone..."
	umount "$MOUNT_DIR"
	if [ $? -eq 0 ]; then
		echo "✅ Unmounted successfully"
	else
		echo "⚠️  Force unmounting..."
		umount -f "$MOUNT_DIR"
	fi
else
	echo "ℹ️  Rclone not mounted"
fi

echo "✅ Cleanup complete"
