---
name: proactive-repo-sweep
description: Coordinator for scheduled or manual proactive repository sweeps. Enforces [PROACTIVE-SWEEP] isolation, 15-minute time box, PR throttle and file-collision gates, lens rotation, and local digest reporting.
---

# Proactive Repository Sweep Coordinator

Run a bounded, non-colliding proactive pass on one repository (or an explicitly
listed pilot subset) using isolated worktrees and strict approval gates.

## Runtime Budgets and Guardrails

1. **Multi-Signal Session Detection:** Scheduled prompts begin with
   `[PROACTIVE-SWEEP]` at the start of the prompt. The global `PreToolUse` hook
   (`proactive-guard.py`) detects sweep sessions via `workspacePaths` under
   `$HOME/.gemini/antigravity/worktrees`, a 24-hour persisted `conversationId`
   registry
   (`$HOME/.gemini/antigravity/proactive-reports/.sweep-conversations.json`),
   and `lastUserInput.lstrip().startswith("[PROACTIVE-SWEEP]")`. In sweep
   sessions, it enforces primary-checkout read-only protection, blocks unmerged
   writes to public `.jules/sentinel.md`, and blocks all remote pushes and PR
   mutations during the `2B` local-first phase.
2. **Permanent Public Disclosure Boundary (`proactive-sentinel`):** Only `bolt`,
   `palette`, and `code-health` candidates may ever graduate to `2A` Draft PRs.
   `proactive-sentinel` findings and fixes stay permanently off public Draft PRs
   (`SECURITY_REPORT_ONLY` local digest or private GitHub Security Advisories).
3. **Wall-Clock Budget:** Keep the entire sweep under **15 minutes** and inspect
   at most **1 target repository per scheduled pilot run** (or up to 2
   repositories after graduation) to avoid model-quota burn and MCP timeout
   contention.
4. **One Improvement Per Run:** Produce at most **one** verified, cohesive
   improvement (or one high-confidence no-op digest if the codebase is already
   clean). Never bundle unrelated refactors.
5. **Shell Rule:** Execute shell commands through `$HOME/bin/agent-zsh -c '...'`
   on macOS; never evaluate Fish syntax.

## Step-by-Step Sweep Protocol

### Step 1: Cleanup Expired Reviewed Worktrees and Check Local + Remote Throttle

1. Prune clean, already-merged or no-op worktrees older than 21 days (longer
   than the 2-week pilot; both dirty worktrees and clean worktrees holding
   unmerged commits ahead of `base_sha` are preserved automatically):
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh cleanup --ttl-days 21`
2. Check both the local `2B` candidate worktree throttle (`>= 2` local dirty or
   unmerged-commit candidate worktrees for `<repo>`, or any `> 7` days old) and
   the remote open proactive Draft PR throttle (`>= 2` open bot Draft PRs or any
   `> 7` days old):
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh check-throttle --repo abhimehro/<repo>`
   If exit code `5` is returned, stop early and write a short `THROTTLED` note
   to `$HOME/.gemini/antigravity/proactive-reports/YYYY-MM-DD-<repo>.md`.

### Step 2: Load Institutional Context and Select Lens

1. Read `<repo>/AGENTS.md` and check recent git history
   (`git -C "$HOME/dev/<repo>" log --since="7 days ago" --oneline`).
2. Select the lens requested by the prompt, or rotate by weekday if unspecified:
   - **Core / Pipeline Repos (`ctrld-sync`, `email-security-pipeline`,
     `personal-config`, `repoprompt-ce`):** rotate `bolt` -> `code-health` ->
     `palette`, plus a read-only `sentinel` audit.
   - **Scientific / Sensor Repos (`Hydrograph_Versus_Seatek_Sensors_Project`,
     `Seatek_Analysis`, `series_correction_project_updated`):** rotate
     `code-health` -> `bolt` (with mandatory `--numeric-check-cmd` tolerance
     verification at `rtol=1e-10, atol=1e-12` in Python / `tolerance = 1e-10` in
     R) + read-only `sentinel`. **Never** run `palette` on research repos.
3. Read the matching `.jules/<lens>.md` journal in `<repo>` and the
   corresponding skill (`proactive-sentinel`, `proactive-bolt`,
   `proactive-palette`, or `proactive-code-health`).

### Step 3: File-Path Collision Check Against Open PRs

