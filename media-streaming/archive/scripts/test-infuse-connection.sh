#!/bin/bash

echo "🔍 Infuse Connection Troubleshooting"
echo "===================================="
echo

# Get network info
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo "📡 Your Mac's IP Address: $LOCAL_IP"
echo

# Load credentials shared with start-media-server-fast.sh
MEDIA_WEBDAV_USER="${MEDIA_WEBDAV_USER:-infuse}"
MEDIA_WEBDAV_PASS="${MEDIA_WEBDAV_PASS-}"
CREDS_FILE="${MEDIA_CREDENTIALS_FILE:-$HOME/.config/media-server/credentials}"

if [[ -z $MEDIA_WEBDAV_PASS && -f $CREDS_FILE ]]; then
	# shellcheck disable=SC1090
	source "$CREDS_FILE"
fi

if [[ -z $MEDIA_WEBDAV_PASS ]]; then
	echo "❌ WebDAV credentials missing."
	echo "   Run: ~/start-media-server-fast.sh to auto-generate credentials."
	exit 1
fi

# Test server status
echo "🖥️  Server Status:"
if lsof -nP -i:8088 | grep -q rclone; then
	echo "✅ rclone server is running on port 8088"
else
	echo "❌ rclone server is NOT running on port 8088"
	echo "   Run: ~/start-media-server-fast.sh"
	exit 1
fi
echo

# Test local connection
echo "🔗 Testing Local Connection:"
if curl -s -u "${MEDIA_WEBDAV_USER}:${MEDIA_WEBDAV_PASS}" http://localhost:8088/ | grep -q "<!DOCTYPE html>"; then
	echo "✅ Local connection works (http://localhost:8088)"
else
	echo "❌ Local connection failed"
fi

# Test network connection
echo
echo "🌐 Testing Network Connection:"
if curl -s -u "${MEDIA_WEBDAV_USER}:${MEDIA_WEBDAV_PASS}" http://$LOCAL_IP:8088/ | grep -q "<!DOCTYPE html>"; then
	echo "✅ Network connection works (http://$LOCAL_IP:8088)"
else
	echo "❌ Network connection failed - likely firewall issue"
fi
echo

# Check firewall
echo "🔥 Firewall Status:"
FIREWALL_STATE=$(sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate | grep State)
echo "$FIREWALL_STATE"

if echo "$FIREWALL_STATE" | grep -q "State = 1"; then
	echo "⚠️  Firewall is enabled - may block connections"
	echo "   Trying to fix..."
	sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/homebrew/bin/rclone --unblockapp /opt/homebrew/bin/rclone
	echo "✅ Added rclone to firewall exceptions"
else
	echo "✅ Firewall is disabled or allowing connections"
fi
echo

# Network diagnostics
echo "📊 Network Diagnostics:"
echo "   WiFi Interface (en0): $(ipconfig getifaddr en0 2>/dev/null || echo 'Not connected')"
echo "   Ethernet (en1): $(ipconfig getifaddr en1 2>/dev/null || echo 'Not connected')"
echo

# Test with different approaches
echo "🧪 Testing Different Connection Methods:"

echo "Method 1: localhost:8088"
curl -s -u "${MEDIA_WEBDAV_USER}:${MEDIA_WEBDAV_PASS}" http://localhost:8088/ -o /dev/null && echo "✅ Works" || echo "❌ Failed"

echo "Method 2: $LOCAL_IP:8088"
curl -s -u "${MEDIA_WEBDAV_USER}:${MEDIA_WEBDAV_PASS}" http://$LOCAL_IP:8088/ -o /dev/null && echo "✅ Works" || echo "❌ Failed"

echo "Method 3: 127.0.0.1:8088"
curl -s -u "${MEDIA_WEBDAV_USER}:${MEDIA_WEBDAV_PASS}" http://127.0.0.1:8088/ -o /dev/null && echo "✅ Works" || echo "❌ Failed"

echo
echo "🎬 INFUSE CONFIGURATION:"
echo "========================"
echo "Protocol: WebDAV"
echo "Address: $LOCAL_IP"
echo "Port: 8088"
echo "Username: ${MEDIA_WEBDAV_USER}"
echo "Password: ${MEDIA_WEBDAV_PASS:-<set in ~/.config/media-server/credentials>}"
echo "Path: /"
echo
echo "💡 TROUBLESHOOTING TIPS:"
echo "- Make sure your Apple device is on the same WiFi network"
echo "- Try using 'localhost' instead of IP if testing on Mac"
echo "- Disable VPN temporarily if having issues"
echo "- Check if Private Relay is blocking connections (iOS/macOS)"
echo

# Alternative port suggestion
echo "🔄 ALTERNATIVE: Try different port (8089):"
echo "pkill -f 'rclone serve'"
echo "rclone serve webdav media: --addr 0.0.0.0:8089 --user ${MEDIA_WEBDAV_USER} --pass ${MEDIA_WEBDAV_PASS} --read-only &"
echo
