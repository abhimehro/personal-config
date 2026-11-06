#!/usr/bin/env bash
#
# Unit tests for scripts/disk-guard.sh
#
# Mocks df, sysctl, du, memory_pressure and sleep via PATH injection so the
# guard's decisions are deterministic and the suite runs on Linux CI (where
# vm.swapusage does not exist at all -- which is itself one of the cases below).
#
# The interesting half of this file is the fail-closed tests. docs/DISK-GUARD.md
# Wiring rule 8 exists because a 2026-11-03 copy job ran to completion with a
# dead swap sensor logging `NA` in plain sight: a guard that cannot read its
# sensor must PAUSE, never report a healthy state it did not measure.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/disk-guard.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-disk-guard')
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0

ok() {
	echo "PASS: $1"
	PASS=$((PASS + 1))
}
bad() {
	echo "FAIL: $1"
	FAIL=$((FAIL + 1))
}

assert_rc() {
	local name="$1" want="$2" got="$3"
	if [ "$want" = "$got" ]; then ok "$name (rc=$got)"; else bad "$name (want rc=$want, got rc=$got)"; fi
}

assert_out() {
	local name="$1" pattern="$2" out="$3"
	if printf '%s' "$out" | grep -Eq "$pattern"; then
		ok "$name"
	else
		bad "$name (pattern '$pattern' not found in: $(printf '%s' "$out" | head -3 | tr '\n' '|'))"
	fi
}

assert_no_out() {
	local name="$1" pattern="$2" out="$3"
	if printf '%s' "$out" | grep -Eq "$pattern"; then
		bad "$name (pattern '$pattern' unexpectedly present)"
	else
		ok "$name"
	fi
}

# ---- shared mock bin -------------------------------------------------------
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

# Every mock reads its value from the environment so one mock bin can be
# re-parameterised per case instead of being rewritten.
cat >"$MOCK_BIN/df" <<'MOCK'
#!/usr/bin/env bash
if [ "${MOCK_DF_BROKEN:-0}" = 1 ]; then
	# Present but silent: exits non-zero with no second line, so an awk-based
	# parser gets an empty string rather than an error it would notice.
	exit 1
fi
# $4 of line 2 is "Available" in 1K-blocks, which is what avail_miib() reads.
printf 'Filesystem 1K-blocks Used Available Capacity Mounted-on\n'
printf '/dev/disk3s5 460000000 300000000 %s 92%% /System/Volumes/Data\n' "${MOCK_AVAIL_KIB:-20000000}"
MOCK
chmod +x "$MOCK_BIN/df"

cat >"$MOCK_BIN/sysctl" <<'MOCK'
#!/usr/bin/env bash
if [ "${MOCK_SYSCTL_MISSING:-0}" = 1 ]; then
	# What "command not found" looks like to a caller that captures stdout: no
	# output and a non-zero status. This is the Linux CI case, where
	# vm.swapusage does not exist at all.
	exit 127
fi
if [ "${MOCK_SYSCTL_BROKEN:-0}" = 1 ]; then
	# Present but unparseable, and it exits 0: the exact shape of a dead sensor.
	# A guard that only checks the exit status reads this as healthy. This is
	# the swapfree_miib=NA regression.
	printf 'vm.swapusage: (not supported)\n'
	exit 0
fi
printf 'total = %sM  used = %sM  free = %sM\n' \
	"${MOCK_SWAP_TOTAL:-4096.00}" "${MOCK_SWAP_USED:-3000.00}" "${MOCK_SWAP_FREE:-900.00}"
MOCK
chmod +x "$MOCK_BIN/sysctl"

cat >"$MOCK_BIN/du" <<'MOCK'
#!/usr/bin/env bash
if [ "${MOCK_DU_BROKEN:-0}" = 1 ]; then exit 1; fi
printf '%s\t%s\n' "${MOCK_DU_KIB:-1024}" "${*: -1}"
MOCK
chmod +x "$MOCK_BIN/du"

cat >"$MOCK_BIN/memory_pressure" <<'MOCK'
#!/usr/bin/env bash
printf 'System-wide memory free percentage: %s%%\n' "${MOCK_MEM_FREE:-44}"
MOCK
chmod +x "$MOCK_BIN/memory_pressure"

