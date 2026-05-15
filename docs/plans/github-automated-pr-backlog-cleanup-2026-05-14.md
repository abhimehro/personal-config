# GitHub automated PR backlog cleanup — execution plan (2026-05-14)

<!-- markdownlint-disable MD013 -->

## Goal

Produce an executable, security-first playbook for a **one-time** review-and-merge cleanup of in-scope automated PRs across six `abhimehro/*` repositories, grounded in `personal-config` skills/docs and each target repo’s own guidance, with full task documentation suitable to seed a future `automated-pr-salvage-agent` workflow.

## Locked policy (Mid-flow resolved)

**Bundle 1 (confirmed 2026-05-14):**

- **Preflight:** Read-only — do **not** pass `--require-write-probes` unless you explicitly widen scope later.
- **Bot scope:** Keep `app/copilot-swe-agent` in the author allowlist alongside the listed bots (`tasks/pr-review-agent.config.yaml` `bot_authors`).
- **Human-authored PRs:** Autonomous **squash-merge** is allowed when automation signals are **strong** (branch/title/body/comments/commits/workflows), consistent with your backlog instructions; you accept higher accountability vs. the default caution in `docs/automated-pr-review-agent.md` L11 for this run.

## Scope snapshot (runtime parameters)

- **Mode:** `review-and-merge` · **Schedule:** `none` · **Merge strategy:** `squash` · **Stale threshold:** `30` days · **Auto-fix:** enabled (lint/format/trivial conflicts only; **never** force-push).
- **Repos (must match `tasks/pr-review-agent.config.yaml` `repos:`):** `abhimehro/personal-config`, `abhimehro/ctrld-sync`, `abhimehro/email-security-pipeline`, `abhimehro/Seatek_Analysis`, `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project`, `abhimehro/series_correction_project_updated`.
- **In-scope authors:** `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]`, `cursor[bot]`, `devin[bot]`, `copilot[bot]`, `app/copilot-swe-agent`, plus human-authored PRs with **clear** automation signals (Bundle 1).

## Background

- **Preflight gate (mandatory):** No inventory, merge, or close until preflight passes (`docs/automated-pr-review-agent.md` L13–18). Entry script `scripts/run-pr-review-session.sh` optionally sources a 1Password-mounted FIFO `.env` (L56–61), then invokes `scripts/preflight-gh-pr-automation.sh` with `--config` defaulting to `tasks/pr-review-agent.config.yaml` (L63–68). Preflight loads `repos:` via `load_repos_from_config` (`scripts/preflight-gh-pr-automation.sh` L66–94).
- **Review pipeline:** Four ordered gates (CI → security → quality → category-specific) in `docs/automated-pr-review-agent.md` L30–35; dispositions MERGE / MERGE-AFTER-FIX / REQUEST-CHANGES / ESCALATE / CLOSE-\* / CONSOLIDATE (L41–51); post-merge re-check of siblings (L55–56); auto-fix boundaries (L37).
- **Phase 2 handoff:** Salvage agent reads Phase 1’s dated report; `tasks/pr-review-YYYY-MM-DD.md` should end with machine-readable **Post-session remainder** (`repo`, `pr`, `reason`) per row (`docs/automated-pr-review-agent.md` L64–67).
- **Prior hazards:** `docs/plans/backlog-cleanup-orchestration-2026-05-09.md` — untracked plan loss on branch switch; **Lesson 0df** (`tasks/lessons.md` L213+); **0cc** burst-merge DIRTY siblings (L193–197); **0t / 0u / 0bb / 0x** main-side CI, infra-first merge, security pipeline gates, blob payloads.
- **Volume:** ~**150** open PRs across six repos with expected duplicates — exhaustive inventory + triage before mutation; **simulation (Item 5) is mandatory.**
- **Cloud / MCP:** `/.claude/skills/cloud-agents-starter/SKILL.md`; GitHub MCP fallback `docs/github-mcp-integration.md` when `gh` struggles at volume.

## Policies cross-check (integrated from Oracle draft)

An Oracle planning pass produced a parallel outline; **no policy overrides** vs Bundle 1 above. Useful emphasis retained here:

