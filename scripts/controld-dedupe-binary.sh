#!/usr/bin/env bash
# Quarantine shadowed /usr/local/bin/ctrld (dev build) when Homebrew v1.5.3 is kept.
# LaunchDaemon already uses /opt/homebrew/bin/ctrld — this only fixes CLI PATH confusion.
# Also writes world-readable /etc/controld/status and chmods active_profile 644.
# USAGE: sudo ./scripts/controld-dedupe-binary.sh
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
	echo "Run with sudo: sudo $0" >&2
	exit 1
fi

if [[ ! -x /opt/homebrew/bin/ctrld ]]; then
	echo "No Homebrew ctrld at /opt/homebrew/bin/ctrld — aborting." >&2
	exit 1
fi

brew_ver=$(/opt/homebrew/bin/ctrld --version 2>/dev/null | head -1 || true)

if [[ -f /usr/local/bin/ctrld && ! -L /usr/local/bin/ctrld ]]; then
	old_ver=$(/usr/local/bin/ctrld --version 2>/dev/null | head -1 || true)
	ts=$(date +%Y%m%d_%H%M%S)
	q="/usr/local/bin/ctrld.quarantined.$ts"
	echo "Quarantining: /usr/local/bin/ctrld ($old_ver) → $q"
	mv /usr/local/bin/ctrld "$q"
	ln -sf /opt/homebrew/bin/ctrld /usr/local/bin/ctrld
	echo "Linked: /usr/local/bin/ctrld → /opt/homebrew/bin/ctrld ($brew_ver)"
elif [[ -L /usr/local/bin/ctrld ]]; then
	echo "Already a symlink: $(ls -la /usr/local/bin/ctrld)"
else
	echo "No /usr/local/bin/ctrld to quarantine."
fi

install -d -m 755 /etc/controld
if [[ -f /etc/controld/active_profile ]]; then
	chmod 644 /etc/controld/active_profile
fi
if [[ -f /etc/controld/ctrld.toml ]]; then
	chmod 644 /etc/controld/ctrld.toml
fi

BIN=/opt/homebrew/bin/ctrld
VER=$("$BIN" --version 2>/dev/null | head -1 || echo unknown)
DIG=no
if dig @127.0.0.1 google.com +short +time=2 +tries=1 2>/dev/null | grep -qE '^[0-9]'; then
	DIG=yes
fi

PROF=unknown
PROTO=unknown
FB=
# shellcheck disable=SC1091
if [[ -r /etc/controld/active_profile ]]; then
	# shellcheck source=/dev/null
	. /etc/controld/active_profile
fi
PROF=${PROFILE_NAME:-$PROF}
PROTO=${PROTOCOL:-$PROTO}
FB=${FALLBACK-}

MODE=local_fallback
if [[ -f /etc/controld/ctrld.toml ]] && head -1 /etc/controld/ctrld.toml | grep -q 'AUTO-GENERATED VIA CD FLAG'; then
	MODE=cd_mode
fi

STATE=WORKING
[[ $DIG == yes ]] || STATE=BROKEN

{
	echo "STATE=$STATE"
	echo "MODE=$MODE"
	echo "PROFILE=$PROF"
	echo "PROTOCOL=$PROTO"
	echo "FALLBACK=${FB:-0}"
	echo "DIG_OK=$DIG"
	echo "BINARY=$BIN"
	echo "VERSION=$VER"
	echo "PORT53=ctrld"
	echo "UPDATED=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >/etc/controld/status
chmod 644 /etc/controld/status

echo "Wrote /etc/controld/status ($STATE / $MODE)"
echo "which -a ctrld:"
which -a ctrld || true
ctrld --version || true
echo "Done. DNS was not restarted — running listener left alone."
