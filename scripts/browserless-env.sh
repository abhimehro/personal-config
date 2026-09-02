#!/usr/bin/env bash
# browserless-env.sh — resolve Browserless secrets from 1Password.
#
# Executed directly:  prints `export KEY=value` lines for eval.
#   eval "$(scripts/browserless-env.sh)"
# Sourced:            exports silently into the current shell.
#   source scripts/browserless-env.sh
#
# Secrets are resolved live from 1Password via op read; nothing is written to
# disk and nothing is printed when sourced.
#
# Committed to personal-config: contains only op:// references, no secrets.

set -euo pipefail

OP_REF_API_KEY="op://Personal/fbbrvhjsd3x7vetbz544uyvjoe/credential"
OP_REF_SA_TOKEN="op://Personal/fbbrvhjsd3x7vetbz544uyvjoe/key"

BROWSERLESS_API_KEY="$(op read "$OP_REF_API_KEY")"
OP_SERVICE_ACCOUNTS_TOKEN="$(op read "$OP_REF_SA_TOKEN")"
export BROWSERLESS_API_KEY OP_SERVICE_ACCOUNTS_TOKEN

# Print only when executed directly (not sourced)
if [ "${BASH_SOURCE[0]:-$0}" = "$0" ]; then
  printf "export BROWSERLESS_API_KEY=%q\n" "$BROWSERLESS_API_KEY"
  printf "export OP_SERVICE_ACCOUNTS_TOKEN=%q\n" "$OP_SERVICE_ACCOUNTS_TOKEN"
fi