# A real `sleep` would make the gate tests take minutes; count the calls so the
# "never retry an ABORT" assertion has evidence rather than just a fast return.
cat >"$MOCK_BIN/sleep" <<'MOCK'
#!/usr/bin/env bash
printf 'x\n' >>"${MOCK_SLEEP_LOG:-/dev/null}"
MOCK
chmod +x "$MOCK_BIN/sleep"

STATE="$TEST_DIR/state"
SCRATCH="$TEST_DIR/scratch"
mkdir -p "$STATE" "$SCRATCH"

# run <args...> -- invokes the guard with the mocks on PATH and isolated state.
# Uses env(1) rather than a subshell export, so nothing leaks between cases.
run() {
	env PATH="$MOCK_BIN:$PATH" \
		DISK_GUARD_STATE="$STATE" \
		DISK_GUARD_SCRATCH="$SCRATCH" \
		"$SCRIPT" "$@"
}

# run_env "K=V K2=V2" <args...> -- same, with per-case sensor overrides. Later
# assignments win in env(1), so a caller may also retarget DISK_GUARD_SCRATCH.
run_env() {
	local envs="$1"
	shift
	# shellcheck disable=SC2086 # deliberate: the caller supplies whitespace-separated K=V pairs
	env PATH="$MOCK_BIN:$PATH" \
		DISK_GUARD_STATE="$STATE" \
		DISK_GUARD_SCRATCH="$SCRATCH" \
		$envs \
		"$SCRIPT" "$@"
}

# ---- check: the three floors ----------------------------------------------
out=$(run_env "MOCK_AVAIL_KIB=20000000" check 2>&1) && rc=0 || rc=$?
assert_rc "check: 19.5 GiB avail is OK" 0 "$rc"

out=$(run_env "MOCK_AVAIL_KIB=5000000" check 2>&1) && rc=0 || rc=$?
assert_rc "check: 4882 MiB avail is PAUSE (below 6144, above 4096)" 1 "$rc"
assert_out "check: PAUSE names the pause floor" 'PAUSE.*pause floor' "$out"

out=$(run_env "MOCK_AVAIL_KIB=2000000" check 2>&1) && rc=0 || rc=$?
assert_rc "check: 1953 MiB avail is ABORT (below 4096)" 2 "$rc"
assert_out "check: ABORT names the hard floor" 'ABORT.*hard floor' "$out"

# Swap FREE is the disk-risk sensor, not swap USED: macOS allocates the next
# swapfile onto the Data volume, so low free is what consumes real disk.
out=$(run_env "MOCK_AVAIL_KIB=20000000 MOCK_SWAP_FREE=100.00" check 2>&1) && rc=0 || rc=$?
assert_rc "check: swap free 100 MiB is PAUSE despite ample disk" 1 "$rc"
assert_out "check: PAUSE blames swap free" 'swap free 100MiB' "$out"

out=$(run_env "MOCK_AVAIL_KIB=20000000 MOCK_SWAP_USED=5000.00" check 2>&1) && rc=0 || rc=$?
assert_rc "check: high swap USED only warns, never pauses" 0 "$rc"
assert_out "check: warns on swap used" 'WARN swap used 5000MiB' "$out"

# ---- check: fail closed on an unreadable sensor (Wiring rule 8) ------------
out=$(run_env "MOCK_SYSCTL_BROKEN=1" check 2>&1) && rc=0 || rc=$?
assert_rc "check: unparseable sysctl is PAUSE, not OK" 1 "$rc"
assert_out "check: says the sensor was unreadable" 'sensor unreadable' "$out"
assert_no_out "check: never logs a healthy OK it did not measure" '^OK|avail=[0-9]+MiB swap_used=[0-9]+MiB swap_free=[0-9]+MiB$' "$out"

# sysctl absent entirely -- the Linux CI case, and the reason this guard cannot
# be trusted on a host where it has not been seen fail.
out=$(run_env "MOCK_SYSCTL_MISSING=1" check 2>&1) && rc=0 || rc=$?
assert_rc "check: a sysctl that returns nothing is PAUSE, not OK" 1 "$rc"
assert_out "check: reports swap_free=NA for the missing sensor" 'swap_free=NA' "$out"

