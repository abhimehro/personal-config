#!/usr/bin/env bash
# Disk-safety governor for long-running, I/O-heavy maintenance work on macOS.
#
# Why this exists: on 2026-11-02 the Data volume swung between 128 MiB and
# 7.6 GiB available while the workflow driving it wrote only 16 MiB, and the
# machine became unusable (no new terminal sessions could be opened). The cause
# was not the workflow's own output -- it is swap growth on a machine with 8 GiB
# of RAM (/private/var/vm lives on the Data volume) plus sparse VM disks that
# expand on demand and File Provider placeholders that materialise on read. A
# "1.5 GiB free is enough" floor is therefore far too low; the machine needs
# several GiB of slack for churn it does not control.
#
# Contract, thresholds and the incident record live in docs/DISK-GUARD.md.
# Callers must not re-implement these numbers: call `disk-guard.sh check` before
# starting I/O, `disk-guard.sh budget <bytes> [dest]` before any write of known
# size, and `disk-guard.sh gate <label>` to wait out a PAUSE.
#
# Wiring rule 8 (docs/DISK-GUARD.md): a guard that never fires is
# indistinguishable from a guard that never needed to. Every sensor here fails
# closed -- an unreadable reading produces PAUSE or REFUSED, never a silent
# healthy-looking number. tests/test_disk_guard.sh injects each failure.

set -euo pipefail

VOL="${DISK_GUARD_VOL:-/System/Volumes/Data}"
STATE_DIR="${DISK_GUARD_STATE:-$HOME/.cache/disk-guard}"
LOG="$STATE_DIR/guard.log"

# --- Floors, in MiB of AVAILABLE space on $VOL -----------------------------
# HARD : refuse everything, stop the workflow, ask the user to free space.
# PAUSE: no new I/O-heavy work; read-only inspection still allowed.
# WARN : proceed, but log and say so.
HARD_MIIB="${DISK_GUARD_HARD:-4096}"
PAUSE_MIIB="${DISK_GUARD_PAUSE:-6144}"
WARN_MIIB="${DISK_GUARD_WARN:-8192}"

# Any single planned write must leave at least this much ABOVE the hard floor.
RESERVE_MIIB="${DISK_GUARD_RESERVE:-1024}"

# --- Swap / memory ceilings ------------------------------------------------
# The disk-risk condition is not "swap is large" -- this machine legitimately
# runs ~4 GiB of swap under normal GUI load on 8 GiB RAM. It is "swap is about
# to expand", because macOS allocates the next swapfile onto $VOL and consumes
# real disk. So PAUSE on low swap FREE, and only WARN on high swap USED.
SWAP_FREE_PAUSE_MIIB="${DISK_GUARD_SWAP_FREE:-512}"
SWAP_USED_WARN_MIIB="${DISK_GUARD_SWAP_USED:-4096}"
SWAP_TOTAL_WARN_MIIB="${DISK_GUARD_SWAP_TOTAL:-6144}"

# --- Scratch budget (cumulative bytes a workflow may write locally) --------
# Override per workflow. The default is the Jules-analysis scratch root, whose
# contents are cited by name in docs/jules-proactive-analysis-2026-11.md §25;
# see the comment beside SCRATCH_CAP_MIIB before pruning anything there.
SCRATCH_ROOT="${DISK_GUARD_SCRATCH:-$HOME/jules-analysis}"
# Raised 25 -> 32 on 2026-11-03 (approved). The 3 MiB overage at the time was
# entirely load-bearing reproduction evidence cited by name in
# docs/jules-proactive-analysis-2026-11.md section 25 -- do NOT "clean up" these
# three to get back under the old cap:
#   index-origins.ndjson    2.1 MiB  origin/status census over the 264 MiB index
#   phase6-tar-listing.txt  1.7 MiB  the *listing* half of the section 23 Rule 3
#                                    content evidence for the archive-integrity
#                                    verdict; reproducible only by another
#                                    ~16-minute streaming pass over 8.6 GiB
#   proactive-corpus.json   448 KiB  the 1,158-session local proactive corpus
# capture-2/ was already pruned 13,964 -> 3,344 KiB against a citation
# intersect, so nothing else in the tree is prunable without breaking the record.
SCRATCH_CAP_MIIB="${DISK_GUARD_SCRATCH_CAP:-32}"
# Flag before the cap is hit. The ceiling was raised once and should not become
# a habit: crossing this line means something new is accumulating, not that the
# cap needs another bump.
SCRATCH_WARN_MIIB="${DISK_GUARD_SCRATCH_WARN:-30}"

