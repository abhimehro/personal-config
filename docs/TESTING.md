# Testing Patterns & Mocking Guide

This guide documents the mock and test patterns used across `tests/`. Read this before writing a new test — especially for `maintenance/bin/` scripts (see issue #439) — so you don't need to reverse-engineer existing tests from scratch.

## Quick reference: test helpers

Most unit-style shell test files in this repo use the same small set of named helpers. For new tests, copy these verbatim into a new test file (some older or ad‑hoc tests may use custom assertions instead):

```bash
PASS=0
FAIL=0

# check: pass if the command exits 0
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

# check_grep: pass if pattern is found in file
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

# check_exit: pass if command exits with the expected code
check_exit() {
    local name="$1"
    local expected="$2"
    shift 2
    local actual=0
    "$@" > "$TEST_DIR/check.log" 2>&1 || actual=$?
    if [[ "$actual" -eq "$expected" ]]; then
        echo "PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (expected exit $expected, got $actual)"
        cat "$TEST_DIR/check.log"
        FAIL=$((FAIL + 1))
    fi
}
```

Real examples: `tests/test_health_check.sh`, `tests/test_system_cleanup.sh`, `tests/test_google_drive_backup.sh`.

---

## Pattern 1 — `$MOCK_BIN` / PATH injection

The most common pattern. Create a temporary directory of fake executables and prepend it to `PATH` so the script-under-test picks up your fakes instead of the real system tools.

```bash
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-mytest')
trap 'rm -rf "$TEST_DIR"' EXIT          # always clean up

MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

# Mock launchctl: returns one healthy agent
cat > "$MOCK_BIN/launchctl" << 'MOCK'
#!/bin/bash
echo "0       -       com.example.agent"
MOCK
chmod +x "$MOCK_BIN/launchctl"

# Mock ping: always succeeds (avoids network dependency in CI)
cat > "$MOCK_BIN/ping" << 'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/ping"

# Inject into PATH for the test run
PATH="$MOCK_BIN:$PATH" bash "$SCRIPT" > "$TEST_DIR/out.log" 2>&1
```

Real examples: `tests/test_health_check.sh:42–88`, `tests/test_network_mode_manager.sh:13–49`.

**Key rules:**
- Always put `MOCK_BIN` *before* the existing `$PATH`.
- Always `chmod +x` every mock binary.
- Use `trap 'rm -rf "$TEST_DIR"' EXIT` — not manual `rm` at the end — so cleanup runs even on error.

---

## Pattern 2 — Log-file assertion (assert a command was called)

When you need to verify that a script *invoked a specific command with specific arguments*, write the mock so it records its invocation to a log file, then assert against that file.

```bash
CALL_LOG="$TEST_DIR/launchctl-calls.log"

# Mock that records every call — write to $TEST_DIR, not /tmp, for parallel-safe isolation
cat > "$MOCK_BIN/launchctl" << MOCK
#!/bin/bash
echo "launchctl called: \$*" >> "$CALL_LOG"
exit 0
MOCK
chmod +x "$MOCK_BIN/launchctl"

# Run the script under test
PATH="$MOCK_BIN:$PATH" bash "$SCRIPT" > /dev/null 2>&1

# Assert the call was made
check_grep "launchctl load was called" \
    "launchctl called: load" "$CALL_LOG"
```

Real examples: `tests/test_media_server_env_vars.sh` (rclone log written to `$HOME/Library/Logs/media-server.log`, then asserted with `grep`).

---

## Pattern 3 — Mock `HOME` isolation

Scripts that write to `~/Library/Logs/` or read from `~/.config/` need an isolated home directory so tests don't touch real user data and so multiple parallel test runs don't collide.

```bash
MOCK_HOME="$TEST_DIR/home"
mkdir -p "$MOCK_HOME/Library/Logs/maintenance"

# Override HOME for the test run only
HOME="$MOCK_HOME" PATH="$MOCK_BIN:$PATH" bash "$SCRIPT" > "$TEST_DIR/out.log" 2>&1

# Assert log was written inside mock home
check_grep "health_check.log created" \
    "Disk usage" "$MOCK_HOME/Library/Logs/maintenance/health_check.log"
```

Real examples: `tests/test_health_check.sh:73–78`, `tests/test_media_server_env_vars.sh:5–7`.

---

## Pattern 4 — Script-patching via `sed` (when PATH injection is not enough)

Some scripts hardcode dependency paths (e.g. `IPV6_MANAGER="/path/to/script"`) or use `BASH_SOURCE`-relative paths that cannot be intercepted via `PATH`. In that case, copy the script to `$TEST_DIR` and patch it with `sed`.

```bash
# Copy script so we don't modify the repo copy
TEST_MANAGER="$TEST_DIR/network-mode-manager.sh"
cp "$REAL_MANAGER" "$TEST_MANAGER"

# Patch hardcoded paths — use portable syntax for both macOS and Linux
if [[ "$(uname -s)" == "Darwin" ]]; then
    sed -i '' "s|IPV6_MANAGER=\".*\"|IPV6_MANAGER=\"$MOCK_IPV6\"|" "$TEST_MANAGER"
else
    sed -i  "s|IPV6_MANAGER=\".*\"|IPV6_MANAGER=\"$MOCK_IPV6\"|" "$TEST_MANAGER"
fi

bash "$TEST_MANAGER" controld browsing > "$TEST_DIR/out.log" 2>&1
```

Real examples: `tests/test_network_mode_manager.sh:57–71`, `tests/test_security_manager_restore.sh:39–48`.

> **Note:** `sed -i ''` (BSD/macOS) and `sed -i` (GNU/Linux) differ. Always branch on `$(uname -s)` when patching scripts in tests that run on both platforms.

---

## Pattern 5 — Platform-skip for macOS-only assertions

Some assertions can only run on macOS (e.g. `launchctl`, BSD `sed`, 1Password agent socket). Guard them with a `uname` check rather than letting the test silently pass or noisily fail.

```bash
if [[ "$(uname -s)" == "Darwin" ]]; then
    check "launchctl list returns agents" \
        bash -c 'launchctl list | grep -q com.example'
else
    echo "SKIP: launchctl check (macOS only)"
fi
```

For a whole-test skip:

```bash
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "SKIP: $(basename "$0") requires macOS — skipping on $(uname -s)"
    exit 0
fi
```

---

## Pattern 6 — Capturing output of expected-to-fail commands under `set -e`

Under `set -euo pipefail`, a command that exits non-zero aborts the test. Use `|| true` (or capture the exit code manually) when you deliberately expect failure:

```bash
# Correct: prevent set -e from aborting the test
OUTPUT=$(bash "$SCRIPT" --bad-flag 2>&1 || true)

# Also correct: capture exit code explicitly
actual=0
bash "$SCRIPT" --bad-flag > "$TEST_DIR/out.log" 2>&1 || actual=$?
[[ "$actual" -eq 2 ]] || { echo "FAIL: expected exit 2, got $actual"; FAIL=$((FAIL+1)); }
```

Real examples: `tests/test_media_server_env_vars.sh:112`, `tests/test_lib_dns_utils.sh:135`.

---

## Standard test file skeleton

Use this as a starting point for any new `tests/test_<name>.sh`:

```bash
#!/usr/bin/env bash
#
# Unit tests for <path/to/script.sh>
# Mocks: <list mocked commands here>

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# NOTE: BASH_SOURCE[0] is the test file itself; "/.." navigates up one level to
# the repo root. This assumes test files live directly inside tests/ (one level deep).
# If you place a test elsewhere, adjust the number of /../ segments accordingly.
SCRIPT="$REPO_ROOT/<path/to/script.sh>"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-<name>')
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0

check() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "PASS: $name"; PASS=$((PASS + 1))
    else
        echo "FAIL: $name"; FAIL=$((FAIL + 1))
    fi
}

check_grep() {
    local name="$1" pattern="$2" file="$3"
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "PASS: $name"; PASS=$((PASS + 1))
    else
        echo "FAIL: $name (pattern '$pattern' not found in $file)"; FAIL=$((FAIL + 1))
    fi
}

# ---- mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

# TODO: add mock binaries here (see patterns above)

echo "=== Testing <name> ==="

# ---- Test 1: happy path exits 0 ----
if PATH="$MOCK_BIN:$PATH" bash "$SCRIPT" > "$TEST_DIR/t1.log" 2>&1; then
    echo "PASS: happy path exits 0"; PASS=$((PASS + 1))
else
    echo "FAIL: happy path exited non-zero"; cat "$TEST_DIR/t1.log"; FAIL=$((FAIL + 1))
fi

# ---- Summary ----
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
```

---

## Known mocking limitations

| Scenario | Limitation | Workaround |
|---|---|---|
| Script calls `/usr/bin/rsync` (absolute path) | PATH injection has no effect | Use `--dry-run` flag if the script supports it (see `test_google_drive_backup.sh`) |
| `launchd` socket activation | Cannot be simulated in a test process | Test the script's behavior when the socket is absent; assert it logs a clear error |
| `launchctl bootout` / `bootstrap` | Requires elevated privileges in CI | Mock `launchctl` via `$MOCK_BIN` and assert the right subcommand is passed |
| BSD `sed -i ''` vs GNU `sed -i` | Script-patching tests break cross-platform | Branch on `$(uname -s)` (see Pattern 4) |
| `sudo`-gated binaries | Cannot be mocked via PATH safely | Refactor the script so the sudo call is isolated; test the surrounding logic without sudo |

---

## Tests known to fail on Linux

The following tests are **expected to fail on Linux** and are automatically skipped or tolerated by `make test`. Do not treat these as real failures in CI:

| Test file | Reason |
|---|---|
| `tests/test_config_fish.sh` | Requires the `fish` shell, which is not present in the Linux CI image |
| `tests/test_ssh_config.sh` | Requires the 1Password SSH agent socket (`~/.1password/agent.sock`) |
| `tests/test_security_manager_restore.sh` | Uses BSD `sed -i ''` syntax (macOS only) |
| `tests/test_media_server_auth.sh` | Credential flow assertion depends on macOS Keychain |

If you add a new test that is intentionally macOS-only, add a `uname` guard at the top (Pattern 5 above) and add an entry to this table.

---

## Smoke test subset (`make test-quick`)

A curated subset of fast, cross-platform tests is wired into `make test-quick`. Use this target for quick pre-commit feedback without running the full suite (~23 tests).

**Included tests:**

| Test | What it covers |
|---|---|
| `tests/test_lib_common.sh` | `scripts/lib/common.sh` — temp-file helpers, path guards |
| `tests/test_lib_dns_utils.sh` | `scripts/lib/dns-utils.sh` — caching, health-check |
| `tests/test_path_validation.py` | Path validation utilities |

All three tests run on macOS and Linux and complete in well under 10 seconds total.

### Pre-commit hook example

Add the following to `.git/hooks/pre-commit` to gate every commit on the smoke suite:

```bash
#!/bin/sh
make test-quick
```

Make the hook executable:

```bash
chmod +x .git/hooks/pre-commit
```
