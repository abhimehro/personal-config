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

# Use a secure temporary directory instead of a file directly in /tmp
# mktemp -d creates a directory with 0700 permissions (rwx------)
TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/op2proton.XXXXXX")
TMP_FILE="${TMP_DIR}/key"

cleanup() {
  # Securely delete the temporary file if it exists
  if [[ -f "${TMP_FILE}" ]]; then
    if command -v shred >/dev/null 2>&1; then
      # GNU shred: overwrite and remove
      shred -u "${TMP_FILE}" 2>/dev/null
    else
      # Fallback: try macOS rm -P (overwrite) or standard rm
      rm -P "${TMP_FILE}" 2>/dev/null || rm -f "${TMP_FILE}"
    fi
  fi
  # Remove the directory
  if [[ -d "${TMP_DIR}" ]]; then
    rm -rf "${TMP_DIR}"
  fi
}
trap cleanup EXIT

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

echo "Imported SSH key '${TITLE}' into Proton Pass vault '${VAULT_NAME}'."
