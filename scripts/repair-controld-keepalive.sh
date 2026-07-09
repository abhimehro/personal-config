#!/usr/bin/env bash
#
# Repair Control D KeepAlive crash-loop / empty-homedir / no-config-mode failure.
#
# As of 2026-07-09: CD Mode (--cd) fails on Control D API numeric `exclude` even
# with ctrld v1.5.3. Default repair goes straight to profile-aware Local Config
# (real profile endpoint — NOT free DNS). Use --cd-mode to force a CD Mode retry.
#
# Symptoms this fixes:
#   - launchctl print system/ctrld shows climbing `runs` count
#   - dig @127.0.0.1 times out while pgrep -x ctrld succeeds
#   - Wi-Fi DNS stuck on 127.0.0.1
#   - limactl (Colima) holding TCP :53 so ctrld cannot bind
#
# SECURITY: Requires admin. Does NOT uninstall Control D permanently —
# stops the LaunchDaemon cleanly, resets DNS to DHCP FIRST, then starts
# the stable Local Config path (or CD Mode if --cd-mode).
#
# USAGE:
#   sudo ./scripts/repair-controld-keepalive.sh
#   sudo ./scripts/repair-controld-keepalive.sh --restart privacy
#   sudo ./scripts/repair-controld-keepalive.sh --restart privacy --cd-mode
#   CONTROLD_PREFER_LOCAL=1 sudo ./scripts/repair-controld-keepalive.sh --restart privacy
#
# If Colima holds :53, free it first (no sudo):
#   ./scripts/free-port53-for-controld.sh --stop-colima
#
# DO NOT repeatedly run uninstall loops.
# DO NOT pass --listen with --cd.
# DO NOT restore static free-DNS ~/.config/controld/ctrld.toml.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/controld-profile.sh
source "$ROOT/scripts/lib/controld-profile.sh"
# shellcheck source=scripts/lib/controld-service.sh
source "$ROOT/scripts/lib/controld-service.sh"

RESTART_PROFILE=""
FORCE_CD_MODE=0

while [[ $# -gt 0 ]]; do
	case "$1" in
	--restart)
		RESTART_PROFILE="${2:-privacy}"
		shift 2
		;;
	--cd-mode)
		FORCE_CD_MODE=1
		shift
		;;
	*)
		echo "Unknown arg: $1" >&2
		echo "Usage: sudo $0 [--restart PROFILE] [--cd-mode]" >&2
		exit 1
		;;
	esac
done

if [[ ${EUID} -ne 0 ]]; then
	echo "Run with sudo: sudo $0 ${*:-}" >&2
	exit 1
fi

_ensure_ctrld_on_path
CTRLD_BIN=$(_resolve_ctrld_bin)
echo "[INFO] Using ctrld: ${CTRLD_BIN:-missing} ($(_ctrld_installed_version))"

# SECURITY: Always restore DHCP before touching the service — never leave the
# host on dead 127.0.0.1 while we stop/uninstall/reinstall.
echo "[INFO] Fail-safe: resetting Wi-Fi / LAN DNS to DHCP BEFORE service work..."
networksetup -setdnsservers Wi-Fi Empty 2>/dev/null || true
networksetup -setdnsservers "USB 10/100/1000 LAN" Empty 2>/dev/null || true
dscacheutil -flushcache 2>/dev/null || true
killall -HUP mDNSResponder 2>/dev/null || true

echo "[INFO] Checking for foreign port 53 holders..."
if command -v lsof >/dev/null 2>&1; then
	foreign=$(lsof -nP -iUDP:53 -iTCP:53 2>/dev/null | awk 'NR>1 && $1 !~ /ctrld/ {print $1, $2; exit}' || true)
	if [[ -n ${foreign-} ]]; then
		echo "[ERROR] Port 53 held by non-ctrld: $foreign" >&2
		echo "        Free it first: $ROOT/scripts/free-port53-for-controld.sh --stop-colima" >&2
		echo "        (or --patch-colima-ignore then colima restart), then re-run this repair." >&2
		echo "        DNS is already on DHCP — network should work." >&2
		exit 1
	fi
fi

