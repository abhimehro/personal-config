# Backlog cleanup — orchestration plan (2026-05-09)

> **RECONSTRUCTED 2026-05-10.** The original document was created during the
> prior session (138 lines after the polish pass) but lived only as an
> untracked file under `docs/plans/`. A delegated salvage agent in Item 4A
> ran `git checkout <pr-branch>` in the working repo, and the untracked
> `docs/plans/` directory did not survive the branch switch. This file is a
> faithful reconstruction built from:
>
> - `tasks/pr-merge-results-2026-05-09.json` (definitive action log)
> - `tasks/pr-review-2026-05-09-orchestrate.md` (Phase 2 handoff)
> - `tasks/lessons.md` (operational rules referenced by the plan)
> - The forked-session transcript embedded in the recovery prompt
>
> Section structure, decisions, and outcomes are quoted from those sources.
> Any prose that could not be verified verbatim is marked _(reconstructed
> paraphrase)_. Use this for audit and pattern review, not as a verbatim
> reference.

---

## Goal

Run a **one-time backlog cleanup** across six repos (review-and-merge enabled,
Phase 2 light salvage approved) using the `builtin-orchestrate` workflow so
the orchestrator can decompose the work into items and dispatch a sub-agent
per item.

## Repos in scope

- `abhimehro/personal-config` (source of truth for skills + docs)
- `abhimehro/ctrld-sync`
- `abhimehro/email-security-pipeline`
- `abhimehro/Seatek_Analysis`
- `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project`
- `abhimehro/series_correction_project_updated`

## Scope expansion

In-scope authors: `dependabot[bot]`, `renovate[bot]`, `google-labs-jules[bot]`,
`devin[bot]`, `copilot[bot]`. **Plus** any PR whose branch name, title,
comments, or review history indicates automation — even when the visible
GitHub author is `abhimehro`.

## Background _(tightened version, post-polish)_

Configuration + entry points are documented in
`docs/automated-pr-review-agent.md`, `docs/automated-pr-salvage-agent.md`,
and `configs/.gemini/skills/cloud-agents-starter/SKILL.md`. Preflight is
`scripts/preflight-gh-pr-automation.sh --config <path>`; the canonical
config is `tasks/pr-review-agent.config.yaml`. Lessons that govern this run
(see `tasks/lessons.md`): `0aa` — disambiguate `update-branch` HTTP 422 by
viewing the PR before deciding; `0bb` — never bypass red gates on
security-classified repos; `0cc` — semantic-lane discipline (one merge per
file-set per pass); `0u` — in-scope infra-fix PRs that unblock the queue
override the default order; `0v` — closure comments must name the canonical
PR; `0t` / `0x` — defer or escalate when `main` CI is red on the way in;
`0de` — a timed-out `agent_run start` may still be executing on the agent
side; reconcile live state before re-dispatching. Orchestration mechanics:
each item should be self-contained (the `pair` agent reads only the plan

- named artifacts), the orchestrator updates this plan with progress
  between items, and the executor stops at the end of each lane to surface
  state before opening the next.

## Approach (4 work items)

The plan decomposes into **four ordered work items**. Item 1 pins scope and
runs preflight; Item 2 collects live inventory in parallel; Item 3 runs the
six lanes (one per repo) under the cluster discipline; Item 4 produces the
Phase 2 handoff and the consolidated session report. Open Questions surface
inside Item 1 via `ask_user`; their resolutions drive Items 1–3.

---

## Item 1 — Pin scope, resolve open questions, run preflight

**Goal.** Establish the configuration the run will use, resolve the three
remaining open questions, and confirm preflight is green before any merge
or close action lands.

**Done when.**

- The three open questions are answered and recorded in a `Decisions:` block in this file.
- A preflight pass with the canonical config (`tasks/pr-review-agent.config.yaml`) returns green for all six repos.
- If decision Q3 (email-security-pipeline) selected `Probe`, the explore agent's CI report exists at `docs/reviews/email-security-pipeline-main-ci-2026-05-09.md` and a `RUN | DEFER` verdict is recorded.

**Step A — Open questions (asked via `ask_user` before decomposition).**

| #   | Question                                                                                                                                          | Default answer              | Effect on later items                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------- |
| Q1  | **Config drift:** rebase-and-merge `personal-config#913` first, or use a session-only `tasks/pr-review-agent.config.local.yaml` override?         | Local override (lower-risk) | "Merge first" adds an Item 1B dispatch; "Local override" writes a `.local.yaml` in Step B          |
| Q2  | **Salvage scope:** light triage only, or allow Phase 2 to open draft salvage PRs for the `Hydrograph#169` and `series_correction#13/14` clusters? | Light triage only           | "Full salvage" expands Item 4 from documentation-only to cherry-pick + draft-PR open               |
| Q3  | **email-security-pipeline gate:** is the `main`-side pytest / CodeQL infra still red — defer the whole repo, or dispatch an infra-fix probe?      | Probe (Lesson 0t / 0x)      | "Defer" skips the email-security-pipeline lane in Item 3; "Probe" adds an Item 1A explore dispatch |

