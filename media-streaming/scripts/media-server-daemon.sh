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

# Get network info — derive LAN IP from the default route interface to avoid VPN/utun addresses
DEFAULT_INTERFACE=$(route get default 2>/dev/null | awk '/interface:/{print $2}' || echo "en0")
PRIMARY_IP=$(ifconfig "$DEFAULT_INTERFACE" 2>/dev/null | awk '/inet / && !/127.0.0.1/ {print $2; exit}')
if [[ -z "$PRIMARY_IP" ]]; then
    PRIMARY_IP="127.0.0.1"
    log "WARNING: Could not detect LAN IP on $DEFAULT_INTERFACE, defaulting to 127.0.0.1"
fi
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
log "🚀 Starting rclone WebDAV server on $PRIMARY_IP:$AVAILABLE_PORT"
log "   User: $WEB_USER"
log "   LAN Address: $PRIMARY_IP:$AVAILABLE_PORT"

# Start rclone in FOREGROUND (no nohup, no &)
# This keeps the script running so LaunchAgent can monitor it
# 🛡️ Sentinel: Pass credentials via env vars scoped to rclone process only (CWE-214)
RCLONE_USER="$WEB_USER" RCLONE_PASS="$WEB_PASS" \
exec rclone serve webdav "media:" \
    --addr "$PRIMARY_IP:$AVAILABLE_PORT" \
    --vfs-cache-mode full \
    --vfs-read-chunk-size 32M \
    --vfs-read-chunk-size-limit 2G \
    --transfers 8 \
    --checkers 16 \
    --read-only \
    --no-modtime
