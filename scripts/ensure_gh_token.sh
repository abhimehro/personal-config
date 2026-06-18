#!/usr/bin/env bash
# SECURITY: Do not `source` GH_TOKEN.env — export GH_TOKEN or use gh auth instead.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n ${GH_TOKEN-} ]]; then
	exit 0
fi

if command -v gh >/dev/null 2>&1 && gh auth status -h github.com >/dev/null 2>&1; then
	export GH_TOKEN
	GH_TOKEN="$(gh auth token)"
	exit 0
fi

if command -v python3 >/dev/null 2>&1; then
	token="$(
		cd "${ROOT}" && python3 - <<'PY'
from gh_token_env import load_gh_token_env

env = load_gh_token_env()
print(env.get("GH_TOKEN", ""))
PY
	)"
	if [[ -n ${token} ]]; then
		export GH_TOKEN="${token}"
		exit 0
	fi
fi

echo "error: GH_TOKEN is not configured." >&2
echo "After rotating your PAT, see docs/github-pat-rotation-runbook.md" >&2
exit 1
