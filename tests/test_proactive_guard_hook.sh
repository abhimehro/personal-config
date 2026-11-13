#!/usr/bin/env bash
#
# Unit tests for configs/antigravity/hooks/proactive-guard.py
# Verifies Antigravity camelCase protojson PreToolUse enforcement:
# - Multi-signal session detection (workspacePaths worktrees URI, persisted
#   conversationId across turns, prefix marker without mid-paragraph false positives)
# - Blocks all git push variants (named remote, explicit URL, -C ~/dev/<repo> push,
#   -c alias.x=push, force flags, +refspec) in 2B sweep sessions
# - Blocks public Sentinel PR creation permanently (even in 2A Draft PR mode)
# - Blocks pre-merge writes to public .jules/sentinel.md unless a fresh ctl.sh
#   post-merge lease file exists (no lingering env var bypass)
# - Blocks direct writes to ~/dev/* during proactive sweep sessions

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GUARD_SCRIPT="${REPO_ROOT}/configs/antigravity/hooks/proactive-guard.py"

TEST_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'test-proactive-guard')"
trap 'rm -rf "$TEST_DIR"' EXIT

export HOME="${TEST_DIR}/home"
mkdir -p "${HOME}/.gemini/antigravity/proactive-reports" "${HOME}/.gemini/antigravity/worktrees" "${HOME}/dev/ctrld-sync"

PASS=0
FAIL=0

assert_decision() {
	local name="$1"
	local expected="$2"
	local payload="$3"
	local out
	out="$(printf '%s' "${payload}" | python3 "${GUARD_SCRIPT}")"
	local actual
	actual="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("decision",""))' <<<"${out}")"
	if [[ ${actual} == "${expected}" ]]; then
		echo "PASS: ${name} (${actual})"
		PASS=$((PASS + 1))
	else
		echo "FAIL: ${name} (expected '${expected}', got '${actual}'; raw=${out})"
		FAIL=$((FAIL + 1))
	fi
}

if [[ ! -f ${GUARD_SCRIPT} ]]; then
	echo "FAIL: guard script missing: ${GUARD_SCRIPT}"
	exit 1
fi

# 1. Proactive sweep session: block plain, explicit URL, -C ~/dev, and -c alias pushes
assert_decision "blocks plain git push in proactive sweep" "deny" '{
  "conversationId": "conv-sweep-1",
  "lastUserInput": "[PROACTIVE-SWEEP] Audit ctrld-sync",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "git push origin feature-branch"}}
}'

assert_decision "blocks explicit URL git push bypassing pushurl=DISABLED" "deny" '{
  "lastUserInput": "[PROACTIVE-SWEEP] Audit ctrld-sync",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "git push https://github.com/abhimehro/ctrld-sync.git HEAD:refs/heads/feat"}}
}'

assert_decision "blocks git -C ~/dev/<repo> push in proactive sweep" "deny" "{
  \"lastUserInput\": \"[PROACTIVE-SWEEP] Audit ctrld-sync\",
  \"toolCall\": {\"name\": \"run_command\", \"args\": {\"CommandLine\": \"git -C ${HOME}/dev/ctrld-sync push origin main\"}}
}"

assert_decision "blocks git -c alias push bypass in proactive sweep" "deny" '{
  "lastUserInput": "[PROACTIVE-SWEEP] Audit ctrld-sync",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "git -c alias.ship=push ship origin HEAD"}}
}'

# 2. Multi-signal session detection: persisted conversationId + workspacePaths + mid-text non-false-positive
assert_decision "persists conversationId across turns when lastUserInput changes" "deny" '{
  "conversationId": "conv-sweep-1",
  "lastUserInput": "Continue verification step",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "gh pr create --draft --title test"}}
}'

assert_decision "detects sidecar session via workspacePaths worktrees URI without prompt marker" "deny" "{
  \"conversationId\": \"conv-ws-only\",
  \"lastUserInput\": \"Run weekly check\",
  \"workspacePaths\": [\"file://${HOME}/.gemini/antigravity/worktrees\"],
  \"toolCall\": {\"name\": \"edit_file\", \"args\": {\"Path\": \"${HOME}/dev/ctrld-sync/main.py\"}}
}"

