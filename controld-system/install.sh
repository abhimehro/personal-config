#!/bin/bash

# Control D System Installation - WORKING CONFIGURATION ONLY
# Installs the verified, working Control D system
# Status: PRODUCTION READY

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        print_error "Don't run the entire script as root. Use sudo only when prompted."
        exit 1
    fi
}

install_system() {
    print_status "Installing Control D system (WORKING CONFIGURATION)..."
    
    # Install profile manager
    if [[ -f "scripts/controld-manager" ]]; then
        sudo cp scripts/controld-manager /usr/local/bin/
        sudo chmod +x /usr/local/bin/controld-manager
        print_success "Installed controld-manager"
    else
        print_error "controld-manager script not found"
        exit 1
    fi
    
    # Install profile configurations
    sudo mkdir -p /etc/controld/profiles
    if [[ -d "configs/profiles" ]]; then
        sudo cp configs/profiles/* /etc/controld/profiles/
        print_success "Installed profile configurations"
    else
        print_error "Profile configurations not found"
        exit 1
    fi
    
    print_success "Installation completed!"
    echo
    echo "Next steps:"
    echo "1. Choose a profile:"
    echo "   sudo controld-manager switch gaming    # Gaming profile"
    echo "   sudo controld-manager switch privacy   # Privacy profile"
    echo
    echo "2. Verify status:"
    echo "   controld-manager status"
    echo
    echo "3. Emergency recovery (if needed):"
    echo "   sudo controld-manager emergency"
}

main() {
    check_permissions
    install_system
}

main "$@"