out=$(run_env "MOCK_DF_BROKEN=1" check 2>&1) && rc=0 || rc=$?
assert_rc "check: silent df is PAUSE, not OK" 1 "$rc"
assert_out "check: reports avail=NA for the dead df sensor" 'avail=NA' "$out"

# ---- report ---------------------------------------------------------------
out=$(run_env "MOCK_AVAIL_KIB=20000000 MOCK_DU_KIB=28672" report 2>&1) && rc=0 || rc=$?
assert_rc "report: exits 0 on healthy sensors" 0 "$rc"
# The capture2.py bug: it compared ABSOLUTE free MiB against a headroom target,
# so the guard never tripped. Headroom must be avail minus the hard floor.
assert_out "report: headroom = avail - HARD (19531 - 4096 = 15435)" 'headroom_above_hard_floor=15435MiB' "$out"
assert_out "report: scratch usage is reported" 'scratch=28MiB / cap=32MiB' "$out"

out=$(run_env "MOCK_AVAIL_KIB=20000000 MOCK_DU_KIB=31744" report 2>&1) && rc=0 || rc=$?
assert_out "report: SCRATCH_CREEP fires above the 30 MiB warn line" 'SCRATCH_CREEP: 31MiB > warn 30MiB' "$out"

out=$(run_env "MOCK_SYSCTL_BROKEN=1" report 2>&1) && rc=0 || rc=$?
assert_rc "report: still exits 0 (it is a display command)" 0 "$rc"
assert_out "report: prints NA rather than a blank for the dead sensor" 'swap total=NA' "$out"
assert_out "report: flags SENSOR_UNREADABLE" 'SENSOR_UNREADABLE' "$out"
assert_out "report: still computes what it can measure" 'headroom_above_hard_floor=15435MiB' "$out"

# A dead disk sensor is the one that makes headroom unknowable, so headroom must
# say NA rather than print a number derived from nothing.
out=$(run_env "MOCK_DF_BROKEN=1" report 2>&1) && rc=0 || rc=$?
assert_out "report: headroom is NA when avail cannot be read" 'headroom_above_hard_floor=NA' "$out"
assert_out "report: avail is NA when df is silent" 'avail=NA' "$out"

# An absent scratch root legitimately holds zero bytes; that is not a dead sensor.
out=$(run_env "DISK_GUARD_SCRATCH=$TEST_DIR/does-not-exist MOCK_DU_KIB=999999" report 2>&1) && rc=0 || rc=$?
assert_out "report: absent scratch root reads 0, not NA" 'scratch=0MiB' "$out"
assert_no_out "report: absent scratch root is not SENSOR_UNREADABLE" 'SENSOR_UNREADABLE' "$out"

# ---- budget ---------------------------------------------------------------
# 1 MiB, rounded up from bytes, into scratch with room under the cap.
out=$(run_env "MOCK_AVAIL_KIB=20000000 MOCK_DU_KIB=1024" budget 1048576 2>&1) && rc=0 || rc=$?
assert_rc "budget: 1 MiB scratch write fits" 0 "$rc"
assert_out "budget: rounds bytes up to whole MiB" 'OK 1MiB write fits' "$out"
assert_out "budget: shows scratch moving 1->2MiB" 'scratch 1->2MiB of 32MiB cap' "$out"

# A write that would breach hard floor + reserve.
out=$(run_env "MOCK_AVAIL_KIB=5242880" budget 2147483648 2>&1) && rc=0 || rc=$?
assert_rc "budget: 2 GiB write against 5 GiB avail is REFUSED" 2 "$rc"
assert_out "budget: names hard + reserve" 'need >= 5120MiB \(hard 4096 \+ reserve 1024\)' "$out"

# The scratch cap applies when no dest is given (legacy behaviour, unchanged).
out=$(run_env "MOCK_AVAIL_KIB=20000000 MOCK_DU_KIB=31744" budget 2097152 2>&1) && rc=0 || rc=$?
assert_rc "budget: 2 MiB over a 31 MiB scratch is REFUSED by the cap" 2 "$rc"
assert_out "budget: says the scratch cap is what refused it" 'scratch would reach 33MiB, cap is 32MiB' "$out"

