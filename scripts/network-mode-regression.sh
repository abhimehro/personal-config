#!/bin/bash
#
# Network Mode Regression Runner
# Runs a full end-to-end sequence:
#   1) Switch to Control D DNS mode
#   2) Verify CONTROL D ACTIVE
#   3) Switch to Windscribe VPN mode
#   4) Verify WINDSCRIBE READY
# and prints a final one-line PASS/FAIL summary with duration.
#
# USAGE: ./scripts/network-mode-regression.sh [profile]
#        (profile defaults to `browsing`)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

MANAGER="./scripts/network-mode-manager.sh"
VERIFY="./scripts/network-mode-verify.sh"

log()  { echo -e "${BLUE}[INFO]${NC} $@"; }
fail() { echo -e "${RED}[FAIL]${NC} $@"; }
pass() { echo -e "${GREEN}[PASS]${NC} $@"; }

ensure_prereqs_regression() {
  if [[ $EUID -eq 0 ]]; then
    echo -e "${RED}[ERR]${NC} Please run as your normal user; this script will use sudo where needed." >&2
    exit 1
  fi
  [[ -x "$MANAGER" ]] || { echo "network-mode-manager.sh not found or not executable" >&2; exit 1; }
  [[ -x "$VERIFY" ]]  || { echo "network-mode-verify.sh not found or not executable" >&2; exit 1; }
}

main() {
  ensure_prereqs_regression

  local profile="${1:-browsing}"
  local start_ts end_ts duration
  local ok=0

  start_ts=$(date +%s)
  log "Starting network mode regression (profile=$profile)..."

  # 1) Switch to Control D DNS mode
  log "Step 1: Switching to CONTROL D (DNS) mode..."
  "$MANAGER" controld "$profile" || ok=1

  # 2) Verify CONTROL D ACTIVE explicitly (profile-aware)
  log "Step 2: Verifying CONTROL D ACTIVE state..."
  if ! "$VERIFY" controld "$profile"; then
    ok=1
  fi

  # 3) Switch to Windscribe VPN mode (Standalone)
  log "Step 3: Switching to STANDALONE WINDSCRIBE (VPN) mode..."
  "$MANAGER" windscribe || ok=1

  # 4) Verify WINDSCRIBE READY explicitly
  log "Step 4: Verifying WINDSCRIBE READY state..."
  if ! "$VERIFY" windscribe; then
    ok=1
  fi

  # 5) Switch to Combined Mode (VPN + Control D)
  log "Step 5: Switching to COMBINED MODE (Windscribe + Privacy)..."
  "$MANAGER" windscribe privacy || ok=1

  # 6) Verify COMBINED state (using profile-aware controld verify)
  log "Step 6: Verifying COMBINED state (VPN active + Control D)..."
  if ! "$VERIFY" controld privacy; then
    ok=1
  fi

  end_ts=$(date +%s)
  duration=$(( end_ts - start_ts ))

  local result
  if [[ $ok -eq 0 ]]; then
    result="PASS"
    pass "Network mode regression completed successfully in ${duration}s."
  else
    result="FAIL"
    fail "Network mode regression encountered issues (see logs above). Duration: ${duration}s."
  fi

  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "SUMMARY TS=${ts} MODE=regression PROFILE=${profile} RESULT=${result} DURATION_SECONDS=${duration}"

  return $ok
}

main "$@"
