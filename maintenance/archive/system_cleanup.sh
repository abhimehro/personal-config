#!/usr/bin/env bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")"/../lib && pwd)/common.sh"
with_lock "system_cleanup"

# Only run on Wednesdays (day 3 of week)
if [[ "$(date +%u)" -ne 3 ]]; then
    log_info "System cleanup skipped - only runs on Wednesdays (today is $(date +%A))"
    exit 0
fi

log_info "System cleanup started"

# 1) Prune user caches older than CLEANUP_CACHE_DAYS
CACHE_DIR="${HOME}/Library/Caches"
if [[ -d "${CACHE_DIR}" ]]; then
  log_info "Pruning caches older than ${CLEANUP_CACHE_DAYS:-30} days in ${CACHE_DIR}"
  find "${CACHE_DIR}" -type f -mtime +${CLEANUP_CACHE_DAYS:-30} -print0 2>/dev/null | xargs -0 rm -f || true
  find "${CACHE_DIR}" -type d -empty -print0 2>/dev/null | xargs -0 rmdir || true
fi

# 2) Clean TMPDIR and /tmp files older than TMP_CLEAN_DAYS
for TDIR in "${TMPDIR:-/tmp}" "/tmp"; do
  if [[ -d "$TDIR" ]]; then
    log_info "Cleaning temporary files older than ${TMP_CLEAN_DAYS:-7} days in $TDIR"
    find "$TDIR" -type f -mtime +${TMP_CLEAN_DAYS:-7} -user "${USER}" -print0 2>/dev/null | xargs -0 rm -f || true
  fi
done

# 3) Xcode DerivedData cleanup (if present)
DDIR="${HOME}/Library/Developer/Xcode/DerivedData"
if [[ -d "${DDIR}" ]]; then
  log_info "Pruning Xcode DerivedData older than ${XCODE_DERIVEDDATA_KEEP_DAYS:-30} days"
  find "${DDIR}" -mindepth 1 -maxdepth 1 -mtime +${XCODE_DERIVEDDATA_KEEP_DAYS:-30} -print0 2>/dev/null | xargs -0 rm -rf || true
fi

# 4) iOS Simulator cleanup (if present)
IOS_SIM_DIR="${HOME}/Library/Developer/CoreSimulator/Caches/dyld"
if [[ -d "${IOS_SIM_DIR}" ]]; then
  log_info "Cleaning iOS Simulator caches"
  find "${IOS_SIM_DIR}" -type f -mtime +7 -print0 2>/dev/null | xargs -0 rm -f || true
fi

# 5) Homebrew cleanup
if command -v brew >/dev/null 2>&1; then
  log_info "Running Homebrew cleanup"
  with_retry 3 3 brew cleanup --prune=${BREW_CLEAN_PRUNE_DAYS:-30} || true
  with_retry 3 3 brew autoremove || true
fi

# 6) Language/tool caches (safe cleanup)
if command -v npm >/dev/null 2>&1; then
  log_info "Verifying npm cache"
  npm cache verify || true
fi

if command -v pip3 >/dev/null 2>&1; then
  log_info "Purging pip cache"
  pip3 cache purge || true
fi

if command -v gem >/dev/null 2>&1; then
  log_info "Cleaning gem cache"
  gem cleanup || true
fi

# 7) macOS system cleanup
log_info "Cleaning system logs and temporary files"

# Clean user logs older than 30 days
USER_LOGS_DIR="${HOME}/Library/Logs"
if [[ -d "${USER_LOGS_DIR}" ]]; then
  find "${USER_LOGS_DIR}" -name "*.log" -mtime +30 -print0 2>/dev/null | xargs -0 rm -f || true
fi

# Clean downloads folder of files older than 90 days (be conservative)
DOWNLOADS_DIR="${HOME}/Downloads"
if [[ -d "${DOWNLOADS_DIR}" ]]; then
  log_info "Cleaning old downloads (90+ days)"
  find "${DOWNLOADS_DIR}" -type f -mtime +90 -print0 2>/dev/null | xargs -0 rm -f || true
fi

# 8) Browser cache cleanup (optional - only very old caches)
for browser_cache in \
  "${HOME}/Library/Caches/com.google.Chrome" \
  "${HOME}/Library/Caches/com.apple.Safari" \
  "${HOME}/Library/Caches/org.mozilla.firefox"; do
  if [[ -d "$browser_cache" ]]; then
    log_info "Cleaning old browser cache: $(basename "$browser_cache")"
    find "$browser_cache" -type f -mtime +14 -print0 2>/dev/null | xargs -0 rm -f || true
  fi
done

# 9) Prune old maintenance logs
prune_logs

# 10) Report disk space after cleanup
DISK_AFTER=$(percent_used "/")
log_info "Disk usage after cleanup: ${DISK_AFTER}%"

log_info "System cleanup complete"
notify "System Cleanup" "Completed successfully (disk: ${DISK_AFTER}%)"
