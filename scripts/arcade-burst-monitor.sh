#!/bin/bash
#
# arcade-burst-monitor.sh - Read-only observer for the ArcadeResetPO launch storm
#
# Background: On macOS 27.0 (build 26A5425a), appstoreagent repeatedly
# dispatched the background task com.apple.appstored.ArcadeResetPO with a
# past-due scheduling timestamp, driving ~1,000-2,400 handler launches per
# minute and pegging dasd at 50-70% of a core (2026-09-06, ~00:28-02:00).
# The storm stopped at 02:00:00, immediately after Game Center settings were
# changed (Identifier reset; Share Friends List / Help Friends Find You /
# Nearby Players disabled; Activity Sharing set to Only You). Causality is
# not yet proven.
#
# Purpose: Verify the loop stays gone. If it returns, record precise burst
# start/stop timestamps, launch rates, and dasd/appstoreagent CPU so the
# responsible setting can be pinpointed. STRICTLY READ-ONLY: this script
# never signals, pauses, kills, or modifies any process.
#
# Watchdog gap (flagged for later, deliberately NOT fixed yet): the existing
# appstoreagent-watchdog only samples appstoreagent CPU%, which stayed at
# 4-6% during the storm while dasd carried the load, so it never fired. If
# this monitor confirms returning bursts, revisit the watchdog's detection
# logic (trigger on ArcadeResetPO churn or dasd load, not appstoreagent CPU
# alone).
#
# Usage:
#   bash arcade-burst-monitor.sh            # single check (used by launchd)
#   bash arcade-burst-monitor.sh --status   # print current state, no query
#
set -uo pipefail

LOG_BIN="/usr/bin/log" # NEVER bare `log` (collides with the zsh builtin)
TASK_NAME="com.apple.appstored.ArcadeResetPO"
PROCESS_NAME="appstoreagent"
BURST_THRESHOLD=60      # handler launches/min to count as a burst (~1/sec)
QUIET_RUNS_TO_END=5     # consecutive quiet runs before a burst is declared over
OVERLAP_GUARD_SECONDS=2 # re-scan slack so boundary events are never missed
MAX_WINDOW_SECONDS=3600 # clamp after sleep/missed runs to keep queries cheap
STATE_DIR="$HOME/Library/Application Support/arcade-burst-monitor"
LAST_CHECK_FILE="$STATE_DIR/last_check"
BURST_FILE="$STATE_DIR/burst_state"
LOG_MODE="${1:-once}"

mkdir -p "$STATE_DIR"

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

snapshot_cpu() {
	# Read-only CPU sample for a process name; "n/a" if not running
	local proc="$1" pid cpu
	pid=$(pgrep -x -- "$proc" 2>/dev/null | head -n1)
	[[ -z $pid ]] && {
		echo "n/a"
		return
	}
	cpu=$(ps -p "$pid" -o %cpu= 2>/dev/null | tr -d ' ')
	echo "${cpu:-n/a}%"
}

# ── Status mode: report state files, no log query ──────────────────────────
if [[ $LOG_MODE == "--status" ]]; then
	if [[ -s $BURST_FILE ]]; then
		b_start=$(awk '{print $1}' "$BURST_FILE")
		if [[ $b_start =~ ^[0-9]+$ ]]; then
			b_peak=$(awk '{print $2}' "$BURST_FILE")
			b_quiet=$(awk '{print $3}' "$BURST_FILE")
			log "STATUS: burst ACTIVE since $(date -r "$b_start" '+%Y-%m-%d %H:%M:%S'), peak ${b_peak:-0}/min, quiet runs ${b_quiet:-0}/${QUIET_RUNS_TO_END}"
		else
			log "STATUS: burst state file unreadable - will reset on next check"
		fi
	else
		log "STATUS: no active burst"
	fi
	if [[ -f $LAST_CHECK_FILE ]]; then
		lc=$(cat "$LAST_CHECK_FILE" 2>/dev/null || echo 0)
		if [[ $lc =~ ^[0-9]+$ ]]; then
			log "STATUS: last checked $(($(date +%s) - lc))s ago"
		else
			log "STATUS: checkpoint unreadable"
		fi
	else
		log "STATUS: no checkpoint yet (first run pending)"
	fi
	exit 0
fi

# ── Sanity: unified log must be available ──────────────────────────────────
if [[ ! -x $LOG_BIN ]]; then
	log "❌ $LOG_BIN missing or not executable - cannot query unified log"
	exit 0
fi

