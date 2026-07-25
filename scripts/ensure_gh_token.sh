#!/usr/bin/env bash
# SECURITY: This helper must be executed, not sourced.
# It prints a resolved GH_TOKEN to stdout and exits 0, or prints an error to
# stderr and exits 1. Callers should capture it with:
#   GH_TOKEN="$(bash "${SCRIPT_DIR}/scripts/ensure_gh_token.sh")"

# Guard must run before set -e so a sourced return 1 does not kill the caller.
if [[ ${BASH_SOURCE[0]} != "$0" ]]; then
	echo "error: ensure_gh_token.sh must be executed, not sourced." >&2
	# shellcheck disable=SC2059
	printf '       use: GH_TOKEN="$(bash %q)"\n' "${BASH_SOURCE[0]}" >&2
	return 1 2>/dev/null || exit 1
fi

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n ${GH_TOKEN:-} ]]; then
	printf '%s\n' "${GH_TOKEN}"
	exit 0
fi

if command -v gh >/dev/null 2>&1 && gh auth status -h github.com >/dev/null 2>&1; then
	token="$(gh auth token 2>/dev/null || true)"
	token="${token//[[:space:]]/}"
	if [[ -n ${token} ]]; then
		printf '%s\n' "${token}"
		exit 0
	fi
fi

if command -v python3 >/dev/null 2>&1; then
	py_rc=0
	token="$(
		cd "${ROOT}" && python3 - <<'PY' 2>/dev/null
from gh_token_env import load_gh_token_env

env = load_gh_token_env()
print(env.get("GH_TOKEN", ""))
PY
	)" || py_rc=$?
	if [[ ${py_rc} -ne 0 ]]; then
		echo "error: GH_TOKEN env file failed security validation." >&2
		echo "Ensure the env file is owned by you and has mode 0600." >&2
		exit 1
	fi
	if [[ -n ${token} ]]; then
		printf '%s\n' "${token}"
		exit 0
	fi
fi

echo "error: GH_TOKEN is not configured." >&2
echo "After rotating your PAT, see docs/github-pat-rotation-runbook.md" >&2
exit 1
