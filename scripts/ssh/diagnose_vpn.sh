#!/usr/bin/env bash
set -Eeuo pipefail

echo "VPN diagnostics helpers live in: $0" >&2
echo "Suggested checks:" >&2
echo "  - nm-status (if Fish functions are installed)" >&2
echo "  - ./scripts/network-mode-status.sh (if present)" >&2
echo "  - scutil --dns | head -50" >&2
exit 0
