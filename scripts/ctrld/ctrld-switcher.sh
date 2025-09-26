#!/bin/bash

# Control D Profile Switcher with Advanced Cleanup
# Version: 2.1
# Author: CodePilot (Based on original review)

set -e

# Color codes for output
RED='\033[0;31m'
CTRLD_PATH="/usr/local/bin/ctrld"
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# Configuration
CTRLD_PATH="/usr/local/bin/ctrld"
LOG_DIR="$HOME/Library/Logs/ctrld"
mkdir -p "$LOG_DIR" 2>/dev/null || true
CONFIG_FILE="/etc/controld/ctrld.toml"
CONTROL_SOCK="/var/run/ctrld_control.sock"

PROFILES_gaming="1xfy57w34t7"
PROFILES_privacy="6m971e9jaf"  # Corrected Privacy Resolver ID

# DNS configurations for each profile
PROFILE_DNS_PRIMARY_gaming="76.76.2.184"
PROFILE_DNS_PRIMARY_privacy="76.76.2.182"

PROFILE_DNS_SECONDARY_gaming="76.76.10.184"
PROFILE_DNS_SECONDARY_privacy="76.76.10.182"

# Logging function with timestamps and levels
log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_file="${LOG_DIR}/ctrld-switcher.log"
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$log_file"
    if [[ "$level" == "ERROR" ]]; then
        echo -e "${RED}${timestamp} [${level}] ${message}${NC}"
    elif [[ "$level" == "INFO" ]]; then
        echo -e "${GREEN}${timestamp} [${level}] ${message}${NC}"
    elif [[ "$level" == "WARNING" ]]; then
        echo -e "${YELLOW}${timestamp} [${level}] ${message}${NC}"
    else
        echo -e "${BLUE}${timestamp} [${level}] ${message}${NC}"
    fi
}

# Function to check if running as root when needed
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        log "WARNING" "This operation requires sudo privileges. Enter password when prompted."
        sudo "$0" "$@"
        exit $?
    fi
}

# Kill all Control D related processes forcefully
kill_controld_processes() {
    log "INFO" "Hunting down Control D processes..."
    
    # Find all ctrld processes
    local pids=$(pgrep -f "ctrld|controld|Control.*D" 2>/dev/null || true)
    
    if [[ ! -z "$pids" ]]; then
        log "WARNING" "Found Control D processes: $pids"
        for pid in $pids; do
            if ! kill -TERM $pid 2>/dev/null; then
                log "WARNING" "Failed to terminate PID $pid gracefully, force killing..."
                kill -9 $pid 2>/dev/null || true
            fi
        done
    fi
    
    # Clean up control socket
    if [[ -e "$CONTROL_SOCK" ]]; then
        log "INFO" "Removing control socket..."
        rm -f "$CONTROL_SOCK"
    fi
}

