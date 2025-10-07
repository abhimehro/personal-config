#!/usr/bin/env bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")"/../lib && pwd)/common.sh"
with_lock "brew_maintenance"

# Only run on Sundays (day 7 of week)
if [[ "$(date +%u)" -ne 7 ]]; then
    log_info "Brew maintenance skipped - only runs on Sundays (today is $(date +%A))"
    exit 0
fi

log_info "Brew maintenance started"
require_cmd brew

# Update Homebrew and check for issues
with_retry 3 5 brew update
BREW_DOCTOR_OUTPUT=$(brew doctor 2>&1 || true)
if ! echo "${BREW_DOCTOR_OUTPUT}" | grep -q "Your system is ready to brew"; then
  log_warn "brew doctor reported issues:"
  log_warn "${BREW_DOCTOR_OUTPUT}"
fi

# Check what's outdated
log_info "Checking for outdated packages..."
brew outdated || true
brew outdated --cask --greedy || true

# Upgrade formulae and casks
log_info "Upgrading formulae..."
with_retry 3 5 brew upgrade || log_warn "brew upgrade had issues"

log_info "Upgrading casks (including auto-updating)..."
with_retry 3 5 brew upgrade --cask --greedy || log_warn "cask upgrade had issues"

# Cleanup
log_info "Cleaning up..."
with_retry 3 5 brew autoremove || true
with_retry 3 5 brew cleanup --prune=${BREW_CLEAN_PRUNE_DAYS:-30} || true

# Check for failed brew services and restart them
if command -v brew >/dev/null 2>&1; then
  FAILED_SERVICES=$(brew services list 2>/dev/null | awk 'NR>1 && $2!="started" && $2!="none" {print $1" "$2}' || true)
  if [[ -n "${FAILED_SERVICES}" ]]; then
    log_warn "Found failed brew services: ${FAILED_SERVICES}"
    while IFS= read -r line; do
      svc_name=$(echo "$line" | awk '{print $1}')
      log_info "Attempting to restart service: $svc_name"
      brew services restart "$svc_name" || log_warn "Failed to restart $svc_name"
    done <<< "${FAILED_SERVICES}"
  fi
fi

prune_logs
log_info "Brew maintenance complete"
notify "Brew Maintenance" "Completed successfully"
