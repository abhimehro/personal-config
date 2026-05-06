## Final Prompt

<taskname="PR Salvage Phase 2"/>

<task>
Execute a Phase 2 "Automated PR Salvage & Recovery" follow-up run based on `docs/automated-pr-salvage-agent.md`.

Produce a numbered work plan, then execute it. The execution must address:

1. Maintainer/reviewer findings on draft PRs (#899, #900, #169, #10) first. Use S9 policy for updates (supersede with new draft PR or `-v2` suffix, no force-push).
2. The remaining open PR live queue overrides:
   - personal-config: #831, #836, #840, #849, #851, #856, #858, #862, #867, #869, #880, #884, #893
   - email-security-pipeline: #760, #777, #778
   - ctrld-sync: #763, #769, #770

Your work plan must include:

- **Preflight order:** run preflight scripts, verify `gh auth`.
- **Per-repo groupings:** Group by repo and detect if a repo is "infra-broken" (4+ PRs with same check failing) before processing individual PRs.
- **Priority tiers:** Process the list according to: T0 infra > T1 security salvage > T2 trust-boundary > T3 routine.
- **Execution rules:** Operations within a repo MUST be serial. Parallel operations across different repos are allowed.
- **Explicit "done when" criteria per item:** e.g., when a `-v2` draft PR is opened and the original is closed with a comment, OR when a PR is closed as superseded.

Deliverables upon completion:

1. Address reviewer findings on #899/#900/#169/#10.
2. Process all open PRs in the list according to the decision tree (salvage, supersede-close, escalate, or no-op close).
3. Append `## Addendum — <today> salvage round 2` to `tasks/pr-review-2026-05-05.md` including a summary table.
4. Append any new patterns/lessons to `tasks/lessons.md`.
   </task>

<architecture>
The Salvage Agent (Phase 2) operates strictly on deferred/escalated PRs and NEVER autonomously merges. Every output must be a draft PR or a closure of superseded work.
- `tasks/pr-review-agent.config.yaml` provides the active repos (human-curated, do not edit autonomously).
- `docs/automated-pr-salvage-agent.md` defines the strict decision tree, triage rules, and the 9 Safeguards (S1-S9).
- `tasks/pr-review-2026-05-05.md` holds the previous Phase 1 and initial Phase 2 run results.
</architecture>

<selected_context>
docs/automated-pr-salvage-agent.md: Full specification of the Salvage Agent, S1-S9 safeguards, trigger conditions, and the decision tree.
tasks/pr-review-2026-05-05.md: Previous session report and the target for appending the new Addendum.
tasks/pr-review-agent.config.yaml: Repo config and bot patterns.
tasks/lessons.md: Append-only ledger of rules from failed automation.
scripts/preflight-gh-pr-automation.sh: Preflight checks script.
AGENTS.md: Meta prompt instructions.
</selected_context>

<relationships>
- New draft PRs MUST cross-reference their originals (`superseded by #...` or `salvages #...`).
- Appends to journal files (`tasks/lessons.md`, `pr-review-2026-05-05.md`) must be appended strictly at the end, without using checkout.
</relationships>

<ambiguities>
The initial request to clarify requirements with the user was skipped. Ensure you verify the exact state of #899, #900, #169, and #10 on GitHub before rewriting them. Always fallback to creating a `-v2` PR and avoid force pushes per S9 policy. Ensure `email-security-pipeline` is treated per S6 policy (never bypass broken pytest). Look out for JSON-blob tripwire (S3) on large single-file perf PRs.
</ambiguities>

## Selection

- Files: 6 total (6 full)
- Total tokens: 22352 (Auto view)
- Token breakdown: full 22352
- Copy preset: complete • 6 files • ~22,352 tokens (up ~0)

### Files

### Selected Files

/Users/speedybee/dev/personal-config/
├── docs/
│ └── automated-pr-salvage-agent.md — 6,166 tokens (full)
├── scripts/
│ └── preflight-gh-pr-automation.sh — 2,657 tokens (full)
├── tasks/
│ ├── lessons.md — 6,352 tokens (full)
│ ├── pr-review-2026-05-05.md — 3,060 tokens (full)
│ └── pr-review-agent.config.yaml — 200 tokens (full)
└── AGENTS.md — 3,917 tokens (full)

---

## Generated Plan

## Chat Send ✅

- **Chat**: `pr-salvage-phase-2-591409` | **Mode**: plan

### Response

### 1. Summary

This plan executes Phase 2 (Salvage & Recovery) for the remaining deferred PR tail from the 2026-05-05 review session. It defines a strict operational sequence to first address maintainer feedback on existing draft salvages (#899, #900, #169, #10) via `-v2` branches (adhering to S9 no-force-push), then triages a specified queue of 19 open PRs across `personal-config`, `email-security-pipeline`, and `ctrld-sync`. The plan strictly enforces the S1-S9 safeguards, prioritizes T0 infra-fixes and T1 security salvages, and tracks all outcomes in a new addendum block within the session report.

### 2. Current-state analysis

The Phase 1 review agent processed 58 PRs, merging 18 and closing 8. The remaining tail was left `OPEN` due to merge conflicts, trust boundaries, or unstable CI.

- A previous Phase 2 run created salvage drafts (#899, #900, #169, #10) which now have human review comments requiring adaptation.
- `email-security-pipeline` is tagged as a security-classified repository (S6 applies: no test bypasses, all salvages are drafts).
- `personal-config` and `ctrld-sync` contain an accumulation of T1/T2 (trust boundary/security) and T3 (perf) PRs that must be evaluated against the current state of `main`.
- State flow for a salvage requires: pulling the original diff -> verifying if it exists on `main` -> applying valid source code to a new branch -> appending (not checking out) journal files (S2) -> creating a new draft PR -> closing the original.

### 3. Design

**Execution Model & State Flow**

1. **Preflight**: Execute `scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml`. Execution terminates immediately if authentication or read/write probes fail.
2. **Data Ingestion**: Fetch current state of the 4 review-pending PRs and 19 queue PRs. Group by repository.
3. **Infra-Breakage Detection (Step 2)**: Query `gh pr checks` for the queue. If 4+ PRs in a repo fail on the identical required check, and `main` is also failing, execution halts for that repo to prioritize a **T0 infra-fix** branch.
4. **Draft PR Refinement (S9)**: For each of the 4 reviewed drafts, create a `-v2` branch from `main`, apply the requested maintainer changes, push a new draft PR, and close the `-v1` PR with a cross-linking comment.
5. **Salvage Processing (Steps 4-5)**:
   - **T1/T2 (Security/Trust)**: Explicit human review required. Branches prefixed with `fix(security)` or similar.
   - **T3 (Routine/Perf)**: Check for JSON-blob corruption (S3) using `head -c 200 <file> | grep -E '\\n.{20,}\\n'`. Close as superseded if `main` already holds the fix.
   - **Journal Files (S2)**: For `.jules/*.md` and `tasks/lessons.md`, changes are strictly appended via text extraction, never via `git checkout`.
6. **Reporting**: The memory of this run is persisted by appending an Addendum table to `tasks/pr-review-2026-05-05.md` and any identified failure patterns to `tasks/lessons.md`.

**Error Handling & Edge Cases**

- **422 on `update-branch`**: Indicates hard conflicts (S5). Fallback is fresh branch checkout from `main` + `git checkout pr_branch -- <files>`.
- **`email-security-pipeline` pytest failures**: Under S6, if `pytest` is red on main, all salvage operations for this repo halt until a T0 PR is created to fix it.

### 4. File-by-file impact

- **`tasks/pr-review-2026-05-05.md`**:
  - **Change**: Append `## Addendum — $(date +%Y-%m-%d) salvage round 2` to the EOF.
  - **Why**: Documents the disposition of the queue overrides and the `-v2` PRs for auditability.
- **`tasks/lessons.md`**:
  - **Change**: Append new `## Lesson <number>:` blocks if novel failure modes are encountered during salvage (e.g., new bot hallucination patterns or CI tripwires).
  - **Why**: Required by the salvage agent specification to ensure continuous learning.
- **Git State (Local/Remote Branches)**:
  - **Change**: Creation of `cursor-agent/salvage-<repo>-<pr>-<label>-v2` branches and `cursor-agent/salvage-<repo>-<pr>-<label>` branches.
  - **Why**: Isolates salvaged code for maintainer review without forcing pushes over active review threads.

### 5. Risks and migration

- **S2 Violation Risk**: Overwriting `tasks/lessons.md` or `.jules/` journals via blanket `git checkout` will wipe history. Strict append-only logic must be enforced.
- **S3 Violation Risk**: Accidentally salvaging a JSON-escaped blob as a Python script. Checked via `head` regex before commit.
- **Orphaned PRs**: If a script fails midway, a new draft PR might be opened without closing the original. The execution order requires atomic operations per PR: push draft -> verify -> close original.

### 6. Implementation order

**Phase 2 Execution Work Plan**

- [ ] **Item 1: Preflight & Draft PR Fixes**
  - Run preflight script.
  - Address reviewer comments on #899, #900 (personal-config), #169 (Hydrograph), #10 (series_correction). Create `-v2` draft PRs, close originals.

- [ ] **Item 2: Process `email-security-pipeline` & `ctrld-sync`**
  - Apply S6 rules for email-security-pipeline (PRs #760, #777, #778).
  - Apply trust boundary rules for ctrld-sync (PRs #763, #769, #770).
  - Create new salvage drafts, close originals. Track outcomes for reporting.

- [ ] **Item 3: Process `personal-config` queue**
  - Process PRs: #831, #836, #840, #849, #851, #856, #858, #862, #867, #869, #880, #884, #893.
  - Apply S3 (JSON-blob) and S2 (journal append) checks. Create new salvage drafts, close originals. Track outcomes for reporting.

- [ ] **Item 4: Finalize Reporting**
  - Compile outcomes from Items 1-3.
  - Append the Addendum to `tasks/pr-review-2026-05-05.md` and new patterns to `tasks/lessons.md`.

> 💡 Continue this plan conversation with ask_oracle(chat_id: "pr-salvage-phase-2-591409", new_chat: false)
