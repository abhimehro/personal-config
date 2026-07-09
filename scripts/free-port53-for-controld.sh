#!/usr/bin/env bash
#
# Free host port 53 so Control D (ctrld) can bind — and keep Colima/Lima from
# stealing it again.
#
# Root cause this addresses:
#   Colima/Lima auto-forwards guest DNS (127.0.0.1:53 / ::1:53) to the host.
#   limactl then LISTENs on TCP *:53 (ssh port forwarder). That blocks ctrld
#   from binding UDP/TCP :53; KeepAlive crash-loops; dig @127.0.0.1 times out.
#
# Permanent fix (Lima merge order matters):
#   Write ~/.colima/_lima/_config/override.yaml with ignore rules that include
#   guestIPMustBeZero: false (Lima 2.x defaults MustBeZero=true, which makes
#   naive ignore rules ineffective — see lima-vm/lima#4403).
#   Appending portForwards to ~/.colima/default/colima.yaml alone does NOT
#   rewrite the generated lima.yaml portForwards list reliably.
#
# Default action is NON-DESTRUCTIVE diagnosis. Explicit flags required to stop
# Colima or rewrite override config.
#
# USAGE:
#   ./scripts/free-port53-for-controld.sh              # diagnose only
#   ./scripts/free-port53-for-controld.sh --stop-colima # stop Colima (frees :53)
#   ./scripts/free-port53-for-controld.sh --patch-colima-ignore
#       # write Lima override ignore for guest :53 (requires colima restart)
#
set -euo pipefail

ACTION="diagnose"
for arg in "$@"; do
	case "$arg" in
	--stop-colima) ACTION="stop-colima" ;;
	--patch-colima-ignore) ACTION="patch-colima" ;;
	-h | --help)
		sed -n '2,28p' "$0"
		exit 0
		;;
	*)
		echo "Unknown arg: $arg" >&2
		exit 2
		;;
	esac
done

OVERRIDE_YAML="${HOME}/.colima/_lima/_config/override.yaml"
COLIMA_YAML="${HOME}/.colima/default/colima.yaml"

echo "=== Port 53 holders ==="
if command -v lsof >/dev/null 2>&1; then
	holders=$(lsof -nP -iUDP:53 -iTCP:53 2>/dev/null || true)
	if [[ -n $holders ]]; then
		echo "$holders"
	else
		echo "(none)"
	fi
else
	echo "lsof not available"
fi

echo
echo "=== ctrld / dig ==="
pgrep -xl ctrld || echo "ctrld: not running"
dig @127.0.0.1 google.com +short +time=2 +tries=1 2>&1 | head -5 || true

foreign=""
if command -v lsof >/dev/null 2>&1; then
	while IFS= read -r line; do
		[[ -z $line || $line == COMMAND* ]] && continue
		if [[ $line != *ctrld* ]]; then
			foreign=$(echo "$line" | awk '{print $1, $2}')
			break
		fi
	done < <(lsof -nP -iUDP:53 -iTCP:53 2>/dev/null || true)
fi

_override_has_port53_ignore() {
	local f="$1"
	[[ -f $f ]] || return 1
	# Require guestPort 53 + ignore + guestIPMustBeZero false (Lima 2.x).
	grep -q 'guestPort: 53' "$f" 2>/dev/null || return 1
	grep -q 'ignore: true' "$f" 2>/dev/null || return 1
	grep -q 'guestIPMustBeZero: false' "$f" 2>/dev/null || return 1
	return 0
}

# Permanent Colima/Lima override does not require a live conflict.
if [[ $ACTION == "patch-colima" ]]; then
	mkdir -p "$(dirname "$OVERRIDE_YAML")"
	if _override_has_port53_ignore "$OVERRIDE_YAML"; then
		echo "[OK] $OVERRIDE_YAML already has guestPort 53 ignore (with guestIPMustBeZero: false)."
		echo "Verify after restart: colima stop && colima start && lsof -nP -iTCP:53 -iUDP:53"
		exit 0
	fi
	if [[ -f $OVERRIDE_YAML ]]; then
		backup="${OVERRIDE_YAML}.bak.$(date +%Y%m%d%H%M%S)"
		cp "$OVERRIDE_YAML" "$backup"
		echo "[INFO] Backed up existing override to $backup"
	fi
	# Lima merges override.yaml into every instance. Rules must be listed BEFORE
	# the broad 1-65535 auto-forwards take effect; override is merged last.
	# guestIPMustBeZero: false is REQUIRED on Lima 2.x (default true breaks ignore).
	cat >"$OVERRIDE_YAML" <<'EOF'
