#!/usr/bin/env bash
# Post-rotation check: confirms gh can call the API without printing tokens.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT}/scripts/ensure_gh_token.sh"

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
