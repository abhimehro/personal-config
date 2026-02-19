#!/bin/bash
#
# Infuse Connection Diagnostic Script
# Diagnoses issues with unified cloud library connection
#
# Usage: ./scripts/diagnose-infuse-connection.sh

set -Eeuo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()      { echo -e "${BLUE}[INFO]${NC} $*"; }
success()  { echo -e "${GREEN}[OK]${NC} $*"; }
warn()     { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()    { echo -e "${RED}[ERROR]${NC} $*" >&2; }

echo "=========================================="
echo "Infuse Connection Diagnostic"
echo "=========================================="
echo ""

# Check rclone installation
if ! command -v rclone &> /dev/null; then
    error "rclone is not installed"
    echo "Install with: brew install rclone"
    exit 1
fi
success "rclone is installed: $(rclone version | head -1)"

# Check rclone config file
RCLONE_CONFIG="$HOME/.config/rclone/rclone.conf"
if [[ ! -f "$RCLONE_CONFIG" ]]; then
    error "rclone config file not found: $RCLONE_CONFIG"
    echo ""
    echo "This is likely why Infuse can't connect!"
    echo ""
    echo "Your rclone configuration was probably lost during the iCloud → OneDrive migration."
    echo ""
    echo "To fix:"
    echo "1. Run: ./scripts/setup-media-library.sh"
    echo "   OR"
    echo "2. Manually configure: rclone config"
    echo ""
    exit 1
fi
success "rclone config file exists: $RCLONE_CONFIG"

# Check remotes
echo ""
echo "== Checking rclone remotes =="
REMOTES=$(rclone listremotes 2>&1)

if echo "$REMOTES" | grep -q "gdrive:"; then
    success "Google Drive remote (gdrive:) configured"

    # Test connection
    if rclone about gdrive: &>/dev/null; then
        success "Google Drive connection: Working"
        echo "  $(rclone about gdrive: | grep -E 'Total|Used|Free' | head -3)"
    else
        warn "Google Drive connection: Failed (authentication may be expired)"
        echo "  Fix with: rclone config reconnect gdrive:"
    fi
else
    error "Google Drive remote (gdrive:) NOT configured"
fi

if echo "$REMOTES" | grep -q "onedrive:"; then
    success "OneDrive remote (onedrive:) configured"

    # Test connection
    if rclone about onedrive: &>/dev/null; then
        success "OneDrive connection: Working"
        echo "  $(rclone about onedrive: | grep -E 'Total|Used|Free' | head -3)"
    else
        warn "OneDrive connection: Failed (authentication may be expired)"
        echo "  Fix with: rclone config reconnect onedrive:"
    fi
else
    error "OneDrive remote (onedrive:) NOT configured"
fi

if echo "$REMOTES" | grep -q "media:"; then
    success "Unified media remote (media:) configured"

    # Test union remote
    if rclone lsd media: &>/dev/null; then
        success "Unified media remote: Working"
        echo ""
        echo "Available folders:"
        rclone lsd media: 2>/dev/null | head -10 || warn "Could not list folders"
    else
        error "Unified media remote: Failed"
        echo "  This is likely why Infuse can't connect!"
        echo ""
        echo "Possible issues:"
        echo "  1. Union remote misconfigured"
        echo "  2. Upstream remotes (gdrive/onedrive) not working"
        echo "  3. Folder paths don't match"
        echo ""
        echo "Check union config:"
        echo "  rclone config show media"
    fi
else
    error "Unified media remote (media:) NOT configured"
    echo ""
    echo "This is why Infuse can't connect!"
    echo ""
    echo "The 'media' remote is a union that combines:"
    echo "  - gdrive:Media"
    echo "  - onedrive:Media"
    echo ""
    echo "To create it:"
    echo "  1. Run: ./scripts/setup-media-library.sh"
    echo "  2. OR manually: rclone config"
    echo "     - Name: media"
    echo "     - Type: union"
    echo "     - Upstreams: gdrive:Media onedrive:Media"
fi

# Check folder structure
echo ""
echo "== Checking folder structure =="

if echo "$REMOTES" | grep -q "gdrive:"; then
    if rclone lsd gdrive:Media &>/dev/null; then
        success "Google Drive Media folder exists"
        echo "  Folders in gdrive:Media:"
        rclone lsd gdrive:Media 2>/dev/null | head -10 || warn "Could not list folders"
    else
        warn "Google Drive Media folder missing or inaccessible"
        echo "  Create with: rclone mkdir gdrive:Media"
    fi
fi

if echo "$REMOTES" | grep -q "onedrive:"; then
    if rclone lsd onedrive:Media &>/dev/null; then
        success "OneDrive Media folder exists"
        echo "  Folders in onedrive:Media:"
        rclone lsd onedrive:Media 2>/dev/null | head -10 || warn "Could not list folders"
    else
        warn "OneDrive Media folder missing or inaccessible"
        echo "  Create with: rclone mkdir onedrive:Media"
    fi
fi

# Check WebDAV server
echo ""
echo "== Checking WebDAV server =="

CREDS_FILE="$HOME/.config/media-server/credentials"
MEDIA_WEBDAV_USER="infuse"
MEDIA_WEBDAV_PASS=""

if [[ -f "$CREDS_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CREDS_FILE"
fi

if lsof -nP -i:8088 2>/dev/null | grep -q rclone; then
    success "WebDAV server is running on port 8088"
    echo "  Process: $(lsof -nP -i:8088 | grep rclone | head -1)"

    # Test local connection
    if curl -s -u "${MEDIA_WEBDAV_USER}:${MEDIA_WEBDAV_PASS}" http://localhost:8088/ &>/dev/null; then
        success "Local WebDAV connection: Working"
    else
        warn "Local WebDAV connection: Failed"
    fi
else
    error "WebDAV server is NOT running on port 8088"
    echo ""
    echo "To start the server:"
    echo "  ./scripts/start-media-server-fast.sh"
    echo ""
    echo "Or manually:"
    echo "  rclone serve webdav media: --addr 0.0.0.0:8088 --user $MEDIA_WEBDAV_USER --pass \"$MEDIA_WEBDAV_PASS\" --read-only"
fi

# Network information
echo ""
echo "== Network Information =="
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en5 2>/dev/null || echo "unknown")
echo "Local IP: $LOCAL_IP"
echo ""
echo "Infuse Configuration:"
echo "  Protocol: WebDAV"
echo "  Address: http://$LOCAL_IP:8088"
echo "  Username: $MEDIA_WEBDAV_USER"
echo "  Password: ${MEDIA_WEBDAV_PASS:-<set in ~/.config/media-server/credentials>}"
echo "  Path: /"

# Summary
echo ""
echo "=========================================="
echo "Diagnostic Summary"
echo "=========================================="

ISSUES=0

if [[ ! -f "$RCLONE_CONFIG" ]]; then
    ((ISSUES++))
fi

if ! echo "$REMOTES" | grep -q "gdrive:"; then
    ((ISSUES++))
fi

if ! echo "$REMOTES" | grep -q "onedrive:"; then
    ((ISSUES++))
fi

if ! echo "$REMOTES" | grep -q "media:"; then
    ((ISSUES++))
fi

if ! lsof -nP -i:8088 2>/dev/null | grep -q rclone; then
    ((ISSUES++))
fi

if [[ $ISSUES -eq 0 ]]; then
    success "All checks passed! Infuse should be able to connect."
    echo ""
    echo "If Infuse still can't connect:"
    echo "  1. Ensure your device is on the same WiFi network"
    echo "  2. Check firewall settings"
    echo "  3. Try restarting the WebDAV server"
else
    error "Found $ISSUES issue(s) that need to be fixed"
    echo ""
    echo "Next steps:"
    echo "  1. Run: ./scripts/setup-media-library.sh"
    echo "  2. This will guide you through:"
    echo "     - Setting up Google Drive remote"
    echo "     - Setting up OneDrive remote"
    echo "     - Creating folder structure"
    echo "     - Creating unified media remote"
    echo "  3. Then start the server: ./scripts/start-media-server-fast.sh"
fi

echo ""
