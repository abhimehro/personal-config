#!/usr/bin/env bash
# ==============================================================================
# PHASE 2: BACKLOG MINER ORCHESTRATOR & SUMMARY GENERATOR
# ==============================================================================
# Part of SecOps Autopilot. Delegates to the Python secops_agent.py.
# Cadence: Bi-weekly / Monthly (1st and 15th at 10:00 AM)
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Phase 2 (bi-weekly cadence) via secops-agent..."
exec uv run "$SCRIPT_DIR/../.agents/skills/secops-autopilot/scripts/secops_agent.py" run --cadence bi-weekly "$@"
