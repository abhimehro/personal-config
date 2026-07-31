#!/bin/bash
# Gaming Mode - Toggle media infrastructure off for latency-critical sessions.
# For NVIDIA GeForce NOW and similar: reclaim CPU/network/memory by pausing the
# media stack (mount, server, Jellyfin, renamer, watchdog).
#
# USAGE:
#   gaming-mode          Toggle (suspend if up, restore if down)
#   gaming-mode on       Unload all media launch agents
#   gaming-mode off      Reload + start all media launch agents
#   gaming-mode status   Show current state of each agent
#
# NOTES:
# - Stop uses `launchctl bootout` (clean unload). Restore uses `launchctl
#   bootstrap <plist>` (loads the job), then `kickstart` to force-run now.
#   bootstrap is required because bootout removes the job from the domain, and
#   only bootstrap reliably re-adds it.
# - On next login RunAtLoad also brings the stack back up normally.
# - Safe to run repeatedly; each step is idempotent.
set -uo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

AGENTS=(
	"com.speedybee.jellyfin"
	"com.speedybee.media.renamer"
	"com.speedybee.media.server"
	"com.speedybee.media.mount"
	"com.speedybee.media.mount-watchdog"
)

DOMAIN="gui/$(id -u)"

log() { echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $*"; }

plist_for() { echo "$HOME/Library/LaunchAgents/$1.plist"; }

agent_in_domain() { launchctl print "$DOMAIN/$1" &>/dev/null; }

agent_running() {
	local pid
	pid=$(launchctl list 2>/dev/null | awk -v a="$1" '$NF==a {print $1}')
	[[ -n $pid && $pid != "0" && $pid != "-" ]]
}

# Stack is "up" if any agent is registered in the domain.
current_state() {
	local a
	for a in "${AGENTS[@]}"; do
		if agent_in_domain "$a"; then
			echo "up"
			return
		fi
	done
	echo "down"
}

stop_stack() {
	log "Gaming Mode ON, suspending media stack..."
	local a
	for a in "${AGENTS[@]}"; do
		if agent_in_domain "$a"; then
			if launchctl bootout "$DOMAIN/$a" 2>/dev/null; then
				log "   paused  $a"
			else
				log "   warn    $a bootout failed"
			fi
		else
			log "   skip    $a already off"
		fi
	done
	log "Media stack suspended. Run gaming-mode off to restore."
}

start_stack() {
	log "Gaming Mode OFF, restoring media stack..."
	local i a plist
	local reversed=()
	for ((i = ${#AGENTS[@]} - 1; i >= 0; i--)); do reversed+=("${AGENTS[i]}"); done
	for a in "${reversed[@]}"; do
		plist=$(plist_for "$a")
		if [[ ! -f $plist ]]; then
			log "   warn    $a plist not found at $plist"
			continue
		fi
		if agent_in_domain "$a"; then
			launchctl kickstart -k "$DOMAIN/$a" 2>/dev/null && log "   restarted $a" || log "   warn    $a kickstart failed"
		else
			launchctl bootstrap "$DOMAIN" "$plist" 2>/dev/null && log "   started $a" || log "   warn    $a bootstrap failed"
		fi
	done
	log "Media stack restored. Give the mount ~10s (FSKit gate), then media-status."
}

show_status() {
	echo "Media stack agent status:"
	local a state
	for a in "${AGENTS[@]}"; do
		if ! agent_in_domain "$a"; then
			state="off (suspended)"
		elif agent_running "$a"; then
			state="RUNNING"
		else
			state="loaded (idle)"
		fi
		printf "   %-40s %s\n" "$a" "$state"
	done
	echo ""
	if [ "$(current_state)" = "up" ]; then
		echo "Overall: media stack is UP (gaming mode OFF)"
	else
		echo "Overall: media stack is DOWN (gaming mode ON)"
	fi
}

main() {
	case "${1:-toggle}" in
	on) stop_stack ;;
	off) start_stack ;;
	status) show_status ;;
	toggle)
		if [ "$(current_state)" = "up" ]; then stop_stack; else start_stack; fi
		;;
	*)
		echo "Usage: gaming-mode [on|off|status]"
		exit 1
		;;
	esac
}
main "$@"
