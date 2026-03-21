#!/usr/bin/env bash
# Canonical copy of Cursor Cloud Agent commit-msg secret scanner.
# Installed copy: ~/.cursor/agent-hooks/<workspace-hash>/commit-msg.cursor
#
# Same spaced-name fix as scripts/cursor_cloud_agent_pre_commit.sh (2026-03-21).

set -e

COMMIT_MSG_FILE="$1"

# Exit early if no secrets are configured
if [ -z "$CLOUD_AGENT_INJECTED_SECRET_NAMES" ]; then
    exit 0
fi

# Track findings
FOUND_ANY=0
FINDINGS=""

# Split secret names by comma and process each
IFS=',' read -ra SECRET_NAMES <<< "$CLOUD_AGENT_INJECTED_SECRET_NAMES"

for raw_name in "${SECRET_NAMES[@]}"; do
    # NOTE: Trim whitespace; labels may contain spaces — use printenv, not ${!var}.
    SECRET_NAME="$(printf '%s' "$raw_name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [ -z "$SECRET_NAME" ]; then
        continue
    fi
    SECRET_VALUE="$(printenv "$SECRET_NAME" 2>/dev/null || true)"

    # Skip empty values or very short values (< 8 chars) to avoid false positives
    if [ -z "$SECRET_VALUE" ] || [ ${#SECRET_VALUE} -lt 8 ]; then
        continue
    fi

    # Search commit message lines while preserving line numbers
    MATCH_LINE=$(nl -ba "$COMMIT_MSG_FILE" | grep -Fi -m1 -e "$SECRET_VALUE" | awk '{print $1}')

    if [ -n "$MATCH_LINE" ]; then
        FOUND_ANY=1
        FINDINGS="$FINDINGS
  Secret:  $SECRET_NAME
  Line:    $MATCH_LINE
"
    fi
done

# Report findings and block commit if any secrets were found
if [ $FOUND_ANY -eq 1 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔐 COMMIT BLOCKED: Secret value detected in commit message"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Your commit message contains values of configured secrets:"
    echo "$FINDINGS"
    echo "Committing this would expose your secrets in the repository history."
    echo ""
    echo "To fix this:"
    echo "  1. Remove the hardcoded secret value from the commit message"
    echo "  2. Use a redacted description instead (e.g. [REDACTED])"
    echo "  3. Retry the commit with a safe message"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "CURSOR_SECRET_SCAN_BLOCKED=1" >&2
    exit 1
fi

exit 0
