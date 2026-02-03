#!/usr/bin/env bash
set -Eeuo pipefail

cat <<'EOF'
Add these aliases/functions to your shell profile if you want shortcuts:

  alias dev-mdns='ssh dev-mdns'
  alias dev-local='ssh dev-local'
  alias dev-auto='ssh dev-auto'

If you installed the helper scripts to ~/.ssh via ./scripts/install_ssh_config.sh:
  ~/.ssh/smart_connect.sh
  ~/.ssh/check_connections.sh
EOF
