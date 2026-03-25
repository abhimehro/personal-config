#!/bin/bash
#
# High-Performance Media Server (Longer Cache)
# Use this when VPN is OFF for best performance at home
#
# Credential file format: shell-quoted assignment (KEY='value')
# Example output written to ~/.config/media-server/credentials:
#   MEDIA_WEBDAV_USER='infuse'
#   MEDIA_WEBDAV_PASS='generated-secret'
# Consumers: strip surrounding single quotes when parsing values
#   raw=$(grep '^KEY=' file | cut -d'=' -f2-)
#   [[ $raw == \'*\' ]] && value=${raw:1:-1} || value=$raw
#   (tr -d "'" also works but removes embedded quotes; prefer the form above)

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ️  [INFO]${NC}  $*"; }
ok() { echo -e "${GREEN}✅ [OK]${NC}    $*"; }

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 High-Performance Local Media Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Stop existing servers
pkill -f "rclone serve webdav" 2>/dev/null || true

# Load or generate credentials
CREDS_FILE="$HOME/.config/media-server/credentials"
MEDIA_WEBDAV_USER="infuse"
MEDIA_WEBDAV_PASS=""

if [[ -f $CREDS_FILE ]]; then
	source "$CREDS_FILE"
fi

if [[ -z $MEDIA_WEBDAV_PASS ]]; then
	echo "⚙️  Generating secure credentials..."
	mkdir -p "$(dirname "$CREDS_FILE")"

	if command -v openssl &>/dev/null; then
		MEDIA_WEBDAV_PASS=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9')
	else
		MEDIA_WEBDAV_PASS=$(head -c 12 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9')
	fi

	echo "MEDIA_WEBDAV_USER='$MEDIA_WEBDAV_USER'" >"$CREDS_FILE"
	echo "MEDIA_WEBDAV_PASS='$MEDIA_WEBDAV_PASS'" >>"$CREDS_FILE"
	chmod 600 "$CREDS_FILE"
	echo "✅ Credentials saved to $CREDS_FILE"
fi

WIFI_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "127.0.0.1")

info "Starting high-performance server..."
ok "Optimized for LOCAL network access"
echo ""
echo "📱 Infuse Configuration:"
echo "   Address: http://$WIFI_IP:8088"
echo "   Username: $MEDIA_WEBDAV_USER"
echo "   Password: $MEDIA_WEBDAV_PASS"
echo ""
info "Press Ctrl+C to stop"
echo ""

# Start with AGGRESSIVE caching for better performance
exec rclone serve webdav media: \
	--addr "0.0.0.0:8088" \
	--user "$MEDIA_WEBDAV_USER" \
	--pass "$MEDIA_WEBDAV_PASS" \
	--dir-cache-time 2h \
	--poll-interval 10m \
	--vfs-cache-mode writes \
	--vfs-cache-max-age 24h \
	--vfs-cache-poll-interval 5m \
	--buffer-size 128M \
	--read-only \
	--log-level INFO
