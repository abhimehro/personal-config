#!/usr/bin/env bash
# ==============================================================================
# PHASE 3: QA, HEALTH CHECK, & DRIFT DETECTION
# ==============================================================================
# Part of SecOps Autopilot. Delegates to the Python secops_agent.py.
# Cadence: Daily (8:00 AM)
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Phase 3 (daily cadence) via secops-agent..."
exec uv run "$SCRIPT_DIR/../.agents/skills/secops-autopilot/scripts/secops_agent.py" run --cadence daily "$@"
