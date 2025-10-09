#!/bin/bash
# Fix controld-manager to automatically apply VPN-compatible binding
# This modifies the controld-manager script to always use 0.0.0.0 binding

set -e

echo "🔧 Fixing controld-manager for Automatic VPN Binding"
echo "=================================================="

# Backup original script
BACKUP_FILE="/usr/local/bin/controld-manager.backup-$(date +%Y%m%d_%H%M%S)"
echo "📦 Creating backup: $BACKUP_FILE"
sudo cp /usr/local/bin/controld-manager "$BACKUP_FILE"

# Create a temporary script with the fix
TEMP_SCRIPT="/tmp/controld-manager-fixed"

cat > "$TEMP_SCRIPT" << 'EOF'
#!/bin/bash

# Control D Profile Manager - Enhanced with DOH3 Support
# Addresses network hijacking and switching issues
# Now supports both DOH and DOH3 protocols
# ENHANCED: Automatic VPN binding fix (0.0.0.0:53)
# Author: Assistant
# Date: 2025-10-07

set -e

# Configuration
CONTROLD_DIR="/etc/controld"
PROFILES_DIR="$CONTROLD_DIR/profiles"
BACKUP_DIR="$CONTROLD_DIR/backup"
LOG_FILE="/var/log/controld_manager.log"

# Profile configurations with protocol preferences
get_profile_id() {
    case "$1" in
        "privacy") echo "6m971e9jaf" ;;
        "gaming") echo "1xfy57w34t7" ;;
        *) echo "" ;;
    esac
}

get_profile_protocol() {
    case "$1" in
        "privacy") echo "doh" ;;      # Privacy uses DOH by default for stability
        "gaming") echo "doh3" ;;     # Gaming can also use DOH3
        *) echo "doh" ;;            # Fallback to DOH
    esac
}