**Step B — Author the override config (if Q1 = local).** Write
`tasks/pr-review-agent.config.local.yaml` recording Q1–Q3 in a leading
`# Decisions:` comment so the executor sees them before any action.

### Decisions (recorded 2026-05-09 from `ask_user` Q1–Q3)

- **Q1 — Config drift:** _Rebase-and-merge `personal-config#913` first, then run with the canonical config._ (Item 1B added.)
- **Q2 — Salvage scope:** _Full salvage — Phase 2 opens draft salvage PRs for the Hydrograph#169 and series_correction#13/14 clusters._
- **Q3 — email-security-pipeline gate:** _Dispatch an infra-fix probe (`explore`) to root-cause the `main`-side breakage first; decide based on its report._ (Item 1A added.)

### Item 1A — `explore` agent: probe email-security-pipeline `main` CI

Output: `docs/reviews/email-security-pipeline-main-ci-2026-05-09.md` with a
verdict (`RUN`, `DEFER`, or `ESCALATE`) and a one-line root cause.

### Item 1B — `pair` agent: server-side rebase-and-merge of `personal-config#913`

Constraint: no local working-tree changes. Use `gh pr merge 913 --squash --auto`
(or `--rebase`) on `abhimehro/personal-config`, then re-run preflight against
the canonical config.

---

## Item 2 — Live inventory + per-repo triage (six parallel `explore` probes)

**Goal.** Build a fresh, snap-of-the-world inventory of in-scope PRs across
the six repos, classify each PR into the standard buckets (READY,
DUPLICATE/SUPERSEDED, STALE, CONFLICTING, ESCALATE, DEFER), and consolidate
into `tasks/pr-inventory.md` and `tasks/pr-triage.md`.

**Done when.**

- Six probes return; each emits a YAML slice with PRs, dispositions, and rationale.
- `tasks/pr-inventory.md` lists every in-scope PR with merge state, CI rollup, author, branch signal, cluster, and title.
- `tasks/pr-triage.md` maps every in-scope PR to a Phase 1 disposition (MERGE / CLOSE-DUPLICATE / CLOSE-STALE / MERGE-AFTER-FIX / ESCALATE / DEFER) plus a summary count.

**Probe brief template.** "List all open PRs for `<repo>` matching the
in-scope authors **or** automation signals in branch names, titles,
comments, or reviewers. For each PR, return repo, number, mergeable state,
CI rollup, author, branch, cluster (Bolt perf, Sentinel security, Jules QA,
Trust boundary, Red gate, or Other), title, and recommended Phase 1
disposition with one-line reasoning. Save to
`tasks/inventory-slices/<repo-slug>.yaml`."

**Probe note.** Title-classification helpers must match emoji-prefixed
automation titles (`⚡ Bolt:`, `🎨 Palette:`, `🛡 Sentinel:`, etc.); naive
`startsWith("Bolt")` will miss them.

---

## Item 3 — Phase 1 dispositions, lane by lane (six `pair` agents, sequential)

**Goal.** Walk each repo's lane and execute its Phase 1 dispositions
(merges, closes, escalations, `update-branch`) under cluster discipline.

**Done when.**

- All in-scope PRs have a recorded outcome (`MERGED`, `CLOSED`, `COMMENTED`, `DEFERRED`, or `DEFER` after `update-branch` 422).
- Trust-boundary PRs are escalated by comment, never merged.
- Red-gated PRs on security-classified repos are deferred (Lesson 0bb), never merged.
- The action log is appended to `tasks/pr-merge-results-2026-05-09.json`.

### Lane order

1. `personal-config` (largest, highest-risk; gates the rest)
2. `ctrld-sync`
3. `Seatek_Analysis`
4. `Hydrograph_Versus_Seatek_Sensors_Project`
5. `series_correction_project_updated`
6. `email-security-pipeline` (last; runs only if Q3 = `RUN`)

### `personal-config` cluster discipline

A _cluster_ is two or more PRs that share at least two file paths or share
the same automation source (e.g., a single Jules sweep across multiple
PRs). Within a cluster:

1. Identify the **canonical PR** (newest + most-focused, lowest
   conflict count, gates green if anyone is green).
2. Process the canonical PR first. If it merges, sibling PRs in the
   cluster flip to one of: zero-diff (close), `update-branch`-clean
   (merge), or DIRTY (defer to Phase 2 with a closure comment naming
   the canonical PR).
