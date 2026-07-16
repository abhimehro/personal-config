#!/usr/bin/env bash
# Run the vendored Secure-at-Inception Python hook with project-local Python.
# SECURITY: Prefer python3 over `uv run` so this works without a plugin pyproject.
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAI_SCRIPT="${HOOK_DIR}/snyk/snyk_secure_at_inception.py"

if [[ ! -f $SAI_SCRIPT ]]; then
	echo "[SAI] Missing hook script: ${SAI_SCRIPT}" >&2
	# Fail open: do not block the agent if the hook is misinstalled.
	printf '%s\n' '{}'
	exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
	echo "[SAI] python3 not found; skipping Secure at Inception" >&2
	printf '%s\n' '{}'
	exit 0
fi

exec python3 "$SAI_SCRIPT"
