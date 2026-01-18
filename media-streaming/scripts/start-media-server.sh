#!/bin/bash
set -euo pipefail

echo "🚀 Starting Unified Media WebDAV Server..."
echo

# Check if union remote exists
if ! command -v rclone >/dev/null 2>&1; then
	echo "❌ rclone not found. Please install rclone."
	exit 1
fi

if ! rclone listremotes | grep -q "^media:$"; then
	echo "❌ 'media' remote not found. Please run setup-media-library.sh first."
	exit 1
fi

# Load or Generate Credentials
CREDS_FILE="$HOME/.config/media-server/credentials"
MEDIA_WEBDAV_USER="infuse"
MEDIA_WEBDAV_PASS=""

if [[ -f $CREDS_FILE ]]; then
	source "$CREDS_FILE"
fi

if [[ -z $MEDIA_WEBDAV_PASS ]]; then
	echo "⚙️  Generating secure credentials..."
	mkdir -p "$(dirname "$CREDS_FILE")"

	# Generate random password (using openssl or fallback to simpler method)
	if command -v openssl &>/dev/null; then
		MEDIA_WEBDAV_PASS=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9')
	else
		# Fallback for systems without openssl
		MEDIA_WEBDAV_PASS=$(head -c 12 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9')
	fi

	echo "MEDIA_WEBDAV_USER='$MEDIA_WEBDAV_USER'" >"$CREDS_FILE"
	echo "MEDIA_WEBDAV_PASS='$MEDIA_WEBDAV_PASS'" >>"$CREDS_FILE"
	chmod 600 "$CREDS_FILE"
	echo "✅ Credentials saved to $CREDS_FILE"
fi

# Get Local IP for display purposes
HOST_IP=$(ipconfig getifaddr en0 2>/dev/null || ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "HOST_IP")

echo "📡 Starting WebDAV server on port 8088..."
echo "🎬 Add this to Infuse:"
echo "   Protocol: WebDAV"
echo "   Address: http://$HOST_IP:8088"
echo "   Username: $MEDIA_WEBDAV_USER"
echo "   Password: $MEDIA_WEBDAV_PASS"
echo "   Path: /"
echo
echo "Press Ctrl+C to stop server"
echo

# Bind to 0.0.0.0 so it is accessible on LAN, but now protected by strong password
rclone serve webdav media: \
	--addr 0.0.0.0:8088 \
	--user "$MEDIA_WEBDAV_USER" \
	--pass "$MEDIA_WEBDAV_PASS" \
	--dir-cache-time 30m \
	--read-only \
	--verbose