# Stop and disable launch daemons
stop_launch_daemons() {
    log "INFO" "Checking for launch daemons..."
    
    local daemon_files=(
        "/Library/LaunchDaemons/com.controld.ctrld.plist"
        "/Library/LaunchDaemons/controld.plist"
        "$HOME/Library/LaunchAgents/com.controld.plist"
    )
    
    for daemon in "${daemon_files[@]}"; do
        if [[ -f "$daemon" ]]; then
            local daemon_name=$(basename "$daemon" .plist)
            log "INFO" "Unloading $daemon_name..."
            
            # Unload daemon
            if [[ "$daemon" == /Library/LaunchDaemons/* ]]; then
                sudo launchctl bootout system "$daemon" 2>/dev/null || true
                sudo launchctl disable "system/$daemon_name" 2>/dev/null || true
            else
                launchctl bootout "gui/$(id -u)" "$daemon" 2>/dev/null || true
                launchctl disable "gui/$(id -u)/$daemon_name" 2>/dev/null || true
            fi
            
            # Remove the daemon file temporarily (we'll restore it later)
            log "INFO" "Backing up and removing $daemon..."
            sudo cp "$daemon" "$daemon.backup" 2>/dev/null || true
            sudo rm -f "$daemon" 2>/dev/null || true
        fi
    done
}

# Free up port 53
free_port_53() {
    log "INFO" "Freeing up port 53..."
    
    # Check if mDNSResponder is using port 53
    if sudo lsof -i :53 -sTCP:LISTEN -sTCP:ESTABLISHED 2>/dev/null | grep -q "mDNSResponder"; then
        log "WARNING" "mDNSResponder is using port 53, temporarily unloading..."
        sudo launchctl unload /System/Library/LaunchDaemons/com.apple.mDNSResponder.plist 2>/dev/null || true
        sleep 2
        echo "mdns_unloaded" > /tmp/ctrld_mdns_status
    fi
    
    # Find processes using port 53
    local processes=$(sudo lsof -i :53 -t 2>/dev/null || true)
    
    if [[ ! -z "$processes" ]]; then
        for pid in $processes; do
            local proc_name=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
            
            # Don't kill system DNS resolver (already handled above)
            if [[ "$proc_name" != "mDNSResponder" ]]; then
                log "WARNING" "Killing process $proc_name (PID: $pid) using port 53..."
                sudo kill -9 $pid 2>/dev/null || true
            fi
        done
    fi
    
    # Wait for port to be freed
    sleep 1
    
    # Verify port is free
    if sudo lsof -i :53 -t 2>/dev/null | grep -v "mDNSResponder" > /dev/null; then
        log "WARNING" "Port 53 might still be in use"
    else
        log "INFO" "Port 53 is free"
    fi
}

# Reset DNS configuration
reset_dns() {
    log "INFO" "Resetting DNS configuration..."
    
    # Get active network interfaces
local interfaces=$(networksetup -listallnetworkservices | grep -v "^\\*")
    
>    while IFS= read -r interface; do
        log "INFO" "Clearing DNS for $interface..."
        sudo networksetup -setdnsservers "$interface" "Empty" 2>/dev/null || true
        
        # Disable proxies
        log "INFO" "Disabling proxy for $interface..."
        sudo networksetup -setwebproxystate "$interface" off 2>/dev/null || true
        sudo networksetup -setsecurewebproxystate "$interface" off 2>/dev/null || true
        sudo networksetup -setsocksfirewallproxystate "$interface" off 2>/dev/null || true
    done <<< "$interfaces"
    
    # Flush DNS cache multiple times to ensure it's clear
    log "INFO" "Flushing DNS cache (multiple passes)..."
    for i in {1..3}; do
        sudo dscacheutil -flushcache 2>/dev/null || true
        sudo killall -HUP mDNSResponder 2>/dev/null || true
        sleep 0.5
    done
}

# Stop AdGuard DNS protection temporarily
manage_adguard() {
    local action=$1
    
    if [[ -x "/Applications/AdGuard.app/Contents/MacOS/AdGuard" ]]; then
        log "INFO" "Managing AdGuard DNS protection..."
        
        if [[ "$action" == "stop" ]]; then
            osascript <<EOF 2>/dev/null || true
tell application "AdGuard"
    if it is running then
        -- Disable DNS protection
        do shell script "defaults write com.adguard.mac.adguard DNSProtectionEnabled -bool false"
    end if
end tell
EOF
        elif [[ "$action" == "start" ]]; then
            osascript <<EOF 2>/dev/null || true
tell application "AdGuard"
    if it is running then
        -- Enable DNS protection
        do shell script "defaults write com.adguard.mac.adguard DNSProtectionEnabled -bool true"
    end if
end tell
EOF
        fi
    fi
}

# Complete cleanup function
complete_cleanup() {
    log "INFO" "Starting complete cleanup..."
    
    # Stop AdGuard DNS temporarily
    manage_adguard "stop"
    
    # Stop launch daemons
    stop_launch_daemons
    
    # Kill all Control D processes
    kill_controld_processes
    
    # Free port 53
    free_port_53
    
    # Reset DNS configuration
    reset_dns
    
    # Remove any leftover configuration
    sudo rm -f /var/run/controld* 2>/dev/null || true
    sudo rm -f /tmp/controld* 2>/dev/null || true
    
    log "INFO" "Cleanup complete!"
}

# Start Control D with specified profile
start_controld() {
    local profile=$1
    local profile_id=$(eval echo \$PROFILES_$profile)
    
    if [[ -z "$profile_id" ]]; then
        log "ERROR" "Unknown profile: $profile"
        exit 1
    fi
    
    log "INFO" "Starting Control D with $profile profile..."
    
    # Set device name
    local device_name="MacBook-Airlocal"
    
    # Build command
    local cmd="'$CTRLD_PATH' run"
    cmd="$cmd --cd='${profile_id}/${device_name}'"
    cmd="$cmd --proto=doh3"
    cmd="$cmd --proxy"
    cmd="$cmd --log='${LOG_DIR}/ctrld.log'"
    cmd="$cmd --iface=auto"
    cmd="$cmd --homedir=/etc/controld"
    cmd="$cmd --config='${CONFIG_FILE}'"
    
    # Create log directory if it doesn't exist
    sudo mkdir -p "$LOG_DIR"
    
    # Start Control D in background
    log "INFO" "Starting Control D daemon..."
    eval "sudo $cmd > '${LOG_DIR}/startup.log' 2>&1 &"
    
    local ctrld_pid=$!
    
    # Wait for startup
    sleep 3
    
    # Verify it's running
    if kill -0 $ctrld_pid 2>/dev/null; then
        log "INFO" "Control D started successfully (PID: $ctrld_pid)"
        
        # Save PID for future reference
        echo $ctrld_pid | sudo tee /var/run/ctrld.pid > /dev/null
        
        # Configure DNS for active interfaces
        configure_dns_for_profile "$profile"
        
        # Re-enable AdGuard with new DNS
        manage_adguard "start"
        
        # Re-enable mDNSResponder if it was unloaded
        if [[ -f /tmp/ctrld_mdns_status ]]; then
            log "INFO" "Reloading mDNSResponder..."
            sudo launchctl load /System/Library/LaunchDaemons/com.apple.mDNSResponder.plist 2>/dev/null || true
            rm -f /tmp/ctrld_mdns_status
        fi
        
        return 0
    else
        log "ERROR" "Failed to start Control D"
        return 1
    fi
}

# Configure DNS for the active profile
configure_dns_for_profile() {
    local profile=$1
    local primary_dns=$(eval echo \$PROFILE_DNS_PRIMARY_$profile)
    local secondary_dns=$(eval echo \$PROFILE_DNS_SECONDARY_$profile)
    
    log "INFO" "Configuring DNS for $profile profile..."
    
    # Set DNS for all active interfaces
local interfaces=$(networksetup -listallnetworkservices | grep -v "^\\*")
    
>    while IFS= read -r interface; do
        # Check if interface is active
        if networksetup -getinfo "$interface" 2>/dev/null | grep -q "IP address"; then
            log "INFO" "Setting DNS for $interface..."
            sudo networksetup -setdnsservers "$interface" 127.0.0.1 "$primary_dns" "$secondary_dns" 2>/dev/null || true
            
            # Set proxy for full routing
            log "INFO" "Setting proxy for $interface..."
            sudo networksetup -setwebproxy "$interface" 127.0.0.1 8080 2>/dev/null || true
            sudo networksetup -setsecurewebproxy "$interface" 127.0.0.1 8080 2>/dev/null || true
            sudo networksetup -setsocksfirewallproxy "$interface" 127.0.0.1 1080 2>/dev/null || true
        fi
    done <<< "$interfaces"
}

# Profile status checker
check_status() {
    log "INFO" "Checking Control D status..."
    
    # Check if Control D is running
    if pgrep -f "ctrld run" > /dev/null; then
        local pid=$(pgrep -f "ctrld run" | head -n1)
        local cmd=$(ps -p $pid -o command= 2>/dev/null || echo "unknown")
        
        # Extract profile from command
        if [[ "$cmd" =~ --cd=([^/]+)/ ]]; then
            local profile_id="${BASH_REMATCH[1]}"
            
            # Find profile name
            for name in gaming privacy; do
                local pid_val=$(eval echo \$PROFILES_$name)
                if [[ "$pid_val" == "$profile_id" ]]; then
                    log "INFO" "Control D is running"
                    log "INFO" "Active profile: $name ($profile_id)"
                    log "INFO" "PID: $pid"
                    
                    # Test DNS resolution
                    log "INFO" "Testing DNS resolution..."
                    local dns_test=$(dig @127.0.0.1 google.com +short +time=2 2>/dev/null | head -n1)
                    if [[ ! -z "$dns_test" ]]; then
                        log "INFO" "DNS resolution working: $dns_test"
                    else
                        log "ERROR" "DNS resolution not working"
                    fi
                    
                    return 0
                fi
            done
        fi
    else
        log "ERROR" "Control D is not running"
        return 1
    fi
}

# Main switch function
switch_profile() {
    local profile=$1
    
    log "INFO" "Switching to $profile profile..."
    
    # Perform complete cleanup
    complete_cleanup
    
    # Wait for system to stabilize
    sleep 2
    
    # Start new profile
    if start_controld "$profile"; then
        log "INFO" "Successfully switched to $profile profile!"
        
        # Show status
        check_status
    else
        log "ERROR" "Failed to switch profile"
        exit 1
    fi
}

# Main script logic
main() {
    case "${1:-}" in
        gaming|privacy)
            check_sudo "$@"
            switch_profile "$1"
            ;;
        stop)
            check_sudo "$@"
            complete_cleanup
            log "INFO" "Control D stopped completely"
            ;;
        status)
            check_status
            ;;
        restart)
            check_sudo "$@"
            local current_profile=$(check_current_profile)
            complete_cleanup
            sleep 2
            if [[ ! -z "$current_profile" ]]; then
                switch_profile "$current_profile"
            else
                log "WARNING" "No previous profile detected, use: $0 [gaming|privacy]"
            fi
            ;;
        *)
            log "INFO" "Control D Profile Switcher"
            log "INFO" "Usage: $0 [gaming|privacy|stop|status|restart]"
            log "INFO" "Commands:"
            log "INFO" "  gaming   - Switch to gaming profile (low latency)"
            log "INFO" "  privacy  - Switch to privacy profile (maximum protection)"
            log "INFO" "  stop     - Stop Control D completely"
            log "INFO" "  status   - Check current status"
            "  restart  - Restart with current profile"
            exit 1
            ;;
    esac
}

# Helper function to detect current profile
check_current_profile() {
    if pgrep -f "ctrld run" > /dev/null; then
        local cmd=$(ps -ax | grep "ctrld run" | grep -v grep | head -n1)
        
        for name in gaming privacy; do
            local pid_val=$(eval echo \$PROFILES_$name)
            if [[ "$cmd" =~ $pid_val ]]; then
                echo "$name"
                return
            fi
        done
    fi
}

# Run main function
main "$@"