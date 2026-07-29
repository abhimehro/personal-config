#!/usr/bin/env bash
# Mark draft pull requests ready and merge them using a safely loaded GH_TOKEN.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
	cat <<'EOF'
Usage: fix_drafts.sh REPO PR_NUMBER [REPO PR_NUMBER ...]

Safely loads GH_TOKEN without sourcing external files, then marks each draft
PR ready before merging it with --squash --delete-branch.
EOF
}

if [[ ${1-} == "-h" || ${1-} == "--help" ]]; then
	usage
	exit 0
fi

if [[ $# -lt 2 || $(($# % 2)) -ne 0 ]]; then
	echo "error: expected REPO PR_NUMBER pairs" >&2
	usage >&2
	exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
	echo "error: gh CLI is required but not installed" >&2
	exit 1
fi

# SECURITY: execute the token helper and capture stdout; do not source it.
GH_TOKEN="$(bash "${SCRIPT_DIR}/scripts/ensure_gh_token.sh")"
if [[ -z ${GH_TOKEN} ]]; then
	echo "error: ensure_gh_token.sh returned an empty token" >&2
	exit 1
fi
export GH_TOKEN

fix_and_merge() {
	local repo="$1"
	local pr="$2"
	echo "Marking ${repo}#${pr} ready and merging..."
	gh pr ready "${pr}" --repo "${repo}"
	gh pr merge "${pr}" --repo "${repo}" --squash --delete-branch
}

pairs=("$@")

for ((i = 0; i < ${#pairs[@]}; i += 2)); do
	repo="${pairs[i]}"
	pr="${pairs[i + 1]}"
	if ! [[ ${pr} =~ ^[0-9]+$ ]]; then
		echo "error: invalid PR number for ${repo}: ${pr}" >&2
		exit 2
	fi
done

for ((i = 0; i < ${#pairs[@]}; i += 2)); do
	fix_and_merge "${pairs[i]}" "${pairs[i + 1]}"
done
