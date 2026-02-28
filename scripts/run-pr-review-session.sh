#!/usr/bin/env bash
set -euo pipefail

# Gate for PR review sessions: run preflight, then print next steps.
# Does not run inventory/review logic — that remains agent-driven.
# See docs/automated-pr-review-agent.md.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE=""
USE_CONFIG_DEFAULT=true

usage() {
  cat <<'USAGE'
Usage:
  run-pr-review-session.sh [options]

Options:
  --config PATH   Use this config for preflight repos (default: tasks/pr-review-agent.config.yaml if present).
  --no-config    Do not use config; pass default repos to preflight (same as preflight with no args).
  -h, --help     Show this help.

Preflight must pass before any triage or write actions. On success, next steps are printed.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      [[ $# -ge 2 ]] || { echo "ERROR: --config requires a value" >&2; exit 1; }
      CONFIG_FILE="$2"
      USE_CONFIG_DEFAULT=false
      shift 2
      ;;
    --no-config)
      USE_CONFIG_DEFAULT=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

cd "$REPO_ROOT"

PREFLIGHT_CMD=("$SCRIPT_DIR/preflight-gh-pr-automation.sh")
if [[ -n "$CONFIG_FILE" ]]; then
  PREFLIGHT_CMD+=(--config "$CONFIG_FILE")
elif [[ "$USE_CONFIG_DEFAULT" == true ]] && [[ -f "tasks/pr-review-agent.config.yaml" ]]; then
  PREFLIGHT_CMD+=(--config tasks/pr-review-agent.config.yaml)
fi

if ! "${PREFLIGHT_CMD[@]}"; then
  echo ""
  echo "Preflight failed. Do not proceed to inventory, merge, or close."
  echo "Fix auth/repo access/permissions and re-run this script or preflight directly."
  exit 1
fi

echo ""
echo "Preflight passed. Proceed with Phase 1 (inventory) per docs/automated-pr-review-agent.md."
echo "Artifacts: tasks/pr-inventory.md, tasks/pr-triage.md, tasks/pr-review-YYYY-MM-DD.md"
