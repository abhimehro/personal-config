#!/usr/bin/env bash
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "🚀 Installing Control D DNS switching solution..."

# Stop old scripts and services
sudo pkill -f dns-gaming || true
sudo pkill -f dns-privacy || true
sudo launchctl bootout system/com.controld.ctrld || true

# Install final working scripts
sudo tee /usr/local/bin/dns-privacy > /dev/null << 'PRIVACY_EOF'
#!/usr/bin/env bash
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "🔒 Switching to privacy profile..."

# Check for port conflicts (exclude ctrld itself)
conflicts=$(sudo lsof -nP -iUDP:53 -iTCP:53 2>/dev/null | grep -v ctrld | grep -v COMMAND || true)
if [[ -n "$conflicts" ]]; then
    log "❌ Port 53 conflicts detected:"
    echo "$conflicts"
    log "Stop conflicting services first"
    exit 1
fi

# Stop current service
sudo launchctl bootout system/com.controld.ctrld 2>/dev/null || true
sleep 1

# Create privacy profile service
sudo tee /Library/LaunchDaemons/com.controld.ctrld.plist > /dev/null << 'PLIST_EOF'
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
        <string>2eoeqoo9ib9</string>
        <string>--listen</string>
        <string>127.0.0.1:53</string>
        <string>--primary_upstream</string>
        <string>https://dns.controld.com/2eoeqoo9ib9</string>
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
PLIST_EOF

# Start service
sudo launchctl bootstrap system /Library/LaunchDaemons/com.controld.ctrld.plist

# Wait and verify
for i in {1..10}; do
    if sudo lsof -nP -iUDP:53 | grep -q ctrld; then
        break
    fi
    sleep 1
done

# Set system DNS
sudo networksetup -setdnsservers "Wi-Fi" "127.0.0.1" 2>/dev/null || \
sudo networksetup -setdnsservers "USB 10/100/1000 LAN" "127.0.0.1" 2>/dev/null || \
log "⚠️  Could not set DNS automatically - set manually to 127.0.0.1"

# Flush DNS
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder

# Test
if dig +short +timeout=3 example.com @127.0.0.1 >/dev/null 2>&1; then
    log "✅ Privacy profile active"
else
    log "❌ DNS test failed"
    exit 1
fi
PRIVACY_EOF

# Create gaming script
sudo tee /usr/local/bin/dns-gaming > /dev/null << 'GAMING_EOF'
#!/usr/bin/env bash
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "🎮 Switching to gaming profile..."

# Check for port conflicts (exclude ctrld itself)
conflicts=$(sudo lsof -nP -iUDP:53 -iTCP:53 2>/dev/null | grep -v ctrld | grep -v COMMAND || true)
if [[ -n "$conflicts" ]]; then
    log "❌ Port 53 conflicts detected:"
    echo "$conflicts"
    log "Stop conflicting services first or use dns-gaming-vpn"
    exit 1
fi

# Stop current service
sudo launchctl bootout system/com.controld.ctrld 2>/dev/null || true
sleep 1

# Create gaming profile service
sudo tee /Library/LaunchDaemons/com.controld.ctrld.plist > /dev/null << 'PLIST_EOF'
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
PLIST_EOF

# Start service
sudo launchctl bootstrap system /Library/LaunchDaemons/com.controld.ctrld.plist

# Wait and verify
for i in {1..10}; do
    if sudo lsof -nP -iUDP:53 | grep -q ctrld; then
        break
    fi
    sleep 1
done

# Set system DNS
sudo networksetup -setdnsservers "Wi-Fi" "127.0.0.1" 2>/dev/null || \
sudo networksetup -setdnsservers "USB 10/100/1000 LAN" "127.0.0.1" 2>/dev/null || \
log "⚠️  Could not set DNS automatically - set manually to 127.0.0.1"

# Flush DNS
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder

# Test
if dig +short +timeout=3 example.com @127.0.0.1 >/dev/null 2>&1; then
    log "✅ Gaming profile active"
else
    log "❌ DNS test failed"
    exit 1
fi
GAMING_EOF

# Create VPN gaming mode
sudo tee /usr/local/bin/dns-gaming-vpn > /dev/null << 'VPN_EOF'
#!/usr/bin/env bash
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "🎮 Switching to gaming VPN mode..."

# Stop ctrld to free port 53
sudo launchctl bootout system/com.controld.ctrld 2>/dev/null || true
sleep 1

# Reset DNS to automatic (lets VPN manage)
sudo networksetup -setdnsservers "Wi-Fi" "Empty" 2>/dev/null || \
sudo networksetup -setdnsservers "USB 10/100/1000 LAN" "Empty" 2>/dev/null || \
log "⚠️  Could not reset DNS automatically"

# Flush DNS
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder

# Test DNS works
if dig +short +timeout=3 example.com @8.8.8.8 >/dev/null 2>&1; then
    log "✅ Gaming VPN mode active - DNS managed by system/VPN"
    log "    Enable your VPN now for optimal gaming"
else
    log "❌ DNS test failed"
    exit 1
fi
VPN_EOF

# Make scripts executable
sudo chmod +x /usr/local/bin/dns-privacy /usr/local/bin/dns-gaming /usr/local/bin/dns-gaming-vpn

# Start privacy mode by default
log "🔧 Starting in privacy mode..."
sudo /usr/local/bin/dns-privacy

log "✅ Installation complete!"
log ""
log "Available commands:"
log "  sudo dns-privacy      - Privacy browsing (blocks ads/trackers)"
log "  sudo dns-gaming       - Gaming profile (low latency)"  
log "  sudo dns-gaming-vpn   - Gaming with VPN (stops ctrld, uses VPN DNS)"
log ""
log "Current status:"
sudo lsof -nP -iUDP:53 2>/dev/null | grep ctrld || log "  No ctrld service running"
dig +short example.com 2>/dev/null | head -1 || log "  DNS test failed"