Before editing any candidate file `<relpath>`, verify no open PR in
`abhimehro/<repo>` touches that exact path:

```bash
"$HOME/dev/personal-config/scripts/proactive-worktree.sh" check-collisions \
  --repo "abhimehro/<repo>" \
  --file "<relpath>"
```

If exit code `4` is returned, pick a non-overlapping candidate or conclude as a
clean no-op.

### Step 4: Isolated Worktree Edit and Hardened Verification

1. Prepare an isolated worktree (fetches `origin`, resolves default branch via
   `refs/remotes/origin/HEAD`, creates a collision-proof
   `YYYYMMDDTHHMMSSZ-pid-nonce` worktree, and sets
   `remote.origin.pushurl = DISABLED` in `local` mode):
   ```bash
   WT_PATH="$("$HOME/dev/personal-config/scripts/proactive-worktree.sh" prepare \
     --repo-path "$HOME/dev/<repo>" \
     --lens "<lens>" \
     --mode local)"
   ```
2. Apply the minimal production code fix inside `"$WT_PATH"`. Never edit files
   under `"$HOME/dev/<repo>"` directly, and never edit tamper-evident build,
   dependency, or test-harness paths (`Makefile`, `pyproject.toml`, `uv.lock`,
   `requirements*.txt`, `setup.cfg`, `tox.ini`, `noxfile.py`, `ruff.toml`,
   `.ruff.toml`, `.python-version`, `DESCRIPTION`, `NAMESPACE`, `.Renviron`,
   `scripts/*`, `Scripts/*`, `conftest.py`, `*/conftest.py`, `tests/*`,
   `*/tests/*`, `Tests/*`, `.jules/sentinel.md`).
3. Run hardened verification (strips `SSH_AUTH_SOCK`, `GH_TOKEN`, and
   `GITHUB_TOKEN` inside verification subprocesses):
   ```bash
   "$HOME/dev/personal-config/scripts/proactive-worktree.sh" verify \
     --worktree "$WT_PATH" \
     --lens "<lens>"
   ```
   (Include `--numeric-check-cmd "<tolerance_assertion>"` whenever `<lens>` is
   `bolt` on a research repository.)
4. If verification passes, commit the change locally inside `"$WT_PATH"` with a
   conventional prefix (`⚡bolt:`, `🎨palette:`, or `chore(qa):`). Do not commit
   unmerged `sentinel` fixes onto branches destined for public Draft PRs; keep
   `sentinel` reports local (`SECURITY_REPORT_ONLY`) or prepare a private GitHub
   Security Advisory patch. If verification fails and cannot be fixed cleanly
   within budget, discard changes in `"$WT_PATH"` and report why.

### Step 5: Write Local Digest (`2B` Strict Local-First Gate)

Write `$HOME/.gemini/antigravity/proactive-reports/YYYY-MM-DD-<repo>.md`
(`chmod 600`) containing:

- **Status:** `CANDIDATE_READY`, `SECURITY_REPORT_ONLY`, `CLEAN_NO_OP`,
  `THROTTLED`, or `MISSED` (written by
  `antigravity-proactive-ctl.sh audit-missed --date YYYY-MM-DD --repo <repo>` if
  a scheduled wake did not run)
- **Substatus:** `NONE` | `FLOAT_REORDER_DRIFT` | `GATE_FAILURE` (flag pure
  reordered `pandas`/`numpy` summation drift `1e-10 < max_rel_diff <= 1e-7`
  under `Status: CLEAN_NO_OP` + `Substatus: FLOAT_REORDER_DRIFT` after
  discarding the candidate so float-reorder noise is tracked separately from
  real `GATE_FAILURE` regressions)
- **Repository & Base Commit:** `abhimehro/<repo>` @ `<base_sha>`
- **Lens:** `sentinel` | `bolt` | `palette` | `code-health`
- **Summary & Failure/Perf Mechanism:** 2-4 concise sentences with file/line
  references
- **Verification Receipt:** Exact command run and exit status / timing delta
- **Isolated Worktree & Branch:** `<worktree_path>` (`<branch_name>`)
- **Promotion Commands (for human review after pilot graduation):** Exact `git`
  / `gh pr create --draft` commands for `bolt`, `palette`, or `code-health` (or
  private GitHub Security Advisory workflow for `sentinel`)

Do **not** push branches or open pull requests during the `2B` local-first
pilot.
