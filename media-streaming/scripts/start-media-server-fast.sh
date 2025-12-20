#!/bin/bash
#
# High-Performance Media Server (Longer Cache)
# Use this when VPN is OFF for best performance at home
#

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${BLUE}ℹ️  [INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}✅ [OK]${NC}    $*"; }

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 High-Performance Local Media Server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Stop existing servers
pkill -f "rclone serve webdav" 2>/dev/null || true

# Load credentials
CREDS_FILE="$HOME/.config/media-server/credentials"
if [[ -f "$CREDS_FILE" ]]; then
    source "$CREDS_FILE"
else
    echo "❌ Credentials not found!"
    exit 1
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
