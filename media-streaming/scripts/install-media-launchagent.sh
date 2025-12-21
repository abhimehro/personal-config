#!/bin/bash
#
# Install High-Performance Media Server LaunchAgent
#

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${BLUE}ℹ️  [INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}✅ [OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}⚠️  [WARN]${NC}  $*"; }

PLIST_NAME="com.speedybee.media.webdav.highperformance.plist"
SOURCE_PLIST="$HOME/Documents/dev/personal-config/media-streaming/launchd/$PLIST_NAME"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Installing High-Performance Media Server Agent"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create logs directory
mkdir -p "$HOME/Library/Logs/media"
info "Created logs directory"

# Check if source plist exists
if [[ ! -f "$SOURCE_PLIST" ]]; then
    echo "❌ Source plist not found: $SOURCE_PLIST"
    exit 1
fi

# Unload any existing media server agents
info "Unloading any existing media server agents..."
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.speedybee.media.webdav."*.plist 2>/dev/null || true
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.abhimehrotra.media.webdav."*.plist 2>/dev/null || true

# Wait a moment for clean unload
sleep 2

# Copy plist to LaunchAgents
info "Installing LaunchAgent..."
cp "$SOURCE_PLIST" "$TARGET_PLIST"

# Load the new agent
info "Loading LaunchAgent..."
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"

# Wait a moment for it to start
sleep 3

# Verify it's running
if launchctl list | grep -q "com.speedybee.media.webdav.highperformance"; then
    ok "High-performance media server LaunchAgent installed and running!"
    echo ""
    info "The server will now start automatically on boot"
    info "Optimizations: 2h cache, 128MB buffer, 24h VFS cache"
    echo ""
    info "Logs:"
    echo "   Output: ~/Library/Logs/media/webdav-fast.out"
    echo "   Errors: ~/Library/Logs/media/webdav-fast.err"
    echo ""
    info "Management commands:"
    echo "   Stop:    launchctl bootout gui/\$(id -u) $TARGET_PLIST"
    echo "   Start:   launchctl bootstrap gui/\$(id -u) $TARGET_PLIST"
    echo "   Status:  launchctl list | grep media.webdav"
    echo "   Logs:    tail -f ~/Library/Logs/media/webdav-fast.out"
    echo ""
    info "Verify server is running:"
    echo "   lsof -nP -i:8088 | grep rclone"
else
    warn "LaunchAgent installed but not running. Check logs:"
    echo "   cat ~/Library/Logs/media/webdav-fast.err"
fi
