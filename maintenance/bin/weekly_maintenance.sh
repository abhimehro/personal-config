#!/usr/bin/env bash
#
# Weekly maintenance shim.
# Deprecated: kept for backward compatibility. The canonical orchestrator is
# run_all_maintenance.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/run_all_maintenance.sh" weekly
