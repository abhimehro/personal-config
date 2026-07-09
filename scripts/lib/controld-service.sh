#!/bin/bash
#
# Control D Service Management Library
# Service lifecycle management, directory setup, and status reporting.
#
# Usage: source "scripts/lib/controld-service.sh"

# Source Guard
if [[ ${_CONTROLD_SERVICE_SH_-} == "true" ]]; then
	return
fi
_CONTROLD_SERVICE_SH_="true"

# State file for currently active profile
ACTIVE_PROFILE_FILE="${CONTROLD_DIR:-/etc/controld}/active_profile"

# Setup necessary directory structure
setup_directories() {
	local controld_dir="$1"
	local profiles_dir="$2"
	local backup_dir="$3"
	local log_file="$4"

	# Pre-flight hardening for log file to prevent symlink-based log hijacking
	if [[ -L $log_file ]]; then
		echo "Security Alert: $log_file is a symlink! Aborting to prevent log hijack." >&2
		return 1
	fi
	if [[ -e $log_file && ! -f $log_file ]]; then
		echo "Security Alert: $log_file is not a regular file! Aborting." >&2
		return 1
	fi

	# Sentinel: Verify all critical paths are not symlinks before creation
	_check_not_symlink() {
		local path="$1" label="${2:-$1}"
		if command -v assert_not_symlink >/dev/null 2>&1; then
			assert_not_symlink "$path" "$label" || { return 1; }
		elif [[ -L $path ]]; then
			return 1
		fi
		return 0
	}

	_check_not_symlink "$controld_dir" "CONTROLD_DIR" || return 1
	_check_not_symlink "$profiles_dir" "PROFILES_DIR" || return 1
	_check_not_symlink "$backup_dir" "BACKUP_DIR" || return 1

	# Sentinel: Securely create directories
	if command -v secure_mkdir >/dev/null 2>&1; then
		secure_mkdir "$controld_dir" 700 || return 1
		secure_mkdir "$profiles_dir" 700 || return 1
		secure_mkdir "$backup_dir" 700 || return 1
	else
		[[ -e $controld_dir && ! -d $controld_dir ]] && return 1
		install -d -m 700 "$controld_dir" "$profiles_dir" "$backup_dir"
	fi

	# Sentinel: Post-creation verification
	if [[ -L $controld_dir ]] || [[ -L $profiles_dir ]] || [[ -L $backup_dir ]]; then
		return 1
	fi
	if [[ ! -d $controld_dir ]] || [[ ! -d $profiles_dir ]] || [[ ! -d $backup_dir ]]; then
		return 1
	fi

	# Sentinel: Securely create log file
	if [[ -L $log_file ]]; then
		rm -f "$log_file"
	fi
	if [[ ! -e $log_file ]]; then
		(umask 077 && touch "$log_file") 2>/dev/null || true
	fi

	if [[ -L $log_file ]]; then
		: # Skip permission change
	elif [[ -f $log_file ]]; then
		chmod 600 "$log_file" 2>/dev/null || true
	fi

	return 0
}

# Wait for process to stop
_wait_for_process_stop() {
	if command -v wait_for_process_stop >/dev/null 2>&1; then
		wait_for_process_stop "$@"
		return
	fi
	local process_name="$1"
	local max_retries="${2:-20}"
	local retry=0
	while pgrep -x -- "$process_name" >/dev/null 2>&1 && [[ $retry -lt $max_retries ]]; do
		sleep 0.1
		retry=$((retry + 1))
	done
}

# Stop ctrld without fighting LaunchDaemon KeepAlive.
# Prefer `service stop` (disables respawn) before any kill. Blind pkill while
# KeepAlive=true just respawns the old unit and races the next start — that is
# the crash-loop / empty-homedir failure mode (launchctl runs count climbing).
_stop_ctrld_cleanly() {
	local max_retries="${1:-50}"
	local retry=0

	_ensure_ctrld_on_path
	# Order matters: service stop first so KeepAlive cannot immediately revive.
	_ctrld service stop 2>/dev/null || true
	_ctrld stop 2>/dev/null || true

	while pgrep -x "ctrld" >/dev/null 2>&1 && [[ $retry -lt $max_retries ]]; do
		_ctrld service stop 2>/dev/null || true
		sleep 0.1
		retry=$((retry + 1))
	done

	if pgrep -x "ctrld" >/dev/null 2>&1; then
		# Last resort: uninstall clears KeepAlive, then terminate stragglers.
		_ctrld service uninstall 2>/dev/null || true
		pkill -x ctrld 2>/dev/null || true
		_wait_for_process_stop "ctrld" 30
		if pgrep -x "ctrld" >/dev/null 2>&1; then
			pkill -9 -x ctrld 2>/dev/null || true
			sleep 0.1
		fi
	fi
}

# Safely stop the Control D service
safe_stop() {
	local backup_dir="$1"

	_stop_ctrld_cleanly 50

	if command -v restore_network_settings >/dev/null 2>&1; then
		restore_network_settings "$backup_dir"
	fi

	rm -f "$ACTIVE_PROFILE_FILE" 2>/dev/null || true

	return 0
}

# Default DNS readiness budget: wall-clock first (silent hang killer), then retry cap.
# Fresh `ctrld start --cd` often needs several seconds before UDP :53 answers;
# KeepAlive respawn gaps must not abort early — but NEVER wait silently for minutes.
CONTROLD_DNS_READY_BUDGET_S="${CONTROLD_DNS_READY_BUDGET_S:-45}"
CONTROLD_DNS_READY_RETRIES="${CONTROLD_DNS_READY_RETRIES:-300}"
CONTROLD_DNS_READY_SLEEP="${CONTROLD_DNS_READY_SLEEP:-0.15}"
# Grace after start before dig/process checks (installer returns before listener binds).
CONTROLD_DNS_READY_GRACE_S="${CONTROLD_DNS_READY_GRACE_S:-2}"
# Progress log interval while waiting (seconds). 0 disables progress lines.
CONTROLD_DNS_READY_PROGRESS_S="${CONTROLD_DNS_READY_PROGRESS_S:-3}"
# Require this many consecutive "no process" observations before declaring death.
# A single pgrep miss during KeepAlive respawn previously aborted in ~1.7s (one dig
# timeout) and recovery then stop-thrashed a unit that was still coming up.
CONTROLD_DNS_DEAD_STREAK="${CONTROLD_DNS_DEAD_STREAK:-20}"
# If a non-ctrld process holds :53, waiting the full budget is useless — fail fast.
CONTROLD_DNS_PORT_CONFLICT_RETRIES="${CONTROLD_DNS_PORT_CONFLICT_RETRIES:-20}"
# After grace, if CD Mode never wrote toml and process stays dead this many seconds → fail.
CONTROLD_DNS_NO_TOML_FAIL_S="${CONTROLD_DNS_NO_TOML_FAIL_S:-8}"
# Default CD Mode config path (used by readiness diagnostics).
CONTROLD_CONFIG_ABS="${CONTROLD_CONFIG_ABS:-/etc/controld/ctrld.toml}"

