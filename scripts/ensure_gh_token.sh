#!/usr/bin/env bash
# SECURITY: Do not source GH_TOKEN.env from repo paths; use env or gh auth.
set -euo pipefail

if [[ -n "${GH_TOKEN:-}" || -n "${GITHUB_TOKEN:-}" ]]; then
	export GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
	exit 0
fi

if command -v gh >/dev/null 2>&1; then
	token="$(gh auth token 2>/dev/null || true)"
	if [[ -n "${token}" ]]; then
		export GH_TOKEN="${token}"
		exit 0
	fi
fi

if [[ -n "${GH_TOKEN_ENV_FILE:-}" && -f "${GH_TOKEN_ENV_FILE}" ]]; then
	# shellcheck disable=SC1090
	set -a
	# NOTE: File must live outside the repo; set GH_TOKEN_ENV_FILE explicitly.
	source "${GH_TOKEN_ENV_FILE}"
	set +a
	if [[ -n "${GH_TOKEN:-}" || -n "${GITHUB_TOKEN:-}" ]]; then
		export GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
		exit 0
	fi
fi

echo "ERROR: Set GH_TOKEN, GITHUB_TOKEN, GH_TOKEN_ENV_FILE, or run 'gh auth login'." >&2
exit 1