mkdir -p "$STATE_DIR"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$LOG"; }

# --- Sensors ---------------------------------------------------------------
# Each prints an integer on success and returns 1 when it cannot read one. They
# never print a placeholder: the caller decides how to fail, and every caller
# here fails closed.

avail_miib() {
	local k
	k=$(df -k "$VOL" 2>/dev/null | awk 'NR==2 {printf "%d", $4/1024}')
	[ -n "$k" ] || return 1
	printf '%s' "$k"
}

swap_miib() {
	# vm.swapusage prints e.g. "total = 5120.00M  used = 3614.56M  free = 1505.44M"
	local v
	v=$(sysctl -n vm.swapusage 2>/dev/null |
		awk -v want="$1" '{
			for (i = 1; i <= NF; i++) {
				if ($i == want) { v = $(i+2); sub(/M$/, "", v); printf "%d", v; exit }
			}
		}')
	[ -n "$v" ] || return 1
	printf '%s' "$v"
}

# Display only -- no gate reads this, so a missing value is not a fail-open.
mem_free_pct() {
	memory_pressure 2>/dev/null |
		awk -F': ' '/percentage/ {gsub(/[^0-9]/, "", $2); print $2; exit}'
}

scratch_miib() {
	# An absent scratch root legitimately holds zero bytes; an existing one that
	# `du` cannot read is an unreadable sensor and must not report 0.
	if [ ! -d "$SCRATCH_ROOT" ]; then
		printf '0'
		return 0
	fi
	local k
	k=$(du -sk "$SCRATCH_ROOT" 2>/dev/null | awk '{print $1}')
	[ -n "$k" ] || return 1
	printf '%d' "$((k / 1024))"
}

# --- report ---------------------------------------------------------------
cmd_report() {
	local a="" st="" su="" sf="" mf="" sc="" sensors_ok=1
	a=$(avail_miib) || sensors_ok=0
	st=$(swap_miib total) || sensors_ok=0
	su=$(swap_miib used) || sensors_ok=0
	sf=$(swap_miib free) || sensors_ok=0
	mf=$(mem_free_pct) || true
	sc=$(scratch_miib) || sensors_ok=0

	printf 'avail=%sMiB (hard=%s pause=%s warn=%s)\n' "${a:-NA}" "$HARD_MIIB" "$PAUSE_MIIB" "$WARN_MIIB"
	printf 'swap total=%sMiB used=%sMiB free=%sMiB (pause when free<%sMiB, warn when used>%sMiB)\n' \
		"${st:-NA}" "${su:-NA}" "${sf:-NA}" "$SWAP_FREE_PAUSE_MIIB" "$SWAP_USED_WARN_MIIB"
	printf 'memory_free=%s%%\n' "${mf:-?}"
	printf 'scratch=%sMiB / cap=%sMiB at %s\n' "${sc:-NA}" "$SCRATCH_CAP_MIIB" "$SCRATCH_ROOT"

	if ((sensors_ok == 0)); then
		printf 'SENSOR_UNREADABLE: at least one of df/sysctl/du returned no parseable value. Report is incomplete; check/gate/budget will fail closed.\n' >&2
		log "SENSOR_UNREADABLE avail=${a:-NA} swap_free=${sf:-NA} scratch=${sc:-NA}"
	fi

	if [ -n "$sc" ] && ((sc > SCRATCH_WARN_MIIB)); then
		printf 'SCRATCH_CREEP: %sMiB > warn %sMiB -- something new is accumulating; investigate rather than raising the cap again\n' \
			"$sc" "$SCRATCH_WARN_MIIB" >&2
		log "WARN scratch_creep scratch=${sc}MiB warn=${SCRATCH_WARN_MIIB}MiB cap=${SCRATCH_CAP_MIIB}MiB"
	fi

	# Headroom is avail MINUS the hard floor -- an earlier capture script
	# compared raw avail against the headroom target, so it never tripped.
	if [ -n "$a" ]; then
		printf 'headroom_above_hard_floor=%sMiB\n' "$((a - HARD_MIIB))"
	else
		printf 'headroom_above_hard_floor=NA\n'
	fi
	return 0
}