3. **`update-branch` HTTP 422 is ambiguous (Lesson 0aa).** Always view
   the PR (`gh pr view`) before deciding; 422 can mean "already
   up-to-date", "merge conflict", or "branch protection hold".
4. **Verify cluster membership against the live inventory before
   acting.** PR numbers may have moved between plan-time and run-time.

| Cluster           | Likely files / signals                                                                                    | Default disposition                                             |
| ----------------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Bolt perf         | `categorize_ready.py`, `parse_inventory.py`, `detect_duplicates.py`; `⚡ Bolt:` title; `bolt-` branch     | Merge canonical, close zero-diff siblings, defer DIRTY siblings |
| Sentinel security | `patch_sentinel*`, `summary.yml`, AI-output ingestion paths; `🛡 Sentinel:` title                         | Escalate; never auto-merge                                      |
| Jules QA          | tests under `tests/`; `salvage-personal-config-` branches                                                 | Merge if green; defer if red on `main`                          |
| Trust boundary    | `.github/`, automation toolchain itself, secret-handling paths                                            | Escalate by comment                                             |
| Red gate          | any PR with failing CodeQL, GitGuardian, Devin Review, ShellCheck, or CodeScene Code Health Review (main) | Defer with red-gate citation                                    |

---

## Item 4 — Phase 2 salvage + session report (full-salvage variant)

**Goal.** Per Q2 = full salvage, open draft salvage PRs for the Hydrograph
and series_correction clusters; produce a single consolidated handoff
artifact and append a session-report entry; verify with the standard
preflight + `make test-quick` gates.

### Item 4A — `pair` agent: salvage execution

For each cluster, clone the repo to `/tmp/salvage-<slug>-<date>/`, create a
new branch from `origin/main`, cherry-pick the canonical PR's commits,
resolve **only trivial conflicts**, push to a `cursor-agent/salvage-…`
branch, and open a draft PR. **Never `git checkout` in the working repo.**

- `Hydrograph#169` cluster (incl. `#170` stacked, `#171` overlapping)
- `series_correction#13/14` cluster (canonical: `#13`)

### Item 4B — `engineer` agent: documentation consolidation

- Write `tasks/pr-merge-results-2026-05-09.json` (full action log).
- Write `tasks/pr-review-2026-05-09-orchestrate.md` (Phase 2 handoff).
- Append a run section to `tasks/pr-review-session-reports.md`.
- Append any new lessons to `tasks/lessons.md`.
- Update `tasks/todo.md` checkboxes.
- Verify: `python -c "import json; json.load(open('tasks/pr-merge-results-2026-05-09.json'))"`, `make test-quick`, `git diff --check -- tasks/ docs/`.

---

## Progress (recorded during execution)

- [x] **Item 1A** — explore probe complete; `docs/reviews/email-security-pipeline-main-ci-2026-05-09.md` returned `RUN` (main green; defer for infra-fix-chasing only, not for the lane itself).
- [x] **Item 1B** — `personal-config#913` squash-merged via `gh pr merge`; canonical config verified; preflight green for six repos.
- [x] **Item 2** — six parallel inventory probes returned; consolidated into `tasks/pr-inventory.md` (29 in-scope PRs) and `tasks/pr-triage.md` (Phase 1 dispositions).
- [x] **Item 3** — Phase 1 dispositions executed across six lanes. Outcome (per `tasks/pr-merge-results-2026-05-09.json`): 3 merged, 4 closed-duplicate, 4 escalated, 3 MERGE-AFTER-FIX deferred on `update-branch` HTTP 422, 16 DEFER to Phase 2.
- [x] **Item 4A** — Hydrograph cluster: `DEFER` because `#172` already merged the core intent on `main`; recommend close-superseded for `#169` and `#171`. series_correction cluster: salvage branch pushed and `series_correction#15` opened as draft from `#13`.
- [x] **Item 4B** — handoff + session report written; verification gates green.

---

## Lessons added during this run

(See `tasks/lessons.md` for canonical text.)

- **Emoji-prefixed automation titles trip naive `startsWith`** — classifiers must accept `⚡ Bolt:`, `🎨 Palette:`, `🛡 Sentinel:`, etc.
- **A canonical PR may be DIRTY against `main` because `main` already absorbed its intent via a sibling merge** — verify by diffing the canonical PR's tree against `main` before salvaging; if empty, close-superseded instead.

## Lesson candidate added in recovery (2026-05-10)

- **`0df` — A salvage agent given a "no local working-tree manipulation" rule will still `git checkout` a PR branch if its prompt mentions cherry-picking commits without a clear `clone-elsewhere` directive.** Mitigation: brief salvage agents to do all branch work in a `git clone` under `/tmp/`, never in the working repo, and commit important documents _before_ dispatching a salvage agent.
