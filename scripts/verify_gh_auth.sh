#!/usr/bin/env bash
# Post-rotation check: confirms gh can call the API without printing tokens.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# SECURITY: execute the token helper and capture stdout; do not source it.
GH_TOKEN="$(bash "${ROOT}/scripts/ensure_gh_token.sh")"
if [[ -z ${GH_TOKEN} ]]; then
	echo "error: ensure_gh_token.sh returned an empty token" >&2
	exit 1
fi
export GH_TOKEN

if ! command -v gh >/dev/null 2>&1; then
	echo "error: GitHub CLI (gh) is not installed." >&2
	exit 1
fi

echo "Checking GitHub authentication (no token values printed)..."
gh auth status -h github.com
gh api user -q '.login' | {
	read -r login
	echo "API check OK for user: ${login}"
}
