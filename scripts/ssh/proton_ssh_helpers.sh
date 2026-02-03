#!/usr/bin/env bash
set -euo pipefail

# Helper abbreviations around Proton Pass SSH agent for use in workflows.

case "${1:-}" in
  start-agent)
    # Start Proton Pass SSH agent for the "SSH Keys" vault.
    exec pass-cli ssh-agent start --vault-name "SSH Keys"
    ;;
  load-into-agent)
    # Load Proton SSH keys into the currently active SSH agent.
    exec pass-cli ssh-agent load --vault-name "SSH Keys"
    ;;
  import-key)
    # Convenience wrapper to call op_to_proton_import.sh
    shift || true
    exec "$(dirname "$0")/op_to_proton_import.sh" "$@"
    ;;
  *)
    cat <<EOF
Usage: ${0##*/} <command> [args]

Commands:
  start-agent       Start Proton Pass SSH agent for vault "SSH Keys"
  load-into-agent   Load Proton SSH keys into current SSH agent
  import-key        Wrapper around op_to_proton_import.sh
                    Example: ${0##*/} import-key "GitHub main key"
EOF
    ;;
esac
