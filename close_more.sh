#!/usr/bin/env bash
# Close additional duplicate pull requests using a safely loaded GH_TOKEN.
set -euo pipefail

if [[ ${1-} != "--yes" ]]; then
	echo "This script closes 4 hardcoded PRs from an April 2026 triage run." >&2
	echo "Re-run with --yes if that is still what you want." >&2
	exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# SECURITY: execute the token helper and capture stdout; do not source it.
GH_TOKEN="$(bash "${SCRIPT_DIR}/scripts/ensure_gh_token.sh")"
if [[ -z ${GH_TOKEN} ]]; then
	echo "error: ensure_gh_token.sh returned an empty token" >&2
	exit 1
fi
export GH_TOKEN

close_pr() {
	local repo="$1"
	local pr="$2"
	local reason="$3"
	echo "Closing ${repo}#${pr} (${reason})..."
	gh pr close "${pr}" --repo "${repo}" --comment "Automated triage: ${reason}"
}

close_pr "abhimehro/ctrld-sync" "702" "Semantic duplicate of a newer automated PR (#707)"
close_pr "abhimehro/ctrld-sync" "697" "Semantic duplicate of a newer automated PR (#706)"
close_pr "abhimehro/personal-config" "732" "Semantic duplicate of a newer automated PR (#744)"
close_pr "abhimehro/personal-config" "724" "Semantic duplicate of a newer automated PR (#744)"
