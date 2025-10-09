#!/bin/bash

# Control D Service Manager - VPN Compatible Version
# Handles launch daemon conflicts and ensures VPN-compatible DNS binding
# Created: October 2025

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CONTROLD_CONFIG="/etc/controld/ctrld.toml"
LAUNCH_DAEMONS=(
    "/Library/LaunchDaemons/com.controld.dns.plist"
    "/Library/LaunchDaemons/com.controld.dns.monitor.plist" 
    "/Library/LaunchDaemons/ctrld.plist"
)

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script requires root privileges. Please run with sudo."
        exit 1
    fi
}

stop_all_controld_services() {
    print_status "Stopping all Control D services..."
    
    # Kill any running processes
    pkill -f "ctrld" 2>/dev/null
    pkill -f "dns-monitor" 2>/dev/null
    
    # Unload all launch daemons
    for daemon in "${LAUNCH_DAEMONS[@]}"; do
        if [ -f "$daemon" ]; then
            basename_daemon=$(basename "$daemon" .plist)
            print_status "Unloading $basename_daemon..."
            launchctl unload "$daemon" 2>/dev/null
            launchctl remove "$basename_daemon" 2>/dev/null
        fi
    done
    
    # Wait for services to stop
    sleep 2
    
    print_success "All Control D services stopped"
}

backup_launch_daemons() {
    print_status "Backing up existing launch daemons..."
    
    local backup_dir="/Users/abhimehrotra/Documents/dev/personal-config/windscribe-controld/daemon-backups"
    mkdir -p "$backup_dir"
    
    for daemon in "${LAUNCH_DAEMONS[@]}"; do
        if [ -f "$daemon" ]; then
            daemon_name=$(basename "$daemon")
            cp "$daemon" "$backup_dir/${daemon_name}.backup.$(date +%Y%m%d_%H%M%S)"
            print_status "Backed up $daemon_name"
        fi
    done
    
    print_success "Launch daemons backed up to $backup_dir"
}

remove_conflicting_daemons() {
    print_status "Removing conflicting launch daemons..."
    
    for daemon in "${LAUNCH_DAEMONS[@]}"; do
        if [ -f "$daemon" ]; then
            daemon_name=$(basename "$daemon")
            rm "$daemon"
            print_status "Removed $daemon_name"
        fi
    done
    
    print_success "Conflicting launch daemons removed"
}

apply_vpn_binding_fix() {
    local config_file="$1"
    if [[ -f "$config_file" ]]; then
        print_status "Applying VPN-compatible binding to $config_file"
        sed -i '' 's/ip = '\''127\.0\.0\.1'\''/ip = '\''0\.0\.0\.0'\''/g' "$config_file"
        print_success "VPN binding fix applied"
    else
        print_warning "Config file not found: $config_file"
    fi
}

create_vpn_compatible_daemon() {
    print_status "Creating VPN-compatible Control D launch daemon..."
    
    cat > /Library/LaunchDaemons/com.controld.vpn.dns.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.controld.vpn.dns</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/ctrld</string>
        <string>run</string>
        <string>--config</string>
        <string>/etc/controld/ctrld.toml</string>
        <string>--skip_self_checks</string>
        <string>--iface=auto</string>
        <string>--homedir=/etc/controld</string>
    </array>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/var/log/controld.vpn.out.log</string>
    
    <key>StandardErrorPath</key>
    <string>/var/log/controld.vpn.err.log</string>
    
    <key>WorkingDirectory</key>
    <string>/etc/controld</string>
    
    <key>UserName</key>
    <string>root</string>
    
    <key>GroupName</key>
    <string>wheel</string>
    
    <key>ProcessType</key>
    <string>Background</string>
    
    <key>ThrottleInterval</key>
    <integer>10</integer>
    
    <key>AbandonProcessGroup</key>
    <true/>
</dict>
</plist>
EOF

    chmod 644 /Library/LaunchDaemons/com.controld.vpn.dns.plist
    chown root:wheel /Library/LaunchDaemons/com.controld.vpn.dns.plist
    
    print_success "VPN-compatible launch daemon created"
}

start_vpn_compatible_service() {
    print_status "Starting VPN-compatible Control D service..."
    
    # Apply VPN binding fix to current config
    apply_vpn_binding_fix "$CONTROLD_CONFIG"
    
    # Load the VPN-compatible daemon
    launchctl load /Library/LaunchDaemons/com.controld.vpn.dns.plist
    launchctl start com.controld.vpn.dns
    
    # Wait for service to start
    sleep 3
    
    # Verify service is running
    if pgrep -f "ctrld run" > /dev/null; then
        print_success "Control D service started with VPN compatibility"
        return 0
    else
        print_error "Failed to start Control D service"
        return 1
    fi
}

stop_vpn_compatible_service() {
    print_status "Stopping VPN-compatible Control D service..."
    
    launchctl unload /Library/LaunchDaemons/com.controld.vpn.dns.plist 2>/dev/null
    launchctl remove com.controld.vpn.dns 2>/dev/null
    pkill -f "ctrld run" 2>/dev/null
    
    print_success "VPN-compatible Control D service stopped"
}