echo "[INFO] Stopping ctrld service (clears KeepAlive)..."
_ctrld service stop 2>/dev/null || true
_ctrld stop 2>/dev/null || true
sleep 1

if pgrep -x ctrld >/dev/null 2>&1; then
	echo "[WARN] Process still alive; uninstalling LaunchDaemon ONCE to clear KeepAlive..."
	_ctrld service uninstall 2>/dev/null || true
	sleep 1
	pkill -x ctrld 2>/dev/null || true
	sleep 1
	if pgrep -x ctrld >/dev/null 2>&1; then
		pkill -9 -x ctrld 2>/dev/null || true
	fi
fi

echo "[INFO] Ensuring /etc/controld exists..."
install -d -m 755 /etc/controld
install -d -m 700 /etc/controld/profiles /etc/controld/backup
# Remove symlink antipattern so we can write a real file.
if [[ -L /etc/controld/ctrld.toml ]]; then
	echo "[WARN] Removing symlink /etc/controld/ctrld.toml (static-profile antipattern)..."
	rm -f /etc/controld/ctrld.toml
fi

# Quarantine user-level static free-DNS config that bypasses profile IDs.
USER_HOME="${SUDO_USER:+$(eval echo "~$SUDO_USER")}"
USER_HOME="${USER_HOME:-$HOME}"
STATIC_USER_TOML="$USER_HOME/.config/controld/ctrld.toml"
if [[ -f $STATIC_USER_TOML ]]; then
	if grep -qE "dns\.controld\.com/free|Control D Default|Hardened for network resilience" "$STATIC_USER_TOML" 2>/dev/null; then
		ts=$(date +%Y%m%d_%H%M%S)
		echo "[WARN] Quarantining static antipattern $STATIC_USER_TOML → ${STATIC_USER_TOML}.broken.$ts"
		mv "$STATIC_USER_TOML" "${STATIC_USER_TOML}.broken.$ts"
	fi
fi

# Remove accidental relative cwd toml leftovers from failed starts.
for leftover in /tmp/ctrld.toml /tmp/ctrld_cwd_test/ctrld.toml "$ROOT/ctrld.toml" "$USER_HOME/ctrld.toml"; do
	if [[ -f $leftover ]]; then
		echo "[WARN] Removing leftover relative config: $leftover"
		rm -f "$leftover"
	fi
done

# Quarantine shadowed /usr/local/bin/ctrld when brew is the kept binary.
if [[ -x /opt/homebrew/bin/ctrld && -f /usr/local/bin/ctrld && ! -L /usr/local/bin/ctrld ]]; then
	brew_ver=$(/opt/homebrew/bin/ctrld --version 2>/dev/null | head -1 || true)
	old_ver=$(/usr/local/bin/ctrld --version 2>/dev/null | head -1 || true)
	if [[ $old_ver != "$brew_ver" ]]; then
		ts=$(date +%Y%m%d_%H%M%S)
		q="/usr/local/bin/ctrld.quarantined.$ts"
		echo "[INFO] Quarantining shadowed CLI: /usr/local/bin/ctrld ($old_ver) → $q"
		echo "       Keeping: /opt/homebrew/bin/ctrld ($brew_ver) — LaunchDaemon already uses this."
		mv /usr/local/bin/ctrld "$q"
		# Optional convenience symlink so PATH still finds brew ctrld.
		ln -sf /opt/homebrew/bin/ctrld /usr/local/bin/ctrld
		echo "[OK] /usr/local/bin/ctrld → /opt/homebrew/bin/ctrld"
	fi
fi

echo "[INFO] Post-stop state:"
pgrep -xl ctrld || echo "  ctrld: stopped"
networksetup -getdnsservers Wi-Fi || true
dig google.com +short +time=2 +tries=1 | head -3 || true