assert_decision "does NOT false-positive when human review quotes [PROACTIVE-SWEEP] mid-sentence" "allow" "{
  \"conversationId\": \"conv-human-review\",
  \"lastUserInput\": \"Question: how does the hook detect a [PROACTIVE-SWEEP] session?\",
  \"toolCall\": {\"name\": \"edit_file\", \"args\": {\"Path\": \"${HOME}/dev/ctrld-sync/main.py\"}}
}"

# 3. Universal force-push & merge speed bumps
assert_decision "blocks git push -f origin main" "deny" '{
  "lastUserInput": "Push my changes",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "git push -f origin main"}}
}'

assert_decision "blocks git push +HEAD:main refspec force push" "deny" '{
  "lastUserInput": "Push my changes",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "git push origin +HEAD:main"}}
}'

assert_decision "blocks git push --force-with-lease origin main" "deny" '{
  "lastUserInput": "Push my changes",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "git push --force-with-lease origin main"}}
}'

assert_decision "allows normal feature branch push in interactive session" "allow" '{
  "conversationId": "conv-interactive",
  "lastUserInput": "Push my feature branch",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "git push -u origin feat/new-check"}}
}'

# 4. Permanent block on public Sentinel PRs even in 2A Draft PR mode
AGY_PROACTIVE_ALLOW_DRAFT_PR=1 assert_decision "blocks Sentinel Draft PR even in 2A mode" "deny" '{
  "conversationId": "conv-sweep-2a",
  "lastUserInput": "[PROACTIVE-SWEEP] Audit ctrld-sync",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "gh pr create --draft --title \"sentinel: fix CWE-78 command injection\""}}
}'

# 5. Public repo Sentinel journal leak prevention (lease file required; ambient env var ignored)
AGY_ALLOW_POST_MERGE_SENTINEL=1 assert_decision "ignores lingering env var and blocks .jules/sentinel.md pre-merge" "deny" "{
  \"lastUserInput\": \"Run /proactive-sentinel on ctrld-sync\",
  \"toolCall\": {\"name\": \"write_file\", \"args\": {\"Path\": \"${HOME}/dev/ctrld-sync/.jules/sentinel.md\"}}
}"

python3 - "${HOME}/.gemini/antigravity/proactive-reports/.sentinel-post-merge-lease.json" <<'PY'
import json, sys, time
from pathlib import Path
p = Path(sys.argv[1])
p.write_text(json.dumps({"repo_name": "ctrld-sync", "merged_pr": 99, "expires_at": time.time() + 120}))
PY

assert_decision "allows .jules/sentinel.md write with valid post-merge lease for matching repo" "allow" "{
  \"lastUserInput\": \"Append post-merge lesson\",
  \"toolCall\": {\"name\": \"edit_file\", \"args\": {\"Path\": \"${HOME}/dev/ctrld-sync/.jules/sentinel.md\"}}
}"

assert_decision "blocks .jules/sentinel.md write for non-matching repo even when lease exists" "deny" "{
  \"lastUserInput\": \"Append post-merge lesson\",
  \"toolCall\": {\"name\": \"edit_file\", \"args\": {\"Path\": \"${HOME}/dev/Seatek_Analysis/.jules/sentinel.md\"}}
}"

# 6. Primary checkout vs isolated worktree / local digest during proactive sweep
assert_decision "allows edit inside isolated proactive worktree" "allow" "{
  \"lastUserInput\": \"[PROACTIVE-SWEEP] Audit ctrld-sync\",
  \"toolCall\": {\"name\": \"edit_file\", \"args\": {\"Path\": \"${HOME}/.gemini/antigravity/worktrees/proactive-ctrld-sync-bolt-20261031T131500Z-123/main.py\"}}
}"

assert_decision "allows writing local proactive digest report" "allow" "{
  \"lastUserInput\": \"[PROACTIVE-SWEEP] Audit ctrld-sync\",
  \"toolCall\": {\"name\": \"write_file\", \"args\": {\"Path\": \"${HOME}/.gemini/antigravity/proactive-reports/2026-10-31-ctrld-sync.md\"}}
}"

