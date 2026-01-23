#!/bin/bash

echo "🔥 VPN-Compatible Media Server"
echo "=============================="
echo

# Get real network interfaces (not VPN)
WIFI_IP=$(ipconfig getifaddr en0 2>/dev/null)
ETHERNET_IP=$(ipconfig getifaddr en1 2>/dev/null)

echo "📡 Network Interfaces:"
echo "   WiFi (en0): ${WIFI_IP:-Not connected}"
echo "   Ethernet (en1): ${ETHERNET_IP:-Not connected}"
echo

# Choose the best interface
if [[ -n "$WIFI_IP" ]]; then
    BIND_IP="$WIFI_IP"
    INTERFACE="WiFi (en0)"
elif [[ -n "$ETHERNET_IP" ]]; then
    BIND_IP="$ETHERNET_IP"
    INTERFACE="Ethernet (en1)"
else
    BIND_IP="127.0.0.1"
    INTERFACE="Localhost only"
    echo "⚠️  No network interfaces found, using localhost"
fi

echo "🎯 Binding to: $BIND_IP ($INTERFACE)"
echo

# Kill existing servers
pkill -f "rclone serve webdav" 2>/dev/null

# Check if union remote exists
if ! rclone listremotes | grep -q "^media:$"; then
    echo "❌ 'media' remote not found. Please run setup-media-library.sh first."
    exit 1
fi

# Load credentials consistently with main server
MEDIA_WEBDAV_USER="${MEDIA_WEBDAV_USER:-infuse}"
MEDIA_WEBDAV_PASS="${MEDIA_WEBDAV_PASS:-}"
CREDS_FILE="${MEDIA_CREDENTIALS_FILE:-$HOME/.config/media-server/credentials}"

if [[ -z "$MEDIA_WEBDAV_PASS" ]]; then
  if [[ -f "$CREDS_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CREDS_FILE"
  else
    echo "⚠️  No password configured. Creating credentials file..."
    mkdir -p "$(dirname "$CREDS_FILE")"
    MEDIA_WEBDAV_PASS=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9')
    {
      echo "MEDIA_WEBDAV_USER='${MEDIA_WEBDAV_USER}'"
      echo "MEDIA_WEBDAV_PASS='${MEDIA_WEBDAV_PASS}'"
    } > "$CREDS_FILE"
    chmod 600 "$CREDS_FILE"
    echo "✓ Generated password saved to $CREDS_FILE"
  fi
fi

echo "🌐 Starting WebDAV server..."
echo "📱 Add this to Infuse:"
echo "   Protocol: WebDAV"
echo "   Address: $BIND_IP"
echo "   Port: 8088"
echo "   Username: ${MEDIA_WEBDAV_USER}"
echo "   Password: ${MEDIA_WEBDAV_PASS:-<set in ~/.config/media-server/credentials>}"
echo "   Path: /"
echo

# VPN-specific tips
echo "🔥 VPN TROUBLESHOOTING TIPS:"
echo "1. Enable 'Allow LAN Traffic' in Proton VPN"
echo "2. Add rclone to VPN split tunneling exceptions"
echo "3. Try disconnecting VPN temporarily to test"
echo "4. Use this address in Infuse: http://$BIND_IP:8088"
echo

echo "Press Ctrl+C to stop server"
echo "Starting server on $BIND_IP:8088..."

# Start server bound to specific interface (not 0.0.0.0)
exec rclone serve webdav media: \
    --addr "$BIND_IP:8088" \
    --user "${MEDIA_WEBDAV_USER}" \
    --pass "${MEDIA_WEBDAV_PASS}" \
    --dir-cache-time 30m \
    --read-only \
    --log-level INFO
