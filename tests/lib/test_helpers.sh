#!/usr/bin/env bash
#
# tests/lib/test_helpers.sh — Shared helpers for shell test files
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/lib/test_helpers.sh"
#   value=$(parse_cred_value "$line")

# Parse a KEY='value', KEY="value", or KEY=value config line and return the
# bare value with any surrounding single or double quotes stripped.
#
# Only outermost quotes are removed; embedded quotes inside the value are left
# intact.  This is necessary because media-server credential files use shell
# assignment syntax (e.g. USERNAME='infuse'), so `cut -d'=' -f2-` returns the
# quoted form.
parse_cred_value() {
  local line="$1"
  local value
  value="$(echo "$line" | cut -d'=' -f2-)"
  # Strip surrounding single quotes
  if [[ $value == \'*\' ]]; then
    value="${value:1:-1}"
  # Strip surrounding double quotes
  elif [[ $value == '"'*'"' ]]; then
    value="${value:1:-1}"
  fi
  echo "$value"
}
