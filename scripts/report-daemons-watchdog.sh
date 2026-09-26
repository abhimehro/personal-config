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
# SECURITY: `pgrep -x --` so a future non-allowlisted name cannot be parsed as a pgrep option (CWE-88).
for name in ReportCrash ReportCrashService ReportMemoryException; do
	pids="$(pgrep -x -- "$name" 2>/dev/null | tr '\n' ',' | sed 's/,$//' || true)"
	if [[ -n $pids ]]; then
		log "process=$name pids=$pids action=leave-alone"
		found=1
	fi
done

if [[ $found -eq 0 ]]; then
	log "no_report_processes"
fi

# Stuck-reporter detection (alert-only).
#
# A healthy ReportCrash* worker exits within seconds of writing its report. A
# worker that stays alive for a long time while using no CPU is hung mid-report.
# We only FLAG such processes; we never kill, disable, throttle, or restart
# anything. Threshold: alive more than STUCK_THRESHOLD_SECS and effectively idle
# (instantaneous CPU below STUCK_IDLE_CPU percent).
#
# macOS BSD ps supports etime ([[dd-]hh:]mm:ss), not POSIX etimes. Parse etime
# into seconds. ReportCrash.Root appears as "ReportCrash daemon" (uid 0); the
# per-user worker is "ReportCrash agent". Both share the ReportCrash basename.
STUCK_THRESHOLD_SECS=600 # 10 minutes
STUCK_IDLE_CPU=0.5       # percent; below this counts as effectively idle

# Convert BSD ps etime ([[dd-]hh:]mm:ss) to integer seconds.
etime_to_seconds() {
	local etime="$1"
	local days=0 rest hours=0 mins=0 secs=0
	etime="${etime// /}"
	if [[ $etime == *-* ]]; then
		days="${etime%%-*}"
		rest="${etime#*-}"
	else
		rest="$etime"
	fi
	IFS=':' read -r a b c <<<"$rest"
	if [[ -n ${c:-} ]]; then
		hours=$a
		mins=$b
		secs=$c
	else
		hours=0
		mins=$a
		secs=$b
	fi
	# Force base-10: ps may zero-pad fields (08, 09).
	echo $((10#$days * 86400 + 10#$hours * 3600 + 10#$mins * 60 + 10#$secs))
}

check_stuck() {
	local name="$1"
	local pid etime_raw cpu etime_sec role uid
	for pid in $(pgrep -x -- "$name" 2>/dev/null); do
		# etime = [[dd-]hh:]mm:ss on macOS; %cpu = instantaneous usage
		read -r etime_raw cpu uid <<<"$(ps -p "$pid" -o etime=,%cpu=,uid= 2>/dev/null)"
		[[ -n ${etime_raw:-} && -n ${cpu:-} ]] || continue
		etime_sec="$(etime_to_seconds "$etime_raw")"
		[[ -n $etime_sec && $etime_sec -gt 0 ]] || continue

		role="worker"
		if [[ $uid == "0" ]]; then
			role="root-daemon"
		fi
		# Prefer args label when present (agent vs daemon).
		case "$(ps -p "$pid" -o args= 2>/dev/null)" in
		*" daemon"*) role="root-daemon" ;;
		*" agent"*) role="user-agent" ;;
		esac

		if ((etime_sec > STUCK_THRESHOLD_SECS)) &&
			awk -v c="$cpu" -v t="$STUCK_IDLE_CPU" 'BEGIN{exit !(c+0 < t+0)}'; then
			log "STUCK_REPORTER name=$name role=$role pid=$pid elapsed_sec=$etime_sec cpu_pct=$cpu ts=$(date '+%Y-%m-%dT%H:%M:%S%z') action=alert-only"
		fi
	done
}

for name in ReportCrash ReportCrashService ReportMemoryException; do
	check_stuck "$name"
done

log "done"