# Epoch seconds (portable; avoids date +%s quirks in some environments).
_controld_now_s() {
	if date +%s >/dev/null 2>&1; then
		date +%s
		return 0
	fi
	perl -e 'print time' 2>/dev/null || echo 0
}

# True when a ctrld worker is visible (process table or launchd PID column).
_ctrld_process_alive() {
	if pgrep -x "ctrld" >/dev/null 2>&1; then
		return 0
	fi
	# launchctl list: "PID Status Label" — PID "-" means not running.
	if command -v launchctl >/dev/null 2>&1; then
		local row
		row=$(launchctl list 2>/dev/null | awk '$3 == "ctrld" {print $1; exit}')
		if [[ -n $row && $row != "-" ]]; then
			return 0
		fi
	fi
	return 1
}

# True when launchd knows about the ctrld job (loaded), even if PID is "-".
_ctrld_launchd_loaded() {
	if ! command -v launchctl >/dev/null 2>&1; then
		return 1
	fi
	if launchctl list 2>/dev/null | awk '$3 == "ctrld" {found=1} END {exit !found}'; then
		return 0
	fi
	# print succeeds only when the job exists; require label text (stubs may exit 0).
	if launchctl print system/ctrld 2>/dev/null | grep -qE 'Label"[[:space:]]*=[[:space:]]*"ctrld"|\"Label\"|ctrld'; then
		return 0
	fi
	return 1
}

# One-line post-start snapshot for progress / fail messages (no secrets).
_ctrld_readiness_snapshot() {
	local config_abs="${1:-${CONTROLD_CONFIG_ABS:-/etc/controld/ctrld.toml}}"
	local proc="dead"
	local launchd="unloaded"
	local toml="missing"
	local port="none"
	local foreign=""

	if _ctrld_process_alive; then
		proc="alive"
	fi
	if _ctrld_launchd_loaded; then
		launchd="loaded"
	fi
	if [[ -f $config_abs ]]; then
		toml="present"
	fi
	foreign=$(_foreign_port53_holder)
	if [[ -n $foreign ]]; then
		port="foreign:$foreign"
	elif command -v lsof >/dev/null 2>&1; then
		if lsof -nP -iUDP:53 -iTCP:53 2>/dev/null | grep -q ctrld; then
			port="ctrld"
		fi
	fi
	echo "proc=$proc launchd=$launchd toml=$toml :53=$port"
}

# Print COMMAND/PID of the first non-ctrld holder of :53, or empty if none / only ctrld.
# Colima/Lima commonly forwards guest DNS to host 127.0.0.1:53 via limactl — that
# steals the port and leaves ctrld KeepAlive crash-looping (exit 1, runs climbing).
# NOTE: limactl often holds TCP *:53 only (ssh forwarder); ctrld still needs UDP :53.
# Treat any non-ctrld TCP/UDP holder as a conflict — TCP steal alone can make bind fail.
_foreign_port53_holder() {
	local line
	if ! command -v lsof >/dev/null 2>&1; then
		return 0
	fi
	while IFS= read -r line; do
		[[ -z $line || $line == COMMAND* ]] && continue
		if [[ $line != *ctrld* ]]; then
			# COMMAND PID USER FD TYPE ... — emit "cmd pid"
			echo "$line" | awk '{print $1, $2}'
			return 0
		fi
	done < <(lsof -nP -iUDP:53 -iTCP:53 2>/dev/null || true)
	return 0
}

# Fail-safe: never leave Wi-Fi/LAN pinned to a dead 127.0.0.1 listener.
# Prefer DHCP Empty over stale localhost DNS when the listener never became ready.
_reset_system_dns_to_dhcp() {
	networksetup -setdnsservers Wi-Fi Empty 2>/dev/null || true
	networksetup -setdnsservers "USB 10/100/1000 LAN" Empty 2>/dev/null || true
	dscacheutil -flushcache 2>/dev/null || true
	# HUP may need root; ignore failure — DHCP Empty is the critical part.
	killall -HUP mDNSResponder 2>/dev/null || true
	sudo killall -HUP mDNSResponder 2>/dev/null || true
}

