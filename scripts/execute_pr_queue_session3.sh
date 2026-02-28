#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="tasks/pr-review-2026-02-28.md"
# Ensure we run from the repository root
cd "$(dirname "$0")/.."

mkdir -p "$(dirname "$LOG_FILE")"

cat << 'EOF' > "$LOG_FILE"
# PR Review Session — 2026-02-28

Execution logs for PR closures and merges.

## Execution Log

```text
EOF

log_cmd() {
  local desc="$1"
  shift
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Executing: $*" | tee -a "$LOG_FILE"
  # Run the command natively, capturing output without terminating on error
  if "$@" >> "$LOG_FILE" 2>&1; then
    echo "  -> SUCCESS" | tee -a "$LOG_FILE"
  else
    echo "  -> FAILED" | tee -a "$LOG_FILE"
  fi
  echo "---------------------------------------------------------" >> "$LOG_FILE"
}

echo "Starting PR Queue Execution..."

# Close Queue - ctrld-sync
log_cmd "Close duplicate PR 406" gh pr close 406 --repo abhimehro/ctrld-sync --comment "Closing: duplicate of parallel pytest work (#399 also fails CI). Consolidate if feature desired."
log_cmd "Close duplicate PR 405" gh pr close 405 --repo abhimehro/ctrld-sync --comment "Closing: duplicate of test workflow (#395 is superset with uv caching). Use #395 instead."
log_cmd "Close duplicate PR 402" gh pr close 402 --repo abhimehro/ctrld-sync --comment "Closing: duplicate of test workflow (#395 is superset). Use #395 instead."
log_cmd "Close duplicate PR 399" gh pr close 399 --repo abhimehro/ctrld-sync --comment "Closing: duplicate of #406, both fail CI. Consolidate if feature desired."
log_cmd "Close stale PR 397" gh pr close 397 --repo abhimehro/ctrld-sync --comment "Closing: zero changed files — SECURITY.md changes already on main."
log_cmd "Close supersed PR 394" gh pr close 394 --repo abhimehro/ctrld-sync --comment "Closing: merge conflicts + subsumed by #396 dead-code removal."

# Close Queue - email-security-pipeline
log_cmd "Close superseded PR 372" gh pr close 372 --repo abhimehro/email-security-pipeline --comment "Closing: superseded by #381 (broader fix with tests)."
log_cmd "Close empty PR 373" gh pr close 373 --repo abhimehro/email-security-pipeline --comment "Closing: zero-diff WIP — no docstrings added."
log_cmd "Close empty PR 371" gh pr close 371 --repo abhimehro/email-security-pipeline --comment "Closing: zero-diff WIP — no refactoring done."
log_cmd "Close empty PR 370" gh pr close 370 --repo abhimehro/email-security-pipeline --comment "Closing: zero-diff WIP — no tests added."

# Merge Queue - ctrld-sync
log_cmd "Merge PR 403" gh pr merge 403 --repo abhimehro/ctrld-sync --squash --delete-branch
log_cmd "Merge PR 401" gh pr merge 401 --repo abhimehro/ctrld-sync --squash --delete-branch
log_cmd "Merge PR 400" gh pr merge 400 --repo abhimehro/ctrld-sync --squash --delete-branch
log_cmd "Merge PR 395" gh pr merge 395 --repo abhimehro/ctrld-sync --squash --delete-branch
log_cmd "Merge PR 398" gh pr merge 398 --repo abhimehro/ctrld-sync --squash --delete-branch

# Merge Queue - email-security-pipeline
log_cmd "Merge PR 374" gh pr merge 374 --repo abhimehro/email-security-pipeline --squash --delete-branch
log_cmd "Merge PR 368" gh pr merge 368 --repo abhimehro/email-security-pipeline --squash --delete-branch
log_cmd "Merge PR 369" gh pr merge 369 --repo abhimehro/email-security-pipeline --squash --delete-branch
log_cmd "Merge PR 378" gh pr merge 378 --repo abhimehro/email-security-pipeline --squash --delete-branch
log_cmd "Merge PR 380" gh pr merge 380 --repo abhimehro/email-security-pipeline --squash --delete-branch
log_cmd "Merge PR 379" gh pr merge 379 --repo abhimehro/email-security-pipeline --squash --delete-branch
log_cmd "Merge PR 377" gh pr merge 377 --repo abhimehro/email-security-pipeline --squash --delete-branch

cat << 'EOF' >> "$LOG_FILE"
```

## Setup Follow-ups (Manual Phase)
- **`email-security-pipeline` #381**: Need to rebase and then merge.
- **`email-security-pipeline` #375**: Need to fix CodeFactor issues and then merge.
- **`personal-config` #385**: Needs rebase + conflict resolution due to intersection with #384 fixes.

EOF

echo "Execution completed. Log saved to ${LOG_FILE}"
