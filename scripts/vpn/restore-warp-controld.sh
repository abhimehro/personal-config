#!/bin/bash

# ======================================================
# restore-warp-controld.sh
# ======================================================
# This script configures WARP+ with Control D DNS
# with safeguards against connection locking
# ======================================================

# Text formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Configuration values
CONTROL_D_DNS_PRIMARY="76.76.2.22"
CONTROL_D_DNS_SECONDARY="76.76.2.23"
WARP_DAEMON_PLIST="/Library/LaunchDaemons/com.cloudflare.1dot1dot1dot1.macos.warp.daemon.plist"

# Error handling function
handle_error() {
    local exit_code=$1
    local error_message=$2
    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}ERROR: $error_message${NC}"
        exit $exit_code
    fi
}

# Stop WARP daemon and clean up
stop_warp() {
    echo "Stopping WARP services..."
    warp-cli --accept-tos disconnect 2>/dev/null
    sudo launchctl unload "$WARP_DAEMON_PLIST" 2>/dev/null
    pkill -f "CloudflareWARP" 2>/dev/null
    sleep 2
    
    # Double-check and force kill if necessary
    if pgrep -f "CloudflareWARP" > /dev/null; then
        pkill -9 -f "CloudflareWARP" 2>/dev/null
        sleep 1
    fi
}

# Configure WARP daemon for non-locking behavior
configure_daemon() {
    echo "Configuring WARP daemon..."
    cat << EOF | sudo tee "$WARP_DAEMON_PLIST" > /dev/null
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cloudflare.1dot1dot1dot1.macos.warp.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/Cloudflare WARP.app/Contents/Resources/CloudflareWARP</string>
    </array>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
    <key>SoftResourceLimits</key>
    <dict>
        <key>NumberOfFiles</key>
        <integer>1024</integer>
    </dict>
    <key>UserName</key>
    <string>root</string>
</dict>
</plist>
EOF
    sudo chmod 644 "$WARP_DAEMON_PLIST"
    sudo chown root:wheel "$WARP_DAEMON_PLIST"
}

# Configure DNS for all active interfaces
configure_dns() {
    echo "Configuring DNS settings..."
    local success=false
    
    while IFS= read -r service; do
        if [[ "$service" != *"*"* ]] && [[ -n "$service" ]]; then
            if networksetup -setdnsservers "$service" "$CONTROL_D_DNS_PRIMARY" "$CONTROL_D_DNS_SECONDARY"; then
                echo -e "${GREEN}Configured DNS for: $service${NC}"
                success=true
            fi
        fi
    done < <(networksetup -listallnetworkservices)
    
    if [ "$success" = false ]; then
        echo -e "${RED}Failed to configure DNS on any interface${NC}"
        return 1
    fi
    return 0
}

# Main execution
echo -e "${BOLD}${BLUE}=== WARP+ with Control D DNS Configuration ===${NC}"

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Requesting root privileges...${NC}"
    exec sudo "$0" "$@"
    exit $?
fi

# 1. Stop existing WARP services
echo -e "\n${BOLD}Step 1:${NC} Stopping existing WARP services..."
stop_warp

# 2. Configure daemon for non-locking behavior
echo -e "\n${BOLD}Step 2:${NC} Configuring WARP daemon..."
configure_daemon
sudo launchctl load "$WARP_DAEMON_PLIST"
sleep 2

# 3. Configure WARP settings
echo -e "\n${BOLD}Step 3:${NC} Configuring WARP settings..."
warp-cli --accept-tos mode warp+doh
handle_error $? "Failed to set WARP mode"

# Important: Disable always-on to prevent connection locking
warp-cli --accept-tos enable-always-on false
handle_error $? "Failed to disable always-on mode"

# 4. Configure DNS
echo -e "\n${BOLD}Step 4:${NC} Configuring DNS settings..."
configure_dns
handle_error $? "Failed to configure DNS"

# 5. Connect WARP
echo -e "\n${BOLD}Step 5:${NC} Connecting WARP..."
warp-cli --accept-tos connect
sleep 3

# 6. Verify configuration
echo -e "\n${BOLD}Step 6:${NC} Verifying configuration..."
status=$(warp-cli status)
if [[ "$status" == *"Connected"* ]]; then
    echo -e "${GREEN}WARP connected successfully${NC}"
else
    echo -e "${YELLOW}Warning: WARP status - $status${NC}"
fi

echo -e "\n${BOLD}${GREEN}Configuration completed!${NC}"
echo -e "You can now use 'vpn-gaming' to switch to ProtonVPN when needed."
echo -e "The connection will not be locked and can be safely switched."
