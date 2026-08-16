#!/bin/bash
# report-daemons-watchdog.sh - break Report* thrash loops
set -u
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"

log() { echo "[$(date "+%Y-%m-%d %H:%M:%S")] $*"; }
UID_NUM=$(id -u)
log "start uid=${UID_NUM}"

# Repair App Tamer rules if needed (fast python)
PREFS="$HOME/Library/Preferences/com.stclairsoft.AppTamer.plist"
if [[ -f "$PREFS" ]]; then
  /usr/bin/python3 - "$PREFS" <<'PY'
import plistlib, sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    data = plistlib.loads(p.read_bytes())
except Exception as e:
    print("apptamer_prefs_read_error", e)
    raise SystemExit(0)
targets = {
    "ReportCrash", "ReportCrashService", "ReportMemoryException",
    "CrashReporterSupportHelper", "osanalyticshelper", "ReportSystemMemory",
}
needles = ("reportcrash", "reportmemory", "osanalytics", "crashreporter")
changed = False
for key, val in list(data.items()):
    if not isinstance(val, dict):
        continue
    name = str(key)
    bid = str(val.get("bundleID", key))
    if name in targets or bid in targets or any(n in name.lower() or n in bid.lower() for n in needles):
        for k, v in {
            "pauseInBackground": False,
            "limitInBackground": False,
            "limitInForeground": False,
            "lowQOSInBackground": False,
            "quitWhenIdle": False,
        }.items():
            if val.get(k) != v:
                val[k] = v
                changed = True
        if isinstance(val.get("cpuLimit"), (int, float)) and float(val["cpuLimit"]) < 1.0:
            val["cpuLimit"] = 1.0
            changed = True
        data[key] = val
if changed:
    p.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY))
    print("apptamer_prefs_repaired=1")
else:
    print("apptamer_prefs_ok=1")
PY
fi

# Disable user-domain reporters (ignore failures)
for svc in   "gui/${UID_NUM}/com.apple.ReportCrash"   "gui/${UID_NUM}/com.apple.ReportCrashService"   "gui/${UID_NUM}/com.apple.ReportMemoryException"
do
  launchctl disable "$svc" >/dev/null 2>&1 || true
done

# Best-effort system disable if sudo -n works
if sudo -n true >/dev/null 2>&1; then
  for svc in     system/com.apple.ReportCrash.Root     system/com.apple.ReportCrash     system/com.apple.ReportCrashService     system/com.apple.ReportMemoryException     system/com.apple.ReportMemoryService     system/com.apple.ReportMemory
  do
    sudo launchctl disable "$svc" >/dev/null 2>&1 || true
  done
  log "system_disable_attempted=1"
else
  log "sudo_unavailable=1"
fi

# CONT then KILL any leftover Report* processes
pids=$(pgrep -f "ReportCrash|ReportMemoryException|ReportCrashService" 2>/dev/null || true)
if [[ -n "${pids}" ]]; then
  log "found_pids=${pids//$'
'/,}"
  for pid in $pids; do
    st=$(ps -p "$pid" -o state= 2>/dev/null | tr -d " " || true)
    if [[ "${st}" == T* ]]; then
      kill -CONT "$pid" 2>/dev/null || true
      log "cont pid=$pid"
    fi
  done
  for pid in $pids; do
    kill -KILL "$pid" 2>/dev/null || true
    log "kill pid=$pid"
  done
else
  log "no_report_pids"
fi

left=$(pgrep -f "ReportCrash|ReportMemoryException|ReportCrashService" 2>/dev/null | wc -l | tr -d " ")
log "live_report_procs=${left}"
log "done"
