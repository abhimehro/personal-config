#!/usr/bin/env bash
# ==============================================================================
# process_exclusions.sh
#
# Central leave-alone / protected-process policy for maintenance automation.
#
# WHY THIS EXISTS
# ---------------
# Under RAM pressure, App Tamer + launchctl disable/kill loops against Apple
# diagnostic agents (ReportCrash*, ReportMemoryException, osanalyticshelper)
# produced a relaunch storm (hundreds of stopped "T" processes, load > 300).
# Automated renice/kill/unload paths that touch core OS, audio, Spotlight, or
# VM guest services can also cause:
#   - launchd-driven relaunch loops
#   - WindowServer / session instability
#   - coreaudiod dropouts
#   - Spotlight thrash (mds / mds_stores)
#   - VM guest freezes (UTM / Parallels / VMware / Virtualization.framework)
#
# RULE
# ----
# Maintenance scripts may optimize eligible *user* apps. They must never
# restart, throttle, renice, unload, or kill anything matched here.
# ReportCrash containment is owned exclusively by scripts/report-daemons-watchdog.sh
# (App Tamer preference repair + targeted cleanup), not by generic optimizers.
#
# Usage:
#   SCRIPT_DIR=...; source "$SCRIPT_DIR/../lib/process_exclusions.sh"
#   if process_is_protected "$pid" "$comm" "$command_line"; then continue; fi
#   if service_label_is_protected "$label"; then continue; fi
# ==============================================================================

# Prevent double-load from rewriting arrays under set -u.
if [[ -n ${PROCESS_EXCLUSIONS_LOADED:-} ]]; then
	return 0 2>/dev/null || exit 0
fi
PROCESS_EXCLUSIONS_LOADED=1

# Exact process basenames / comm values that must never be automated against.
# Keep this list boring and explicit; prefer matching helpers below for prefixes.
PROTECTED_PROCESS_NAMES=(
	launchd
	kernel_task
	WindowServer
	WindowManager
	loginwindow
	coreaudiod
	mds
	mds_stores
	mdworker
	mdworker_shared
	corespotlightd
	SystemUIServer
	Dock
	Finder
	cfprefsd
	distnoted
	notifyd
	syslogd
	logd
	UserEventAgent
	launchservicesd
	coreduetd
	fileproviderd
	bird
	# VM / virtualization guest services and hosts
	VirtualMachine
	com.apple.Virtualization.VirtualMachine
	UTM
	qemu-system-aarch64
	qemu-system-x86_64
	prl_client_app
	prl_disp_service
	vmware-vmx
	# VPN / security agents that drop connectivity or auth if disturbed
	Windscribe
	1Password
	# Crash reporters: do not kill/renice from generic optimizers
	ReportCrash
	ReportCrashService
	ReportMemoryException
	ReportMemoryService
	osanalyticshelper
	CrashReporterSupportHelper
	ReportSystemMemory
	SubmitDiagInfo
)

# Substrings matched case-insensitively against comm or full command line.
PROTECTED_PROCESS_PATTERNS=(
	"com.apple."
	"/System/Library/"
	"/usr/libexec/"
	"Virtualization"
	"VirtualMachine"
	"ReportCrash"
	"ReportMemory"
	"osanalytics"
	"CrashReporter"
	"coreaudiod"
	"WindowServer"
	"mds_stores"
	"/mdworker"
	"UTM.app"
	"qemu-system"
	"prl_"
	"vmware"
	"Windscribe"
	"1Password"
	"BlackHole"
)

# launchctl labels / agent names that must not be disabled, unloaded, or
# re-enabled by service_optimizer / service_monitor / performance_optimizer.
PROTECTED_SERVICE_PATTERNS=(
	"com.apple.ReportCrash"
	"com.apple.ReportMemory"
	"com.apple.osanalytics"
	"com.apple.CrashReporter"
	"com.apple.SubmitDiagInfo"
	"com.apple.WindowServer"
	"com.apple.audio"
	"coreaudio"
	"com.apple.mds"
	"com.apple.metadata"
	"com.apple.Virtualization"
	"qemu"
	"utm"
	"prl"
	"vmware"
	"windscribe"
	"1password"
	"com.openssh.ssh-agent"
	"com.apple.ssh-agent"
)

