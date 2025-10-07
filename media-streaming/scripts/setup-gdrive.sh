#!/bin/bash
echo "🚀 Setting up Google Drive for rclone..."
echo
echo "This will open your browser to authorize Google Drive access."
echo "Please:"
echo "1. Sign in to your Google account"
echo "2. Grant rclone permission to access your Google Drive"
echo "3. Come back here when done"
echo
read -p "Press Enter to continue..."

# Run rclone config for Google Drive
rclone config create gdrive drive config_is_local false