- **Four-gate framing:** CI Health → Security → Code Quality → Category-specific — matches `docs/automated-pr-review-agent.md` L30–35.
- **Main-side CI (0t / 0bb):** If `main` required checks fail (or 4+ PRs share the same failing required check), **defer all merges** in that repo for that wave; never bypass gates on a security-classified pipeline.
- **Infra-first (0u):** If an in-scope PR fixes the broken CI, merge it first, `gh api -X PUT repos/$REPO/pulls/$PR/update-branch` on siblings, re-evaluate.
- **Payload / blob (0x):** `SyntaxError` at line 1 → treat as possible stringified blob; escalate rather than blind auto-fix.
- **Execution spine:** Oracle’s Items 1–7 naming matches this document’s work-item ordering (preflight → context → inventory → triage → **simulation halt** → execution → reporting).

## Approach

1. **Verify config, then gate credentials and GitHub** — Confirm **six** `repos:` entries in YAML before preflight. Run **1Password FIFO pre-check** (Item 1). Then read-only preflight (`scripts/run-pr-review-session.sh` → `scripts/preflight-gh-pr-automation.sh`).
2. **Discover per-repo norms with pacing** — Context into `tasks/pr-review-2026-05-14.md`; **`sleep 2` between repositories**; **GitHub MCP** if `gh` times out.
3. **Inventory → triage** — `tasks/pr-inventory.md` then `tasks/pr-triage.md`; paginate ~150 PRs; **`sleep 2` between repos** during bulk listing.
4. **Simulation before mutation** — `## Planned mutations (simulation — pending human sign-off)` in `tasks/pr-triage.md` with **exact** `gh pr merge` / `gh pr close` lines; **no** merges/closes until you sign off.
5. **Execution after sign-off** — Merge order per skill; re-fetch live PR state **after each merge**; **never** force-push.
6. **Workspace isolation** — No `git checkout` / `git switch` of PR heads inside the `personal-config` documentation hub; ephemeral clones or API-only (`tasks/lessons.md` **0df**).
7. **Report + salvage tail** — Session file, `tasks/pr-review-session-reports.md`, `tasks/lessons.md`, **Post-session remainder** YAML rows.

**Note:** RepoPrompt `context_builder` timed out during planning; an Oracle draft was supplied separately — integrated above, not a replacement authority.

## Work Items

### Item 1 — Six-repo config verification, 1Password FIFO pre-check, preflight, and policy pin

**Goal:** Prove the automation config matches intent, secrets injection is live, and GitHub read access is sound before any inventory.

**Done when:**

1. **Six-repo scope:** In `tasks/pr-review-2026-05-14.md`, document that `tasks/pr-review-agent.config.yaml` lists **six** `repos:` entries (lines 7–13). If count ≠ 6, **stop** and fix YAML before preflight.
2. **1Password FIFO pre-check:** From repo root: `.env` exists, `test -p .env`, `test -r .env`, plus a **bounded non-leaking** read (`timeout` + drain to `/dev/null` or equivalent) so a missing inject does not hang silently — **never** echo secret values to logs or markdown.
3. `scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` exits **0** (read-only; no `--require-write-probes`).
4. **Policy pin** in `tasks/pr-review-2026-05-14.md`: Bundle 1 bullets, bot list including `app/copilot-swe-agent`, squash, stale 30d, auto-fix on, read-only preflight.

**Key files:** `tasks/pr-review-agent.config.yaml` L7–13; `scripts/run-pr-review-session.sh` L56–78; `scripts/preflight-gh-pr-automation.sh` L66–94; `docs/github-app-pr-automation-checklist.md`.

**Dependencies:** None.

**Size:** S

### Item 2 — Per-repository context packet (rate-limited, MCP fallback)

**Goal:** Each target repo has a captured “how to verify” note; stay under GitHub secondary rate limits.

**Done when:** For all six repos, `tasks/pr-review-2026-05-14.md` lists default branch, stack signals, CI workflow names (`gh api` or MCP), and README / `AGENTS.md` / `AGENT.md` test commands **as read from that repo** (or “none documented”). **`sleep 2` after each repo’s fetch block.** On `gh` timeout, **complete via GitHub MCP** and note which path succeeded.

**Key files:** `docs/github-mcp-integration.md`.

**Dependencies:** Item 1.

**Size:** M

### Item 3 — Open PR inventory (full + in-scope flag, rate-limited, MCP fallback)

**Goal:** Exhaustive enumeration for ~150 PRs.

