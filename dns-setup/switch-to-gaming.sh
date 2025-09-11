#!/usr/bin/env bash
set -euo pipefail

# Simple gaming profile switch
GAMING_PROFILE="1igcvpwtsfg"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "🎮 Switching to gaming profile..."

# Check if we can bind to port 53
if lsof -nP -iUDP:53 | grep -v ctrld | grep -q .; then
    log "❌ Non-ctrld process on port 53. Cannot switch safely."
    exit 1
fi

# Stop current ctrld
sudo launchctl bootout system/com.controld.ctrld || true

# Create new LaunchDaemon for gaming
sudo tee /Library/LaunchDaemons/com.controld.ctrld.plist > /dev/null << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.controld.ctrld</string>
    <key>UserName</key>
    <string>root</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/ctrld</string>
        <string>run</string>
        <string>--cd</string>
        <string>1igcvpwtsfg</string>
        <string>--listen</string>
        <string>127.0.0.1:53</string>
        <string>--primary_upstream</string>
        <string>https://dns.controld.com/1igcvpwtsfg</string>
        <string>--log</string>
        <string>/var/log/ctrld.log</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/usr/local/var/ctrld</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/ctrld.out.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/ctrld.err.log</string>
</dict>
</plist>
EOF

# Start new service
sudo launchctl bootstrap system /Library/LaunchDaemons/com.controld.ctrld.plist

# Wait and verify
sleep 3
if ! lsof -nP -iUDP:53 | grep -q ctrld; then
    log "❌ Failed to start ctrld on port 53"
    exit 1
fi

# Test DNS
if ! dig +short +timeout=3 example.com @127.0.0.1 >/dev/null; then
    log "❌ DNS test failed"
    exit 1
fi

log "✅ Gaming profile active"
