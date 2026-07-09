#!/usr/bin/env bash
#
# One-screen Control D health check — plain English, no jargon dump.
#
# USAGE:
#   ./scripts/controld-status.sh
#   fish:  ./scripts/controld-status.sh
#
# Reads /etc/controld/status when present (world-readable). Falls back to
# dig + process inspection. Does not require sudo for the common WORKING case.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/controld-service.sh
source "$ROOT/scripts/lib/controld-service.sh" 2>/dev/null || true

STATUS_FILE="${CONTROLD_STATUS_FILE:-/etc/controld/status}"
ACTIVE_FILE="/etc/controld/active_profile"
TOML="/etc/controld/ctrld.toml"
LISTENER="${CONTROLD_LISTENER_IP:-127.0.0.1}"

_bin=""
_ver="unknown"
if command -v _resolve_ctrld_bin >/dev/null 2>&1; then
	_bin=$(_resolve_ctrld_bin 2>/dev/null || true)
	_ver=$(_ctrld_installed_version 2>/dev/null || true)
else
	_bin=$(command -v ctrld 2>/dev/null || true)
	[[ -n $_bin ]] && _ver=$("$_bin" --version 2>/dev/null | head -1 || true)
fi

dig_ok=0
dig_sample=""
if dig_sample=$(dig @"$LISTENER" google.com +short +time=2 +tries=1 2>/dev/null | head -3 | tr '\n' ' '); then
	if [[ -n ${dig_sample// /} ]]; then
		dig_ok=1
	fi
fi

proc_alive=0
proc_cmd=""
if pgrep -x ctrld >/dev/null 2>&1; then
	proc_alive=1
	proc_cmd=$(pgrep -lf ctrld 2>/dev/null | head -1 || true)
fi

port53="none"
if command -v lsof >/dev/null 2>&1; then
	port53=$(lsof -nP -iUDP:53 -iTCP:53 2>/dev/null | awk 'NR>1 {print $1; exit}' || echo "none")
	[[ -z $port53 ]] && port53="none"
fi

mode="unknown"
profile="unknown"
protocol="unknown"
state="UNKNOWN"
fallback=""

if [[ -r $STATUS_FILE ]]; then
	# shellcheck disable=SC1090
	source "$STATUS_FILE" 2>/dev/null || true
	state="${STATE:-$state}"
	mode="${MODE:-$mode}"
	profile="${PROFILE:-$profile}"
	protocol="${PROTOCOL:-$protocol}"
fi

if [[ -r $ACTIVE_FILE ]]; then
	# shellcheck disable=SC1090
	source "$ACTIVE_FILE" 2>/dev/null || true
	profile="${PROFILE_NAME:-$profile}"
	protocol="${PROTOCOL:-$protocol}"
	fallback="${FALLBACK:-}"
fi

if [[ $mode == "unknown" ]]; then
	if [[ -r $TOML ]] && head -1 "$TOML" 2>/dev/null | grep -q 'AUTO-GENERATED VIA CD FLAG'; then
		mode="cd_mode"
	elif [[ $fallback == "1" ]] || { [[ -r $TOML ]] && grep -qE "dns\.controld\.com/[A-Za-z0-9]+" "$TOML" 2>/dev/null && ! grep -q 'AUTO-GENERATED VIA CD FLAG' "$TOML" 2>/dev/null; }; then
		mode="local_fallback"
	elif [[ $proc_alive -eq 1 && $dig_ok -eq 1 ]]; then
		# Config not readable without sudo — infer from live listener (typical FALLBACK path).
		mode="local_fallback"
	elif [[ $proc_alive -eq 0 ]]; then
		mode="stopped"
	fi
fi

if [[ $dig_ok -eq 1 && $proc_alive -eq 1 ]]; then
	state="WORKING"
elif [[ $dig_ok -eq 0 && $proc_alive -eq 1 ]]; then
	state="BROKEN"
elif [[ $dig_ok -eq 0 && $proc_alive -eq 0 ]]; then
	state="BROKEN"
fi

mode_plain="$mode"
case "$mode" in
cd_mode) mode_plain="CD Mode (API-generated config)" ;;
local_fallback) mode_plain="Local Config fallback (real profile endpoint — NOT free DNS)" ;;
stopped) mode_plain="stopped" ;;
esac

echo "=== Control D status ==="
if [[ $state == "WORKING" ]]; then
	echo "Verdict:  WORKING"
else
	echo "Verdict:  BROKEN (or not running)"
fi
echo "Mode:     $mode_plain"
echo "Profile:  $profile  protocol=$protocol"
echo "dig @$LISTENER: $([[ $dig_ok -eq 1 ]] && echo "OK → ${dig_sample}" || echo "FAIL (timeout/empty)")"
echo "Binary:   ${_bin:-not found}"
echo "Version:  $_ver"
echo "Port 53:  $port53"
if [[ -n $proc_cmd ]]; then
	echo "Process:  $proc_cmd"
else
	echo "Process:  (not running)"
fi
if [[ -r $STATUS_FILE ]]; then
	echo "Status file: $STATUS_FILE (readable)"
elif [[ -e $STATUS_FILE ]]; then
	echo "Status file: $STATUS_FILE (exists but not readable — run repair once as root)"
else
	echo "Status file: (none yet — created on next successful repair)"
fi
if [[ ! -r $ACTIVE_FILE && -e $ACTIVE_FILE ]]; then
	echo "Note:     active_profile is root-only — use: sudo cat $ACTIVE_FILE"
	echo "          (or read $STATUS_FILE after repair; fish/bat Permission denied is not a DNS failure)"
fi
echo ""
if [[ $state == "WORKING" && $mode == "local_fallback" ]]; then
	echo "Note: CD Mode (--cd) still fails on Control D API exclude schema (even v1.5.3)."
	echo "      Local Config with your profile ID is the intentional stable path for now."
elif [[ $state != "WORKING" ]]; then
	echo "Fix:  sudo $ROOT/scripts/repair-controld-keepalive.sh --restart privacy"
	echo "Then: $ROOT/scripts/controld-status.sh"
fi
