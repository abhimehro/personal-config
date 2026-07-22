#!/usr/bin/env bash
#
# Runner script for weekly repository health review (Research Repos)
# Scheduled by launchd: com.speedybee.repo-health.research (Tuesdays 09:00)

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$HOME/Library/Logs/maintenance"
LOG_FILE="$LOG_DIR/repo_health_research.log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=========================================="
echo "Starting Weekly Repo Health (Research Repos)"
echo "Timestamp: $(date -Iseconds)"
echo "=========================================="

cd "$REPO_ROOT"

# Preflight verification
if [[ -f "$SCRIPT_DIR/preflight-gh-pr-automation.sh" ]]; then
	echo "[INFO] Running preflight check..."
	bash "$SCRIPT_DIR/preflight-gh-pr-automation.sh" --repo abhimehro/series_correction_project_updated --repo abhimehro/Hydrograph_Versus_Seatek_Sensors_Project --repo abhimehro/Seatek_Analysis || {
		echo "[WARN] Preflight check reported warnings/errors. Proceeding with caution..."
	}
fi

SPEC_FILE="$REPO_ROOT/tasks/weekly-repo-health-research.md"
if [[ -f $SPEC_FILE ]]; then
	echo "[INFO] Task specification loaded from $SPEC_FILE"
else
	echo "[ERROR] Task specification $SPEC_FILE not found."
	exit 1
fi

echo "[INFO] Research Repos review execution ready."
echo "[INFO] Target Repositories:"
echo "  - /Users/speedybee/dev/series_correction_project_updated"
echo "  - /Users/speedybee/dev/Hydrograph_Versus_Seatek_Sensors_Project"
echo "  - /Users/speedybee/dev/Seatek_Analysis"
echo "=========================================="
echo "[SUCCESS] Research Repos weekly health runner completed."
