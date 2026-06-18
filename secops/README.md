# SecOps Autopilot: Operating & Security Guide

This is a local-first, low-cost workstation maintenance system across three
execution phases. It integrates standard system tools, local AI reasoning (via a
**tiered, timeout-safe AI CLI engine**), and guards against credential leakage,
configuration drift, and unvetted branch changes.

> **Source of truth:** these scripts live in `personal-config/secops/` and are
> symlinked to `~/secops` by `scripts/sync_all_configs.sh`. The LaunchAgent
> plists are backed up in `personal-config/launch-agents/` and installed via
> `secops/install.sh`. History logs (`~/.*-history.log`) stay local and are
> gitignored.

## Shared System Configurations & Directory Structure

```
~/secops/  ->  personal-config/secops/   (symlink)
├── phase1-workflow-updater.sh     # Weekly GHA version pinning & locks check
├── phase2-mine.sh                 # Bi-weekly structural technical debt miner kickoff
├── phase3-qa-health.sh            # Daily local test runner & drift detection
├── lib/
│   └── ai_engine.sh               # Shared tiered AI diagnostic engine + hard timeout
├── install.sh                     # Install/load (or --uninstall) the LaunchAgents
└── README.md                      # This operating guide
```

| Detail                           | Rule / Path                                                                                                                                                    |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Repos Managed**                | `personal-config`, `ctrld-sync`, `email-security-pipeline`, `Seatek_Analysis`, `Hydrograph_Versus_Seatek_Sensors_Project`, `series_correction_project_updated` |
| **Repos Root**                   | `/Users/speedybee/dev/`                                                                                                                                        |
| **Append-Only History Logs**     | `~/.workflow-updater-history.log`, `~/.backlog-miner-history.log`, `~/.qa-health-history.log`                                                                  |
| **LaunchAgents Dir**             | `~/Library/LaunchAgents/` (`com.speedybee.secops.phase1/2/3.plist`)                                                                                            |
| **Diagnostic Inputs Temp Paths** | `/tmp/test_run_<repo>.log`, `/tmp/drift_audit.log`                                                                                                             |

---

## The Three Automation Phases

### Phase 1: GitHub Actions Workflow Updater

- **Purpose:** Keeps GitHub Actions dependencies current and locked to secure,
  immutable commit SHAs. It compiles and validates changes before committing,
  keeping your cloud runs fast, secure, and cost-effective.
- **Cadence:** Weekly, Mondays at 9:00 AM (via
  `com.speedybee.secops.phase1.plist`).
- **Tool Required:** `gh-aw` (GitHub CLI Action Lockfile extension).
- **Security Safeguards:**
  1. Never commits compiled `.lock.yml` files (only
     `.github/aw/actions-lock.json`).
  2. A dry-run compile validation gate (`gh aw compile --validate`) must pass
     successfully before any commit is written.
  3. Skips non-GHA repositories or missing tooling gracefully to avoid breaking
     the execution loop.

### Phase 2: Backlog Triage & Technical Debt Mining

- **Purpose:** Complements your active PR review and consolidation agents. While
  those handle inbound PR branches, Phase 2 systematically scans the _existing_
  codebase for tech debt, outdated patterns, security hygiene gaps, and
  performance bottlenecks, logging structural status.
- **Cadence:** Bi-weekly, 1st and 15th of each month at 10:00 AM (via
  `com.speedybee.secops.phase2.plist`).
- **Tool Required:** Windsurf Cascade, Cursor Agent, or Gemini CLI + Repo Prompt
  (Local MCP).
- **Security Safeguards:**
  1. Strictly restricted to generating structured markdown tasks. **Never**
     commits or writes direct code changes.
  2. Scope is capped to 1-2 directories or modules per run to control context
     limits.
  3. Always checks `tasks/lessons.md` first to honor established codebase rules.
  4. Limits output to a maximum of 3 highly actionable tasks.

### Phase 3: QA Health Check & System Drift Detection

