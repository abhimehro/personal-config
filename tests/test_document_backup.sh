#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/document_backup.sh
# Mocks rsync and tar; verifies backup invocation, exclusion flags,
# missing-source handling, archive creation, and old-backup pruning.
#
# Pattern: $MOCK_BIN PATH injection + mock HOME isolation (docs/TESTING.md)
# rsync and tar are intercepted via $MOCK_BIN; no real filesystem backup runs.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/document_backup.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-doc-backup')
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0

check_pass() {
    local name="$1"
    echo "PASS: $name"
    PASS=$((PASS + 1))
}

check_fail() {
    local name="$1"
    local detail="${2:-}"
    echo "FAIL: $name${detail:+ ($detail)}"
    FAIL=$((FAIL + 1))
}

check_output() {
    local name="$1"
    local pattern="$2"
    local logfile="$3"
    if grep -q "$pattern" "$logfile" 2>/dev/null; then
        check_pass "$name"
    else
        check_fail "$name" "pattern '$pattern' not found in $logfile"
    fi
}

# ---- mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

RSYNC_LOG="$TEST_DIR/rsync.log"
TAR_LOG="$TEST_DIR/tar.log"

# Mock rsync: record full invocation to RSYNC_LOG (script suppresses stdout)
cat > "$MOCK_BIN/rsync" << MOCK
#!/usr/bin/env bash
echo "RSYNC: \$*" >> "$RSYNC_LOG"
exit 0
MOCK
chmod +x "$MOCK_BIN/rsync"

# Mock tar: record invocation and touch the archive file for cleanup-count tests.
# -czf <archive> <src>: $1=-czf, $2=archive path (relative to cwd = $BACKUP_DIR)
cat > "$MOCK_BIN/tar" << MOCK
#!/usr/bin/env bash
echo "TAR: \$*" >> "$TAR_LOG"
if [[ "\$1" == "-czf" && -n "\${2:-}" ]]; then
    touch "\$2" 2>/dev/null || true
fi
exit 0
MOCK
chmod +x "$MOCK_BIN/tar"

# ---- mock HOME ----
# Scripts intentionally missing to test graceful skip path.
MOCK_HOME="$TEST_DIR/home"
mkdir -p "$MOCK_HOME/Documents/proj"
mkdir -p "$MOCK_HOME/Desktop"
echo "readme" > "$MOCK_HOME/Documents/proj/readme.txt"
# NOTE: $HOME/Scripts is intentionally absent — tests graceful "not found, skipping" path.

echo "=== Testing maintenance/bin/document_backup.sh ==="

# ---- Test 1: exits 0 with a mix of existing and missing source dirs ----
true > "$RSYNC_LOG"
true > "$TAR_LOG"
t1_exit=0
PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" \
    bash "$SCRIPT" > "$TEST_DIR/t1.log" 2>&1 || t1_exit=$?
if [[ "$t1_exit" -eq 0 ]]; then
    check_pass "exits 0 with existing+missing source directories"
else
    check_fail "exits 0 with existing+missing source directories" "exit=$t1_exit"
    cat "$TEST_DIR/t1.log"
fi

# ---- Test 2: rsync is called (at least once) ----
if grep -q "RSYNC:" "$RSYNC_LOG" 2>/dev/null; then
    check_pass "rsync invoked for existing source directories"
else
    check_fail "rsync invoked for existing source directories" "RSYNC_LOG empty"
fi

# ---- Test 3: rsync uses --exclude='.DS_Store' ----
check_output "rsync --exclude=.DS_Store flag present" \
    "exclude=.DS_Store" "$RSYNC_LOG"

# ---- Test 4: rsync uses --exclude='*.tmp' ----
check_output "rsync --exclude=*.tmp flag present" \
    "exclude=.*tmp" "$RSYNC_LOG"

# ---- Test 5: Backups directory created under mock HOME ----
if [[ -d "$MOCK_HOME/Backups" ]]; then
    check_pass "Backups directory created under mock HOME"
else
    check_fail "Backups directory created under mock HOME" "not found: $MOCK_HOME/Backups"
fi

# ---- Test 6: missing source directory (Scripts) skipped gracefully ----
check_output "missing source dir skipped with warning" \
    "not found, skipping" "$TEST_DIR/t1.log"

# ---- Test 7: tar archive creation attempted ----
if grep -q "TAR:" "$TAR_LOG" 2>/dev/null; then
    check_pass "tar invoked for archive creation"
else
    check_fail "tar invoked for archive creation" "TAR_LOG empty"
fi

# ---- Test 8: mock HOME isolation — backup destinations use mock HOME ----
# Assert via mocked command logs instead of inspecting the real $HOME/Backups.
# The rsync/tar invocations should target $MOCK_HOME/Backups and never $HOME/Backups.
real_backup_dir="$HOME/Backups"
if grep -q "$MOCK_HOME/Backups" "$RSYNC_LOG" 2>/dev/null || \
   grep -q "$MOCK_HOME/Backups" "$TAR_LOG" 2>/dev/null; then
    if ! grep -q "$real_backup_dir" "$RSYNC_LOG" 2>/dev/null && \
       ! grep -q "$real_backup_dir" "$TAR_LOG" 2>/dev/null; then
        check_pass "mock HOME isolation — backups use MOCK_HOME/Backups, not real HOME"
    else
        check_fail "mock HOME isolation — backups use MOCK_HOME/Backups, not real HOME" \
            "real HOME path found in rsync/tar logs: $real_backup_dir"
    fi
else
    check_fail "mock HOME isolation — backups use MOCK_HOME/Backups, not real HOME" \
        "no MOCK_HOME/Backups destination found in rsync/tar logs"
fi

# ---- Test 9: old backup pruning — keeps ≤5 when 7 archives pre-exist ----
# Pre-create 7 dated archives so the script sees them during the cleanup phase.
BACKUP_DIR="$MOCK_HOME/Backups"
mkdir -p "$BACKUP_DIR"
for i in $(seq 1 7); do
    touch "$BACKUP_DIR/documents_backup_2026030${i}_120000.tar.gz"
done
true > "$RSYNC_LOG"
true > "$TAR_LOG"
t9_exit=0
PATH="$MOCK_BIN:$PATH" HOME="$MOCK_HOME" \
    bash "$SCRIPT" > "$TEST_DIR/t9.log" 2>&1 || t9_exit=$?
if [[ "$t9_exit" -eq 0 ]]; then
    check_pass "cleanup run exits 0 when 7 pre-existing archives present"
else
    check_fail "cleanup run exits 0 when 7 pre-existing archives present" "exit=$t9_exit"
    cat "$TEST_DIR/t9.log"
fi
# After pruning, at most 5 archives should remain in total (including any new one from this run).
# shellcheck disable=SC2012  # ls glob matches only known-safe names; find alternative doesn't simplify
remaining=$(ls "$BACKUP_DIR"/documents_backup_*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
if [[ "$remaining" -le 5 ]]; then
    check_pass "old backups pruned (≤5 archives after cleanup of 7+new)"
else
    check_fail "old backups pruned" "expected ≤5, got $remaining"
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