check_service_status() {
    print_status "Checking Control D service status..."
    
    echo
    echo -e "${BLUE}=== Launch Daemon Status ===${NC}"
    if [ -f "/Library/LaunchDaemons/com.controld.vpn.dns.plist" ]; then
        echo "✅ VPN-compatible daemon: INSTALLED"
    else
        echo "❌ VPN-compatible daemon: NOT FOUND"
    fi
    
    echo
    echo -e "${BLUE}=== Process Status ===${NC}"
    if pgrep -f "ctrld run" > /dev/null; then
        echo "✅ Control D process: RUNNING"
        echo "   PID: $(pgrep -f "ctrld run")"
    else
        echo "❌ Control D process: NOT RUNNING"
    fi
    
    echo
    echo -e "${BLUE}=== DNS Binding Status ===${NC}"
    local dns_binding=$(lsof -nP -iTCP:53 -iUDP:53 2>/dev/null | grep ctrld | head -1)
    if [[ -n "$dns_binding" ]]; then
        echo "✅ DNS service: ACTIVE"
        echo "   $dns_binding"
        
        if echo "$dns_binding" | grep -q "0.0.0.0:53"; then
            echo "✅ VPN compatibility: ENABLED (0.0.0.0:53)"
        elif echo "$dns_binding" | grep -q "127.0.0.1:53"; then
            echo "❌ VPN compatibility: DISABLED (127.0.0.1:53)"
        fi
    else
        echo "❌ DNS service: NOT ACTIVE"
    fi
    
    echo
    echo -e "${BLUE}=== Configuration Status ===${NC}"
    if [ -f "$CONTROLD_CONFIG" ]; then
        local current_profile=$(readlink "$CONTROLD_CONFIG" | grep -o 'ctrld\.[^.]*\.toml' | cut -d'.' -f2)
        echo "✅ Active profile: ${current_profile:-unknown}"
        echo "   Config: $CONTROLD_CONFIG"
    else
        echo "❌ Configuration: NOT FOUND"
    fi
}

cleanup_and_setup() {
    print_status "Performing complete Control D cleanup and VPN-compatible setup..."
    
    stop_all_controld_services
    backup_launch_daemons
    remove_conflicting_daemons
    create_vpn_compatible_daemon
    
    print_success "Cleanup and setup complete!"
    print_warning "Control D service is ready but NOT started."
    print_warning "Use '$0 start' to start with VPN compatibility."
}

test_windscribe_compatibility() {
    print_status "Testing Windscribe + Control D compatibility..."
    
    # Check if Control D is running
    if ! pgrep -f "ctrld run" > /dev/null; then
        print_error "Control D is not running. Start it first with: $0 start"
        return 1
    fi
    
    # Check DNS binding
    local dns_binding=$(lsof -nP -iTCP:53 -iUDP:53 2>/dev/null | grep ctrld)
    if ! echo "$dns_binding" | grep -q "0.0.0.0:53"; then
        print_error "Control D is not using VPN-compatible binding"
        return 1
    fi
    
    print_success "Control D is running with VPN-compatible configuration"
    print_status "You can now connect Windscribe VPN with 'Local DNS' setting"
    
    return 0
}

show_usage() {
    echo "Control D Service Manager - VPN Compatible Version"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  cleanup    - Remove conflicting daemons and setup VPN-compatible service"
    echo "  start      - Start Control D with VPN compatibility"
    echo "  stop       - Stop Control D service"
    echo "  restart    - Restart Control D service"
    echo "  status     - Show detailed service status"
    echo "  test       - Test Windscribe compatibility"
    echo "  logs       - Show recent Control D logs"
    echo
    echo "Examples:"
    echo "  sudo $0 cleanup    # First time setup"
    echo "  sudo $0 start      # Start Control D for VPN use"
    echo "  sudo $0 test       # Verify VPN compatibility"
}

show_logs() {
    print_status "Showing recent Control D logs..."
    
    echo
    echo -e "${BLUE}=== Control D Output Logs ===${NC}"
    if [ -f "/var/log/controld.vpn.out.log" ]; then
        tail -20 /var/log/controld.vpn.out.log
    else
        echo "No output logs found"
    fi
    
    echo
    echo -e "${BLUE}=== Control D Error Logs ===${NC}"
    if [ -f "/var/log/controld.vpn.err.log" ]; then
        tail -20 /var/log/controld.vpn.err.log
    else
        echo "No error logs found"
    fi
}

# Main script logic
case "${1:-}" in
    "cleanup")
        check_root
        cleanup_and_setup
        ;;
    "start")
        check_root
        start_vpn_compatible_service
        ;;
    "stop")
        check_root
        stop_vpn_compatible_service
        ;;
    "restart")
        check_root
        stop_vpn_compatible_service
        sleep 2
        start_vpn_compatible_service
        ;;
    "status")
        check_service_status
        ;;
    "test")
        test_windscribe_compatibility
        ;;
    "logs")
        show_logs
        ;;
    *)
        show_usage
        ;;
esac