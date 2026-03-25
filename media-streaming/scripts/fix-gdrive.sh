#!/bin/bash

echo "🔧 Fixing Google Drive Remote"
echo "=============================="
echo

echo "Current remotes:"
rclone listremotes
echo

echo "Testing current gdrive status..."
if rclone about gdrive: &>/dev/null; then
	echo "✅ gdrive remote is already working!"
	exit 0
else
	echo "❌ gdrive remote needs authentication refresh"
fi

echo
echo "🔐 Attempting to reconnect gdrive remote..."
echo "This will open your browser for Google authorization."
echo
read -p "Press Enter to continue..."

echo "Running: rclone config reconnect gdrive:"
rclone config reconnect gdrive:

echo
echo "Testing connection..."
if rclone about gdrive: &>/dev/null; then
	echo "✅ gdrive remote is now working!"
	echo "📊 Drive info:"
	rclone about gdrive:
else
	echo "❌ Reconnect failed. Let's delete and recreate..."
	echo
	read -p "Delete gdrive remote and start fresh? (y/n): " -n 1 -r
	echo
	if [[ $REPLY =~ ^[Yy]$ ]]; then
		rclone config delete gdrive
		echo "✅ Old gdrive remote deleted"
		echo "Now run: ~/setup-media-library.sh to recreate it"
	fi
fi
