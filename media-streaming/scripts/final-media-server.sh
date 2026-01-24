#!/bin/bash

echo "🔧 Final Media Server - Rclone WebDAV (1Password Integrated)"
echo "============================================================"
echo

# Kill any existing servers
echo "🧹 Cleaning up existing servers..."
pkill -f "rclone serve" 2>/dev/null
pkill -f "infuse-media-server.py" 2>/dev/null
pkill -f "python.*media.*server" 2>/dev/null
sleep 2

# Network discovery
echo "🔍 Network Discovery:"
DEFAULT_INTERFACE=$(route get default | grep interface | awk '{print $2}')
echo "   Default Interface: $DEFAULT_INTERFACE"

PRIMARY_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")
echo "   🎯 Using IP: $PRIMARY_IP"
echo

# Find port
echo "🔌 Finding available port..."
AVAILABLE_PORT=8080
for port in 8080 8081 8082 8083; do
    if ! lsof -nP -i:$port | grep -q LISTEN; then
        AVAILABLE_PORT=$port
        break
    fi
done
echo "   ✅ Using Port: $AVAILABLE_PORT"

# Check rclone
echo "📡 Checking rclone configuration..."
if ! rclone listremotes | grep -q "media:"; then
    echo "❌ Error: 'media:' remote not found"
    exit 1
fi

echo

# 🔐 Authentication Setup (1Password)
echo "🔐 Configuring Authentication..."
if ! command -v op &>/dev/null; then
    echo "   ❌ 'op' CLI not found. Please install 1Password CLI."
    exit 1
fi

# Attempt to fetch credentials.
echo "   Reading credentials from 1Password (Item: 'MediaServer')..."
# Try to read 'username' and 'password' from item 'MediaServer' in 'Personal' vault
WEB_USER=$(op read "op://Personal/MediaServer/username" 2>/dev/null) || WEB_USER=""
WEB_PASS=$(op read "op://Personal/MediaServer/password" 2>/dev/null) || WEB_PASS=""

if [[ -z "$WEB_USER" || -z "$WEB_PASS" ]]; then
    echo "   ⚠️  Could not retrieve 'MediaServer' credentials from 1Password."
    echo "   ⚠️  Falling back to generated credentials for this session."
    echo "   Action: Create an item 'MediaServer' in your 'Private' vault with 'username' and 'password' fields."

    WEB_USER="admin"
    WEB_PASS=$(openssl rand -base64 12)
    echo "   👤 Temp User: $WEB_USER"
    echo "   🔑 Temp Pass: $WEB_PASS"
else
    echo "   ✅ Credentials loaded from 1Password"
fi

echo "🚀 Starting Rclone WebDAV Server..."
echo "   Command: rclone serve webdav media: --addr 0.0.0.0:$AVAILABLE_PORT --user <hidden> --pass <hidden>"

# Start Rclone WebDAV
# --addr 0.0.0.0:$PORT binds to ALL interfaces (VPN, LAN, Localhost)
# --vfs-cache-mode full is CRITICAL for streaming reliability with Infuse
nohup rclone serve webdav "media:" \
    --addr "0.0.0.0:$AVAILABLE_PORT" \
    --user "$WEB_USER" \
    --pass "$WEB_PASS" \
    --vfs-cache-mode full \
    --read-only \
    --no-modtime \
    > ~/Library/Logs/media-server.log 2>&1 &

SERVER_PID=$!
echo "   PID: $SERVER_PID"
sleep 5

# Validation
if ps -p $SERVER_PID > /dev/null; then
    echo "   ✅ Server is RUNNING"
else
    echo "   ❌ Server FAILED to start. Check logs:"
    cat ~/Library/Logs/media-server.log
    exit 1
fi

echo
echo "🎬 INFUSE CONFIGURATION:"
echo "========================"
echo "Protocol: WebDAV (HTTPS/HTTP)"
echo "Username: $WEB_USER"
echo "Password: (As set in 1Password)"
echo
echo "--- OPTION 1: LAN / Home (Best Performance) ---"
echo "Address:  $PRIMARY_IP"
echo "Port:     $AVAILABLE_PORT"
echo
echo "--- OPTION 2: External / VPN (Universal) ---"
echo "Address:  82.21.151.194"
echo "Port:     22650  (Forwards to local $AVAILABLE_PORT)"
echo "Note: Ensure your router/VPN forwards 22650 -> $PRIMARY_IP:$AVAILABLE_PORT"
echo
echo "📱 Recommendation: Create ONE entry using the LAN address if possible (better speed)."
echo "   If you travel, create a second entry using the External address."
echo
echo "This server is now running in the background."
echo "Logs: ~/Library/Logs/media-server.log"