# Wait until the local DNS listener answers, or until timeout.
# Returns 0 on success, 1 on timeout / sustained process death / port conflict / no-toml.
# Does not treat transient start warnings (e.g. "service not installed") as API failures.
# SECURITY: dig success is required — port bind alone is not enough to pin system DNS.
# SECURITY: dig must not be treated as success when only limactl holds TCP :53 (UDP
# still times out today with ssh forwarder; still require no foreign holder on success).
# SECURITY: never hang silently — wall-clock budget + progress logs every few seconds.
_wait_for_dns_ready() {
	local listener_ip="$1"
	local max_retries="${2:-$CONTROLD_DNS_READY_RETRIES}"
	local sleep_s="${3:-$CONTROLD_DNS_READY_SLEEP}"
	# Nested default: under set -u, bare ${4:-$CONTROLD_CONFIG_ABS} explodes if
	# CONTROLD_CONFIG_ABS was unset after source (tests / repair env).
	local config_abs="${4:-${CONTROLD_CONFIG_ABS:-/etc/controld/ctrld.toml}}"
	local retry=0
	local conflict_retries="${CONTROLD_DNS_PORT_CONFLICT_RETRIES:-20}"
	local dead_streak_limit="${CONTROLD_DNS_DEAD_STREAK:-20}"
	local dead_streak=0
	local foreign=""
	local grace="${CONTROLD_DNS_READY_GRACE_S:-2}"
	local budget_s="${CONTROLD_DNS_READY_BUDGET_S:-45}"
	local progress_s="${CONTROLD_DNS_READY_PROGRESS_S:-3}"
	local no_toml_fail_s="${CONTROLD_DNS_NO_TOML_FAIL_S:-8}"
	local started_s last_progress_s now_s elapsed_s
	local saw_toml=0
	local saw_alive=0
	local snap=""

	started_s=$(_controld_now_s)
	last_progress_s=$started_s

	# SECURITY / bash 3.2: never juxtapose $var with Unicode U+2026 (ellipsis).
	# macOS /bin/bash glues the rune onto the name → "unbound variable" under
	# set -u (Lesson 0dr). Always use ASCII "..." after expansions.
	if [[ $grace != "0" && $grace != "0.0" ]]; then
		echo -e "\033[0;36m[INFO]\033[0m Waiting for Control D DNS on @$listener_ip (budget ${budget_s}s)..." >&2
		sleep "$grace"
	else
		echo -e "\033[0;36m[INFO]\033[0m Waiting for Control D DNS on @$listener_ip (budget ${budget_s}s)..." >&2
	fi

	while [[ $retry -lt $max_retries ]]; do
		now_s=$(_controld_now_s)
		elapsed_s=$((now_s - started_s))
		if [[ $elapsed_s -ge $budget_s ]]; then
			snap=$(_ctrld_readiness_snapshot "$config_abs")
			echo -e "\033[0;31m[ERROR]\033[0m DNS readiness budget (${budget_s}s) exhausted. $snap" >&2
			return 1
		fi

		if [[ -f $config_abs ]]; then
			saw_toml=1
		fi
		if _ctrld_process_alive; then
			saw_alive=1
			dead_streak=0
		else
			dead_streak=$((dead_streak + 1))
		fi

		# Prefer dig (UDP) — matches how macOS/clients query the listener.
		# Always use +time/+tries so a dead listener cannot hang the wait loop.
		if dig @"$listener_ip" google.com +short +time=1 +tries=1 >/dev/null 2>&1; then
			# Reject false-positive answers if a foreign process owns :53.
			foreign=$(_foreign_port53_holder)
			if [[ -z $foreign ]]; then
				echo -e "\033[0;32m[OK]\033[0m dig @$listener_ip succeeded after ${elapsed_s}s." >&2
				return 0
			fi
			echo -e "\033[1;33m[WARN]\033[0m dig @$listener_ip succeeded but port 53 is held by: $foreign — not treating as Control D ready." >&2
		fi

		# KeepAlive respawn leaves brief gaps — only fail after a sustained streak.
		if [[ $dead_streak -ge $dead_streak_limit ]]; then
			snap=$(_ctrld_readiness_snapshot "$config_abs")
			echo -e "\033[0;31m[ERROR]\033[0m ctrld process stayed dead (streak=$dead_streak). $snap" >&2
			return 1
		fi

		# CD Mode must write AUTO-GENERATED toml under --config. If neither toml
		# nor process ever appears after a short settle, "Service started" was a lie.
		if [[ $saw_toml -eq 0 && $saw_alive -eq 0 && $elapsed_s -ge $no_toml_fail_s ]]; then
			snap=$(_ctrld_readiness_snapshot "$config_abs")
			echo -e "\033[0;31m[ERROR]\033[0m Post-start: no $config_abs and no ctrld process after ${elapsed_s}s (CLI said started but daemon never stayed up). $snap" >&2
			echo -e "\033[0;31m[ERROR]\033[0m Check: sudo tail -80 /usr/local/var/log/ctrld.err.log ; launchctl print system/ctrld" >&2
			return 1
		fi

		# Foreign holder of :53 (e.g. limactl from Colima) — ctrld cannot bind.
		foreign=$(_foreign_port53_holder)
		if [[ -n $foreign ]]; then
			if [[ $retry -ge $conflict_retries ]]; then
				echo -e "\033[0;31m[ERROR]\033[0m Port 53 is held by non-ctrld process: $foreign (often Colima/Lima DNS forward). Control D cannot become ready." >&2
				return 1
			fi
		fi

		# Progress every few seconds so a long wait never looks like a hang.
		if [[ $progress_s != "0" && $((now_s - last_progress_s)) -ge $progress_s ]]; then
			snap=$(_ctrld_readiness_snapshot "$config_abs")
			# ASCII "..." only — see Lesson 0dr (Unicode ellipsis + set -u).
			echo -e "\033[0;36m[INFO]\033[0m Still waiting for dig @$listener_ip... ${elapsed_s}s/${budget_s}s -- $snap" >&2
			last_progress_s=$now_s
		fi

		sleep "$sleep_s"
		retry=$((retry + 1))
	done
	snap=$(_ctrld_readiness_snapshot "$config_abs")
	echo -e "\033[0;31m[ERROR]\033[0m DNS readiness retry cap ($max_retries) hit. $snap" >&2
	return 1
}

# Apply system DNS to the local Control D listener and flush caches.
# SECURITY: only call after _wait_for_dns_ready succeeds — never point the
# system resolver at a dead 127.0.0.1 listener.
_apply_localhost_dns() {
	local listener_ip="$1"

	networksetup -setdnsservers Wi-Fi "$listener_ip" 2>/dev/null || true
	networksetup -setdnsservers "USB 10/100/1000 LAN" "$listener_ip" 2>/dev/null || true

	sleep 0.2
	local configured_dns
	configured_dns=$(networksetup -getdnsservers Wi-Fi 2>/dev/null || echo "")
	if ! echo "$configured_dns" | grep -q "$listener_ip"; then
		sleep 0.5
		networksetup -setdnsservers Wi-Fi "$listener_ip" 2>/dev/null || true
		networksetup -setdnsservers "USB 10/100/1000 LAN" "$listener_ip" 2>/dev/null || true
	fi

	dscacheutil -flushcache 2>/dev/null || true
	sudo killall -HUP mDNSResponder 2>/dev/null || true
}

# True when start logs indicate a real Control D API / resolver fetch failure.
# Ignores expected install chatter such as "service not installed".
# SECURITY: dig timeouts / listener-not-ready are handled in restart_with_native_profile
# control flow — they must never set FALLBACK via this classifier.
# Also scans daemon log: CLI often prints "Service started" while LaunchDaemon
# crash-loops on schema errors that only appear in /etc/controld/ctrld.log.
_is_native_api_failure() {
	local start_err_log="$1"
	local daemon_log="${2:-/etc/controld/ctrld.log}"
	local pattern='Maintenance is in progress|failed to fetch resolver config|failed to fetch.*config|resolver config.*fail|API.*(error|fail|unavailable)|unauthorized|forbidden|cannot unmarshal.*ResolverConfig|cannot unmarshal.*exclude'

	if [[ -f $start_err_log ]] && grep -qiE "$pattern" "$start_err_log" 2>/dev/null; then
		return 0
	fi
	# Recent daemon log only (last ~80 lines) — avoid matching ancient rotated noise.
	if [[ -f $daemon_log ]] && tail -n 80 "$daemon_log" 2>/dev/null | grep -qiE "$pattern"; then
		return 0
	fi
	return 1
}

# True when Control D API JSON schema is incompatible with this ctrld binary.
# Smoking gun (2026-07-09): json: cannot unmarshal number into Go struct field
# ResolverConfig.body.resolver.exclude of type string — KeepAlive crash-loop,
# missing /etc/controld/ctrld.toml, dig @127.0.0.1 timeout (Lesson 0dr).
_is_ctrld_api_schema_incompat() {
	local start_err_log="$1"
	local daemon_log="${2:-/etc/controld/ctrld.log}"
	local pattern='cannot unmarshal.*(exclude|ResolverConfig)|unmarshal number into Go struct field.*exclude'

	if [[ -f $start_err_log ]] && grep -qiE "$pattern" "$start_err_log" 2>/dev/null; then
		return 0
	fi
	if [[ -f $daemon_log ]] && tail -n 80 "$daemon_log" 2>/dev/null | grep -qiE "$pattern"; then
		return 0
	fi
	return 1
}