# service_optimizer / service_monitor must never put these on a disable list.
REPORT_DAEMON_SERVICE_LABELS=(
	"com.apple.ReportCrash"
	"com.apple.ReportCrash.Root"
	"com.apple.ReportCrashService"
	"com.apple.ReportMemoryException"
	"com.apple.ReportMemoryService"
	"com.apple.ReportMemory"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_pe_lc() {
	# Portable lowercase (bash 3.2 on macOS has no ${var,,}).
	printf "%s" "$1" | tr "[:upper:]" "[:lower:]"
}

process_name_is_protected() {
	local name="${1:-}"
	[[ -z $name ]] && return 1
	local base n p
	base="${name##*/}"
	for n in "${PROTECTED_PROCESS_NAMES[@]}"; do
		if [[ $base == "$n" || $name == "$n" ]]; then
			return 0
		fi
	done
	local lc lp
	lc="$(_pe_lc "$name")"
	for p in "${PROTECTED_PROCESS_PATTERNS[@]}"; do
		lp="$(_pe_lc "$p")"
		if [[ $lc == *"$lp"* ]]; then
			return 0
		fi
	done
	return 1
}

# process_is_protected [pid] [comm] [full_command]
# Any one of the identifiers may be empty. Returns 0 if protected.
process_is_protected() {
	local pid="${1:-}"
	local comm="${2:-}"
	local full="${3:-}"

	if [[ -n $comm ]] && process_name_is_protected "$comm"; then
		return 0
	fi
	if [[ -n $full ]] && process_name_is_protected "$full"; then
		return 0
	fi

	# Resolve from pid when callers only have a PID.
	if [[ -n $pid && $pid =~ ^[0-9]+$ ]]; then
		local resolved_comm resolved_args
		resolved_comm="$(ps -p "$pid" -o comm= 2>/dev/null | sed "s/^ *//;s/ *$//" || true)"
		resolved_args="$(ps -p "$pid" -o args= 2>/dev/null | sed "s/^ *//" || true)"
		if [[ -n $resolved_comm ]] && process_name_is_protected "$resolved_comm"; then
			return 0
		fi
		if [[ -n $resolved_args ]] && process_name_is_protected "$resolved_args"; then
			return 0
		fi
		# Never touch PID 0/1 style core daemons if somehow presented.
		if [[ $pid -le 1 ]]; then
			return 0
		fi
	fi
	return 1
}

service_label_is_protected() {
	local label="${1:-}"
	[[ -z $label ]] && return 1
	local lc p fixed lf
	lc="$(_pe_lc "$label")"
	for fixed in "${REPORT_DAEMON_SERVICE_LABELS[@]}"; do
		lf="$(_pe_lc "$fixed")"
		if [[ $lc == "$lf" || $lc == *"$lf"* ]]; then
			return 0
		fi
	done
	for p in "${PROTECTED_SERVICE_PATTERNS[@]}"; do
		lf="$(_pe_lc "$p")"
		if [[ $lc == *"$lf"* ]]; then
			return 0
		fi
	done
	return 1
}

# Filter a newline-separated PID list, printing only unprotected PIDs.
filter_unprotected_pids() {
	local pid
	while IFS= read -r pid; do
		pid="${pid// /}"
		[[ -z $pid ]] && continue
		if process_is_protected "$pid"; then
			continue
		fi
		printf "%s\n" "$pid"
	done
}

# True if a problem-process kill pattern is too broad / protected.
problem_process_pattern_is_protected() {
	local pattern="${1:-}"
	[[ -z $pattern ]] && return 0
	# Inert placeholder used by service_monitor under bash 3.2 + set -u
	[[ $pattern == __service_monitor_no_problem_processes__ ]] && return 0
	process_name_is_protected "$pattern" || service_label_is_protected "$pattern"
}
