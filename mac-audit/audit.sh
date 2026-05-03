#!/usr/bin/env bash
# audit.sh — Mac System Audit Tool
# Usage: ./audit.sh [--report] [--ci] [--module launch|brew|defaults|all]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"
REPORT_DIR="$SCRIPT_DIR/reports"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="$REPORT_DIR/audit_$TIMESTAMP.txt"

# shellcheck source=lib/colors.sh
source "$LIB_DIR/colors.sh"
# shellcheck source=lib/launch_agents.sh
source "$LIB_DIR/launch_agents.sh"
# shellcheck source=lib/brew_audit.sh
source "$LIB_DIR/brew_audit.sh"
# shellcheck source=lib/defaults_audit.sh
source "$LIB_DIR/defaults_audit.sh"

SAVE_REPORT=false
MODULE="all"
export CI_MODE=false

while [[ $# -gt 0 ]]; do
	case "$1" in
	--report) SAVE_REPORT=true ;;
	--ci) CI_MODE=true ;;
	--module)
		MODULE="${2:-all}"
		case "$MODULE" in
		launch | brew | defaults | all) ;;
		*)
			fail "Unknown module: $MODULE"
			exit 1
			;;
		esac
		shift
		;;
	-h | --help)
		echo "Usage: $0 [--report] [--ci] [--module launch|brew|defaults|all]"
		exit 0
		;;
	*)
		echo "Unknown flag: $1"
		exit 1
		;;
	esac
	shift
done

printf "\n%b╔══════════════════════════════════════════╗%b\n" "${BOLD}" "${RESET}"
printf "%b║       Mac Audit Tool  •  %s       ║%b\n" "${BOLD}" "$(date +'%Y-%m-%d')" "${RESET}"
printf "%b╚══════════════════════════════════════════╝%b\n" "${BOLD}" "${RESET}"
info "Host:  $(hostname)"
info "macOS: $(sw_vers -productVersion) ($(sw_vers -buildVersion))"
info "Arch:  $(uname -m)"
[[ $CI_MODE == "true" ]] && info "Mode:  CI (hardware-only checks skipped)"

run_module() {
	case "$1" in
	launch) check_launch_agents ;;
	brew) check_brew ;;
	defaults) check_defaults ;;
	*)
		fail "Unknown module: $1"
		exit 1
		;;
	esac
}

if [[ $MODULE == "all" ]]; then
	check_launch_agents
	check_brew
	check_defaults
else
	run_module "$MODULE"
fi

header "Audit Summary"
printf "  Launch agents flagged : %s / %s\n" \
	"${LAUNCH_AGENTS_FLAGGED:-N/A}" "${LAUNCH_AGENTS_TOTAL:-N/A}"
printf "  Brew outdated         : %s\n" "${BREW_OUTDATED:-N/A}"
printf "  Brew casks installed  : %s\n" "${BREW_CASKS:-N/A}"
echo

if [[ $SAVE_REPORT == true ]]; then
	mkdir -p "$REPORT_DIR"
	tmp_report=$(mktemp "$REPORT_DIR/audit.XXXXXX.tmp")
	"$0" --module all ${CI_MODE:+--ci} 2>&1 |
		sed 's/\x1b\[[0-9;]*m//g' >"$tmp_report"
	mv "$tmp_report" "$REPORT_FILE"
	info "Report saved: $REPORT_FILE"
fi

FAIL_COUNT=$((${LAUNCH_AGENTS_FLAGGED:-0}))
[[ $FAIL_COUNT -gt 0 ]] && exit 1 || exit 0