# --- check: exit 0 ok / 1 pause / 2 abort --------------------------------
cmd_check() {
	local a="" su="" st="" sf="" sensors_ok=1 rc=0 why=""
	a=$(avail_miib) || sensors_ok=0
	su=$(swap_miib used) || sensors_ok=0
	st=$(swap_miib total) || sensors_ok=0
	sf=$(swap_miib free) || sensors_ok=0

	if ((sensors_ok == 0)); then
		printf 'PAUSE sensor unreadable (avail=%s swap_used=%s swap_total=%s swap_free=%s) -- refusing to report a healthy state this guard cannot measure\n' \
			"${a:-NA}" "${su:-NA}" "${st:-NA}" "${sf:-NA}" >&2
		log "PAUSE sensor_unreadable avail=${a:-NA} swap_free=${sf:-NA}"
		return 1
	fi

	if ((a < HARD_MIIB)); then
		rc=2
		why="avail ${a}MiB < hard floor ${HARD_MIIB}MiB"
	elif ((a < PAUSE_MIIB)); then
		rc=1
		why="avail ${a}MiB < pause floor ${PAUSE_MIIB}MiB"
	elif ((sf < SWAP_FREE_PAUSE_MIIB)); then
		rc=1
		why="swap free ${sf}MiB < ${SWAP_FREE_PAUSE_MIIB}MiB (next swapfile would land on ${VOL})"
	fi

	if ((rc == 0 && a < WARN_MIIB)); then
		printf 'WARN avail %sMiB < %sMiB\n' "$a" "$WARN_MIIB"
		log "WARN avail=${a}MiB"
	fi
	if ((rc == 0 && su > SWAP_USED_WARN_MIIB)); then
		printf 'WARN swap used %sMiB > %sMiB\n' "$su" "$SWAP_USED_WARN_MIIB"
		log "WARN swap_used=${su}MiB"
	fi
	if ((rc == 0 && st > SWAP_TOTAL_WARN_MIIB)); then
		printf 'WARN swap total %sMiB > %sMiB\n' "$st" "$SWAP_TOTAL_WARN_MIIB"
		log "WARN swap_total=${st}MiB"
	fi

	if ((rc > 0)); then
		printf '%s %s\n' "$([[ $rc -eq 2 ]] && echo ABORT || echo PAUSE)" "$why" >&2
		log "$([[ $rc -eq 2 ]] && echo ABORT || echo PAUSE) ${why}"
	else
		log "OK avail=${a}MiB swap_used=${su}MiB swap_free=${sf}MiB"
	fi
	return "$rc"
}

