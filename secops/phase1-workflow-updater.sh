#!/usr/bin/env bash
# ==============================================================================
# PHASE 1: GITHUB ACTIONS WORKFLOW UPDATER
# ==============================================================================
# Part of SecOps Autopilot. Delegates to the Python secops_agent.py.
# Cadence: Weekly (Mondays at 9:00 AM)
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Phase 1 (weekly cadence) via secops-agent..."
exec uv run "$SCRIPT_DIR/../.agents/skills/secops-autopilot/scripts/secops_agent.py" run --cadence weekly "$@"
