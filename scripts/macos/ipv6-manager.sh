#!/bin/bash
# IPv6 Manager for macOS
# Disables/Enables IPv6 to prevent issues with IPv4-only VPN tunnels

set -e

# Get all network services
get_network_services() {
    networksetup -listallnetworkservices | grep -v "^An asterisk"
}

# Disable IPv6 on all interfaces
disable_ipv6() {
    echo "Disabling IPv6 on all network interfaces..."
    
    # 1. Standard networksetup method
    while IFS= read -r service; do
        if [[ -n "$service" ]]; then
            # ⚡ Bolt Optimization: Check state first to avoid expensive write operations
            # Writing system config is slow; reading is fast. Only write if needed.
            if networksetup -getinfo "$service" 2>/dev/null | grep -q "IPv6: Off"; then
                echo "    (already disabled: $service)"
            else
                echo "  Disabling IPv6 on: $service"
                sudo networksetup -setv6off "$service" 2>/dev/null || echo "    (skipped: $service)"
            fi
        fi
    done < <(get_network_services)

    # 2. Sysctl method (Disable Router Advertisements globally)
    echo "  Disabling IPv6 Router Advertisements (sysctl)..."
    sudo sysctl -w net.inet6.ip6.accept_rtadv=0 2>/dev/null || true
    
    echo "✓ IPv6 disabled on all interfaces"
    echo ""
    echo "Verifying IPv6 status:"
    check_ipv6_status
}

# Enable IPv6 on all interfaces
enable_ipv6() {
    echo "Enabling IPv6 on all network interfaces..."
    
    # 1. Standard networksetup method
    while IFS= read -r service; do
        if [[ -n "$service" ]]; then
            # ⚡ Bolt Optimization: Check state first to avoid expensive write operations
            if networksetup -getinfo "$service" 2>/dev/null | grep -q "IPv6: Automatic"; then
                 echo "    (already enabled: $service)"
            else
                echo "  Enabling IPv6 on: $service"
                sudo networksetup -setv6automatic "$service" 2>/dev/null || echo "    (skipped: $service)"
            fi
        fi
    done < <(get_network_services)

    # 2. Sysctl method (Re-enable Router Advertisements)
    echo "  Enabling IPv6 Router Advertisements (sysctl)..."
    sudo sysctl -w net.inet6.ip6.accept_rtadv=1 2>/dev/null || true
    
    echo "✓ IPv6 enabled on all interfaces"
    echo ""
    echo "Verifying IPv6 status:"
    check_ipv6_status
}

# Check IPv6 status
check_ipv6_status() {
    echo "Current IPv6 configuration:"
    echo ""
    
    while IFS= read -r service; do
        if [[ -n "$service" ]]; then
            local ipv6_config=$(networksetup -getinfo "$service" 2>/dev/null | grep "IPv6:" || echo "IPv6: Unknown")
            echo "  $service: $ipv6_config"
        fi
    done < <(get_network_services)
    
    echo ""
    echo "Active IPv6 addresses:"
    ifconfig | grep "inet6" | grep -v "::1" | grep -v "fe80::" || echo "  No IPv6 addresses found"
}

# Main
case "${1:-}" in
    "disable")
        disable_ipv6
        ;;
    "enable")
        enable_ipv6
        ;;
    "status")
        check_ipv6_status
        ;;
    *)
        echo "IPv6 Manager for macOS"
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  disable   Disable IPv6 on all network interfaces"
        echo "  enable    Enable IPv6 on all network interfaces"
        echo "  status    Check current IPv6 configuration"
        echo ""
        echo "Why disable IPv6?"
        echo "  - Windscribe VPN only supports IPv4"
        echo "  - Apps attempting IPv6 connections will timeout/fail"
        echo "  - Causes Raycast updates and other services to fail"
        echo ""
        echo "Examples:"
        echo "  sudo $0 disable    # Disable IPv6 (recommended with Windscribe)"
        echo "  $0 status          # Check current status"
        echo "  sudo $0 enable     # Re-enable IPv6 (if needed)"
        ;;
esac
