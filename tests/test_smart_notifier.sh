#!/usr/bin/env bash
#
# Unit tests for maintenance/bin/smart_notifier.sh
# Mocks: osascript
#
# Covers:
#   1. Script exits 0 and writes load message to notifications.log
#   2. smart_notify dispatches notification via osascript (call-log assertion)
#   3. Graceful degradation when osascript is absent — exits 0, logs fallback
#   4. Empty title/message fails validation and returns non-zero
#   5. SMART_NOTIFIER_DISABLE=1 suppresses osascript dispatch

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/smart_notifier.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-smart-notifier')
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0

check() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name"
        FAIL=$((FAIL + 1))
    fi
}

check_grep() {
    local name="$1"
    local pattern="$2"
    local file="$3"
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (pattern '$pattern' not found in $file)"
        FAIL=$((FAIL + 1))
    fi
}

# ---- mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

OSASCRIPT_LOG="$TEST_DIR/osascript-calls.log"

# Mock osascript: records every invocation so tests can assert it was called
cat > "$MOCK_BIN/osascript" << MOCK
#!/bin/bash
echo "osascript \$*" >> "$OSASCRIPT_LOG"
exit 0
MOCK
chmod +x "$MOCK_BIN/osascript"

# ---- helper: create isolated home with notification config ----
# Pre-create config with quiet hours and rate limiting disabled so tests
# behave consistently regardless of the time of day they run.
make_mock_home() {
    local home="$1"
    local log_dir="$home/Library/Logs/maintenance"
    mkdir -p "$log_dir"
    cat > "$log_dir/notification_config.json" << 'JSON'
{
  "enabled": true,
  "quiet_hours": { "enabled": false },
  "priority_levels": {
    "critical": { "always_notify": true,  "sound": "Basso",   "subtitle": "Critical Alert" },
    "warning":  { "always_notify": false, "sound": "default", "subtitle": "System Warning" },
    "info":     { "always_notify": false, "sound": "none",    "subtitle": "System Info"    },
    "success":  { "always_notify": false, "sound": "none",    "subtitle": "Task Completed" }
  },
  "rate_limiting": { "enabled": false }
}
JSON
}

echo "=== Testing maintenance/bin/smart_notifier.sh ==="

# ---- Test 1: script exits 0 and writes load message to notifications.log ----
HOME1="$TEST_DIR/home1"
make_mock_home "$HOME1"

if PATH="$MOCK_BIN:$PATH" HOME="$HOME1" bash "$SCRIPT" > "$TEST_DIR/t1.log" 2>&1; then
    echo "PASS: script exits 0 when run directly"
    PASS=$((PASS + 1))
else
    echo "FAIL: script exited non-zero"
    cat "$TEST_DIR/t1.log"
    FAIL=$((FAIL + 1))
fi

check_grep "load message written to notifications.log" \
    "Smart notification system loaded successfully" \
    "$HOME1/Library/Logs/maintenance/notifications.log"

# ---- Test 2: smart_notify dispatches notification via osascript ----
HOME2="$TEST_DIR/home2"
make_mock_home "$HOME2"

cat > "$TEST_DIR/t2.sh" << EOF
#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=maintenance/bin/smart_notifier.sh
source "$SCRIPT"
smart_notify 'info' 'Test Title' 'Test message body'
EOF

PATH="$MOCK_BIN:$PATH" HOME="$HOME2" bash "$TEST_DIR/t2.sh" > "$TEST_DIR/t2.log" 2>&1

check_grep "osascript called for notification dispatch" "osascript" "$OSASCRIPT_LOG"
check_grep "dispatch logged in notifications.log" "Sent notification \[info\]" \
    "$HOME2/Library/Logs/maintenance/notifications.log"

# ---- Test 3: graceful degradation when osascript is absent ----
# Patch a copy of the script so 'command -v osascript' always fails,
# making the test platform-independent (real osascript exists on macOS).
HOME3="$TEST_DIR/home3"
make_mock_home "$HOME3"

