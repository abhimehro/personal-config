#!/usr/bin/env bash
set -Eeuo pipefail

if command -v python >/dev/null 2>&1; then
  exec python "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$@"
fi

echo "Error: python or python3 is required but not found in PATH." >&2
exit 127