# Prefer Homebrew ctrld when /usr/local/bin shadows an older direct install.
# LaunchDaemon already uses /opt/homebrew/bin/ctrld; CLI PATH often hits
# /usr/local/bin first (dev builds) — that mismatch caused "two installs" confusion.
# Tests: honor PATH mocks unless the only hit is the known shadowed /usr/local binary.
_resolve_ctrld_bin() {
	local path_bin=""
	if [[ -n ${CTRLD_BIN-} && -x ${CTRLD_BIN} ]]; then
		echo "$CTRLD_BIN"
		return 0
	fi
	path_bin=$(command -v ctrld 2>/dev/null || true)
	# Shadowed direct install: PATH finds /usr/local first, but brew is the kept binary.
	if [[ $path_bin == /usr/local/bin/ctrld && -x /opt/homebrew/bin/ctrld ]]; then
		echo /opt/homebrew/bin/ctrld
		return 0
	fi
	if [[ -n $path_bin && -x $path_bin ]]; then
		echo "$path_bin"
		return 0
	fi
	if [[ -x /opt/homebrew/bin/ctrld ]]; then
		echo /opt/homebrew/bin/ctrld
		return 0
	fi
	if [[ -x /usr/local/bin/ctrld ]]; then
		echo /usr/local/bin/ctrld
		return 0
	fi
	return 1
}

# Run the resolved ctrld binary (not whatever PATH happens to shadow).
_ctrld() {
	local bin
	bin=$(_resolve_ctrld_bin)
	if [[ -z $bin ]]; then
		echo -e "\033[0;31m[ERROR]\033[0m ctrld binary not found." >&2
		return 127
	fi
	"$bin" "$@"
}

# Put resolved ctrld first on PATH for this process (and children).
_ensure_ctrld_on_path() {
	local bin dir
	bin=$(_resolve_ctrld_bin)
	[[ -n $bin ]] || return 0
	dir=$(dirname "$bin")
	case ":$PATH:" in
	*":$dir:"*) ;;
	*) export PATH="$dir:$PATH" ;;
	esac
	export CTRLD_BIN="$bin"
}

# Report installed ctrld version (best-effort; never fails the caller).
_ctrld_installed_version() {
	local ver="" bin
	bin=$(_resolve_ctrld_bin)
	if [[ -n $bin ]]; then
		ver=$("$bin" --version 2>/dev/null | head -1 || true)
		if [[ -z $ver ]]; then
			ver=$("$bin" version 2>/dev/null | head -1 || true)
		fi
	fi
	echo "${ver:-unknown}"
}

# World-readable non-secret status (avoids bat/fish Permission denied on active_profile).
# active_profile may stay 600; this file is intentionally 644.
CONTROLD_STATUS_FILE="${CONTROLD_STATUS_FILE:-/etc/controld/status}"

_write_controld_status_file() {
	local state="$1" # WORKING|BROKEN|UNKNOWN
	local mode="$2"  # cd_mode|local_fallback|stopped
	local profile="${3-}"
	local protocol="${4-}"
	local extra="${5-}"
	local bin ver dig_ok="no" holder="none" status_file
	status_file="$CONTROLD_STATUS_FILE"
	bin=$(_resolve_ctrld_bin)
	ver=$(_ctrld_installed_version)
	if dig @"${CONTROLD_LISTENER_IP:-127.0.0.1}" google.com +short +time=2 +tries=1 >/dev/null 2>&1; then
		dig_ok="yes"
	fi
	holder=$(_foreign_port53_holder 2>/dev/null || true)
	if [[ -z $holder ]] && pgrep -x ctrld >/dev/null 2>&1; then
		holder="ctrld"
	elif [[ -z $holder ]]; then
		holder="none"
	fi
	{
		echo "STATE=$state"
		echo "MODE=$mode"
		echo "PROFILE=${profile:-unknown}"
		echo "PROTOCOL=${protocol:-unknown}"
		echo "DIG_OK=$dig_ok"
		echo "BINARY=${bin:-unknown}"
		echo "VERSION=$ver"
		echo "PORT53=$holder"
		echo "UPDATED=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
		[[ -n $extra ]] && echo "$extra"
	} >"$status_file" 2>/dev/null || true
	chmod 644 "$status_file" 2>/dev/null || true
}

# True when toml is profile-aware Local Config (real profile endpoint, not free DNS, not CD Mode).
_has_profile_local_toml() {
	local config_abs="${1:-/etc/controld/ctrld.toml}"
	[[ -f $config_abs ]] || return 1
	if head -1 "$config_abs" 2>/dev/null | grep -q 'AUTO-GENERATED VIA CD FLAG'; then
		return 1
	fi
	if grep -qE 'dns\.controld\.com/free|freedns\.controld\.com/free' "$config_abs" 2>/dev/null; then
		return 1
	fi
	grep -qE "endpoint = 'https://dns\.controld\.com/[A-Za-z0-9]+'" "$config_abs" 2>/dev/null
}

# Skip CD Mode thrash when schema is known-broken, env prefers local, or FALLBACK=1 toml exists.
# Override with CONTROLD_FORCE_CD_MODE=1 (repair --cd-mode) to attempt CD Mode again.
_prefer_profile_local_start() {
	local daemon_log="${1:-/etc/controld/ctrld.log}"
	local profile_file="${2:-$ACTIVE_PROFILE_FILE}"
	local config_abs="${3:-/etc/controld/ctrld.toml}"

	if [[ ${CONTROLD_FORCE_CD_MODE:-0} == "1" ]]; then
		return 1
	fi
	if [[ ${CONTROLD_PREFER_LOCAL:-0} == "1" ]]; then
		return 0
	fi
	# As of 2026-07-09: CD Mode utility API returns numeric exclude; v1.5.3 still fails.
	# Default stable path is profile Local Config unless --cd-mode forces a retry.
	if [[ ${CONTROLD_SKIP_CD_DEFAULT:-1} == "1" ]]; then
		return 0
	fi
	if _is_ctrld_api_schema_incompat "/dev/null" "$daemon_log"; then
		return 0
	fi
	if [[ -f $profile_file ]] && grep -q 'FALLBACK=1' "$profile_file" 2>/dev/null; then
		_has_profile_local_toml "$config_abs" && return 0
	fi
	return 1
}

