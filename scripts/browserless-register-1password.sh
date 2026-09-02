#!/usr/bin/env bash
# browserless-register-1password.sh — register the 1Password service account
# with Browserless via the REST API, and print the integrationId.
#
# Usage:
#   scripts/browserless-register-1password.sh [--allow-domain https://app.example.com]
#
# Idempotent: if an integration with the same label already exists, prints its
# id instead of creating a duplicate. Requires scripts/browserless-env.sh.
#
# SECURITY: The ops_... service-account token is resolved from 1Password at
# runtime and sent only to Browserless over HTTPS. It is never printed, logged,
# or committed. The Browserless API key is likewise resolved at runtime.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/browserless-env.sh
source "${repo_root}/scripts/browserless-env.sh"

LABEL="personal-config-browserless-1password"
ENDPOINT="https://production-sfo.browserless.io"

allow_domains=()
while [ $# -gt 0 ]; do
  case "$1" in
    --allow-domain)
      allow_domains+=("$2")
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Build allowedDomains JSON array (empty = allow any public https origin)
if [ ${#allow_domains[@]} -gt 0 ]; then
  domains_json="$(printf "%s\n" "${allow_domains[@]}" | jq -Rsc "split(\"\n\")[:-1]")"
else
  domains_json="[]"
fi

api_call() {
  # api_call <method> <path> [json-body]
  local method="$1" path="$2" body="${3:-}" tmp status
  tmp="$(mktemp)"
  status="$(curl -sS --max-time 30 -o "$tmp" -w "%{http_code}" \
    -X "$method" \
    ${body:+-H "Content-Type: application/json" -d "$body"} \
    "${ENDPOINT}${path}?token=${BROWSERLESS_API_KEY}")"
  if ! jq -e . "$tmp" >/dev/null 2>&1; then
    echo "ERROR: Browserless API returned HTTP ${status} (non-JSON body):" >&2
    head -c 300 "$tmp" >&2
    echo >&2
    rm -f "$tmp"
    if [ "$status" = "401" ]; then
      echo "Hint: 401 means the BROWSERLESS_API_KEY 1Password item does not hold" >&2
      echo "      a valid Browserless dashboard API key. Verify the item:" >&2
      echo "      op://Personal/fbbrvhjsd3x7vetbz544uyvjoe/credential" >&2
    fi
    return 1
  fi
  cat "$tmp"
  rm -f "$tmp"
}

# Check for an existing integration with the same label (idempotency)
existing="$(api_call GET "/integrations/onepassword" \
  | jq -r --arg label "$LABEL" "(map(select(.label == \$label)) | first | .id) // empty")"

if [ -n "$existing" ]; then
  echo "INTEGRATION_ID=$existing"
  echo "(existing integration found with label: $LABEL)" >&2
  exit 0
fi

# Register the service account
integration_id="$(api_call POST "/integrations/onepassword" \
  "{\"label\": \"${LABEL}\", \"serviceAccountToken\": \"${OP_SERVICE_ACCOUNTS_TOKEN}\", \"allowedDomains\": ${domains_json}}" \
  | jq -r ".id // empty")"

if [ -z "$integration_id" ]; then
  echo "ERROR: registration succeeded but no integration id in response." >&2
  exit 1
fi

echo "INTEGRATION_ID=${integration_id}"
