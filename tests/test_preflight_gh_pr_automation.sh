#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/preflight-gh-pr-automation.sh"

TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'test-preflight-gh-pr-automation')"
trap 'rm -rf "$TEST_DIR"' EXIT

MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

GH_LOG="$TEST_DIR/gh.log"
export GH_LOG

cat > "$MOCK_BIN/gh" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail

echo "$*" >> "$GH_LOG"

if [[ "$1" == "auth" && "$2" == "status" ]]; then
  exit 0
fi

if [[ "$1" == "repo" && "$2" == "view" ]]; then
  exit 0
fi

if [[ "$1" == "pr" && "$2" == "list" ]]; then
  echo "563"
  exit 0
fi

if [[ "$1" == "pr" && "$2" == "view" ]]; then
  echo '{"number":563}'
  exit 0
fi

if [[ "$1" == "pr" && "$2" == "checks" ]]; then
  if [[ "${GH_CHECKS_MODE:-ok}" == "error" ]]; then
    echo "simulated checks failure" >&2
    exit 1
  fi

  echo "Tests (fail): https://github.com/abhimehro/ctrld-sync/pull/563/checks?check_run_id=65965568921"
  exit 0
fi

if [[ "$1" == "api" && "$2" == "graphql" ]]; then
  if [[ "$*" == *"viewerCanEnableAutoMerge"* ]]; then
    echo "true"
  elif [[ "$*" == *"viewerCanUpdate"* ]]; then
    echo "true"
  else
    echo '{"viewerCanUpdate":true}'
  fi
  exit 0
fi

echo "unexpected gh invocation: $*" >&2
exit 1
MOCK
chmod +x "$MOCK_BIN/gh"

PASS=0
FAIL=0

check_contains() {
  local name="$1"
  local pattern="$2"
  local file="$3"
  if grep -Fq -- "$pattern" "$file"; then
    echo "PASS: $name"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $name (missing pattern: $pattern)"
    FAIL=$((FAIL + 1))
  fi
}

check_exit_code() {
  local name="$1"
  local expected="$2"
  local actual="$3"
  if [[ "$actual" -eq "$expected" ]]; then
    echo "PASS: $name"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $name (expected $expected got $actual)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Test 1: warns with failing check link/check_run_id ==="
rm -f "$GH_LOG"
GH_CHECKS_MODE=ok PATH="$MOCK_BIN:$PATH" bash "$SCRIPT" --repo abhimehro/ctrld-sync > "$TEST_DIR/t1.out" 2>&1
check_contains "includes failing-check warning" "[WARN] abhimehro/ctrld-sync#563 has failing checks:" "$TEST_DIR/t1.out"
check_contains "includes check_run_id URL in warning" "check_run_id=65965568921" "$TEST_DIR/t1.out"
check_contains "includes formatted failing check line" "Tests (fail): https://github.com/abhimehro/ctrld-sync/pull/563/checks?check_run_id=65965568921" "$TEST_DIR/t1.out"
check_contains "requests minimal fields from gh pr checks" "--json name,bucket,link" "$GH_LOG"
check_contains "uses full jq filter and formatter for failing checks" '--jq .[] | select(.bucket == "fail" or .bucket == "cancel") | "\(.name) (\(.bucket)): \(.link // "no-link")"' "$GH_LOG"
PR_CHECKS_CALLS="$(grep -c "pr checks" "$GH_LOG" || true)"
if [[ "$PR_CHECKS_CALLS" == "1" ]]; then
  echo "PASS: invokes gh pr checks once"
  PASS=$((PASS + 1))
else
  echo "FAIL: expected one gh pr checks call, got $PR_CHECKS_CALLS"
  FAIL=$((FAIL + 1))
fi

echo "=== Test 2: fails with stderr details when check visibility call fails ==="
rm -f "$GH_LOG"
set +e
GH_CHECKS_MODE=error PATH="$MOCK_BIN:$PATH" bash "$SCRIPT" --repo abhimehro/ctrld-sync > "$TEST_DIR/t2.out" 2>&1
EXIT_CODE=$?
set -e
check_exit_code "returns non-zero on check visibility failure" 1 "$EXIT_CODE"
check_contains "propagates check visibility failure context" "check visibility failed. Details: simulated checks failure" "$TEST_DIR/t2.out"

echo "=== Test 3: loads repos from YAML config ==="
rm -f "$GH_LOG"
cat > "$TEST_DIR/pr-review-agent.config.yaml" <<'EOF'
repos:
  - abhimehro/ctrld-sync
  - abhimehro/email-security-pipeline

bot_authors:
  - app/copilot-swe-agent
EOF
PATH="$MOCK_BIN:$PATH" bash "$SCRIPT" --config "$TEST_DIR/pr-review-agent.config.yaml" > "$TEST_DIR/t3.out" 2>&1
check_contains "config mode checks first repo" "repo view abhimehro/ctrld-sync" "$GH_LOG"
check_contains "config mode checks second repo" "repo view abhimehro/email-security-pipeline" "$GH_LOG"
check_contains "config mode succeeds" "[PASS] Preflight completed successfully for 2 repository/repositories" "$TEST_DIR/t3.out"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ "$FAIL" -eq 0 ]]
