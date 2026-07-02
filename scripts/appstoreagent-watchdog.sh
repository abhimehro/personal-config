#!/bin/bash
#
# appstoreagent-watchdog.sh - Auto-pause a runaway appstoreagent process
#
# Background: Since the most recent macOS update, `appstoreagent` has been
# observed getting stuck in a retry loop (reportedly tied to a malformed
# Apple Arcade "recent_times" query) and pegging the CPU continuously
# instead of running briefly in the background as it normally does.
# Killing it outright just causes launchd/the App Store to respawn it into
# the same loop, so this watchdog instead sends SIGSTOP to freeze it when
# it spikes, then SIGCONT after a cooldown to give it a chance to settle.
# If it spikes again after being resumed, it gets paused again on the next
# check.
#
# Usage:
#   bash appstoreagent-watchdog.sh            # single check (used by launchd)
#   bash appstoreagent-watchdog.sh --once      # same as above, explicit
#   bash appstoreagent-watchdog.sh --status    # print current state, no action
#
set -uo pipefail

PROCESS_NAME="appstoreagent"
CPU_THRESHOLD=20 # percent; sustained above this triggers a pause
COOLDOWN_SECONDS=300 # how long to keep it paused before resuming
STATE_DIR="$HOME/Library/Application Support/appstoreagent-watchdog"
STATE_FILE="$STATE_DIR/paused_since"
LOG_MODE="${1:-once}"

mkdir -p "$STATE_DIR"

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

get_pid() {
	pgrep -x "$PROCESS_NAME" 2>/dev/null | head -n1
}

get_cpu_percent() {
	local pid="$1"
	ps -p "$pid" -o %cpu= 2>/dev/null | tr -d ' '
}

get_proc_state() {
	local pid="$1"
	ps -p "$pid" -o state= 2>/dev/null | tr -d ' '
}

is_stopped_state() {
	# macOS ps reports a leading 'T' in the state string for stopped processes
	[[ $1 == T* ]]
}

pause_process() {
	local pid="$1"
	if kill -STOP "$pid" 2>/dev/null; then
		date +%s >"$STATE_FILE"
		log "⏸️  Paused $PROCESS_NAME (pid $pid) - CPU exceeded ${CPU_THRESHOLD}% threshold"
		return 0
	fi
	log "❌ Failed to pause $PROCESS_NAME (pid $pid)"
	return 1
}

resume_process() {
	local pid="$1"
	if kill -CONT "$pid" 2>/dev/null; then
		rm -f "$STATE_FILE"
		log "▶️  Resumed $PROCESS_NAME (pid $pid) after cooldown"
		return 0
	fi
	log "❌ Failed to resume $PROCESS_NAME (pid $pid)"
	return 1
}

main() {
	local pid cpu state paused_since elapsed

	pid=$(get_pid)

	if [[ -z $pid ]]; then
		log "ℹ️  $PROCESS_NAME is not currently running - nothing to do"
		rm -f "$STATE_FILE"
		exit 0
	fi

	state=$(get_proc_state "$pid")

	if [[ "$LOG_MODE" == "--status" ]]; then
		cpu=$(get_cpu_percent "$pid")
		log "$PROCESS_NAME pid=$pid state=$state cpu=${cpu:-unknown}%"
		exit 0
	fi

	# Already paused by us: check whether the cooldown has elapsed
	if [[ -f $STATE_FILE ]] && is_stopped_state "$state"; then
		paused_since=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
		elapsed=$(($(date +%s) - paused_since))
		if [[ $elapsed -ge $COOLDOWN_SECONDS ]]; then
			resume_process "$pid"
		else
			log "⏳ $PROCESS_NAME still cooling down (${elapsed}s / ${COOLDOWN_SECONDS}s)"
		fi
		exit 0
	fi

	# Stopped, but not by us (or state file missing) - leave it alone
	if is_stopped_state "$state"; then
		log "ℹ️  $PROCESS_NAME is stopped externally - leaving as-is"
		exit 0
	fi

	cpu=$(get_cpu_percent "$pid")
	if [[ -z $cpu ]]; then
		log "⚠️  Could not read CPU usage for pid $pid"
		exit 0
	fi

	# Compare as integer (drop decimal portion) to avoid needing bc/awk
	cpu_int=${cpu%%.*}
	if [[ $cpu_int -ge $CPU_THRESHOLD ]]; then
		log "🔥 $PROCESS_NAME (pid $pid) at ${cpu}% CPU - exceeds ${CPU_THRESHOLD}% threshold"
		pause_process "$pid"
	else
		log "✅ $PROCESS_NAME (pid $pid) at ${cpu}% CPU - within normal range"
	fi
}

main