- **Purpose:** Verifies build and test paths across active repos, audits macOS
  local configurations, and logs results. Passes log anomalies to a local AI CLI
  for diagnostics.
- **Cadence:** Daily at 8:00 AM (via `com.speedybee.secops.phase3.plist`).
- **Tool Required:** A working AI CLI for headless diagnostic summaries —
  resolved automatically by `lib/ai_engine.sh` (see **AI Diagnostic Engine**
  below). No single tool is mandatory; the engine degrades to dumping the raw
  log.
- **Test convention:** Phase 3 runs each repo's _own_ declared tests —
  `make test-all`/`make test` when a Makefile target exists, `npm run test` only
  when a `test` script is declared, otherwise the repo's `.venv/bin/pytest` (or
  `pytest` on PATH). Repos with no recognized test path are **skipped, not
  failed**.
- **Security Safeguards:**
  1. Fail-secure design: alerts via macOS notifications on test failures.
  2. **Audit Only:** Never attempts to auto-repair delicate system
     infrastructure (DNS, LaunchAgents, SSH key permissions). Report and alert
     only.
  3. Integrates with the `verify_ssh_config.sh` and standard `scutil --dns`
     checks to surface anomalies.
  4. Every per-repo test run and every AI call is wrapped in a hard wall-clock
     timeout so a hung suite or hung AI CLI can never wedge the daemon.

---

## Google Jules: Cooperative Integration & Safekeeping

### Understanding Google Jules

Google Jules is a highly capable agent at surfacing code fixes and proactively
generating PRs. However, because it works autonomously, it can occasionally:

- Duplicate changes or submit multiple alternative PRs addressing the same issue
  (e.g., overlapping optimizations).
- Attempt multiple credential verifications, touching identical files.
- Commit using human credentials (e.g., pushing branches authored by `abhimehro`
  rather than `jules[bot]`).

To prevent Jules' proactive contributions from creating friction or technical
debt, we coordinate Jules alongside our **PR Review, Consolidation, and Salvage
Agent Workflow**:

```
┌─────────────────┐       ┌────────────────────────────┐       ┌───────────────────────────────┐
│  Google Jules   │ ────> │ PR Review / Consolidation  │ ────> │       PR Salvage Agent        │
│ Proactive PRs / │       │     (Immediate Triage)     │       │      (Late-Day Review)        │
│ Fix Recommendations     │   Filter, review, squash/  │       │  Identifies merge anomalies,  │
└─────────────────┘       │   close duplicates/stale   │       │  stale branches, and salvage  │
                          └────────────────────────────┘       └───────────────────────────────┘
```

### Integration Guidelines for AI & Human Agents

1. **Deduplication:** When reviewing open PRs, look for the Jules task link in
   the description body (since Jules pushes as `abhimehro`). Instantly close
   duplicate or overlapping Jules PRs in favor of a single consolidated PR
   (using squash merges).
2. **Exclusion of Ordinary Human Work:** Strictly preserve true human-authored
   PRs. Only automate reviews and closes on branches exhibiting clear automation
   signals (such as Jules/Sentinel branches, specific bot footers, or the
   `google-labs-jules` bootstrap comment).
3. **Task Definition Verification:** Check `tasks/todo.md` and
   `tasks/lessons.md` before approving Jules-suggested code patterns. If Jules
   suggests patterns that violate active rules (such as missing
   `set -euo pipefail` in shell templates or bare `except:` blocks in Python),
   reject the PR and write a custom lesson in `tasks/lessons.md` to prevent
   recurrence.

---

## Instructions for AI Agents Running Task Mining

When you are asked to run a Phase 2 Mining session on this directory, copy and
paste the prompt block below into your terminal context:

```markdown
# SYSTEMATIC REFACTORING & BACKLOG MINER

## Role

You are the Code Quality Improvement Agent. Active PR agents already handle
incoming changes. Your job is the opposite direction: scan the existing codebase
for technical debt, outdated patterns, and missed optimizations that have
quietly sat on the back burner.

## Discovery

1. Use Repo Prompt to pull the directory structure and file contents of the
   target module only (1-2 directories per run).
2. Read tasks/lessons.md to honor historical patterns, mistakes, and rules.

## Analysis Criteria

- Outdated patterns: shell scripts missing `set -euo pipefail`, Python using
  bare `except:`, deprecated APIs.
- Security hygiene: hardcoded config, loose permissions, missing input
  sanitization.
- Performance: redundant file I/O, unoptimized loops, heavy synchronous work.

## Output Rules

- Do not write or modify code.
- Generate at most 3 specific, actionable tasks.
- If nothing is worth filing, say so and stop.
- Append each task to tasks/todo.md using exactly this structure:

### [Refactor] <Short, Descriptive Title>

- **Objective:** <Single-sentence goal>
- **Files Affected:** <Specific paths and line ranges>
- **Rationale:** <Security, performance, maintainability, or reliability reason>
- **Suggested Approach:**
  - <Step 1>
  - <Step 2>
  - <Step 3, optional>
- **Acceptance Criteria:**
  - <Verifiable condition>
  - <Verifiable condition>
```

---

## AI Diagnostic Engine (`lib/ai_engine.sh`)

Phase 1 and Phase 3 source this shared library. It provides two things:

- `run_timeout <seconds> <cmd...>` — a portable hard wall-clock cap (stock macOS
  has no `timeout`/`gtimeout`; this uses a `perl` `alarm` + `fork`/`exec`).
- `ai_diagnose <prompt>` — reads a log on **stdin**, embeds it into the prompt,
  and asks the first working AI CLI to analyze it. It **never hangs** (each
  attempt is time-boxed) and **never fails the caller** (always returns 0).

### Engine order (configurable)

Default chain = **only engines verified to work headlessly on this machine**
(2026-05-31 audit):

| Tier | Engine | Invocation                                              | Status                                                                   |
| ---- | ------ | ------------------------------------------------------- | ------------------------------------------------------------------------ |
| 1    | `vibe` | `vibe -p "<prompt>" --agent auto-approve --output text` | **PRIMARY** — verified working; clean text; `[ara-pyshim]` line stripped |
| 2    | `raw`  | dumps the log                                           | always works                                                             |

```bash
: "${SECOPS_AI_ENGINE:=vibe raw}"   # default in lib/ai_engine.sh
```

