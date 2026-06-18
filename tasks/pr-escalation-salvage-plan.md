# Escalation tail — salvage plan for human / Phase-2 agents (2026-05-03)

**Companion docs:**
[Automated PR Salvage & Recovery Agent](../docs/automated-pr-salvage-agent.md)
(Phase 2 — draft PRs only, no autonomous merge),
[Automated PR Review Agent](../docs/automated-pr-review-agent.md),
`tasks/lessons.md` (0cc burst cascade, 0x `media_analyzer`, 0y journals).
**Session logs:** review activity in `tasks/review-session-reports.md`; salvage
activity in `tasks/salvage-session-reports.md`.

**Live state:** Always re-fetch with
`gh pr list --repo <owner/repo> --state open --json …` before acting; numbers
and mergeability drift quickly after `main` moves.

---

## Executive summary

| Repo                                | Situation                                                                                                          | Recommended strategy                                                                                                                                                                                               |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `abhimehro/personal-config`         | Burst merges cleared most CLEAN PRs; **tail is overlap-heavy** (Bolt perf + Sentinel QA shells + mega Jules drops) | **Fresh-from-main branches** per _intent lane_; cherry-pick or manual replay of _minimal file sets_; **discard** wholesale `.jules/*`, `.trunk/plugins/trunk`, and unrelated skill blobs unless explicitly desired |
| `abhimehro/email-security-pipeline` | Overlapping Palette UX PRs + conflicted Bolt/`requirements` churn                                                  | **One rebased Palette PR** (prefer newer `#764` over `#747`); isolate **`requirements.txt`** into its own reviewed migration PR; treat **`#732`** as **multi-subsystem** — split workflows vs ML vs alert path     |

---

## A. `abhimehro/personal-config`

### A1. Bolt concurrency lane (`run_merges.py`, `parse_inventory.py`, `categorize_ready.py`)

