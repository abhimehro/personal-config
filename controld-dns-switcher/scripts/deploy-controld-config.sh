#!/bin/bash

# Control D DNS Configuration Deployment Script
# Deploys the verified working configuration for Control D DNS switching
# 
# Usage: ./deploy-controld-config.sh
# 
# This script configures:
# - Network interface DNS settings to point to Control D
# - PATH configuration for Raycast compatibility
# - Binary symlinks for Apple Silicon
# - DNS cache flush

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    error "This script is designed for macOS only"
    exit 1
fi

# Check for required binaries
REQUIRED_BINARIES=("/usr/local/bin/controld-switcher" "/usr/local/bin/quick-dns-switch")
for binary in "${REQUIRED_BINARIES[@]}"; do
    if [[ ! -f "$binary" ]]; then
        error "Required binary not found: $binary"
        echo "Please ensure Control D is properly installed"
        exit 1
    fi
done

log "Starting Control D DNS configuration deployment..."

# 1. Get active network services
log "Detecting network interfaces..."
NETWORK_SERVICES=$(networksetup -listallnetworkservices | grep -v "^An asterisk" | grep -v "^$")

# Common network service names to configure
SERVICES_TO_CONFIGURE=("USB 10/100/1000 LAN" "Wi-Fi" "Ethernet")

# 2. Configure DNS for each relevant network service
for service in "${SERVICES_TO_CONFIGURE[@]}"; do
    if echo "$NETWORK_SERVICES" | grep -q "^$service$"; then
        log "Configuring DNS for: $service"
        if sudo networksetup -setdnsservers "$service" 127.0.0.1; then
            success "DNS configured for $service"
        else
            warn "Failed to configure DNS for $service (may not be available)"
        fi
    else
        warn "Network service '$service' not found, skipping"
    fi
done

# 3. Create symlink for Apple Silicon compatibility
if [[ $(uname -m) == "arm64" ]]; then
    log "Configuring Apple Silicon compatibility..."
    if [[ -d "/opt/homebrew/bin" ]]; then
        sudo ln -sf /usr/local/bin/controld-switcher /opt/homebrew/bin/controld-switcher
        sudo ln -sf /usr/local/bin/quick-dns-switch /opt/homebrew/bin/quick-dns-switch
        success "Created symlinks in /opt/homebrew/bin"
    else
        warn "/opt/homebrew/bin not found, skipping symlink creation"
    fi
fi

# 4. Update PATH in bash profile
log "Updating PATH configuration..."
BASH_PROFILE="$HOME/.bash_profile"
PATH_EXPORT='export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"'

if ! grep -q "/opt/homebrew/bin:/usr/local/bin" "$BASH_PROFILE" 2>/dev/null; then
    echo "$PATH_EXPORT" >> "$BASH_PROFILE"
    success "Updated PATH in $BASH_PROFILE"
else
    log "PATH already configured in $BASH_PROFILE"
fi

# 5. Flush DNS cache
log "Flushing DNS cache..."
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder 2>/dev/null || true
success "DNS cache flushed"

# 6. Verify Control D service status
log "Verifying Control D service..."
if sudo launchctl list | grep -q "com.controld.ctrld"; then
    success "Control D daemon is running"
else
    error "Control D daemon is not running"
    echo "Please check Control D installation and start the service"
    exit 1
fi

# 7. Test DNS resolution
log "Testing DNS resolution through Control D..."
if dig +short google.com > /dev/null 2>&1; then
    success "DNS resolution working"
else
    error "DNS resolution failed"
    echo "Please check network connectivity and Control D configuration"
    exit 1
fi

# 8. Check if queries are being logged
log "Checking Control D query logging..."
RECENT_LOGS=$(sudo tail -n 10 /var/log/ctrld-switcher/ctrld.log 2>/dev/null | grep -c "QUERY\|REPLY" || echo "0")
if [[ $RECENT_LOGS -gt 0 ]]; then
    success "Control D is processing DNS queries ($RECENT_LOGS recent queries found)"
else
    warn "No recent DNS queries found in logs - this may be normal for a fresh installation"
fi

# 9. Final status check
log "Performing final status check..."
if controld-switcher status > /dev/null 2>&1; then
    CURRENT_PROFILE=$(controld-switcher status 2>/dev/null | grep -o '"profile": "[^"]*"' | cut -d'"' -f4)
    CURRENT_STATUS=$(controld-switcher status 2>/dev/null | grep -o '"status": "[^"]*"' | cut -d'"' -f4)
    
    if [[ "$CURRENT_STATUS" == "active" ]]; then
        success "Control D is active with profile: $CURRENT_PROFILE"
    else
        warn "Control D status: $CURRENT_STATUS"
    fi
else
    warn "Unable to get Control D status (may require sudo)"
fi

echo
success "Control D DNS configuration deployment completed!"
echo
echo "Next steps:"
echo "1. Restart Raycast to pick up PATH changes"
echo "2. Test profile switching: sudo quick-dns-switch gaming"
echo "3. Verify Raycast extension shows 'Connected' status"
echo
echo "For troubleshooting, see: controld-dns-switcher/WORKING_CONFIGURATION.md"

# 10. Offer to test profile switching
read -p "Would you like to test profile switching now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "Testing profile switching..."
    
    echo "Current profile:"
    sudo controld-switcher status | grep profile || true
    
    echo
    log "Switching to gaming profile..."
    sudo quick-dns-switch gaming
    
    echo
    log "Switching back to privacy profile..."
    sudo quick-dns-switch privacy
    
    echo
    success "Profile switching test completed!"
fi

exit 0