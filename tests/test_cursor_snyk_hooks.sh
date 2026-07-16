#!/usr/bin/env bash
# Smoke tests for .cursor hooks (Secure at Inception + dependency health reminder).
set -euo pipefail

echo "=========================================="
echo "Testing Cursor Snyk / dependency hooks"
echo "=========================================="

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAI_WRAPPER="${REPO_ROOT}/.cursor/hooks/run-snyk-sai.sh"
DEP_HOOK="${REPO_ROOT}/.cursor/hooks/dependency-health-reminder.sh"
HOOKS_JSON="${REPO_ROOT}/.cursor/hooks.json"
SAI_PY="${REPO_ROOT}/.cursor/hooks/snyk/snyk_secure_at_inception.py"

fail() {
	echo "❌ FAIL: $*" >&2
	exit 1
}

echo ""
echo "Test 1: Hook files exist and are executable"
echo "---"
[[ -f $HOOKS_JSON ]] || fail "hooks.json missing"
[[ -x $SAI_WRAPPER ]] || fail "run-snyk-sai.sh missing or not executable"
[[ -x $DEP_HOOK ]] || fail "dependency-health-reminder.sh missing or not executable"
[[ -f $SAI_PY ]] || fail "snyk_secure_at_inception.py missing"
[[ -f ${REPO_ROOT}/.cursor/hooks/snyk/lib/scan_runner.py ]] || fail "scan_runner.py missing"
echo "✅ PASS"

echo ""
echo "Test 2: hooks.json declares afterFileEdit, stop, beforeShellExecution"
echo "---"
python3 - <<PY || fail "hooks.json schema check failed"
import json
from pathlib import Path
data = json.loads(Path("${HOOKS_JSON}").read_text())
assert data.get("version") == 1
hooks = data.get("hooks") or {}
for key in ("afterFileEdit", "stop", "beforeShellExecution"):
    assert key in hooks and isinstance(hooks[key], list) and hooks[key], key
print("ok")
PY
echo "✅ PASS"

echo ""
echo "Test 3: SAI wrapper handles unknown event (empty follow-up)"
echo "---"
out="$(printf '%s' '{"hook_event_name":"sessionStart","workspace_roots":["'"${REPO_ROOT}"'"]}' | bash "$SAI_WRAPPER")"
echo "$out" | python3 -c 'import json,sys; json.load(sys.stdin)' || fail "SAI wrapper did not return JSON: $out"
echo "✅ PASS"

echo ""
echo "Test 4: SAI stop with no pending changes returns empty object"
echo "---"
out="$(printf '%s' '{"hook_event_name":"stop","workspace_roots":["'"${REPO_ROOT}"'"]}' | bash "$SAI_WRAPPER")"
echo "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d == {}, d' || fail "bad stop output: $out"
echo "✅ PASS"

echo ""
echo "Test 5: dependency hook allows non-install commands"
echo "---"
out="$(printf '%s' '{"command":"ls -la"}' | bash "$DEP_HOOK")"
echo "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("permission")=="allow"' || fail "expected allow: $out"
echo "✅ PASS"

echo ""
echo "Test 6: dependency hook injects agent_message on pip install"
echo "---"
out="$(printf '%s' '{"command":"pip install requests"}' | bash "$DEP_HOOK")"
echo "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)
assert d.get("permission")=="allow", d
assert "snyk_package_health_check" in (d.get("agent_message") or ""), d
' || fail "expected health-check guidance: $out"
echo "✅ PASS"

echo ""
echo "Test 7: dependency hook skips uninstall"
echo "---"
out="$(printf '%s' '{"command":"npm uninstall lodash"}' | bash "$DEP_HOOK")"
echo "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)
assert d.get("permission")=="allow", d
assert not d.get("agent_message"), d
' || fail "uninstall should not inject guidance: $out"
echo "✅ PASS"

echo ""
echo "All Cursor Snyk / dependency hook tests passed."
