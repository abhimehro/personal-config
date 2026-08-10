#!/bin/bash
# report-daemons-watchdog.sh - observe Apple crash reporters without interfering
#
# ReportCrash*, including the root-owned ReportCrash.Root daemon, are managed by
# launchd. Killing or disabling them from a user LaunchAgent causes futile work,
# misleading logs, and can amplify crash/relaunch pressure. This compatibility
# script is intentionally read-only. Its historical path is retained so existing
# LaunchAgent installations continue to work safely.

set -u
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "start mode=observe-only uid=$(id -u)"

found=0
for name in ReportCrash ReportCrashService ReportMemoryException; do
    pids="$(pgrep -x "$name" 2>/dev/null | tr '\n' ',' | sed 's/,$//' || true)"
    if [[ -n "$pids" ]]; then
        log "process=$name pids=$pids action=leave-alone"
        found=1
    fi
done

if [[ "$found" -eq 0 ]]; then
    log "no_report_processes"
fi

log "done"