# --- budget <bytes> [dest]: will this write fit and stay clear of the floor? -
# dest is OPTIONAL. Without it, behaviour is unchanged: the write is assumed to
# land in SCRATCH_ROOT and is checked against both the disk floor and the scratch
# cap. Pass a dest outside SCRATCH_ROOT (e.g. a CloudDocs path) and the scratch-cap
# branch is skipped -- it was written for scratch writes only, so applying it to a
# write elsewhere refuses spuriously. The disk-floor branch always applies.
#
# <bytes> must count every byte the operation MATERIALISES, not just the bytes it
# writes. A copy whose source is a `dataless` File Provider file costs
# hydrate(source) + stage(dest) -- double the file size. Check `ls -lO` for the
# `dataless` flag and `stat -f %b` for resident blocks before budgeting.
cmd_budget() {
	local want_b="${1:?usage: disk-guard.sh budget <bytes> [dest]}"
	local dest="${2:-}"
	local a="" sc="" need sensors_ok=1
	a=$(avail_miib) || sensors_ok=0
	sc=$(scratch_miib) || sensors_ok=0

	if ((sensors_ok == 0)); then
		printf 'REFUSED: cannot read the sensors needed to budget this write (avail=%s scratch=%s)\n' \
			"${a:-NA}" "${sc:-NA}" >&2
		log "REFUSED budget sensor_unreadable want=${want_b}B"
		return 2
	fi

	need=$(((want_b + 1048575) / 1048576)) # bytes -> MiB, rounded up
	if ((a - need < HARD_MIIB + RESERVE_MIIB)); then
		printf 'REFUSED write of %sMiB: would leave %sMiB, need >= %sMiB (hard %s + reserve %s)\n' \
			"$need" "$((a - need))" "$((HARD_MIIB + RESERVE_MIIB))" "$HARD_MIIB" "$RESERVE_MIIB" >&2
		log "REFUSED budget want=${need}MiB avail=${a}MiB"
		return 2
	fi

	if [[ -n $dest && $dest != "$SCRATCH_ROOT"* ]]; then
		printf 'OK %sMiB write fits (avail %sMiB, leaves %sMiB); scratch cap skipped: dest %s is outside %s\n' \
			"$need" "$a" "$((a - need))" "$dest" "$SCRATCH_ROOT"
		log "OK budget want=${need}MiB avail=${a}MiB dest=${dest} scratch_cap=skipped"
		return 0
	fi

	if ((sc + need > SCRATCH_CAP_MIIB)); then
		printf 'REFUSED: scratch would reach %sMiB, cap is %sMiB. Send bulk output to a remote instead.\n' \
			"$((sc + need))" "$SCRATCH_CAP_MIIB" >&2
		log "REFUSED scratch_cap want=${need}MiB scratch=${sc}MiB"
		return 2
	fi

	printf 'OK %sMiB write fits (avail %sMiB, scratch %s->%sMiB of %sMiB cap)\n' \
		"$need" "$a" "$sc" "$((sc + need))" "$SCRATCH_CAP_MIIB"
	log "OK budget want=${need}MiB avail=${a}MiB scratch=${sc}MiB"
}

# --- gate <label>: check, and on PAUSE poll until safe or timeout ----------
cmd_gate() {
	local label="${1:-step}"
	local timeout_s="${2:-300}" interval_s="${3:-30}" waited=0 rc=0
	while :; do
		rc=0
		cmd_check || rc=$?
		if ((rc == 0)); then
			((waited > 0)) && printf 'gate[%s]: cleared after %ss\n' "$label" "$waited"
			log "gate[${label}] passed waited=${waited}s"
			return 0
		fi
		if ((rc == 2)); then
			printf 'gate[%s]: ABORT -- hard floor breached, not retrying.\n' "$label" >&2
			log "gate[${label}] ABORT"
			return 2
		fi
		if ((waited >= timeout_s)); then
			printf 'gate[%s]: still PAUSED after %ss.\n' "$label" "$waited" >&2
			log "gate[${label}] timeout waited=${waited}s"
			return 1
		fi
		sleep "$interval_s"
		waited=$((waited + interval_s))
	done
}

case "${1:-check}" in
report) cmd_report ;;
check) cmd_check ;;
budget)
	shift
	cmd_budget "$@"
	;;
gate)
	shift
	cmd_gate "$@"
	;;
*)
	printf 'usage: %s {report|check|budget <bytes> [dest]|gate <label> [timeout_s] [interval_s]}\n' "$0" >&2
	exit 64
	;;
esac
