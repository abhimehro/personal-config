#!/usr/bin/env bash
#
# Runner script for weekly repository health review (General Repos)
# Scheduled by launchd: com.speedybee.repo-health.general (Thursdays 09:00)

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$HOME/Library/Logs/maintenance"
LOG_FILE="$LOG_DIR/repo_health_general.log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=========================================="
echo "Starting Weekly Repo Health (General Repos)"
echo "Timestamp: $(date -Iseconds)"
echo "=========================================="

cd "$REPO_ROOT"

# Preflight verification
if [[ -f "$SCRIPT_DIR/preflight-gh-pr-automation.sh" ]]; then
	echo "[INFO] Running preflight check..."
	bash "$SCRIPT_DIR/preflight-gh-pr-automation.sh" --repo abhimehro/personal-config --repo abhimehro/email-security-pipeline --repo abhimehro/ctrld-sync --repo abhimehro/repoprompt-ce || {
		echo "[WARN] Preflight check reported warnings/errors. Proceeding with caution..."
	}
fi

SPEC_FILE="$REPO_ROOT/tasks/weekly-repo-health-general.md"
if [[ -f $SPEC_FILE ]]; then
	echo "[INFO] Task specification loaded from $SPEC_FILE"
else
	echo "[ERROR] Task specification $SPEC_FILE not found."
	exit 1
fi

echo "[INFO] General Repos review execution ready."
echo "[INFO] Target Repositories:"
echo "  - /Users/speedybee/dev/personal-config"
echo "  - /Users/speedybee/dev/email-security-pipeline"
echo "  - /Users/speedybee/dev/ctrld-sync"
echo "  - /Users/speedybee/dev/repoprompt-ce"
echo "=========================================="
echo "[SUCCESS] General Repos weekly health runner completed."