Override via env vars (also settable in the plists' `EnvironmentVariables`):

```bash
SECOPS_AI_ENGINE="vibe raw"     # default
SECOPS_AI_TIMEOUT=45            # per-attempt seconds (default 60)
```

### ⚠️ Critical: launchd PATH must include `~/.local/bin`

`vibe` (and `cursor-agent`, `devin`) install to **`~/.local/bin`**, which is
**not** on the default login PATH that launchd uses. The three plists therefore
prepend `/Users/speedybee/.local/bin` in `EnvironmentVariables → PATH`. Without
this, the now-primary `vibe` engine is invisible to the daemons and every
`ai_diagnose` call silently degrades to `raw`. If you regenerate the plists,
**keep `~/.local/bin` first in PATH.**

### Opt-in / disabled engines (each has a known headless failure here)

These are still implemented in `lib/ai_engine.sh` but are **not** in the default
chain. Re-enable explicitly (e.g. `SECOPS_AI_ENGINE="vibe cursor-agent raw"`)
once the underlying issue is fixed:

- **`copilot`** — _broken install._ The pinned package index
  `~/Library/Caches/copilot/pkg/darwin-arm64/1.0.56/index.js` is missing, so
  every invocation prints `ERR_MODULE_NOT_FOUND`. The engine now guards against
  this (treats the error as "unavailable" so it can't poison a diagnosis).
  Reinstall the GitHub Copilot CLI to restore. _User also deprioritizes Copilot
  due to recent quality/quota changes._
- **`cursor-agent`** — logged in (`abhimehrotra@bears.mybrcc.edu`), correct flag
  is `-f`/`--force` (**not** `--trust`, which doesn't exist), but headless print
  mode returns empty and spawns child `node` processes that outlive a single-PID
  kill. The hardened `run_timeout` (process-group kill, see below) now contains
  these, but the engine still produces no usable output — needs investigation.
- **`gemini`** — `oauth-personal` auth path **blocks indefinitely** in a non-TTY
  / launchd context and the configured model has 404'd. Confirmed still hanging
  in the 2026-05-31 audit. Opt-in only via `_ai_try_gemini`
  (`SECOPS_GEMINI_MODEL`, default `gemini-2.5-flash`).

### Hardened `run_timeout` (process-group kill)

The old `run_timeout` killed only the immediate child PID, so node/python
helpers spawned by an AI CLI could survive and wedge the daemon (root cause of
multi-minute hangs). It now runs the child in its own process group (`setpgid`)
and sends `kill(-9, …)` to the **whole group** on timeout, then reaps any
stragglers. Stock-macOS portable (perl `alarm` + `fork`/`exec`, no coreutils).

---

## Operations

### Install / load the LaunchAgents

```bash
bash ~/secops/install.sh            # install + (re)load all three agents
bash ~/secops/install.sh --uninstall
```

### Manual dry runs

```bash
# Phase 3 with a cheap, fast AI (no premium cost) to validate test logic:
SECOPS_AI_ENGINE="raw" bash ~/secops/phase3-qa-health.sh

# Phase 3 with real diagnostics:
bash ~/secops/phase3-qa-health.sh

# Phase 1 is network + git-write; inspect before letting it push.
```

### Status & logs

```bash
launchctl list | grep secops            # loaded? last exit code (col 2)
tail ~/.qa-health-history.log           # START / PASS / SKIP / FAIL / SUCCESS
tail ~/.workflow-updater-history.log
tail ~/.backlog-miner-history.log
tail ~/Library/Logs/maintenance/secops_phase3.{out,err}
```

A `launchctl list` second column of `-` means "not currently running"; the third
column is the **last exit code** (`0` = healthy). Each phase now logs a `START`
line so you can always confirm it fired.

---

## Troubleshooting

| Symptom                                   | Cause                                                                | Fix                                                                       |
| ----------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Phase 3 "fails" on `personal-config`      | repo has `package.json` but no `test` script; it uses a Makefile     | Fixed: runner now prefers `make test`/`make test-all`.                    |
| Phase 3 "fails" on a Python repo          | ran system `python3` (missing deps) or collected legacy/broken tests | Fixed: runner prefers the repo's `.venv/bin/pytest`.                      |
| Daemon hangs for many minutes             | AI CLI (esp. Gemini) blocked with no timeout                         | Fixed: all AI + test calls are time-boxed via `run_timeout`.              |
| `~/.workflow-updater-history.log` missing | Phase 1 never fired (weekly; or load failed)                         | `START` logging added; verify with `launchctl list                        |
| AI summary shows raw log only             | no AI engine produced output (all timed out / absent)                | Confirm at least one of `copilot`/`cursor-agent`/`vibe` works headlessly. |

## Changelog

- **2026-05-31:** Replaced Gemini-only AI path with a tiered, timeout-safe
  engine (`lib/ai_engine.sh`: copilot → cursor-agent → vibe → raw). Fixed Phase
  3 test runner to honor each repo's real test convention (Makefile /
  npm-if-declared / venv-pytest) and to skip (not fail) repos with no test path.
  Added hard timeouts to all AI and test/network calls. Added `START` logging to
  all phases. Moved authoritative scripts into `personal-config/secops/`
  (symlinked to `~/secops`), backed up plists to `launch-agents/`, added
  `install.sh`, and wired the symlink into `scripts/sync_all_configs.sh`.