# Static fallback is ONLY for confirmed Control D API / resolver maintenance
# OR API schema incompatibility with the installed ctrld binary.
# Listener-not-ready and dig timeouts are handled separately in restart flow —
# they must never call this path (control-flow gate, not log-string coincidence).
_should_static_api_fallback() {
	local start_err_log="$1"
	local daemon_log="${2:-/etc/controld/ctrld.log}"
	_is_ctrld_api_schema_incompat "$start_err_log" "$daemon_log" && return 0
	_is_native_api_failure "$start_err_log" "$daemon_log"
}

# Write a profile-aware Local Config toml (REAL profile endpoint — never free DNS).
# Used when CD Mode --cd fetch fails due to API schema incompat / maintenance.
# Optional 4th arg: protocol (doh|doh3); default doh for maximum fallback stability.
# SECURITY: endpoint MUST be https://dns.controld.com/<profile_id> — never /free.
_write_profile_local_config() {
	local profile_name="$1"
	local profile_id="$2"
	local config_abs="$3"
	local protocol="${4:-doh}"
	local controld_dir profiles_dir fallback_file proto_type bootstrap_ip

	if [[ -z $profile_id || $profile_id == *'/'* || $profile_id == *'..'* ]]; then
		echo -e "\033[0;31m[ERROR]\033[0m Refusing profile local config with invalid profile_id." >&2
		return 1
	fi
	if [[ $profile_id == "free" ]]; then
		echo -e "\033[0;31m[ERROR]\033[0m Refusing free-DNS antipattern endpoint." >&2
		return 1
	fi

	proto_type="doh"
	if [[ $protocol == "doh3" ]]; then
		proto_type="doh3"
	fi
	# Historical working bootstrap for dns.controld.com premium endpoints.
	bootstrap_ip="${CONTROLD_BOOTSTRAP_IP:-76.76.2.22}"

	controld_dir=$(dirname "$config_abs")
	profiles_dir="$controld_dir/profiles"
	install -d -m 755 "$controld_dir" 2>/dev/null || true
	install -d -m 700 "$profiles_dir" 2>/dev/null || true

	fallback_file="$profiles_dir/ctrld.$profile_name.fallback.toml"
	# Prefer shared generator when present (same endpoint contract).
	if command -v generate_fallback_config >/dev/null 2>&1 && [[ $proto_type == "doh" ]]; then
		if ! generate_fallback_config "$profile_name" "$profile_id" "$profiles_dir"; then
			return 1
		fi
	else
		cat >"$fallback_file" <<EOF
# TEMPORARY profile-aware Local Config — CD Mode API schema incompatible / unreachable.
# endpoint uses REAL profile id (NOT free DNS). Remove when ctrld CD Mode works again.
[listener]
  [listener.0]
    ip = '127.0.0.1'
    port = 53

[network]
  [network.0]
    name = 'Network 0'
    cidrs = ['0.0.0.0/0']

[upstream]
  [upstream.0]
    name = 'Control D ($profile_name)'
    type = '${proto_type}'
    endpoint = 'https://dns.controld.com/${profile_id}'
    bootstrap_ip = '${bootstrap_ip}'
    timeout = 5000
EOF
		chmod 600 "$fallback_file" 2>/dev/null || true
	fi

	# Refuse free-DNS antipattern before installing.
	if grep -qE "dns\.controld\.com/free|freedns\.controld\.com/free" "$fallback_file" 2>/dev/null; then
		echo -e "\033[0;31m[ERROR]\033[0m Fallback file contains free-DNS antipattern; aborting." >&2
		rm -f "$fallback_file"
		return 1
	fi
	if ! grep -q "dns.controld.com/${profile_id}" "$fallback_file" 2>/dev/null; then
		echo -e "\033[0;31m[ERROR]\033[0m Fallback file missing profile endpoint for $profile_id." >&2
		return 1
	fi

	# Install as real file (not symlink) at config_abs for Local Config Mode.
	if [[ -L $config_abs ]]; then
		rm -f "$config_abs"
	fi
	cp -f "$fallback_file" "$config_abs"
	chmod 600 "$config_abs" 2>/dev/null || true
	return 0
}

# After schema-incompat / API failure: stop KeepAlive thrash, write profile toml,
# start Local Config Mode (NO --cd), dig-prove, then pin DNS.
# Returns 0 on dig-proven success.
_start_profile_local_fallback() {
	local profile_id="$1"
	local profile_name="$2"
	local protocol="$3"
	local controld_dir="$4"
	local listener_ip="$5"
	local start_err_log="${6-}"
	local config_abs="$controld_dir/ctrld.toml"
	local ver
	local own_log=0

	if [[ -z $start_err_log ]]; then
		start_err_log=$(mktemp "${TMPDIR:-/tmp}/ctrld_fb.XXXXXX")
		own_log=1
	fi

	ver=$(_ctrld_installed_version)
	_ensure_ctrld_on_path
	echo -e "\033[1;33m[INFO]\033[0m Stable path: profile-aware Local Config (ctrld ${ver})." >&2
	echo -e "\033[1;33m[INFO]\033[0m Endpoint: https://dns.controld.com/${profile_id} (NOT free DNS)." >&2
	echo -e "\033[1;33m[INFO]\033[0m CD Mode (--cd) skipped until Control D fixes API exclude schema; force with repair --cd-mode." >&2

	# Stop KeepAlive crash-loop BEFORE writing config — do not leave thrashing daemon.
	_stop_ctrld_cleanly 50

	if ! _write_profile_local_config "$profile_name" "$profile_id" "$config_abs" "$protocol"; then
		echo -e "\033[0;31m[ERROR]\033[0m Could not write profile-aware local config." >&2
		_reset_system_dns_to_dhcp
		_write_controld_status_file "BROKEN" "stopped" "$profile_name" "$protocol"
		[[ $own_log -eq 1 ]] && rm -f "$start_err_log"
		return 1
	fi

	echo "[INFO] profile-local argv: ctrld service start --config=$config_abs --skip_self_checks (NO --cd; stable local path)" >>"$start_err_log"
	if ! _ctrld service start --config="$config_abs" --skip_self_checks >>"$start_err_log" 2>&1; then
		_ctrld start --config="$config_abs" --skip_self_checks >>"$start_err_log" 2>&1 || true
	fi

	if ! _wait_for_dns_ready "$listener_ip" "$CONTROLD_DNS_READY_RETRIES" "$CONTROLD_DNS_READY_SLEEP" "$config_abs"; then
		echo -e "\033[0;31m[ERROR]\033[0m Profile-aware Local Config started but dig @$listener_ip failed. Resetting DNS to DHCP." >&2
		_stop_ctrld_cleanly 50
		_reset_system_dns_to_dhcp
		_write_controld_status_file "BROKEN" "stopped" "$profile_name" "$protocol"
		[[ $own_log -eq 1 ]] && rm -f "$start_err_log"
		return 1
	fi

	_apply_localhost_dns "$listener_ip"
	echo -e "PROFILE_NAME=$profile_name\nPROFILE_ID=$profile_id\nPROTOCOL=$protocol\nINTENDED_PROTOCOL=$protocol\nFALLBACK=1\nFALLBACK_REASON=api_schema_or_unreachable" >"$ACTIVE_PROFILE_FILE"
	# Readable without sudo so fish/bat do not Permission-denied on `cat`.
	chmod 644 "$ACTIVE_PROFILE_FILE" 2>/dev/null || true
	_write_controld_status_file "WORKING" "local_fallback" "$profile_name" "$protocol" "ENDPOINT=https://dns.controld.com/${profile_id}"
	echo -e "\033[0;32m[OK]\033[0m Profile-aware Local Config listening; dig @$listener_ip OK (stable path until CD Mode API is fixed)." >&2
	[[ $own_log -eq 1 ]] && rm -f "$start_err_log"
	return 0
}