# THE QUEUED FIX: a dest outside scratch must not be charged to the scratch cap.
# Before this, an 8.59 GiB CloudDocs write was refused spuriously because the
# cap branch was written for scratch writes only.
CLOUD="$TEST_DIR/CloudDocs/HomeBackup"
mkdir -p "$CLOUD"
out=$(run_env "MOCK_AVAIL_KIB=20000000 MOCK_DU_KIB=31744" budget 2097152 "$CLOUD" 2>&1) && rc=0 || rc=$?
assert_rc "budget: same 2 MiB write with an outside dest is OK" 0 "$rc"
assert_out "budget: states the scratch cap was skipped and why" 'scratch cap skipped: dest .* is outside' "$out"
assert_out "budget: still reports what the write leaves on disk" 'leaves 19529MiB' "$out"

# The disk floor still applies to an outside dest -- skipping the cap is not
# skipping the guard.
out=$(run_env "MOCK_AVAIL_KIB=5242880" budget 2147483648 "$CLOUD" 2>&1) && rc=0 || rc=$?
assert_rc "budget: outside dest does not bypass the disk floor" 2 "$rc"

# A dest INSIDE scratch is still a scratch write.
out=$(run_env "MOCK_AVAIL_KIB=20000000 MOCK_DU_KIB=31744" budget 2097152 "$SCRATCH/sub" 2>&1) && rc=0 || rc=$?
assert_rc "budget: dest inside scratch still applies the cap" 2 "$rc"

out=$(run_env "MOCK_SYSCTL_BROKEN=1 MOCK_DU_BROKEN=1" budget 1024 2>&1) && rc=0 || rc=$?
assert_rc "budget: unreadable sensors REFUSE the write" 2 "$rc"
assert_out "budget: says it could not read the sensors" 'cannot read the sensors needed to budget' "$out"

out=$(run budget 2>&1) && rc=0 || rc=$?
assert_rc "budget: missing <bytes> is a usage error" 1 "$rc"

# ---- gate -----------------------------------------------------------------
SLEEP_LOG="$TEST_DIR/sleeps"
slept() { [ -s "$SLEEP_LOG" ] && echo yes || echo no; }

: >"$SLEEP_LOG"
out=$(run_env "MOCK_SLEEP_LOG=$SLEEP_LOG MOCK_AVAIL_KIB=20000000" gate healthy 5 1 2>&1) && rc=0 || rc=$?
assert_rc "gate: passes straight through when check is clean" 0 "$rc"
assert_out "gate: a clean gate never sleeps" '^no$' "$(slept)"

: >"$SLEEP_LOG"
out=$(run_env "MOCK_SLEEP_LOG=$SLEEP_LOG MOCK_AVAIL_KIB=2000000" gate abort 5 1 2>&1) && rc=0 || rc=$?
assert_rc "gate: ABORT propagates as 2" 2 "$rc"
assert_out "gate: says it is not retrying" 'ABORT -- hard floor breached, not retrying' "$out"
assert_out "gate: ABORT never enters the retry loop" '^no$' "$(slept)"

: >"$SLEEP_LOG"
out=$(run_env "MOCK_SLEEP_LOG=$SLEEP_LOG MOCK_AVAIL_KIB=5000000" gate pause 3 1 2>&1) && rc=0 || rc=$?
assert_rc "gate: a PAUSE that never clears times out as 1" 1 "$rc"
assert_out "gate: reports how long it waited" 'still PAUSED after 3s' "$out"
assert_out "gate: the timeout loop actually polled" '^yes$' "$(slept)"

# ---- usage ----------------------------------------------------------------
out=$(run nonsense 2>&1) && rc=0 || rc=$?
assert_rc "usage: unknown subcommand exits 64" 64 "$rc"
assert_out "usage: documents the optional budget dest" 'budget <bytes> \[dest\]' "$out"

echo ""
echo "Passed: $PASS  Failed: $FAIL"
[ "$FAIL" -eq 0 ]
