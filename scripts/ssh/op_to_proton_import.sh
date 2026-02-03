#!/usr/bin/env bash
set -euo pipefail

# PURPOSE: Safely import an SSH private key (from 1Password or elsewhere)
# into Proton Pass's "SSH Keys" vault without leaving long-lived plaintext
# copies on disk.
#
# USAGE:
#   op_to_proton_import.sh "Key title" [vault-name]
#
# If vault-name is omitted, defaults to "SSH Keys".
# The script will prompt you to paste the private key, then hit Ctrl+D.

TITLE=${1:-}
VAULT_NAME=${2:-SSH Keys}

if [[ -z "${TITLE}" ]]; then
  echo "Usage: $0 \"Key title\" [vault-name]" >&2
  exit 1
fi

TMP_FILE=$(mktemp "${TMPDIR:-/tmp}/op2proton.XXXXXX")
trap 'rm -f "${TMP_FILE}"' EXIT

cat <<EOF
Paste the SSH PRIVATE KEY for "${TITLE}" below.
When finished, press Ctrl+D on an empty line.
EOF

# Read key from stdin into temporary file (no echo back to screen)
cat >"${TMP_FILE}"

# Import into Proton Pass
pass-cli item create ssh-key import \
  --from-private-key "${TMP_FILE}" \
  --vault-name "${VAULT_NAME}" \
  --title "${TITLE}"

# Securely delete the temporary file (best-effort; trap will also remove)
if command -v rm >/dev/null 2>&1; then
  rm -P "${TMP_FILE}" 2>/dev/null || rm -f "${TMP_FILE}"
fi

trap - EXIT

echo "Imported SSH key '${TITLE}' into Proton Pass vault '${VAULT_NAME}'."