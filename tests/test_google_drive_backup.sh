#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/google_drive_backup.sh
# Mocks date; verifies dry-run behavior, fail-secure exclusion
# fallback, Monday skip, and argument handling.
# NOTE: google_drive_backup.sh calls /usr/bin/rsync directly (absolute path),
# so rsync cannot be intercepted via PATH mocking; tests use --dry-run instead.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/google_drive_backup.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-gdrive-backup')
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0

check_exit() {
	local name="$1"
	local expected="$2"
	shift 2
	local actual=0
	"$@" >"$TEST_DIR/check.log" 2>&1 || actual=$?
	if [[ $actual -eq $expected ]]; then
		echo "PASS: $name"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $name (expected exit $expected, got $actual)"
		cat "$TEST_DIR/check.log"
		FAIL=$((FAIL + 1))
	fi
}

check_output() {
	local name="$1"
	local pattern="$2"
	local logfile="$3"
	if grep -q "$pattern" "$logfile" 2>/dev/null; then
		echo "PASS: $name"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $name (pattern '$pattern' not found)"
		FAIL=$((FAIL + 1))
	fi
}

# ---- mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

# Mock date for day-of-week tests: returns Monday (1) for +%u
cat >"$MOCK_BIN/date_monday" <<'MOCK'
#!/bin/bash
if [[ "$*" == "+%u" ]]; then
    echo "1"
else
    exec /bin/date "$@"
fi
MOCK
chmod +x "$MOCK_BIN/date_monday"

# ---- shared mock home ----
MOCK_HOME="$TEST_DIR/home"
mkdir -p "$MOCK_HOME"

# ---- Test 1: --help exits 0 ----
check_exit "--help exits 0" 0 \
	bash "$SCRIPT" --help

# ---- Test 2: unknown argument exits 2 ----
check_exit "unknown arg exits 2" 2 \
	bash "$SCRIPT" --bogus-flag

# ---- Test 3: --dry-run --light exits 0 (no backup paths needed) ----
if PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" FORCE_RUN=1 \
	bash "$SCRIPT" --dry-run --light \
	>"$TEST_DIR/t3.log" 2>&1; then
	echo "PASS: --dry-run --light exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: --dry-run --light exited non-zero"
	cat "$TEST_DIR/t3.log"
	FAIL=$((FAIL + 1))
fi

# ---- Test 4: missing excludes file triggers fail-secure fallback ----
# Pass a non-existent excludes file; script should warn and apply defaults
t4_exit=0
PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" FORCE_RUN=1 \
	bash "$SCRIPT" --dry-run --light \
	--excludes "$TEST_DIR/no_such_excludes.txt" \
	>"$TEST_DIR/t4.log" 2>&1 || t4_exit=$?
if [[ $t4_exit -eq 0 ]]; then
	echo "PASS: missing excludes exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: missing excludes exited $t4_exit (expected 0)"
	cat "$TEST_DIR/t4.log"
	FAIL=$((FAIL + 1))
fi

check_output "missing excludes triggers fallback warning" \
	"DEFAULT SECURITY EXCLUSIONS" "$TEST_DIR/t4.log"

# ---- Test 4b: installed and custom excludes cannot expose .gemini ----
mkdir -p "$MOCK_HOME/.gemini"
printf 'synthetic-only\n' >"$MOCK_HOME/.gemini/synthetic-credential.txt"
mkdir -p "$MOCK_HOME/.aws" "$MOCK_HOME/.config/gh" "$MOCK_HOME/Documents"
printf 'synthetic-only\n' >"$MOCK_HOME/.aws/config"
printf 'synthetic-only\n' >"$MOCK_HOME/.config/gh/hosts.yml"
printf 'synthetic-only\n' >"$MOCK_HOME/Documents/.env.local"
printf 'safe config\n' >"$MOCK_HOME/.bashrc"
printf 'optional config\n' >"$MOCK_HOME/.gitconfig"
printf '%s\r\n' '- .gitconfig' >"$TEST_DIR/custom.exclude"

