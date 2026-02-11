#!/usr/bin/env bash
#
# Gentle commit-msg hook for autofix commits.
# - Triggers only when the subject starts with "autofix(".
# - Warns (does NOT block) if Autofix trailers are missing.
#
# Recommended trailers:
#   Autofix-PR: #<n>
#   Autofix-Cycle: <k>
#   Review-Inputs: Copilot,Gemini,Human
#   Mode: T2+S+H
#
# Installation (from repo root):
#   mkdir -p .git/hooks
#   ln -sf ../../scripts/git-hooks/autofix-trailers-commit-msg.sh .git/hooks/commit-msg
#

set -euo pipefail

MSG_FILE="${1-}"

if [[ -z ${MSG_FILE} || ! -f ${MSG_FILE} ]]; then
	# No message file; nothing to do.
	exit 0
fi

# Read the first line (subject), trimming leading whitespace.
subject="$(sed -n '1s/^[[:space:]]*//p' "${MSG_FILE}")"

# Only care about autofix commits.
if [[ ! ${subject} =~ ^autofix\(.+\): ]]; then
	exit 0
fi

# If at least one Autofix trailer is already present, do nothing.
if grep -qiE '^[[:space:]]*Autofix-PR:' "${MSG_FILE}"; then
	exit 0
fi

cat >&2 <<'EOF'
[autofix trailers] Commit subject starts with "autofix(" but no Autofix-PR/Autofix-Cycle trailers were found.
Recommended to add (manually or via your commit template):
  Autofix-PR: #<n>
  Autofix-Cycle: <k>
  Review-Inputs: Copilot,Gemini,Human
  Mode: T2+S+H

This is a gentle reminder only; the commit is not blocked.
EOF

exit 0