**Done when:** `tasks/pr-inventory.md` has per-repo tables: PR #, URL, title, author, head/base, created/updated, stale?, labels, draft, mergeable, checks summary, inclusion reason (bot **or** signal). **Paginate** all pages. **`sleep 2` between repositories** for bulk `gh pr list` / GraphQL. Annotate MCP fallback rows if used.

**Key files:** `tasks/pr-inventory.md`; `docs/automated-pr-review-agent.md` L21–26.

**Dependencies:** Items 1–2.

**Size:** L

### Item 4 — Triage and risk classification

**Goal:** Exactly one disposition per in-scope PR.

**Done when:** `tasks/pr-triage.md` lists each in-scope PR with category (`SECURITY`, `DEPENDENCY`, `PERFORMANCE`, `UI`, `REFACTOR`, `FEATURE`, `CI/INFRA` per L25–26) and disposition (MERGE, MERGE-AFTER-FIX, REQUEST-CHANGES, ESCALATE, CLOSE-DUPLICATE, CLOSE-STALE, CONSOLIDATE); duplicate links; **`email-security-pipeline`** stricter handling per `docs/automated-pr-salvage-agent.md`.

**Key files:** `tasks/pr-triage.md`; `docs/automated-pr-review-agent.md` L30–51; `tasks/lessons.md` (0bb, 0t, 0u, 0cc).

**Dependencies:** Item 3.

**Size:** L

### Item 5 — Simulation pass (dry-run; human sign-off)

**Goal:** Every destructive action visible before execution.

**Done when:** `tasks/pr-triage.md` contains **`## Planned mutations (simulation — pending human sign-off)`** with exact `gh pr merge … --squash` and `gh pr close … --comment …` (and other mutating `gh` lines). **No** merge/close/push until you approve this block in writing.

**Key files:** `tasks/pr-triage.md`; `tasks/pr-review-2026-05-14.md` (sign-off timestamp).

**Dependencies:** Item 4.

**Size:** M

### Item 6 — Execution passes (post–sign-off)

**Goal:** Apply approved commands; handle queue shifts.

**Done when:** Actions logged in `tasks/pr-review-2026-05-14.md` with PR URLs. **MERGE-AFTER-FIX:** fix commit via normal push (**never** force-push). **After each merge:** refresh that repo’s open in-scope PR metadata before the next merge.

**Key files:** `docs/automated-pr-review-agent.md` L37–56; `tasks/lessons.md` (0aa, 0cc, 0df).

**Dependencies:** Item 5 + **your explicit sign-off** on the simulation section.

**Size:** L

### Item 7 — Reporting, lessons, salvage handoff

**Goal:** Close Phase 1; prime salvage.

**Done when:** `tasks/pr-review-2026-05-14.md` has counts + **Post-session remainder** YAML rows (`repo`, `pr`, `reason`); `tasks/pr-review-session-reports.md` appended; `tasks/lessons.md` updated; summary lists merged/closed/escalated PR URLs.

**Key files:** `docs/automated-pr-review-agent.md` L57–67; `docs/automated-pr-salvage-agent.md`.

**Dependencies:** Item 6.

**Size:** M

## Open Questions

- **Planning artifact:** `context_builder` previously timed out; this file is authoritative unless regenerated.

## References

- `docs/automated-pr-review-agent.md`
- `docs/automated-pr-salvage-agent.md`
- `docs/github-app-pr-automation-checklist.md`
- `docs/github-mcp-integration.md`
- `scripts/run-pr-review-session.sh`, `scripts/preflight-gh-pr-automation.sh`
- `tasks/pr-review-agent.config.yaml`, `tasks/lessons.md`
- `docs/plans/backlog-cleanup-orchestration-2026-05-09.md`
- `AGENTS.md`
- `.claude/skills/cloud-agents-starter/SKILL.md`

## Appendix — Oracle draft (supplementary context only)

During an early planning pass, an **Oracle-aligned markdown draft** restated the same spine: **Scope & Configurations** (mode/schedule/merge/stale/auto-fix/six repos/bot list), **Policies & Safeguards** (four-gate review, Lessons **0t/0bb**, **0u**, **0x**, never force-push, merge ordering, **0cc** cascade avoidance, **0df** workspace defense), and **Items 1–7** (preflight → context → inventory → triage → simulation halt → execution → reporting with `Post-session remainder`). That draft was **not** meant to replace this plan; it is preserved here only so future readers see **convergent evidence** between Oracle output and the locked Bundle 1 + file-anchor structure above. If Oracle and this document ever diverge, **this document wins**.
