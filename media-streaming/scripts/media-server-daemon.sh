#!/bin/bash
#
# Media Server - Foreground Runner for LaunchAgent
# Keeps rclone running in foreground so LaunchAgent can monitor it
#
set -euo pipefail

# Set PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "🔧 Media Server - Starting..."

# Kill any existing rclone servers
pkill -f "rclone serve" 2>/dev/null || true
sleep 2

# Get network info
PRIMARY_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "unknown")

log "Network: LAN=$PRIMARY_IP, Public=$PUBLIC_IP"

# Find available port
AVAILABLE_PORT=8080
for port in 8080 8081 8082 8083; do
    if ! lsof -nP -i:$port 2>/dev/null | grep -q LISTEN; then
        AVAILABLE_PORT=$port
        break
    fi
done

log "Using port: $AVAILABLE_PORT"

# Check rclone remote
if ! rclone listremotes 2>/dev/null | grep -q "media:"; then
    log "ERROR: 'media:' remote not found"
    exit 1
fi

# Get 1Password credentials
log "Loading credentials from 1Password..."

if ! command -v op &>/dev/null; then
    log "ERROR: 1Password CLI not found"
    exit 1
fi

WEB_USER=$(op read "op://Personal/MediaServer/username" 2>/dev/null) || WEB_USER=""
WEB_PASS=$(op read "op://Personal/MediaServer/password" 2>/dev/null) || WEB_PASS=""

if [[ -z "$WEB_USER" || -z "$WEB_PASS" ]]; then
    log "ERROR: Could not retrieve 1Password credentials"
    log "Please sign into 1Password CLI: op signin"
    exit 1
fi

log "✅ Credentials loaded"
log "🚀 Starting rclone WebDAV server on 0.0.0.0:$AVAILABLE_PORT"
log "   User: $WEB_USER"
log "   LAN Address: $PRIMARY_IP:$AVAILABLE_PORT"

# Start rclone in FOREGROUND (no nohup, no &)
# This keeps the script running so LaunchAgent can monitor it
# 🛡️ Sentinel: Use env vars for credentials to hide them from process list (ps aux)
export RCLONE_USER="$WEB_USER"
export RCLONE_PASS="$WEB_PASS"

exec rclone serve webdav "media:" \
    --addr "0.0.0.0:$AVAILABLE_PORT" \
    --vfs-cache-mode full \
    --vfs-read-chunk-size 32M \
    --vfs-read-chunk-size-limit 2G \
    --transfers 8 \
    --checkers 16 \
    --read-only \
    --no-modtime
