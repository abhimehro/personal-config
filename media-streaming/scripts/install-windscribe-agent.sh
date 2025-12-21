#!/bin/bash
#
# Install Windscribe-compatible media server LaunchAgent
#

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${BLUE}ℹ️  [INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}✅ [OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}⚠️  [WARN]${NC}  $*"; }

PLIST_NAME="com.speedybee.media.webdav.windscribe.plist"
SOURCE_PLIST="$HOME/Documents/dev/personal-config/media-streaming/launchd/$PLIST_NAME"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Installing Windscribe Media Server Agent"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create logs directory
mkdir -p "$HOME/Library/Logs/media"
info "Created logs directory"

# Check if source plist exists
if [[ ! -f "$SOURCE_PLIST" ]]; then
    warn "Source plist not found: $SOURCE_PLIST"
    exit 1
fi

# Unload old agent if it exists
if launchctl list | grep -q "com.speedybee.media.webdav.windscribe"; then
    info "Unloading existing agent..."
    launchctl bootout "gui/$(id -u)" "$TARGET_PLIST" 2>/dev/null || true
fi

# Copy plist to LaunchAgents
info "Installing LaunchAgent..."
cp "$SOURCE_PLIST" "$TARGET_PLIST"

# Load the new agent
info "Loading LaunchAgent..."
launchctl bootstrap "gui/$(id -u)" "$TARGET_PLIST"

# Wait a moment for it to start
sleep 2

# Verify it's running
if launchctl list | grep -q "com.speedybee.media.webdav.windscribe"; then
    ok "Media server LaunchAgent installed and running!"
    echo ""
    info "The server will now start automatically on boot"
    info "Logs: ~/Library/Logs/media/webdav-windscribe.{out,err}"
    echo ""
    info "Management commands:"
    echo "   Stop:    launchctl bootout gui/\$(id -u) $TARGET_PLIST"
    echo "   Start:   launchctl bootstrap gui/\$(id -u) $TARGET_PLIST"
    echo "   Status:  launchctl list | grep media.webdav"
    echo "   Logs:    tail -f ~/Library/Logs/media/webdav-windscribe.out"
else
    warn "LaunchAgent installed but not running. Check logs:"
    echo "   cat ~/Library/Logs/media/webdav-windscribe.err"
fi