T3_SCRIPT="$TEST_DIR/t3_notifier.sh"
cp "$SCRIPT" "$T3_SCRIPT"
if [[ "$(uname -s)" == "Darwin" ]]; then
    sed -i '' 's|command -v osascript|command -v __unavailable__|g' "$T3_SCRIPT"
else
    sed -i 's|command -v osascript|command -v __unavailable__|g' "$T3_SCRIPT"
fi

cat > "$TEST_DIR/t3.sh" << EOF
#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=maintenance/bin/smart_notifier.sh
source "$T3_SCRIPT"
smart_notify 'warning' 'No Backend' 'Test without osascript'
EOF

EXIT3=0
PATH="$MOCK_BIN:$PATH" HOME="$HOME3" bash "$TEST_DIR/t3.sh" > "$TEST_DIR/t3.log" 2>&1 || EXIT3=$?

if [[ "$EXIT3" -eq 0 ]]; then
    echo "PASS: exits 0 when notification backend is absent"
    PASS=$((PASS + 1))
else
    echo "FAIL: exited $EXIT3 when notification backend is absent"
    cat "$TEST_DIR/t3.log"
    FAIL=$((FAIL + 1))
fi

check_grep "fallback message logged when backend absent" "osascript not available" \
    "$HOME3/Library/Logs/maintenance/notifications.log"

# ---- Test 4: empty title fails validation and returns non-zero ----
HOME4="$TEST_DIR/home4"
make_mock_home "$HOME4"

cat > "$TEST_DIR/t4.sh" << EOF
#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=maintenance/bin/smart_notifier.sh
source "$SCRIPT"
smart_notify 'info' '' 'Some message'
EOF

EXIT4=0
PATH="$MOCK_BIN:$PATH" HOME="$HOME4" bash "$TEST_DIR/t4.sh" > "$TEST_DIR/t4.log" 2>&1 || EXIT4=$?

if [[ "$EXIT4" -ne 0 ]]; then
    echo "PASS: empty title returns non-zero exit code"
    PASS=$((PASS + 1))
else
    echo "FAIL: empty title should have returned non-zero (got exit $EXIT4)"
    FAIL=$((FAIL + 1))
fi

check_grep "validation error logged for missing title" "Title and message are required" \
    "$HOME4/Library/Logs/maintenance/notifications.log"

# ---- Test 5: SMART_NOTIFIER_DISABLE=1 suppresses osascript dispatch ----
HOME5="$TEST_DIR/home5"
make_mock_home "$HOME5"

OSASCRIPT_LOG5="$TEST_DIR/osascript-calls5.log"
MOCK_BIN5="$TEST_DIR/mock_bin5"
mkdir -p "$MOCK_BIN5"

cat > "$MOCK_BIN5/osascript" << MOCK5
#!/bin/bash
echo "osascript \$*" >> "$OSASCRIPT_LOG5"
exit 0
MOCK5
chmod +x "$MOCK_BIN5/osascript"

cat > "$TEST_DIR/t5.sh" << EOF
#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=maintenance/bin/smart_notifier.sh
source "$SCRIPT"
smart_notify 'info' 'Suppressed' 'Should not be dispatched'
EOF

EXIT5=0
SMART_NOTIFIER_DISABLE=1 PATH="$MOCK_BIN5:$PATH" HOME="$HOME5" \
    bash "$TEST_DIR/t5.sh" > "$TEST_DIR/t5.log" 2>&1 || EXIT5=$?

if [[ "$EXIT5" -eq 0 ]]; then
    echo "PASS: SMART_NOTIFIER_DISABLE=1 exits 0"
    PASS=$((PASS + 1))
else
    echo "FAIL: SMART_NOTIFIER_DISABLE=1 exited $EXIT5"
    cat "$TEST_DIR/t5.log"
    FAIL=$((FAIL + 1))
fi

if [[ ! -f "$OSASCRIPT_LOG5" ]]; then
    echo "PASS: SMART_NOTIFIER_DISABLE=1 suppresses osascript call"
    PASS=$((PASS + 1))
else
    echo "FAIL: osascript was called despite SMART_NOTIFIER_DISABLE=1"
    cat "$OSASCRIPT_LOG5"
    FAIL=$((FAIL + 1))
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
