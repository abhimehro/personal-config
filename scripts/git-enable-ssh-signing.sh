#!/usr/bin/env bash
#
# Configure git commit signing with SSH (1Password agent friendly).
# - Sets git global signing to SSH using a public key.
# - Checks for a running SSH agent socket (defaults to 1Password socket).
# - Warns if the key or agent is missing.
#
# Usage:
#   ./scripts/git-enable-ssh-signing.sh [--key ~/.ssh/id_ed25519.pub] [--sock ~/.1password/agent.sock]
#

set -euo pipefail

KEY="${1:-}"
SOCK="${2:-}"

# Parse optional flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --key)
      KEY="$2"
      shift 2
      ;;
    --sock)
      SOCK="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

# Defaults
KEY=${KEY:-"$HOME/.ssh/id_ed25519.pub"}
SOCK=${SOCK:-"$HOME/.1password/agent.sock"}

info()  { echo "[INFO] $*"; }
warn()  { echo "[WARN] $*" >&2; }
error() { echo "[ERR ] $*" >&2; exit 1; }

if [[ ! -f "$KEY" ]]; then
  error "Public key not found at $KEY. Export your 1Password SSH public key there, or pass --key <path>."
fi

if [[ -S "${SSH_AUTH_SOCK:-}" ]]; then
  ACTIVE_SOCK="$SSH_AUTH_SOCK"
else
  ACTIVE_SOCK="$SOCK"
fi

if [[ ! -S "$ACTIVE_SOCK" ]]; then
  warn "SSH agent socket not found at $ACTIVE_SOCK. If using 1Password, ensure the agent is enabled and socket is present."
else
  info "SSH agent socket found: $ACTIVE_SOCK"
fi

# Apply git configs
info "Configuring git to use SSH signing with key: $KEY"
git config --global gpg.format ssh
git config --global user.signingkey "$KEY"
git config --global commit.gpgsign true

# Show resulting config
info "Git signing configuration:"
git config --global --get gpg.format || true
git config --global --get user.signingkey || true
git config --global --get commit.gpgsign || true

# Check agent has the key (best-effort)
if command -v ssh-add >/dev/null 2>&1; then
  if SSH_AUTH_SOCK="$ACTIVE_SOCK" ssh-add -L >/dev/null 2>&1; then
    info "ssh-add -L succeeded (agent is reachable)."
  else
    warn "ssh-add -L failed. Ensure the agent is running and the key is loaded."
  fi
else
  warn "ssh-add not found; skipped agent key check."
fi

cat <<'NEXT'

Next steps:
- If using 1Password SSH agent, keep it running and ensure the key is allowed for signing.
- To verify: git commit -S -m "test" --allow-empty && git log --show-signature -1
- If GitHub rejects pushes, add your public key (~/.ssh/id_ed25519.pub) in GitHub Settings → SSH and GPG keys.
NEXT