# 7. replace_file_content tool coverage and argument aliases (H-1)
rm -f "${HOME}/.gemini/antigravity/proactive-reports/.sentinel-post-merge-lease.json"
assert_decision "blocks replace_file_content to primary dev checkout in proactive sweep" "deny" "{
  \"lastUserInput\": \"[PROACTIVE-SWEEP] Audit ctrld-sync\",
  \"toolCall\": {\"name\": \"replace_file_content\", \"args\": {\"filePath\": \"${HOME}/dev/ctrld-sync/main.py\"}}
}"

assert_decision "blocks replace_file_content to .jules/sentinel.md pre-merge" "deny" "{
  \"lastUserInput\": \"Audit findings\",
  \"toolCall\": {\"name\": \"replace_file_content\", \"args\": {\"path\": \"${HOME}/dev/ctrld-sync/.jules/sentinel.md\"}}
}"

assert_decision "blocks file target with file:// URI scheme prefix" "deny" "{
  \"lastUserInput\": \"[PROACTIVE-SWEEP] Audit ctrld-sync\",
  \"toolCall\": {\"name\": \"edit_file\", \"args\": {\"Path\": \"file://${HOME}/dev/ctrld-sync/main.py\"}}
}"

# 8. Shell flag grouping and option parsing: bash -ec vs bash --norc (W-3)
assert_decision "unwraps combined shell flags like bash -ec for push detection" "deny" '{
  "lastUserInput": "[PROACTIVE-SWEEP] Audit ctrld-sync",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "bash -ec \"git push origin main\""}}
}'

assert_decision "does not misparse bash --norc as -c flag" "allow" '{
  "conversationId": "conv-interactive-norc",
  "lastUserInput": "Interactive testing",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "bash --norc \"git push origin main\""}}
}'

# 9. Hyphenated repository lease boundary (W-2: repoprompt vs repoprompt-ce)
python3 - "${HOME}/.gemini/antigravity/proactive-reports/.sentinel-post-merge-lease.json" <<'PY'
import json, sys, time
from pathlib import Path
p = Path(sys.argv[1])
p.write_text(json.dumps({"repo_name": "repoprompt", "merged_pr": 101, "expires_at": time.time() + 120}))
PY

assert_decision "blocks repoprompt-ce sentinel edit when lease is only for repoprompt" "deny" "{
  \"lastUserInput\": \"Update sentinel\",
  \"toolCall\": {\"name\": \"edit_file\", \"args\": {\"Path\": \"${HOME}/dev/repoprompt-ce/.jules/sentinel.md\"}}
}"

assert_decision "blocks shell sentinel mutation for repoprompt-ce with repoprompt lease" "deny" "{
  \"lastUserInput\": \"Stage sentinel\",
  \"toolCall\": {\"name\": \"run_command\", \"args\": {\"CommandLine\": \"git -C ${HOME}/dev/repoprompt-ce add .jules/sentinel.md\"}}
}"

# 10. Atomic permissions fix: pre-existing 0644 state file ends up at 0600 (H-2)
CONV_REG="${HOME}/.gemini/antigravity/proactive-reports/.sweep-conversations.json"
echo '{"stale": 1}' >"${CONV_REG}"
chmod 0644 "${CONV_REG}"

assert_decision "updates sweep registry on proactive input" "deny" '{
  "conversationId": "conv-perms-test",
  "lastUserInput": "[PROACTIVE-SWEEP] Audit ctrld-sync",
  "toolCall": {"name": "run_command", "args": {"CommandLine": "git push origin main"}}
}'

PERMS="$(stat -c "%a" "${CONV_REG}" 2>/dev/null || stat -f "%OLp" "${CONV_REG}" 2>/dev/null || python3 -c 'import os,sys; print(oct(os.stat(sys.argv[1]).st_mode)[-3:])' "${CONV_REG}")"
if [[ ${PERMS} == "600" ]]; then
	echo "PASS: pre-existing 0644 registry file atomically updated to 0600 permissions"
	PASS=$((PASS + 1))
else
	echo "FAIL: registry file permissions expected 600, got ${PERMS}"
	FAIL=$((FAIL + 1))
fi

echo ""
echo "Summary: PASS=${PASS} FAIL=${FAIL}"
[[ ${FAIL} -eq 0 ]]