# Start / reinstall ctrld in CD Mode (--cd profile_id) with an absolute config path.
#
# CRITICAL (2026-07-09 Lesson 0do): NEVER pass `--listen` with `--cd`.
# ctrld treats `--listen` as "no config mode" (isNoConfigStart). The LaunchDaemon
# then fatals with `"listen" and "primary_upstream" flags must be set in no config
# mode` before CD Mode can fetch/write config → "<no log output…>" → self-uninstall.
# CD Mode already binds 127.0.0.1:53 from the API-generated toml.
#
# Also: `NTC Generating controld config: ctrld.toml` (relative basename) is a FALSE
# POSITIVE when `--config=/abs/path` is set but the file does not exist yet —
# noticeWritingControlDConfig logs stale defaultConfigFile; writeConfigFile still
# uses configPath. Do not treat that notice alone as failure.
#
# Absolute `--config=/etc/controld/ctrld.toml` WITH `--cd` stays CD Mode (file gets
# AUTO-GENERATED VIA CD FLAG) — it is NOT Local Config Mode / static free-DNS.
#
# Prefer stop→start with new flags (v1.3.8+ reinstalls when flags change). Uninstall
# only when KeepAlive leaves a zombie after stop — never thrash uninstall on every switch.
# Prefer `service start` (no OS DNS steering) — we apply localhost DNS only after dig.
#
# Argv (logged): ctrld service start --cd <id> --proto doh|doh3 \
#   --config=/etc/controld/ctrld.toml --skip_self_checks
_force_reinstall_ctrld_native() {
	local profile_id="$1"
	local protocol="$2"
	local start_err_log="$3"
	# $4 was historically listen_addr — IGNORED (passing --listen breaks CD Mode).
	local _ignored_listen="${4-}"
	local config_abs="${5:-/etc/controld/ctrld.toml}"
	local controld_dir
	controld_dir=$(dirname "$config_abs")
	local proto_flag="doh"
	local start_argv
	local ctrld_bin

	if [[ $protocol == "doh3" ]]; then
		proto_flag="doh3"
	fi

	_ensure_ctrld_on_path
	ctrld_bin=$(_resolve_ctrld_bin)

	# Ensure system config dir exists and is writable by root (CD Mode output path).
	install -d -m 755 "$controld_dir" 2>/dev/null || true
	# Keep profiles/backup private; main dir must allow LaunchDaemon write of toml.
	install -d -m 700 "$controld_dir/profiles" "$controld_dir/backup" 2>/dev/null || true

	_ctrld service stop 2>/dev/null || true
	_ctrld stop 2>/dev/null || true

	# Uninstall only if the process is still alive after stop (KeepAlive zombie).
	# Unconditional uninstall caused: relative notice + no logs → Service uninstalled.
	if pgrep -x "ctrld" >/dev/null 2>&1; then
		echo "[WARN] ctrld still alive after stop; uninstalling once to clear KeepAlive." >>"$start_err_log"
		_ctrld service uninstall 2>/dev/null || true
		sleep 0.5
		pkill -x ctrld 2>/dev/null || true
		_wait_for_process_stop "ctrld" 30
	fi

	# Real argv — log it so repair/debug never guess. NO --listen (see Lesson 0do).
	start_argv=(service start --cd "$profile_id" --proto "$proto_flag" --config="$config_abs" --skip_self_checks)
	echo "[INFO] ctrld bin=$ctrld_bin argv: ctrld ${start_argv[*]}" >>"$start_err_log"

	if ! _ctrld "${start_argv[@]}" >>"$start_err_log" 2>&1; then
		# Fresh hosts / service helper quirks: fall back to `ctrld start` (same flags).
		echo "[INFO] ctrld argv fallback: ctrld start --cd $profile_id --proto $proto_flag --config=$config_abs --skip_self_checks" >>"$start_err_log"
		_ctrld start \
			--cd "$profile_id" \
			--proto "$proto_flag" \
			--config="$config_abs" \
			--skip_self_checks >>"$start_err_log" 2>&1
	fi

	# Brief settle — CLI "Service started" can return before LaunchDaemon binds or
	# before CD Mode writes toml. Log facts for the dig-wait (do not treat as success).
	sleep 0.5
	{
		echo "[INFO] post-start settle:"
		if pgrep -x "ctrld" >/dev/null 2>&1; then
			echo "  process: alive"
		else
			echo "  process: DEAD (CLI may still have said Service started)"
		fi
		if [[ -f $config_abs ]]; then
			echo "  config: present ($config_abs)"
		else
			echo "  config: MISSING ($config_abs)"
		fi
		if command -v launchctl >/dev/null 2>&1; then
			if launchctl list 2>/dev/null | awk '$3 == "ctrld" {found=1} END {exit !found}'; then
				echo "  launchd: loaded"
			else
				echo "  launchd: not loaded"
			fi
		fi
	} >>"$start_err_log" 2>&1
}

# Start ctrld natively for a profile ID + protocol; append stdout/stderr to log.
# Optional 4th arg: controld_dir (default /etc/controld).
_start_ctrld_native() {
	local profile_id="$1"
	local protocol="$2"
	local start_err_log="$3"
	local controld_dir="${4:-/etc/controld}"
	# Pass empty listen slot (ignored) so config_abs stays 5th arg.
	_force_reinstall_ctrld_native "$profile_id" "$protocol" "$start_err_log" "" "$controld_dir/ctrld.toml"
}

