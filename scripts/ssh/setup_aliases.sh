#!/usr/bin/env bash
set -Eeuo pipefail

cat <<'EOF'
Add these aliases/functions to your shell profile if you want shortcuts:

  alias cursor-mdns='ssh cursor-mdns'
  alias cursor-local='ssh cursor-local'
  alias cursor-auto='ssh cursor-auto'

If you installed the helper scripts to ~/.ssh via ./scripts/install_ssh_config.sh:
  ~/.ssh/smart_connect.sh
  ~/.ssh/check_connections.sh
EOF
