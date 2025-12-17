#!/usr/bin/env bash
set -Eeuo pipefail

# Wrapper around repo-native connection test.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

exec "$REPO_ROOT/scripts/test_ssh_connections.sh" "$@"