# Stop the current service, link config, and restart
restart_with_config() {
	local config_file="$1"
	local controld_dir="$2"
	local protocol="$3"
	local listener_ip="$4"

	_stop_ctrld_cleanly 50

	# Create symlink to active configuration only after the service is down so
	# KeepAlive cannot restart against a half-removed config.
	ln -sf "$config_file" "$controld_dir/ctrld.toml"

	# Prefer service start so the LaunchDaemon stays installed across switches.
	# Fall back to `ctrld start` if `service start` is unavailable.
	local start_err_log
	_ensure_ctrld_on_path
	start_err_log=$(mktemp "${TMPDIR:-/tmp}/ctrld_err.XXXXXX")
	if ! _ctrld service start --config="$controld_dir/ctrld.toml" --skip_self_checks >"$start_err_log" 2>&1; then
		# Expected on fresh hosts: service not installed yet. Install via start.
		_ctrld start --config="$controld_dir/ctrld.toml" --skip_self_checks >>"$start_err_log" 2>&1 || true
	fi
	# Surface non-install warnings without treating them as fatal yet.
	if [[ -s $start_err_log ]]; then
		grep -viE 'service not installed' "$start_err_log" >&2 || true
	fi

	if ! _wait_for_dns_ready "$listener_ip"; then
		echo -e "\033[1;33m[WARN]\033[0m Control D config start did not become ready in time." >&2
		cat "$start_err_log" >&2 || true
		rm -f "$start_err_log" 2>/dev/null || true
		_stop_ctrld_cleanly 50
		_reset_system_dns_to_dhcp
		return 1
	fi
	rm -f "$start_err_log" 2>/dev/null || true

	_apply_localhost_dns "$listener_ip"
	return 0
}

# Emergency recovery
emergency_recovery() {
	local backup_dir="$1"
	local controld_dir="$2"

	_stop_ctrld_cleanly 50
	rm -f "$controld_dir/ctrld.toml"
	rm -f "$ACTIVE_PROFILE_FILE"

	if command -v restore_network_settings >/dev/null 2>&1; then
		restore_network_settings "$backup_dir"
	fi

	sudo dscacheutil -flushcache 2>/dev/null || true
	sudo killall -HUP mDNSResponder 2>/dev/null || true

	if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
		return 0
	else
		return 1
	fi
}

# Stop the current service, and restart natively via profile ID
restart_with_native_profile() {
	local profile_id="$1"
	local profile_name="$2"
	local protocol="$3"
	local controld_dir="$4"
	local listener_ip="$5"

	# Preflight: foreign :53 holders (Colima limactl) make readiness impossible.
	local foreign_holder
	foreign_holder=$(_foreign_port53_holder)
	if [[ -n $foreign_holder ]]; then
		echo -e "\033[1;33m[WARN]\033[0m Port 53 already held by: $foreign_holder — Control D may fail to bind. Free it first (see scripts/free-port53-for-controld.sh)." >&2
	fi

	# Stop KeepAlive first — never pkill while the LaunchDaemon can respawn.
	_stop_ctrld_cleanly 50

	# Do NOT delete $controld_dir/ctrld.toml here. CD Mode regenerates it in place.
	# Deleting it before start (combined with force-uninstall) made ctrld write a
	# relative `ctrld.toml` into CWD → LaunchDaemon crash → "no log output" → uninstall.
	# If a leftover symlink points at a static profile TOML, remove only the symlink
	# so CD Mode can write a real file (not follow a broken link).
	if [[ -L "$controld_dir/ctrld.toml" ]]; then
		rm -f "$controld_dir/ctrld.toml" 2>/dev/null || true
	fi

	local start_err_log
	start_err_log=$(mktemp "${TMPDIR:-/tmp}/ctrld_err.XXXXXX")
	: >"$start_err_log"

	# Stable path (2026-07-09): skip CD Mode thrash when schema is known-broken.
	# Force CD Mode with CONTROLD_FORCE_CD_MODE=1 (repair --cd-mode).
	if _prefer_profile_local_start "/etc/controld/ctrld.log" "$ACTIVE_PROFILE_FILE" "$controld_dir/ctrld.toml"; then
		_start_profile_local_fallback "$profile_id" "$profile_name" "$protocol" "$controld_dir" "$listener_ip" "$start_err_log"
		local fb_rc=$?
		rm -f "$start_err_log" 2>/dev/null || true
		return $fb_rc
	fi

	# CD Mode: --cd <profile_id> + absolute --config under /etc/controld.
	# `service start` accepts --cd (no OS DNS steering). First install may emit
	# "service not installed" then install — expected, not fatal.
	_start_ctrld_native "$profile_id" "$protocol" "$start_err_log" "$controld_dir" || true

	# Print actionable messages; suppress expected "service not installed" chatter.
	if [[ -s $start_err_log ]]; then
		grep -viE 'service not installed' "$start_err_log" || true
	fi

	# Hard failure signals (Lesson 0do): no-log + self-uninstall, or no-config-mode
	# fatal from accidental --listen. Do NOT treat "Generating …: ctrld.toml" alone
	# as failure — that notice is a false positive when abs --config file is new.
	if grep -qiE 'no log output is obtained from ctrld process|Service uninstalled|"listen" and "primary_upstream" flags must be set in no config mode' "$start_err_log" 2>/dev/null; then
		echo -e "\033[0;31m[ERROR]\033[0m ctrld start failed (no-log / self-uninstall / no-config-mode). Resetting DNS to DHCP; not pinning 127.0.0.1." >&2
		echo -e "\033[0;31m[ERROR]\033[0m Check argv in log for forbidden --listen; expect: service start --cd … --config=/etc/controld/ctrld.toml" >&2
		rm -f "$start_err_log" 2>/dev/null || true
		_stop_ctrld_cleanly 50
		_reset_system_dns_to_dhcp
		return 1
	fi

	# Record intended profile/protocol early so status/reconcile see intent
	# even while we wait for DNS readiness. Never rewrite PROTOCOL to doh here.
	echo -e "PROFILE_NAME=$profile_name\nPROFILE_ID=$profile_id\nPROTOCOL=$protocol\nINTENDED_PROTOCOL=$protocol" >"$ACTIVE_PROFILE_FILE"
	chmod 644 "$ACTIVE_PROFILE_FILE" 2>/dev/null || true

	local dns_ready=0
	if _should_static_api_fallback "$start_err_log"; then
		_start_profile_local_fallback "$profile_id" "$profile_name" "$protocol" "$controld_dir" "$listener_ip" "$start_err_log"
		local fb_rc=$?
		rm -f "$start_err_log" 2>/dev/null || true
		return $fb_rc
	fi

	if _wait_for_dns_ready "$listener_ip"; then
		dns_ready=1
	else
		# Slow dig / KeepAlive race / port conflict — NOT an API failure *unless*
		# the daemon log shows schema unmarshal / fetch fatal (CLI said started).
		if _should_static_api_fallback "$start_err_log"; then
			_start_profile_local_fallback "$profile_id" "$profile_name" "$protocol" "$controld_dir" "$listener_ip" "$start_err_log"
			local fb_rc=$?
			rm -f "$start_err_log" 2>/dev/null || true
			return $fb_rc
		fi
		# Only recover when the unit is truly dead or :53 is free of foreign holders.
		# Never stop a still-alive unit mid-boot (that caused the ~1.7s thrash).
		echo -e "\033[1;33m[WARN]\033[0m DNS listener not ready after start budget; attempting recovery (not API fallback)." >&2
		foreign_holder=$(_foreign_port53_holder)
		if [[ -n $foreign_holder ]]; then
			echo -e "\033[0;31m[ERROR]\033[0m Port 53 conflict during recovery: $foreign_holder. Skipping restart thrash; resetting DNS to DHCP." >&2
			rm -f "$start_err_log" 2>/dev/null || true
			_stop_ctrld_cleanly 50
			_reset_system_dns_to_dhcp
			return 1
		fi
		# If process is still alive, give one more readiness window before reinstall.
		if _ctrld_process_alive; then
			echo -e "\033[1;33m[WARN]\033[0m ctrld still running — extending readiness wait before reinstall." >&2
			if _wait_for_dns_ready "$listener_ip"; then
				dns_ready=1
			fi
		fi
		if [[ $dns_ready -ne 1 ]]; then
			# One recovery restart — keep existing CD-generated toml; do not delete it.
			_stop_ctrld_cleanly 50
			echo "--- recovery restart ---" >>"$start_err_log"
			_start_ctrld_native "$profile_id" "$protocol" "$start_err_log" "$controld_dir" || true
			if _should_static_api_fallback "$start_err_log"; then
				_start_profile_local_fallback "$profile_id" "$profile_name" "$protocol" "$controld_dir" "$listener_ip" "$start_err_log"
				local fb_rc=$?
				rm -f "$start_err_log" 2>/dev/null || true
				return $fb_rc
			fi
			if _wait_for_dns_ready "$listener_ip"; then
				dns_ready=1
			else
				# Final check: daemon may have logged schema error after CLI returned.
				if _should_static_api_fallback "$start_err_log"; then
					_start_profile_local_fallback "$profile_id" "$profile_name" "$protocol" "$controld_dir" "$listener_ip" "$start_err_log"
					local fb_rc=$?
					rm -f "$start_err_log" 2>/dev/null || true
					return $fb_rc
				fi
				echo -e "\033[0;31m[ERROR]\033[0m DNS listener still not ready after recovery. Resetting system DNS to DHCP (not classifying as API failure)." >&2
				rm -f "$start_err_log" 2>/dev/null || true
				_stop_ctrld_cleanly 50
				_reset_system_dns_to_dhcp
				return 1
			fi
		fi
	fi

	rm -f "$start_err_log" 2>/dev/null || true
	if [[ $dns_ready -ne 1 ]]; then
		echo -e "\033[0;31m[ERROR]\033[0m Refusing to set system DNS to $listener_ip without a working listener." >&2
		_reset_system_dns_to_dhcp
		_write_controld_status_file "BROKEN" "stopped" "$profile_name" "$protocol"
		return 1
	fi
	_apply_localhost_dns "$listener_ip"
	_write_controld_status_file "WORKING" "cd_mode" "$profile_name" "$protocol"
	return 0
}

