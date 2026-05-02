#!/usr/bin/env bash
# lib/launch_agents.sh — audit Launch Agents and Daemons
# Variables set here (LAUNCH_AGENTS_FLAGGED, LAUNCH_AGENTS_TOTAL) are consumed
# by the parent audit.sh after sourcing; shellcheck can't see cross-file usage.
# shellcheck disable=SC2034
set -euo pipefail

check_launch_agents() {
	header "Launch Agents & Daemons"
	local dirs=("$HOME/Library/LaunchAgents" "/Library/LaunchAgents"
		"/Library/LaunchDaemons" "/System/Library/LaunchDaemons")
	local suspicious_patterns=(".tmp." "unknown" "com.adobe."
		"com.google.keystone" "com.oracle.java")
	local total=0 flagged=0
	for dir in "${dirs[@]}"; do
		[[ -d $dir ]] || continue
		info "Scanning: $dir"
		while IFS= read -r -d '' plist; do
			total=$((total + 1))
			local label program
			label=$(defaults read "$plist" Label 2>/dev/null || basename "$plist" .plist)
			program=$(defaults read "$plist" Program 2>/dev/null ||
				defaults read "$plist" ProgramArguments 2>/dev/null ||
				echo "(none)")
			label=${label//$'\n'/ }
			label=${label//$'\r'/ }
			label=${label//$'\t'/ }
			program=${program//$'\n'/ }
			program=${program//$'\r'/ }
			program=${program//$'\t'/ }
			local flagged_this=0
			for pattern in "${suspicious_patterns[@]}"; do
				if echo "$label $program" | grep -qiF "$pattern"; then
					warn "Flagged: $label  →  $program"
					flagged=$((flagged + 1))
					flagged_this=1
					break
				fi
			done
			local bin
			bin=$(defaults read "$plist" Program 2>/dev/null || true)
			if [[ -n $bin && ! -e $bin && $flagged_this -eq 0 ]]; then
				if defaults read "$plist" _LimitLoadToBootMode >/dev/null 2>&1; then
					info "Boot-mode limited daemon binary unavailable outside its boot context: $label  →  $bin"
				elif [[ $plist == /System/Library/LaunchDaemons/* ]]; then
					info "Apple system daemon references unavailable binary (often expected on modern macOS): $label  →  $bin"
				else
					if [[ -L $bin ]]; then
						warn "Orphaned (broken symlink): $label  →  $bin"
					else
						warn "Orphaned (binary missing): $label  →  $bin"
					fi
					flagged=$((flagged + 1))
				fi
			fi
		done < <(find "$dir" -maxdepth 1 -name "*.plist" -print0 2>/dev/null)
	done
	echo
	if [[ $flagged -eq 0 ]]; then
		pass "Checked $total agents/daemons — none flagged"
	else
		fail "$flagged/$total agents/daemons flagged"
	fi
	LAUNCH_AGENTS_FLAGGED=$flagged
	LAUNCH_AGENTS_TOTAL=$total
}
