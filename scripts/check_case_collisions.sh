#!/usr/bin/env bash
#
# check_case_collisions.sh
#
# Fail when tracked or staged paths differ only by capitalization.
# This prevents GitHub/macOS case-insensitive filesystem conflicts such as:
#   .Jules/palette.md
#   .jules/palette.md
#
# Intended hooks: pre-commit, pre-push, CI

set -euo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	echo "check_case_collisions: not inside a Git work tree" >&2
	exit 1
fi

# Include tracked index paths plus staged path names. git ls-files normally covers
# staged paths, but diff --cached keeps the check explicit for rename/delete flows.
collisions="$({
	{
		git ls-files
		git diff --cached --name-only --diff-filter=ACMRT
	} | awk '
		BEGIN { failed = 0 }
		{
			key = tolower($0)
			if (!($0 in seen_exact)) {
				seen_exact[$0] = 1
				seen[key] = seen[key] ? seen[key] "\n" $0 : $0
				count[key]++
			}
		}
		END {
			for (k in count) {
				if (count[k] > 1) {
					failed = 1
					print "case-insensitive path collision:"
					print seen[k]
					print ""
				}
			}
			exit failed
		}'
} 2>&1)" || {
	echo "$collisions" >&2
	echo "Refusing operation: paths must be unique when compared case-insensitively." >&2
	echo "Fix by keeping one canonical casing, usually lowercase, and removing/renaming the duplicate with git mv." >&2
	exit 1
}

printf '%s\n' "No case-insensitive path collisions detected."