# Show status of Control D manager
show_status() {
	local controld_dir="$1"

	echo "=== Control D Profile Manager Status ==="
	echo

	if pgrep -f ctrld >/dev/null; then
		echo "Service Status: ✅ Running"

		if [[ -f $ACTIVE_PROFILE_FILE ]]; then
			# Read state
			source "$ACTIVE_PROFILE_FILE"

			local profile_name="${PROFILE_NAME:-unknown}"
			local protocol="${PROTOCOL:-unknown}"
			local profile_id="${PROFILE_ID:-unknown}"

			if command -v redact_profile_id >/dev/null 2>&1; then
				profile_id=$(redact_profile_id "$profile_id")
			fi

			echo "Active Profile: $profile_name"
			echo "Profile ID: $profile_id"
			echo "Protocol: $protocol"
		elif [[ -L "$controld_dir/ctrld.toml" ]]; then
			local current_config
			current_config=$(readlink "$controld_dir/ctrld.toml")
			local profile_name="${current_config##*/}"
			profile_name="${profile_name#ctrld.}"
			profile_name="${profile_name%.toml}"
			local protocol
			protocol=$(grep "type = " "$current_config" 2>/dev/null | sed "s/.*type = '\(.*\)'.*/\1/" || echo "unknown")
			local profile_id="unknown"
			if command -v get_profile_id >/dev/null 2>&1; then
				profile_id=$(get_profile_id "$profile_name")
				if command -v redact_profile_id >/dev/null 2>&1; then
					profile_id=$(redact_profile_id "$profile_id")
				fi
			fi

			echo "Active Profile: $profile_name (Legacy TOML)"
			echo "Profile ID: $profile_id"
			echo "Protocol: $protocol"
		else
			echo "Active Profile: Unknown (direct configuration)"
		fi

		local dns_servers
		dns_servers=$(networksetup -getdnsservers Wi-Fi 2>/dev/null || echo "Unknown")
		echo "System DNS: $dns_servers"

		if command -v test_current_connection >/dev/null 2>&1; then
			if test_current_connection "$controld_dir" >/dev/null 2>&1; then
				echo "Connection: ✅ Working"
			else
				echo "Connection: ❌ Issues detected"
			fi
		else
			echo "Connection: ⚠️ Cannot verify (missing functions)"
		fi
	else
		echo "Service Status: ❌ Stopped"
	fi

	echo
	echo "Available Profiles:"
	if command -v get_all_profiles >/dev/null 2>&1; then
		for profile in $(get_all_profiles); do
			local default_protocol="unknown"
			local profile_id="unknown"
			if command -v get_profile_protocol >/dev/null 2>&1; then
				default_protocol=$(get_profile_protocol "$profile")
			fi
			if command -v get_profile_id >/dev/null 2>&1; then
				profile_id=$(get_profile_id "$profile")
				if command -v redact_profile_id >/dev/null 2>&1; then
					profile_id=$(redact_profile_id "$profile_id")
				fi
			fi
			echo "  - $profile ($profile_id) - Default: $default_protocol"
		done
	fi

	echo
	echo "Protocols:"
	echo "  - doh3: DNS-over-HTTPS/3 (QUIC) - Faster, more secure"
	echo "  - doh:  DNS-over-HTTPS (TCP) - Fallback for compatibility"
	echo
	echo "Profile modes:"
	echo "  - doh-ipv4:  DoH + IPv6 disabled (Windscribe IPv4-only / static IP)"
	echo "  - doh3-ipv6: DoH3 + IPv6 enabled (standalone Control D)"
	echo "  - doh-ipv6:  DoH + IPv6 enabled (Windscribe IPv6-capable WireGuard)"
}

# Self-execution guard for testing
if [[ ${BASH_SOURCE[0]} == "${0}" ]]; then
	# Return 0 when executed directly
	return 0 2>/dev/null
fi
