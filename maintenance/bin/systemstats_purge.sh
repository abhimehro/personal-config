#!/usr/bin/env bash
#
# systemstats_purge.sh
#
# Purpose:
#   Reduce CPU pressure from macOS `systemstats` (the com.apple.systemstats.*
#   daemons that feed power/energy analytics). We cannot disable or remove the
#   daemon itself -- it lives in /System/Library/LaunchDaemons and is protected
#   by SIP. Instead this script:
#     1. Purges accumulated *.stats history in /private/var/db/systemstats,
#        which shrinks the dataset the daily "analysis" job has to churn through.
#     2. Optionally kicks the currently running instance so a fresh, idle one
#        is spawned on the next scheduled interval.
#
#   App Tamer's AutoSlow handles the live CPU throttling (see
#   maintenance/conf/apptamer_autoslow.applescript); this script is purely
#   about keeping the on-disk history small so the analysis pass stays cheap.
#
# Requirements:
#   - Needs root to touch /private/var/db/systemstats. When run without sudo it
#     logs a warning and exits 0 (so it never breaks an automated chain).
#
# Idempotent:
#   Safe to run repeatedly. A missing glob (nothing to delete) is treated as
#   success, not an error -- mirrors the harmless fish "No matches" message you
#   saw when re-running the manual rm.

set -euo pipefail

# --- Load shared library (logging, locking, prune helpers) -------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "$SCRIPT_DIR/../lib/common.sh"

with_lock "systemstats_purge"

STATS_DIR="/private/var/db/systemstats"
# Set KICK_DAEMON=1 to also `killall systemstats` after purging (relaunches
# automatically on the next scheduled interval). Off by default to stay gentle.
KICK_DAEMON="${SYSTEMSTATS_KICK_DAEMON:-0}"

log_info "systemstats purge started"

# --- Privilege check (soft-fail to keep automated chains green) --------------
if [[ ${EUID} -ne 0 ]]; then
	log_warn "Not running as root; skipping systemstats purge (run via sudo to enable)."
	log_info "systemstats purge complete (no-op)"
	exit 0
fi

if [[ ! -d ${STATS_DIR} ]]; then
	log_warn "Stats directory ${STATS_DIR} not found; nothing to purge."
	exit 0
fi

# --- Purge accumulated .stats history ----------------------------------------
# nullglob keeps the loop quiet when there is nothing to match.
shopt -s nullglob
stats_files=("${STATS_DIR}"/*.stats)
shopt -u nullglob

PURGED=0
if [[ ${#stats_files[@]} -gt 0 ]]; then
	if [[ ${DRY_RUN:-0} == "1" ]]; then
		log_info "[DRY_RUN] Would remove ${#stats_files[@]} *.stats file(s) from ${STATS_DIR}"
	else
		rm -f "${stats_files[@]}" 2>/dev/null || true
		PURGED=${#stats_files[@]}
		log_info "Removed ${PURGED} *.stats file(s) from ${STATS_DIR}"
	fi
else
	log_info "No *.stats files present in ${STATS_DIR} (already clean)"
fi

# --- Optionally kick the running daemon --------------------------------------
if [[ ${KICK_DAEMON} == "1" && ${DRY_RUN:-0} != "1" ]]; then
	if killall systemstats 2>/dev/null; then
		log_info "Sent SIGTERM to running systemstats (will relaunch on next interval)"
	else
		log_info "No running systemstats instance to kick"
	fi
fi

notify "systemstats Purge" "Removed ${PURGED} stats file(s)"
log_info "systemstats purge complete"
echo "systemstats purge completed successfully!"