# personal-config: do not forward guest DNS to host :53 (breaks Control D / ctrld)
# Written by scripts/free-port53-for-controld.sh --patch-colima-ignore
# See: https://github.com/lima-vm/lima/issues/4403 (guestIPMustBeZero)
portForwards:
  - guestIP: "127.0.0.1"
    guestPort: 53
    guestIPMustBeZero: false
    ignore: true
  - guestIP: "::1"
    guestPort: 53
    guestIPMustBeZero: false
    ignore: true
  - guestIP: "0.0.0.0"
    guestPort: 53
    guestIPMustBeZero: false
    ignore: true
  - guestIP: "::"
    guestPort: 53
    guestIPMustBeZero: false
    ignore: true
EOF
	chmod 600 "$OVERRIDE_YAML"
	echo "[OK] Wrote $OVERRIDE_YAML (Lima override — applies on next colima start)"
	# Also stamp colima.yaml with a comment pointer (does not replace override).
	if [[ -f $COLIMA_YAML ]] && ! grep -q 'personal-config:.*override.yaml' "$COLIMA_YAML" 2>/dev/null; then
		printf '\n# personal-config: guest :53 ignore lives in ~/.colima/_lima/_config/override.yaml\n' >>"$COLIMA_YAML"
	fi
	echo
	echo "Apply with:"
	echo "  colima stop && colima start"
	echo "Then confirm limactl is NOT on :53:"
	echo "  lsof -nP -iTCP:53 -iUDP:53"
	echo "Then start Control D:"
	echo "  sudo ./scripts/repair-controld-keepalive.sh --restart privacy"
	exit 0
fi

if [[ -z $foreign ]]; then
	echo
	echo "[OK] No foreign :53 holder detected."
	if ! _override_has_port53_ignore "$OVERRIDE_YAML"; then
		echo "[HINT] Colima may reclaim :53 on next start. Permanent fix:"
		echo "  ./scripts/free-port53-for-controld.sh --patch-colima-ignore"
		echo "  then: colima stop && colima start"
	else
		echo "[OK] Lima override already ignores guest :53."
	fi
	exit 0
fi

echo
echo "[WARN] Foreign port 53 holder: $foreign"

case "$ACTION" in
diagnose)
	echo
	echo "Next steps (pick one):"
	echo "  1) Temporary:  ./scripts/free-port53-for-controld.sh --stop-colima"
	echo "  2) Permanent:  ./scripts/free-port53-for-controld.sh --patch-colima-ignore"
	echo "                 then: colima stop && colima start"
	echo "  3) Repair CD:  sudo ./scripts/repair-controld-keepalive.sh --restart privacy"
	echo "                 (only after :53 is free of limactl)"
	exit 1
	;;
stop-colima)
	if ! command -v colima >/dev/null 2>&1; then
		echo "[ERROR] colima not in PATH" >&2
		exit 1
	fi
	echo "[INFO] Stopping Colima to free host :53..."
	colima stop
	sleep 1
	echo "=== After stop ==="
	lsof -nP -iUDP:53 -iTCP:53 2>/dev/null || echo "(none)"
	echo "[OK] Port 53 should be free. Restart Control D:"
	echo "  sudo ./scripts/repair-controld-keepalive.sh --restart privacy"
	echo "For permanent coexistence, also run:"
	echo "  ./scripts/free-port53-for-controld.sh --patch-colima-ignore"
	echo "  colima start   # after Control D is healthy"
	;;
*)
	echo "Internal error: unknown action $ACTION" >&2
	exit 2
	;;
esac