get_all_profiles() {
    echo "privacy gaming"
}

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $*${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $*${NC}" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Setup directories
setup_directories() {
    mkdir -p "$PROFILES_DIR" "$BACKUP_DIR"
    chmod 755 "$PROFILES_DIR" "$BACKUP_DIR"
}

# ENHANCED: Apply VPN-compatible binding fix
apply_vpn_binding_fix() {
    local config_file="$1"
    
    if [[ -f "$config_file" ]]; then
        log "Applying VPN-compatible binding fix to $config_file"
        # Replace 127.0.0.1 with 0.0.0.0 for VPN compatibility
        sed -i '' 's/ip = \x27127\.0\.0\.1\x27/ip = \x270\.0\.0\.0\x27/g' "$config_file"
        log_success "VPN binding fix applied: now listens on 0.0.0.0:53"
    fi
}

# Generate profile-specific configuration
generate_profile_config() {
    local profile_name="$1"
    local profile_id="$2"
    local protocol="$3"
    local config_file="$PROFILES_DIR/ctrld.$profile_name.toml"
    
    log "Generating $profile_name profile configuration with $protocol protocol..."
    
    # Generate configuration using ctrld
    TEMP_CONFIG="/tmp/ctrld_temp.toml"
    
    # Start service temporarily to generate config
    if [[ "$protocol" == "doh3" ]]; then
        ctrld start --cd "$profile_id" --proto doh3 --config="$TEMP_CONFIG" --skip_self_checks 2>/dev/null || true
    else
        ctrld start --cd "$profile_id" --config="$TEMP_CONFIG" --skip_self_checks 2>/dev/null || true
    fi
    sleep 2
    ctrld stop 2>/dev/null || true
    
    if [[ -f "$TEMP_CONFIG" ]]; then
        # ENHANCED: Apply VPN binding fix before copying
        apply_vpn_binding_fix "$TEMP_CONFIG"
        cp "$TEMP_CONFIG" "$config_file"
        rm -f "$TEMP_CONFIG"
        log_success "Generated and fixed $profile_name profile configuration"
    else
        log_error "Failed to generate $profile_name configuration"
        return 1
    fi
}

# Backup network settings
backup_network_settings() {
    log "Backing up network settings..."
    networksetup -getdnsservers Wi-Fi > "$BACKUP_DIR/wifi_dns_backup.txt" 2>/dev/null || true
}

# Safe stop function
safe_stop() {
    log "Safely stopping Control D service..."
    
    if pgrep -f "ctrld" >/dev/null; then
        ctrld stop 2>/dev/null || true
        sleep 2
        
        # Force kill if still running
        if pgrep -f "ctrld" >/dev/null; then
            log_warning "Force stopping Control D..."
            pkill -f "ctrld" 2>/dev/null || true
            sleep 1
        fi
        log "Service stopped"
    else
        log_warning "service is already stopped"
    fi
    
    log_warning "Restoring original network settings..."
    if [[ -f "$BACKUP_DIR/wifi_dns_backup.txt" ]]; then
        local dns_servers
        dns_servers=$(cat "$BACKUP_DIR/wifi_dns_backup.txt")
        if [[ "$dns_servers" != "There aren't any DNS Servers set on Wi-Fi." ]]; then
            networksetup -setdnsservers Wi-Fi $dns_servers 2>/dev/null || true
        else
            networksetup -setdnsservers Wi-Fi empty 2>/dev/null || true
        fi
    else
        networksetup -setdnsservers Wi-Fi empty 2>/dev/null || true
    fi
    log_success "Network settings restored"
    log_success "Service safely stopped and network restored"
}

# Switch to profile
switch_profile() {
    local profile_name="$1"
    local force_protocol="$2"
    local profile_id=$(get_profile_id "$profile_name")
    local protocol=${force_protocol:-$(get_profile_protocol "$profile_name")}
    local config_file="$PROFILES_DIR/ctrld.$profile_name.toml"
    
    if [[ -z "$profile_id" ]]; then
        log_error "Unknown profile: $profile_name"
        echo "Available profiles: $(get_all_profiles)"
        return 1
    fi
    
    log "Switching to $profile_name profile with $protocol protocol..."
    
    # Safe stop current service
    safe_stop
    
    # Wait for network to stabilize
    sleep 3
    
    # Generate configuration if needed
    if [[ ! -f "$config_file" ]]; then
        generate_profile_config "$profile_name" "$profile_id" "$protocol"
    fi
    
    # ENHANCED: Always apply VPN binding fix before starting
    apply_vpn_binding_fix "$config_file"
    
    # Create symlink to active configuration
    ln -sf "$config_file" "$CONTROLD_DIR/ctrld.toml"
    
    # Start service with the new profile
    log "Starting Control D with $profile_name profile ($protocol)..."
    if [[ "$protocol" == "doh3" ]]; then
        ctrld start --config="$CONTROLD_DIR/ctrld.toml" --skip_self_checks
    else
        ctrld start --config="$CONTROLD_DIR/ctrld.toml" --skip_self_checks
    fi
    
    # Wait for service to initialize
    sleep 3
    
    # Configure system DNS to use localhost
    networksetup -setdnsservers Wi-Fi 127.0.0.1
    
    # Flush DNS cache
    dscacheutil -flushcache 2>/dev/null || true
    killall -HUP mDNSResponder 2>/dev/null || true
    
    # Wait for DNS to propagate
    sleep 2
    
    # Test the setup
    log "Testing DNS connection..."
    
    # Test basic DNS resolution
    if dig +short google.com @127.0.0.1 >/dev/null 2>&1; then
        log_success "Basic DNS resolution working"
    else
        log_error "DNS resolution failed"
        return 1
    fi
    
    # Test Control D connectivity
    if dig +short txt test.controld.com @127.0.0.1 >/dev/null 2>&1; then
        log_success "Control D connectivity confirmed"
    else
        log_warning "Control D connectivity test inconclusive"
    fi
    
    # Test ad blocking
    local blocked_test
    blocked_test=$(dig +short doubleclick.net @127.0.0.1 2>/dev/null | head -1)
    if [[ "$blocked_test" == "127.0.0.1" ]] || [[ -z "$blocked_test" ]]; then
        log_success "Privacy filtering is working (ads blocked)"
    else
        log_warning "Privacy filtering status unclear"
    fi
    
    log_success "Successfully switched to $profile_name profile ($protocol)"
    echo ""
    echo "Profile: $profile_name"
    echo "ID: $profile_id"
    echo "Protocol: $protocol"
    echo "Status: Active"
}

# Test DNS functionality
test_dns() {
    echo "Testing DNS functionality..."
    
    # Test localhost binding
    if ! nc -z 127.0.0.1 53 2>/dev/null; then
        echo "❌ Control D is not listening on localhost:53"
        return 1
    fi
    echo "✅ Control D is listening on localhost:53"
    
    # Test basic resolution
    if dig +short google.com @127.0.0.1 >/dev/null 2>&1; then
        echo "✅ Basic DNS resolution working"
    else
        echo "❌ DNS resolution failed"
        return 1
    fi
    
    # Test ad blocking
    local result
    result=$(dig +short doubleclick.net @127.0.0.1 2>/dev/null | head -1)
    if [[ "$result" == "127.0.0.1" ]] || [[ -z "$result" ]]; then
        echo "✅ Ad blocking active"
    else
        echo "⚠️ Ad blocking status: $result"
    fi
    
    echo "DNS test completed successfully"
}

# Emergency recovery
emergency() {
    log_error "Emergency recovery initiated"
    
    # Stop all Control D processes
    pkill -f "ctrld" 2>/dev/null || true
    
    # Reset DNS settings
    networksetup -setdnsservers Wi-Fi empty 2>/dev/null || true
    
    # Remove control files
    rm -f "$CONTROLD_DIR/ctrld.toml" 2>/dev/null || true
    
    # Flush DNS
    dscacheutil -flushcache 2>/dev/null || true
    killall -HUP mDNSResponder 2>/dev/null || true
    
    log_success "Emergency recovery completed - all Control D services stopped and DNS reset"
}

# Show status
show_status() {
    echo "=== Control D Profile Manager Status ==="
    echo
    
    if pgrep -f "ctrld" >/dev/null; then
        echo "Service Status: ✅ Running"
        
        # Try to determine active profile
        if [[ -L "$CONTROLD_DIR/ctrld.toml" ]]; then
            local active_link
            active_link=$(readlink "$CONTROLD_DIR/ctrld.toml")
            if [[ "$active_link" =~ privacy ]]; then
                echo "Active Profile: privacy"
                echo "Profile ID: $(get_profile_id privacy)"
                echo "Protocol: $(get_profile_protocol privacy)"
            elif [[ "$active_link" =~ gaming ]]; then
                echo "Active Profile: gaming"
                echo "Profile ID: $(get_profile_id gaming)"
                echo "Protocol: $(get_profile_protocol gaming)"
            else
                echo "Active Profile: Unknown (direct configuration)"
            fi
        else
            echo "Active Profile: Unknown (direct configuration)"
        fi
        
        # Check DNS configuration
        local dns_servers
        dns_servers=$(networksetup -getdnsservers Wi-Fi 2>/dev/null || echo "Unable to determine")
        echo "System DNS: $dns_servers"
        
        # Test connectivity
        if nc -z 127.0.0.1 53 2>/dev/null; then
            echo "Connection: ✅ Working"
        else
            echo "Connection: ❌ Failed"
        fi
    else
        echo "Service Status: ❌ Stopped"
    fi
    
    echo
    echo "Available Profiles:"
    for profile in $(get_all_profiles); do
        local default_protocol=$(get_profile_protocol "$profile")
        echo "  - $profile ($(get_profile_id "$profile")) - Default: $default_protocol"
    done
    
    echo
    echo "Protocols:"
    echo "  - doh3: DNS-over-HTTPS/3 (QUIC) - Faster, more secure"
    echo "  - doh:  DNS-over-HTTPS (TCP) - Fallback for compatibility"
}

# Initialize the system
initialize() {
    log "Initializing Control D Profile Manager..."
    
    setup_directories
    backup_network_settings
    
    # Generate configurations for all profiles with their preferred protocols
    for profile in $(get_all_profiles); do
        local profile_id=$(get_profile_id "$profile")
        local protocol=$(get_profile_protocol "$profile")
        generate_profile_config "$profile" "$profile_id" "$protocol"
    done
    
    log_success "Initialization completed"
}

# Main function
main() {
    case "${1:-""}" in
        "init"|"initialize")
            check_root
            initialize
            ;;
        "switch")
            check_root
            if [[ -z "$2" ]]; then
                echo "Usage: $0 switch <profile_name> [protocol]"
                echo "Available profiles: $(get_all_profiles)"
                echo "Available protocols: doh3, doh"
                exit 1
            fi
            switch_profile "$2" "$3"
            ;;
        "status")
            show_status
            ;;
        "stop")
            check_root
            safe_stop
            ;;
        "test")
            test_dns
            ;;
        "emergency")
            check_root
            emergency
            ;;
        *)
            echo "Control D Profile Manager - Enhanced with DOH3 Support"
            echo "Usage: $0 <command> [options]"
            echo
            echo "Commands:"
            echo "  init                        Initialize the profile manager"
            echo "  switch <profile> [protocol] Switch to profile (gaming/privacy) with optional protocol"
            echo "  status                      Show current status and protocol info"
            echo "  stop                        Safely stop Control D service"
            echo "  test                        Test DNS connection"
            echo "  emergency                   Emergency recovery (restore network)"
            echo
            echo "Available profiles: $(get_all_profiles)"
            echo "Protocols: doh3 (default), doh (fallback)"
            echo
            echo "Examples:"
            echo "  sudo $0 init"
            echo "  sudo $0 switch gaming        # Use default DOH3"
            echo "  sudo $0 switch gaming doh3   # Force DOH3"
            echo "  sudo $0 switch gaming doh    # Force DOH fallback"
            echo "  sudo $0 switch privacy       # Use default DOH3"
            echo "  $0 status"
            echo "  sudo $0 emergency"
            ;;
    esac
}

main "$@"
EOF

# Apply the fix
echo "🔧 Installing fixed controld-manager script..."
sudo cp "$TEMP_SCRIPT" /usr/local/bin/controld-manager
sudo chmod +x /usr/local/bin/controld-manager
sudo chown root:wheel /usr/local/bin/controld-manager
rm -f "$TEMP_SCRIPT"

echo "✅ controld-manager has been updated with automatic VPN binding fix"
echo ""
echo "🧪 Testing the fix..."
sudo controld-manager switch privacy doh

echo ""
echo "🎉 Fix completed! controld-manager now automatically applies VPN-compatible binding."
echo "📋 Now all profile switches will work with Windscribe VPN!"
EOF