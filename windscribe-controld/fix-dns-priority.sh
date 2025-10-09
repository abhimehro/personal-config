#!/bin/bash

# DNS Priority Fix for Windscribe + Control D
# Ensures Control D DNS filtering takes precedence over VPN DNS

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

backup_dns_config() {
    print_status "Backing up current DNS configuration..."
    
    # Backup resolver configuration
    if [ -d "/etc/resolver" ]; then
        cp -r /etc/resolver /etc/resolver.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
    fi
    
    print_success "DNS configuration backed up"
}

create_dns_override() {
    print_status "Creating DNS override for Control D priority..."
    
    # Ensure resolver directory exists
    mkdir -p /etc/resolver
    
    # Create Control D priority resolver
    cat > /etc/resolver/controld << EOF
# Control D DNS Priority Override
# Forces Control D to handle DNS resolution over VPN DNS
nameserver 127.0.0.1
port 53
timeout 2
EOF
    
    # Set appropriate permissions
    chmod 644 /etc/resolver/controld
    chown root:wheel /etc/resolver/controld
    
    print_success "DNS override created for Control D priority"
}

remove_dns_override() {
    print_status "Removing DNS override..."
    
    if [ -f "/etc/resolver/controld" ]; then
        rm /etc/resolver/controld
        print_success "DNS override removed"
    else
        print_warning "No DNS override found to remove"
    fi
}

test_dns_priority() {
    print_status "Testing DNS priority..."
    
    echo
    echo -e "${BLUE}=== DNS Resolution Test ===${NC}"
    
    # Test blocked domain
    blocked_result=$(dig doubleclick.net +short 2>/dev/null)
    if [[ "$blocked_result" == "127.0.0.1" ]]; then
        echo "✅ Control D filtering: ACTIVE"
        echo "   doubleclick.net → 127.0.0.1 (blocked)"
    else
        echo "❌ Control D filtering: INACTIVE"
        echo "   doubleclick.net → $blocked_result"
    fi
    
    # Test normal domain
    normal_result=$(dig google.com +short 2>/dev/null | head -1)
    if [[ -n "$normal_result" && "$normal_result" != "127.0.0.1" ]]; then
        echo "✅ Normal DNS: WORKING"
        echo "   google.com → $normal_result"
    else
        echo "❌ Normal DNS: FAILED"
    fi
    
    # Check which DNS servers are active
    echo
    echo -e "${BLUE}=== Active DNS Servers ===${NC}"
    scutil --dns | grep "nameserver" | head -3
    
    return 0
}

flush_dns_cache() {
    print_status "Flushing DNS cache..."
    
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder
    
    print_success "DNS cache flushed"
}

show_usage() {
    echo "DNS Priority Fix for Windscribe + Control D"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  enable     - Enable Control D DNS priority over VPN DNS"
    echo "  disable    - Disable DNS priority override (use default VPN DNS)"
    echo "  test       - Test current DNS priority and filtering"
    echo "  flush      - Flush DNS cache"
    echo
    echo "Examples:"
    echo "  sudo $0 enable    # Force Control D to handle DNS"
    echo "  sudo $0 test      # Check if Control D filtering is active"
    echo "  sudo $0 disable   # Revert to VPN DNS handling"
}

# Main script logic
case "${1:-}" in
    "enable")
        check_root
        backup_dns_config
        create_dns_override
        flush_dns_cache
        sleep 2
        test_dns_priority
        print_success "Control D DNS priority enabled!"
        print_warning "If issues occur, run: sudo $0 disable"
        ;;
    "disable")
        check_root
        remove_dns_override
        flush_dns_cache
        sleep 2
        test_dns_priority
        print_success "DNS priority override disabled"
        ;;
    "test")
        test_dns_priority
        ;;
    "flush")
        check_root
        flush_dns_cache
        ;;
    *)
        show_usage
        ;;
esac