for exclude_case in installed custom; do
	if [[ $exclude_case == installed ]]; then
		excludes="$REPO_ROOT/maintenance/conf/backup.exclude"
	else
		excludes="$TEST_DIR/custom.exclude"
	fi
	destination="$TEST_DIR/backup-$exclude_case"
	if HOME="$MOCK_HOME" FORCE_RUN=1 bash "$SCRIPT" --run --light --no-delete \
		--dest "$destination" --excludes "$excludes" \
		>"$TEST_DIR/t4-$exclude_case.log" 2>&1 && \
		[[ -f "$destination$MOCK_HOME/.bashrc" ]] && \
		[[ ! -e "$destination$MOCK_HOME/.gemini/synthetic-credential.txt" ]] && \
		[[ ! -e "$destination$MOCK_HOME/.aws/config" ]] && \
		[[ ! -e "$destination$MOCK_HOME/.config/gh/hosts.yml" ]] && \
		[[ ! -e "$destination$MOCK_HOME/Documents/.env.local" ]] && \
		{ [[ $exclude_case != custom ]] || [[ ! -e "$destination$MOCK_HOME/.gitconfig" ]]; }; then
		echo "PASS: $exclude_case excludes protect .gemini while backing up other dotfiles"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $exclude_case excludes did not protect .gemini or backup failed"
		cat "$TEST_DIR/t4-$exclude_case.log"
		FAIL=$((FAIL + 1))
	fi
done

# Reject rsync rules that would reset exclusions or include protected files.
for unsafe_case in reset include; do
	if [[ $unsafe_case == reset ]]; then
		printf '!\r\n' >"$TEST_DIR/unsafe.exclude"
	else
		printf '+ .gemini/\r\n' >"$TEST_DIR/unsafe.exclude"
	fi
	check_exit "$unsafe_case rule fails before backup" 2 env HOME="$MOCK_HOME" FORCE_RUN=1 \
		bash "$SCRIPT" --run --light --no-delete --dest "$TEST_DIR/backup-$unsafe_case" \
		--excludes "$TEST_DIR/unsafe.exclude"
	if [[ ! -e "$TEST_DIR/backup-$unsafe_case$MOCK_HOME/.gemini/synthetic-credential.txt" ]]; then
		echo "PASS: $unsafe_case rule did not copy .gemini"
		PASS=$((PASS + 1))
	else
		echo "FAIL: $unsafe_case rule copied .gemini"
		FAIL=$((FAIL + 1))
	fi
done

# ---- Test 5: Monday light-mode skip (no FORCE_RUN) ----
# Mock date to return Monday; light mode should skip and exit 0
cp "$MOCK_BIN/date_monday" "$MOCK_BIN/date"
if PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" \
	bash "$SCRIPT" --dry-run --light \
	>"$TEST_DIR/t5.log" 2>&1; then
	echo "PASS: Monday skip exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: Monday skip exited non-zero"
	cat "$TEST_DIR/t5.log"
	FAIL=$((FAIL + 1))
fi

check_output "Monday skip prints skipping message" \
	"Skipping Light Backup on Monday" "$TEST_DIR/t5.log"
rm -f "$MOCK_BIN/date"

# ---- Test 6: FORCE_RUN=1 bypasses Monday skip ----
cp "$MOCK_BIN/date_monday" "$MOCK_BIN/date"
if PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" FORCE_RUN=1 \
	bash "$SCRIPT" --dry-run --light \
	>"$TEST_DIR/t6.log" 2>&1; then
	echo "PASS: FORCE_RUN=1 bypass exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: FORCE_RUN=1 bypass exited non-zero"
	cat "$TEST_DIR/t6.log"
	FAIL=$((FAIL + 1))
fi

# When FORCE_RUN=1, the script should NOT print the skipping message
if ! grep -q "Skipping Light Backup on Monday" "$TEST_DIR/t6.log" 2>/dev/null; then
	echo "PASS: FORCE_RUN=1 bypasses Monday skip"
	PASS=$((PASS + 1))
else
	echo "FAIL: FORCE_RUN=1 did not bypass Monday skip"
	FAIL=$((FAIL + 1))
fi
rm -f "$MOCK_BIN/date"

# ---- Test 7: --dry-run --full exits 0 ----
if PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" \
	bash "$SCRIPT" --dry-run --full \
	>"$TEST_DIR/t7.log" 2>&1; then
	echo "PASS: --dry-run --full exits 0"
	PASS=$((PASS + 1))
else
	echo "FAIL: --dry-run --full exited non-zero"
	cat "$TEST_DIR/t7.log"
	FAIL=$((FAIL + 1))
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