**Open PRs (snapshot):**
[#884](https://github.com/abhimehro/personal-config/pull/884),
[#880](https://github.com/abhimehro/personal-config/pull/880),
[#867](https://github.com/abhimehro/personal-config/pull/867) (CONFLICTING),
[#851](https://github.com/abhimehro/personal-config/pull/851).

**Observation:** `#867` carries **34 paths** — essentially a **rollup** of
scripts already touched by merges to `main` (copilot-demo, mole libs,
`detect_duplicates.py`, CI scripts). Rebasing this branch interactively will
burn reviewer time.

**Salvage playbook:**

1. On a fresh clone:
   `git checkout main && git pull && git checkout -b salvage/bolt-pr-fetch-minimal`.
2. Use **`git show pull/<884>/head:run_merges.py`** (after
   `git fetch origin pull/884/head`) or GitHub PR patch view to extract **only**
   the concurrent-fetch logic for `run_merges.py`.
3. Repeat for **`parse_inventory.py`** from `#851` if still absent from `main`
   (`git diff main -- parse_inventory.py` on PR branch).
4. **Do not** copy `.jules/*.md`, `.trunk/plugins/trunk`, or unrelated
   mole/adguard edits from Bolt PRs unless each hunk is justified (Lesson **0y**
   — journal integrity).
5. Open **one draft PR** titled e.g.
   `perf(pr-automation): concurrent gh prefetch + parse_inventory table strip`,
   reference `#884/#851`, **close** `#867/#884/#851/#880` once superseded with
   explicit file overlap notes (Lesson **0v**).

### A2. Palette / QA shell hygiene (`setup.sh`, mac-audit, boolean prompts)

**Open PRs:** [#849](https://github.com/abhimehro/personal-config/pull/849),
[#840](https://github.com/abhimehro/personal-config/pull/840).

**Observation:** Both touch **`mac-audit/audit.sh`** and
**`mac-audit/lib/defaults_audit.sh`**. `#849` additionally touches
**`setup.sh`** (Sentinel terminal-injection theme overlapping `#863`).

**Salvage playbook:**

1. Diff vs `main` per file: `gh pr diff 849 --name-only` vs current tree.
2. Prefer **one** branch replaying **`setup.sh`** escape fixes + Palette prompt
   wording **without** bundled unrelated audit edits — or sequence **audit PR**
   then **setup PR** to reduce conflict surface.
3. Close `#840` if `#849` ⊇ QA audit conclusions after reconciliation.

### A3. Sentinel `setup.sh` / terminal injection — [#863](https://github.com/abhimehro/personal-config/pull/863)

**Observation:** Files include **`patch_sentinel.sh`** and
**`resolve_conflict.sh`** — read as **salvage tooling**, not routine product
changes. CI snapshot showed green ShellCheck/CodeScene, but GitHub rollup may
remain **UNSTABLE** until branch synced.

**Human gate before merge:**

1. Confirm both scripts are intentional, audited, and not redundant with repo
   automation already on `main`.
2. If they were one-off Jules artifacts, **drop them** on a salvage branch and
   keep only **`setup.sh`** / mole fixes that survive review.
3. If merge still blocked: merge `main` into the PR branch with ordinary commits
   (**no force-push**).

### A4. `detect_duplicates` / imports — [#869](https://github.com/abhimehro/personal-config/pull/869), [#862](https://github.com/abhimehro/personal-config/pull/862)

**Observation:** `#869` still lists `detect_duplicates.py`, `run_merges.py`,
tests — much may already match `main` post-merge-wave.

**Salvage playbook:**

1. `git fetch origin pull/869/head && git diff main...FETCH_HEAD --stat`.
2. If stat collapses to noise → **close zero-diff / superseded** (Lesson
   **0b**).
3. Else cherry-pick **only remaining commits** affecting `detect_duplicates.py`
   onto fresh branch.

### A5. Single-file CI fixes — [#858](https://github.com/abhimehro/personal-config/pull/858), [#856](https://github.com/abhimehro/personal-config/pull/856), [#874](https://github.com/abhimehro/personal-config/pull/874)

**Observation:** Prior session flagged CodeScene / ShellCheck failures — after
`main` advanced, **re-run checks**.

**Salvage playbook:**

1. `gh pr checks <n> --repo abhimehro/personal-config`.
2. Fix trivial ShellCheck locally → push additional commit to PR branch (same
   credential as `gh`, Lesson **0j**).
3. If CodeScene fails on complexity only — maintainer decision to accept
   refactor vs split tests.

### A6. Mega conflicting Jules drops (~867–870 files) — [#838](https://github.com/abhimehro/personal-config/pull/838), [#836](https://github.com/abhimehro/personal-config/pull/836), [#832](https://github.com/abhimehro/personal-config/pull/832), [#831](https://github.com/abhimehro/personal-config/pull/831)

**Observation:** PR
[#838](https://github.com/abhimehro/personal-config/pull/838) is **CONFLICTING**
with ~870 changed files starting under `.agents/skills/*`, HF manifests, etc. —
**high probability** of unrelated churn burying the actual CWE-78 eval fix.

**Salvage playbook (mandatory decomposition):**

1. Use GitHub **Files changed** filter or API:
   `gh api repos/abhimehro/personal-config/pulls/838/files --paginate --jq '.[].filename'`
   → bucket into **security-critical paths**
   (`configs/.config/mole/lib/core/*.sh`, `app_protection.sh`, etc.) vs
   **documentation/skills churn**.
2. For security bucket only: create **`salvage/sentinel-cwe78-eval-<topic>`**
   from `main`, apply patches via `git checkout pr838 -- path` **only after**
   verifying each path diff vs `main` is still needed (Lesson **0aa**).
3. Explicitly **exclude** wholesale `.agents/skills/**` additions unless
   reviewed as trusted supply-chain (HF/Jules blobs).
4. Close `#836/#832/#831` once superseded by narrowed salvage drafts or verify
   each addresses a **distinct** CWE/palette concern.

---

## B. `abhimehro/email-security-pipeline`

### B1. Duplicate Palette UX — [#764](https://github.com/abhimehro/email-security-pipeline/pull/764) vs [#747](https://github.com/abhimehro/email-security-pipeline/pull/747)

**Observation:** Same title; `#764` newer (`2026-05-03` vs `2026-04-30`). Both
CONFLICTING/DIFF snapshots overlap **`alert_system.py`**.

**Recommendation:** Treat **`#764` as canonical**; rebase onto `main`, resolve
conflicts once; close **`#747`** as superseded with overlap explanation.

### B2. Explicit TLS / verify step — [#760](https://github.com/abhimehro/email-security-pipeline/pull/760)

**Observation:** Single-file `alert_system.py`; earlier CodeScene rollup may
block autonomous merge.

**Playbook:** Re-run checks post-rebase; if CodeScene-only failure, decide
acceptable delta vs split helper extraction.

### B3. Requirements / ML dependency migration — [#744](https://github.com/abhimehro/email-security-pipeline/pull/744)

**Observation:** Touches **`requirements.txt`** +
**`tests/test_setup_wizard.py`** — trust-boundary class change.

**Playbook:** Separate **dependency policy PR** (human-approved semver pins,
SBOM impact, CI matrix) from **test-only** adjustments; never squash unrelated
ML commenting with wizard tests without explicit approval.

### B4. Bolt performance mega — [#732](https://github.com/abhimehro/email-security-pipeline/pull/732)

**Observation:** Touches **`media_analyzer.py`**, **`spam_analyzer.py`**,
workflows, `CHANGELOG.md`, `AGENTS.md`, `.trunk/trunk.yaml` — same failure mode
class as Lesson **0x** (blob/regression risk).

**Playbook:**

1. **Do not** merge wholesale.
2. Split salvage drafts: **(i)** workflow-only, **(ii)** spam analyzer perf,
   **(iii)** media analyzer — each branch ≤5 logical files unless justified.
3. Run **`python -m py_compile`** on every touched `.py` before push.

---

## C. Agent workflow checklist (repeatable)

1. **Preflight:**
   `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml`.
2. **Inventory refresh:** `gh pr list --repo … --state open`.
3. **Per PR:** `gh pr diff N --name-only`, `gh pr checks N`, compare against
   **`main`** (`git fetch origin main`).
4. **Salvage:** fresh branch from `main`; minimal cherry-picks / path-scoped
   checkouts; **draft PR** referencing originals; close originals with supersede
   comments.
5. **Never:** force-push to contributor branches without owner consent; bypass
   failing required checks without documented unrelated-proof.

---

## D. Optional quick wins (verify then execute)

These may already be merge-ready after local sync — confirm mergeability in
GitHub UI/`gh pr merge --dry-run` before merging:

- **personal-config
  [#863](https://github.com/abhimehro/personal-config/pull/863):** CI largely
  green; resolve **trust questions on helper scripts** first.
- **email
  [#760](https://github.com/abhimehro/email-security-pipeline/pull/760):** after
  `#764/#747` consolidation settles alert paths.

_(Phase 2 Salvage Agent still prefers **draft PR outcomes** even when CI is
green.)_