# ── Establish the query window from the last checkpoint ────────────────────
now=$(date +%s)
if [[ -f $LAST_CHECK_FILE ]]; then
	last_check=$(cat "$LAST_CHECK_FILE" 2>/dev/null || echo "")
else
	last_check=$((now - 60)) # first run: sample the past minute
fi

# Validate and clamp: never query a window larger than MAX_WINDOW_SECONDS
if [[ ! $last_check =~ ^[0-9]+$ ]] || ((last_check >= now)) || ((now - last_check > MAX_WINDOW_SECONDS)); then
	last_check=$((now - 60))
fi

elapsed=$((now - last_check))
((elapsed < 1)) && elapsed=1

start_fmt=$(date -r "$((last_check - OVERLAP_GUARD_SECONDS))" '+%Y-%m-%d %H:%M:%S')
end_fmt=$(date -r "$now" '+%Y-%m-%d %H:%M:%S')

# ── Query the unified log (read-only) ──────────────────────────────────────
tmp_out=$(mktemp) || {
	log "❌ mktemp failed - skipping this cycle"
	exit 0
}
if ! "$LOG_BIN" show \
	--start "$start_fmt" \
	--end "$end_fmt" \
	--style compact \
	--info --debug \
	--predicate "process == \"$PROCESS_NAME\" AND eventMessage CONTAINS \"$TASK_NAME\"" \
	>"$tmp_out" 2>/dev/null; then
	log "⚠️ log query failed for window $start_fmt → $end_fmt - skipping (checkpoint not advanced)"
	rm -f "$tmp_out"
	exit 0
fi
count=$(grep -c "Calling launch handler" "$tmp_out" || true)
rm -f "$tmp_out"

rate=$((count * 60 / elapsed))

# ── Burst state machine ────────────────────────────────────────────────────
burst_start=""
burst_peak=0
quiet_runs=0
if [[ -s $BURST_FILE ]]; then
	b_start=$(awk '{print $1}' "$BURST_FILE")
	if [[ $b_start =~ ^[0-9]+$ ]]; then
		burst_start=$b_start
		burst_peak=$(awk '{print $2}' "$BURST_FILE")
		quiet_runs=$(awk '{print $3}' "$BURST_FILE")
		[[ $burst_peak =~ ^[0-9]+$ ]] || burst_peak=0
		[[ $quiet_runs =~ ^[0-9]+$ ]] || quiet_runs=0
	else
		rm -f "$BURST_FILE" # corrupt state; reset
	fi
fi

if ((rate >= BURST_THRESHOLD)); then
	dasd_cpu=$(snapshot_cpu "dasd")
	agent_cpu=$(snapshot_cpu "$PROCESS_NAME")
	if [[ -z $burst_start ]]; then
		burst_start=$now
		burst_peak=0
		quiet_runs=0
		log "🚨 BURST START - $count handler launches in ${elapsed}s (rate ${rate}/min ≥ ${BURST_THRESHOLD}/min) | dasd ${dasd_cpu} | appstoreagent ${agent_cpu}"
	else
		log "🚨 BURST ACTIVE - $count launches in ${elapsed}s (rate ${rate}/min, peak ${burst_peak}/min, since $(date -r "$burst_start" '+%H:%M:%S')) | dasd ${dasd_cpu} | appstoreagent ${agent_cpu}"
	fi
	((rate > burst_peak)) && burst_peak=$rate
	printf '%s %s %s\n' "$burst_start" "$burst_peak" "$quiet_runs" >"$BURST_FILE"
elif [[ -n $burst_start ]]; then
	quiet_runs=$((quiet_runs + 1))
	if ((quiet_runs >= QUIET_RUNS_TO_END)); then
		duration=$((now - burst_start))
		log "✅ BURST ENDED - lasted $((duration / 60))m $((duration % 60))s, peak ${burst_peak}/min, end $(date '+%H:%M:%S')"
		rm -f "$BURST_FILE"
	else
		printf '%s %s %s\n' "$burst_start" "$burst_peak" "$quiet_runs" >"$BURST_FILE"
		log "⏳ burst cooling - rate ${rate}/min below ${BURST_THRESHOLD}/min, quiet run ${quiet_runs}/${QUIET_RUNS_TO_END}"
	fi
else
	log "✅ quiet - $count launches in ${elapsed}s (rate ${rate}/min)"
fi

# ── Advance checkpoint only after a fully successful cycle ─────────────────
printf '%s\n' "$now" >"$LAST_CHECK_FILE"