if [[ -n $RESTART_PROFILE ]]; then
	PROFILE_ID="$(get_profile_id "$RESTART_PROFILE" 2>/dev/null || true)"
	PROTOCOL="$(get_profile_protocol "$RESTART_PROFILE" 2>/dev/null || echo doh3)"
	if [[ -z $PROFILE_ID ]]; then
		echo "[ERROR] Unknown profile '$RESTART_PROFILE' (need privacy|browsing|gaming or env CTRLD_*_PROFILE)." >&2
		exit 1
	fi

	# SECURITY: Ctrl-C / kill during dig-wait must leave DHCP (never pin 127.0.0.1).
	_repair_interrupt() {
		echo "" >&2
		echo "[WARN] Interrupted — leaving Wi-Fi/LAN on DHCP (safe). Control D was NOT pinned." >&2
		networksetup -setdnsservers Wi-Fi Empty 2>/dev/null || true
		networksetup -setdnsservers "USB 10/100/1000 LAN" Empty 2>/dev/null || true
		exit 130
	}
	trap '_repair_interrupt' INT TERM

	START_ERR=$(mktemp "${TMPDIR:-/tmp}/ctrld_repair.XXXXXX")
	: >"$START_ERR"

	if [[ $FORCE_CD_MODE -eq 1 ]]; then
		export CONTROLD_FORCE_CD_MODE=1
		echo "[INFO] --cd-mode: forcing CD Mode attempt (may fail on API exclude schema)..."
		echo "       argv: ctrld service start --cd $PROFILE_ID --proto $PROTOCOL --config=/etc/controld/ctrld.toml --skip_self_checks"
		_force_reinstall_ctrld_native "$PROFILE_ID" "$PROTOCOL" "$START_ERR" "" "/etc/controld/ctrld.toml" || true
		if [[ -s $START_ERR ]]; then
			grep -viE 'service not installed' "$START_ERR" || true
		fi
		if grep -qiE 'no log output is obtained from ctrld process|Service uninstalled|"listen" and "primary_upstream"' "$START_ERR" 2>/dev/null; then
			echo "[FAIL] ctrld CD Mode start failed hard. Falling through to Local Config..." >&2
		elif _wait_for_dns_ready "127.0.0.1" "$CONTROLD_DNS_READY_RETRIES" "$CONTROLD_DNS_READY_SLEEP" "/etc/controld/ctrld.toml"; then
			echo -e "PROFILE_NAME=$RESTART_PROFILE\nPROFILE_ID=$PROFILE_ID\nPROTOCOL=$PROTOCOL\nINTENDED_PROTOCOL=$PROTOCOL" >/etc/controld/active_profile
			chmod 644 /etc/controld/active_profile
			_apply_localhost_dns "127.0.0.1"
			_write_controld_status_file "WORKING" "cd_mode" "$RESTART_PROFILE" "$PROTOCOL"
			rm -f "$START_ERR"
			trap - INT TERM
			echo "[OK] CD Mode listener healthy on 127.0.0.1"
			grep -E "endpoint|type" /etc/controld/ctrld.toml 2>/dev/null | head -6 || true
			exit 0
		fi
		echo "[WARN] CD Mode dig failed — using profile Local Config (stable path)..."
	else
		echo "[INFO] Stable path: profile-aware Local Config (skipping CD Mode thrash)."
		echo "       Profile=$RESTART_PROFILE id=$PROFILE_ID proto=$PROTOCOL"
		echo "       Force CD Mode later with: sudo $0 --restart $RESTART_PROFILE --cd-mode"
	fi

	if _start_profile_local_fallback "$PROFILE_ID" "$RESTART_PROFILE" "$PROTOCOL" "/etc/controld" "127.0.0.1" "$START_ERR"; then
		rm -f "$START_ERR"
		trap - INT TERM
		echo "[OK] Control D is WORKING via profile Local Config (FALLBACK=1)."
		echo "     This is intentional until Control D fixes CD Mode API exclude schema."
		echo "     Not free DNS — endpoint uses your real profile id."
		grep -E "endpoint|type|bootstrap" /etc/controld/ctrld.toml 2>/dev/null | head -8 || true
		echo "Status: $ROOT/scripts/controld-status.sh"
		exit 0
	fi

	echo "[FAIL] Profile-aware Local Config failed — DNS left on DHCP." >&2
	rm -f "$START_ERR"
	trap - INT TERM
	exit 1
fi

echo "[OK] Repair complete (service stopped; DNS on DHCP)."
echo "Restart with: sudo $0 --restart privacy"
echo "Status:       $ROOT/scripts/controld-status.sh"
