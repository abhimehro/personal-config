#!/usr/bin/env bash
# Canonical copy of Cursor Cloud Agent pre-commit secret scanner.
# Installed copy (environment-specific): ~/.cursor/agent-hooks/<workspace-hash>/pre-commit.cursor
#
# Fix 2026-03-21: secret *labels* in CLOUD_AGENT_INJECTED_SECRET_NAMES may contain
# spaces (e.g. "GitHub SSH Key"). Bash ${!name} indirect expansion requires an
# identifier; use printenv "$name" instead.
#
# Keep this file in sync with the hook Cursor injects so fixes are reviewable in git.

set -e

# Exit early if no secrets are configured
if [ -z "$CLOUD_AGENT_INJECTED_SECRET_NAMES" ]; then
	exit 0
fi

# Default diff base: staged changes against HEAD
DIFF_ARGS=(--cached)
# How we derive candidate files:
# - "diff": files from git diff + DIFF_ARGS
# - "merge_msg_conflicts": conflict files parsed from MERGE_MSG on older Git versions
FILES_SOURCE_MODE="diff"
MERGE_MSG_PATH=""

# Smart merge handling:
# If MERGE_HEAD exists and AUTO_MERGE is available, compare index against
# AUTO_MERGE to isolate only edits made during conflict resolution.
# This avoids scanning inherited upstream merge changes across unrelated files.
if git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
	if git rev-parse -q --verify AUTO_MERGE >/dev/null 2>&1; then
		DIFF_ARGS=(--cached AUTO_MERGE)
	else
		# Older Git fallback: use conflict file list from MERGE_MSG.
		# If parsing fails, we safely fall back to standard diff-based scanning.
		MERGE_MSG_PATH=$(git rev-parse --git-path MERGE_MSG 2>/dev/null || true)
		if [ -n "$MERGE_MSG_PATH" ] && [ -f "$MERGE_MSG_PATH" ] && grep -q '^#	' "$MERGE_MSG_PATH"; then
			FILES_SOURCE_MODE="merge_msg_conflicts"
		fi
	fi
fi

# Build list of binary files from staged content using git's detection
# git diff --cached --numstat shows "-	-	<filename>" for binary files
declare -A BINARY_FILES
while IFS=$'\t' read -r added deleted filename; do
	if [ "$added" = "-" ] && [ "$deleted" = "-" ]; then
		BINARY_FILES["$filename"]=1
	fi
done < <(git diff "${DIFF_ARGS[@]}" --numstat 2>/dev/null || true)

# Build candidate file list once (null-delimited for spaces in filenames)
SCANNED_FILES=()
if [ "$FILES_SOURCE_MODE" = "merge_msg_conflicts" ]; then
	# MERGE_MSG stores conflict paths as lines like: "#	path/to/file"
	while IFS= read -r FILE; do
		[ -n "$FILE" ] && SCANNED_FILES+=("$FILE")
	done < <(sed -n 's/^#	//p' "$MERGE_MSG_PATH" 2>/dev/null || true)
fi

if [ ${#SCANNED_FILES[@]} -eq 0 ]; then
	while IFS= read -r -d '' FILE; do
		SCANNED_FILES+=("$FILE")
	done < <(git diff "${DIFF_ARGS[@]}" --name-only -z --diff-filter=d -- 2>/dev/null || true)
fi

if [ ${#SCANNED_FILES[@]} -eq 0 ]; then
	exit 0
fi

# Track findings
FOUND_ANY=0
FINDINGS=""

# Split secret names by comma and process each
IFS=',' read -ra SECRET_NAMES <<<"$CLOUD_AGENT_INJECTED_SECRET_NAMES"

for raw_name in "${SECRET_NAMES[@]}"; do
	# NOTE: Comma-split entries may include leading/trailing whitespace; trim so
	# lookup matches the actual environment variable name.
	# SECURITY: Bash indirect expansion (${!var}) only allows identifier-shaped names.
	# Injected secret labels may contain spaces (e.g. "GitHub SSH Key"); use printenv.
	SECRET_NAME="$(printf '%s' "$raw_name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
	if [ -z "$SECRET_NAME" ]; then
		continue
	fi
	SECRET_VALUE="$(printenv "$SECRET_NAME" 2>/dev/null || true)"

	# Skip empty values or very short values (< 8 chars) to avoid false positives
	if [ -z "$SECRET_VALUE" ] || [ ${#SECRET_VALUE} -lt 8 ]; then
		continue
	fi

	# Process candidate files with merge-aware scope
	for FILE in "${SCANNED_FILES[@]}"; do
		# Skip if file doesn't exist (might be in a submodule or special case)
		if [ ! -f "$FILE" ]; then
			continue
		fi

		# Handle binary vs text files differently
		if [ "${BINARY_FILES[$FILE]}" = "1" ]; then
			# For binary files, check if secret exists in the diff (added content only)
			# No line number or pragma support for binary files
			if git diff "${DIFF_ARGS[@]}" -U0 -- "$FILE" 2>/dev/null | grep -a '^+' | grep -v '^+++ [ab/]' | grep -qaFi -e "$SECRET_VALUE"; then
				FOUND_ANY=1
				FINDINGS="$FINDINGS
  Secret:  $SECRET_NAME
  File:    $FILE (binary file)
"
			fi
		else
			# Search only the ADDED lines in the diff for the secret value
			# This avoids false positives for secrets that already exist in the repo
			# Use awk to parse hunk headers and track line numbers, then grep for the secret
			MATCH_LINE=$(git diff "${DIFF_ARGS[@]}" -U0 -- "$FILE" 2>/dev/null | awk '
              /^@@/ {
                # Parse hunk header to get new file line number
                # $3 is like "+N" or "+N,M" - extract the starting line number
                s = $3
                gsub(/^\+/, "", s)
                gsub(/,.*/, "", s)
                line = s + 0
                next
              }
              /^\+/ && !/^\+\+\+ [ab\/]/ {
                # Print line number and content (without leading +)
                print line ":" substr($0, 2)
                line++
              }
            ' | grep -v "pragma: allowlist secret" | grep -Fi -m1 -e "$SECRET_VALUE" | cut -d: -f1)

			if [ -n "$MATCH_LINE" ]; then
				FOUND_ANY=1
				FINDINGS="$FINDINGS
  Secret:  $SECRET_NAME
  File:    $FILE
  Line:    $MATCH_LINE
"
			fi
		fi
	done
done

# Report findings and block commit if any secrets were found
if [ $FOUND_ANY -eq 1 ]; then
	echo ""
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo "🔐 COMMIT BLOCKED: Secret value detected in staged files"
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo ""
	echo "Your commit contains values of configured secrets:"
	echo "$FINDINGS"
	echo "Committing this would expose your secrets in the repository history."
	echo ""
	echo "To fix this:"
	echo "  1. Remove the hardcoded secret value from the file(s)"
	echo "  2. Use environment variables instead (e.g., process.env.SECRET_NAME)"
	echo "  3. Stage your changes and try committing again"
	echo ""
	echo "If this secret is intentional (e.g., a test fixture), add to the line:"
	echo "  // pragma: allowlist secret"
	echo ""
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo "CURSOR_SECRET_SCAN_BLOCKED=1" >&2
	exit 1
fi

exit 0
