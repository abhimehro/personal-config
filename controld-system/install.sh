#!/bin/bash

# Control D System Installation
# Thin wrapper around the audited setup entry point.
# Does not overwrite /etc/controld/controld.env resolver IDs.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ $EUID -eq 0 ]]; then
	print_error "Don't run the entire script as root. Use sudo only when prompted."
	exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SETUP_SCRIPT="$REPO_ROOT/scripts/setup-controld.sh"

if [[ ! -f $SETUP_SCRIPT ]]; then
	print_error "setup-controld.sh not found at $SETUP_SCRIPT"
	exit 1
fi

print_status "Delegating to audited setup: $SETUP_SCRIPT"
exec bash "$SETUP_SCRIPT" "$@"
