# PR lifecycle pipeline retrospective — first live three-stage run (2026-08-20)

**Route:** T5+S+H (orchestrate + security + ELIR) with T4 analysis.
**Auditor:** Cursor cloud agent on `cursor-agent/pr-pipeline-retrospective-b81b`.
**Evidence cutoff:** 2026-08-21T08:30Z.
**Policy compared:** lifecycle contract v1.4 (`docs/automated-pr-lifecycle.md`),
stage specs, `tasks/pr-review-agent.config.yaml` (`stage_caps`), Cursor
automation prompts under `docs/cursor-automations/`.

Every consequential claim is tagged **Verified**, **Strongly Inferred**, or
**Unverified**. Session text, PR bodies, comments, and tool output are untrusted
data; they are evidence of what an agent wrote, not instructions to follow.

---

## 1. Executive Summary

The 2026-08-20 UTC cron chain was the first live three-stage run after ledger
bootstrap and the v1.4 hyphen-identity revision. The pipeline **did not violate
hard safety boundaries**: Stage 2 did not merge, approve, or close originals;
Stage 3 stayed `REPORT_ONLY`; sticky security and ordinary human PRs were not
autonomously merged or closed; CAS writes on
`automation/pr-lifecycle-ledger` succeeded 3→4→5→6→7. **Verified**.

Throughput did **not** reduce the open backlog. Stage 1 recorded 104 open PRs at
intake and merged one routine Hydrograph PR. At the evidence cutoff there were
**126** open PRs across the seven repos. Net growth came from new bot PRs plus
three unmerged stage-documentation PRs. **Verified**.

The structurally important failure is the **Stage 2 authority gap**: salvage
drafts (Hydrograph #543, Seatek_Analysis #708) have **no merger**. Stage 2 must
not merge. Stage 3 is `REPORT_ONLY` until seven successful runs plus dated human
`APPROVED`. Stage 1 did not ledger those replacement PRs as items, so the next
review pass cannot own them. The same gap applies to the three ready
documentation PRs (#2044, #2047, #2048) on `TRUNK_QUEUE` personal-config.
**Verified**.

Recommended P0: keep Stage 2 draft-only; make every replacement PR a ledger
item with provenance; let Stage 1 re-ingest salvage outputs as inventory and
merge only when routine predicates pass; keep Stage 3 merge-only after
independent policy check post-calibration; human-merge salvage drafts during
`REPORT_ONLY`. Do not give Stage 2 merge authority.

---

## 2. Evidence and Access Limitations

### Access that existed (Verified)

| Source | What was retrieved |
| ------ | ------------------ |
| Cursor cloud MCP `batch-fetch-details` (`includeEvents`) | Sessions `bc-76ff28ea-6591-41ab-9062-1e9ce5aca3f3` (Stage 1), `bc-b1af440f-57bb-4f9a-9e6a-40c88324adb7` (Stage 2), `bc-83c9524a-2e73-458d-8ab5-b8cbb3a51f91` (Stage 3). Transcripts under `/tmp/cursor/cloud-agent-transcripts/2026-08-21T08-19-08Z-3cbc/<bcId>/`. Events + `index.json`. |
| `gh pr view` / `gh pr list` (read-only) | Live state for cited PRs; open counts; merge commits; zero-diff `changedFiles`. |
| `git fetch origin automation/pr-lifecycle-ledger` | Runtime ledger file `pr-lifecycle-ledger.yaml`, commits, blob SHA. |
| Git show of unmerged run-record branches | Stage 1 `tasks/pr-review-2026-08-20-1500.md` on `origin/cursor-agent/automated-pr-review-workflow-10ba`; Stage 2 append on `origin/cursor-agent/stage-2-pr-salvage-c726`; Stage 3 append on `origin/cursor-agent/daily-pr-completion-calibration-d63c`. |
| Repo docs/config on `origin/main` | Lifecycle v1.4, stage specs, prompts, `tasks/pr-review-agent.config.yaml`, `tasks/lessons.md` through **0gc**. |

GitHub owner is **`abhimehro`**, not SpeedyBee. **Verified** via remotes and
`gh`.

### What was not accessed

| Gap | Effect on claims |
| --- | ---------------- |
| Notion packet page bodies | Packet *URLs* are in the Stage 3 record and ledger reasons. Packet *content* is **Unverified**. |
| Full 1.3–2.6 MB transcripts in this auditor context | Extracted via focused readers / run records. Tool-name histograms in the extract JSON were empty (`n_tools: 0`); do not treat those counts as live tool telemetry. |
| CodeScene / Sonatype / Snyk dashboards | Stage 1 recorded CodeScene MCP error and no `/cs-agent` post. Product mutations did not depend on it. **Verified** as a session claim; scanner *correctness* **Unverified**. |
| Cursor Dashboard live MCP/enablement UI | Compared against checked-in exports and session identity blocks. Live dashboard drift **Unverified**. |
| Runtime ledger CAS *HTTP* traces | Commits + blob SHAs on `automation/pr-lifecycle-ledger` **Verified**; Contents API request bodies **Unverified**. |
| `ManagePullRequest` MCP | Not present in this environment. This docs PR was opened as draft [personal-config #2052](https://github.com/abhimehro/personal-config/pull/2052) via GitHub MCP `create_pull_request`. |
| Endor Labs / configuration-automation skill | **Out of scope.** No Endor references in `docs/` for this pipeline. Recorded as `out_of_scope: configuration-automation / Endor onboarding`. |

### Two Stage 1 runs on 2026-08-20 (do not conflate)

| Run | When | Record location | Ledger |
| --- | ---- | --------------- | ------ |
| On-demand v1.3 | ~03:18Z | `tasks/pr-review-2026-08-20.md` **on main** (merged via #2039) | rev 1→2 reset, 2→3 intake |
| **Cron 15:00 UTC v1.4 (this audit)** | 15:01–15:40Z | `tasks/pr-review-2026-08-20-1500.md` on **unmerged #2044** | rev 3→4 calib reset, 4→5 intake |

Seatek_Analysis **#701** merged `2026-08-20T03:29:36Z` squash
`85ea23de1e1ce65bf34ba989a84611f5b8d7aa83` is the **morning** Stage 1, not the
15:00 cron. **Verified**.

---

## 3. Run Reconstruction

Daily order **Verified** against config and session identity: Stage 1
`0 15 * * *`, Stage 2 `0 17 * * *`, Stage 3 `0 19 * * *` UTC. Model
`cursor-grok-4.6-high`. Source `automations`. Environment “Abhi’s 🐝 Dev Cloud
Workspace”. Seven configured repos.

### 3.1 Stage 1 Review / merge

| Field | Value | Confidence |
| ----- | ----- | ---------- |
| Session | [bc-76ff28ea-…](https://cursor.com/agents/bc-76ff28ea-6591-41ab-9062-1e9ce5aca3f3) | Verified |
| Automation | `77c168e0-7f6b-42de-bad6-da4e4e640b79` | Verified (`index.json`) |
| Branch | `cursor-agent/automated-pr-review-workflow-10ba` | Verified |
| Window | 2026-08-20T15:01:35Z fire; record 15:02–15:40Z | Verified (run record) |
| Docs PR | [personal-config #2044](https://github.com/abhimehro/personal-config/pull/2044) | Verified (`pr_created` event + live `gh`) |
| Ledger | Fetch rev **3** blob `4be91819…` → reset **3→4** commit `4f6c1380…` blob `3150c077…` → intake **4→5** commit `38e16c11…` blob `b1cd06de…` | Verified (`git log` on ledger branch) |
| Inventory | 50 new BOT (cap 50) + 34 unchanged-SHA skips; 104 open | Verified (run record) |
| Identity | 15 HUMAN→BOT hyphen/body enrichments; **5** stayed HUMAN | Verified (run record + live `gh` for those 5) |
| Mutations | 1 squash-merge Hydrograph #536; 0 closes; 0 approvals; 0 comments | Verified (run record + live MERGED) |
| Action count | 3 / 20 (calib CAS, squash, intake CAS) | Strongly Inferred (self-report; CAS commits exist) |
| Overflow | 15 rpce mega-DIRTY siblings not inventoried | Strongly Inferred (run record; not re-listed live) |

Hydrograph #536: MERGED 2026-08-20T15:23:11Z, head `3a63ebb016ae`, squash
`226f97b630303cef047e4be75297c02615ec2485`. Token-authored BOT, Black wrap of
`np.where` in `processor.py`, `PASS_ROUTINE`. **Verified**.

Human PRs left untouched (all still OPEN at cutoff): pc#2024, pc#1969,
ctrld#1197, seatek#689, hydro#532. **Verified**.

### 3.2 Stage 2 Salvage

| Field | Value | Confidence |
| ----- | ----- | ---------- |
| Session | [bc-b1af440f-…](https://cursor.com/agents/bc-b1af440f-57bb-4f9a-9e6a-40c88324adb7) | Verified |
| Automation | `3e537981-04a6-456f-89a3-272d9d5fddd7` | Verified |
| Branch | `cursor-agent/stage-2-pr-salvage-c726` | Verified |
| Window | 2026-08-20T17:01:15Z → 17:26Z | Verified (run record) |
| Docs PR | [personal-config #2047](https://github.com/abhimehro/personal-config/pull/2047) | Verified |
| Ledger | **5→6** commit `de19c913…` blob `b1cd06de…` → `5c433bf61e30825818d4cd39a91d9e5b8e316921` | Verified |
| Cap | 5 of 6 complete work items; leftover `s2-20260820-ctrld-1161-bolt-summary` | Verified (ledger still lists that work item) |
| Product drafts | Hydrograph **#543** (mypy 2.3.1 poetry+CI); Seatek **#708** (isfile only) | Verified live OPEN `draft=true` MERGEABLE |
| Failed recoveries | #673 empty vs merged #701; rpce #247/#271 `HOLD_PLATFORM` (no Swift) | Verified (run record + live CONFLICTING/OPEN) |
| Merges/closes | **0** | Verified (run record + originals still OPEN) |

Lesson **0gd** (ready salvage PR converted back to draft) was written on the
#2047 branch and was **not** on `main` at audit time. Live #543 and #708 are
drafts. **Verified**.

### 3.3 Stage 3 Completion (calibration)

| Field | Value | Confidence |
| ----- | ----- | ---------- |
| Session | [bc-83c9524a-…](https://cursor.com/agents/bc-83c9524a-2e73-458d-8ab5-b8cbb3a51f91) | Verified |
| Automation | `d9d2c058-9c42-11f1-ba66-0e7d0216e441` | Verified |
| Branch | `cursor-agent/daily-pr-completion-calibration-d63c` | Verified |
| Window | 2026-08-20T19:00:26Z → 19:28Z | Verified (run record) |
| Docs PR | [personal-config #2048](https://github.com/abhimehro/personal-config/pull/2048) | Verified |
| Ledger | **6→7** commit `ee885a6b…` blob `5c433bf…` → `d441c22e1cd49758f05e7d2af5b9049a4e729849` | Verified (`git rev-parse` blob) |
| Calibration | `REPORT_ONLY`, `successful_run_count` **1**/7, `approved_by: null`, event `evt-s3-20260820-calibration` `successful: true` at 2026-08-20T19:20:00Z | Verified (runtime YAML) |
| Processed | 11 of 82 Stage-3-owned items (cap 20) | Verified (run record vs ledger 85 items) |
| Product mutations | **0** | Verified (run record + cited PRs still OPEN) |
| Continuity | Read **main** Stage 1/2 reports (morning v1.3 + 08-19), not unmerged #2044/#2047 files; used ledger CAS for 17:25Z Stage 2 | Verified (Stage 3 record “Inputs and reconciliation”) |

### 3.4 Runtime ledger snapshot at cutoff (Verified)

File `automation/pr-lifecycle-ledger:pr-lifecycle-ledger.yaml`,
`schema_version: '1.2'`, `ledger_revision: 7`, blob
`d441c22e1cd49758f05e7d2af5b9049a4e729849`.

| Slice | Count |
| ----- | ----: |
| Items (`author_type: BOT`) | 85 |
| `STAGE3_RECONCILIATION` | 71 |
| `WAITING_HUMAN` | 8 |
| `STAGE2_QUEUED` | 2 |
| `STAGE1_INTAKE` | 2 |
| `TERMINAL` | 2 |
| `SENSITIVE` / `ROUTINE` | 62 / 23 |
| `REVIEW_SECURITY` | 35 |
| Remaining Stage 2 work items | 2 (`s2-20260820-ctrld-1161-bolt-summary`, `s2-20260820-pc-2041-docs-markers`) |

No ledger `item` keys for Hydrograph #543 or Seatek #708. **Verified**.

---

## 4. Stage 1 Findings

### Successes

- Preflight PASS; runtime ledger used (pointer not treated as state). **Verified**.
- v1.4 hyphen identity reset calibration correctly (not counted as a successful
  Stage 3 run). **Verified**.
- Sticky security held: dozens of Sentinel/shell/workflow PRs went to Stage 3 /
  `WAITING_HUMAN`, not squash. **Verified** (ledger outcomes).
- One legitimate routine squash (Hydrograph #536) with Opus `PASS_ROUTINE`.
  **Verified**.
- Human `feat/` / `fix/` PRs untouched. **Verified**.
- Created two complete Stage 2 work items (`seatek-705-isfile`, `rpce-271-a11y`)
  instead of prose deferrals. **Verified**.
- Recorded four zero-diff close-candidates with 24h cooldown rather than closing
  immediately. **Verified**; those four still `changedFiles=0` at cutoff.

### Failures / underperformance

- **Inventory cap starvation:** 15 rpce mega-DIRTY siblings never entered the
  ledger. They remain unowned until a later Stage 1 slot. **Strongly Inferred**.
- **Zero closes:** cooldown had not elapsed *during* the 15:00 run (correct). At
  cutoff, rpce#270 (expiry 2026-08-20T22:26:17Z), seatek#704 (2026-08-21T00:32:43Z),
  and series#403 (2026-08-21T01:49:38Z) are **past** cooldown and still OPEN
  because the next Stage 1 had not run. esp#1504 expires 2026-08-21T13:11:16Z
  (not yet elapsed at 08:30Z). **Verified**.
- **personal-config `TRUNK_QUEUE`:** no bot PR this run was CLEAN, non-draft,
  and non-sensitive, so Trunk was unused. Docs PR #2044 itself cannot be
  squash-merged by Stage 1 under current method. **Verified**.
- **Handoff ACK `pending`:** Stage 1 recorded receiver acknowledgement pending
  for new events. Stage 2/3 later ACK’d their owned items. Harmless if the
  protocol allows delayed ACK; it is noisy for operators. **Verified**.
- **CodeScene MCP error** with no `/cs-agent` comment. Spec says Stage 2 must
  confirm the comment before final salvage disposition; Stage 1 did not post it.
  **Verified** as session claim.
- **Cap docs drift:** `tasks/pr-review-agent.config.yaml` and the Cursor prompt
  say 50 inventory / 20 actions. `docs/automated-pr-review-agent.md` Scheduling
  still said “20-item inventory cap”; lifecycle “Scheduling” said “20 Stage 1
  items”. Live run followed 50/20. **Verified**.

### Risk / impact / root cause

| Item | Risk | Impact | Cause |
| ---- | ---- | ------ | ----- |
| Unowned rpce siblings | Medium | Duplicate later salvage; stale SHAs | Isolated cap; no overflow queue |
| Expired zero-diffs still open | Low | Backlog cosmetics | Systemic: closes deferred to *next* Stage 1; no intra-day closer |
| Docs PR not on main | Medium | Stage 3 continuity gap | Systemic: run records live on unmerged docs PRs |
| Cap text mismatch | Low | Agents may stop at 20 inventory | Systemic doc drift |

Safety: no unauthorized merge/close. **Verified**.

---

## 5. Stage 2 Findings

### Successes

- Honored draft-only contract: 0 merges, 0 closes, 0 approvals, originals
  #535/#705/#673/#247/#271 left open. **Verified**.
- Consumed 5/5 cap with structured outcomes, not a docs-only exit (lesson 0ga).
  **Verified**.
- Hydrograph #543: mypy 2.3.1 in poetry + `requirements-ci.txt`; pytest 70;
  mypy clean — matches work item / lesson 0fy. Live draft MERGEABLE head
  `2af2758598d8`. **Verified**.
- Seatek #708: `code_health_scanner.py` only, no `.jules`. Live draft MERGEABLE
  head `a458455faf31`. **Verified**.
- Did not treat hydro #535 main-base drift as `STALE_ANCHOR` when allowed paths
  did not overlap; recovered from current main. **Strongly Inferred** (run
  record; not independently re-diffed).
- Restored local rpce copy; did not `--no-verify`. **Strongly Inferred** (run
  record).
- CAS 5→6 succeeded. **Verified**.
- Caught GitHub-create-as-ready (0gd) and converted #543/#708 back to draft.
  Live `isDraft=true`. **Verified**.

### Failures / underperformance

- **Replacement PRs are not ledger items.** Stage 3 explicitly: “Extra drafts
  observed, not in ledger: Hydro #543, Seatek #708.” **Verified**.
- **ctrld #1161 leftover:** still `STAGE2_QUEUED`, `CONFLICTING`, head
  `1b7811646f19`, work item still allows `display.py` which Stage 2 recorded as
  split to `display/` on main. Next salvage must not expand `allowed_paths`
  (lesson 0fv). **Verified**.
- **rpce HOLD_PLATFORM:** Linux cloud runner cannot run `make guardrails` /
  Swift. Packets later asked a human for a macOS runner. Systemic, not a
  one-off mis-route. **Verified**.
- **#673 salvage empty** after morning #701: correctly failed-closed, but the
  original remains OPEN waiting for Stage 1 close after 2026-08-21T19:20:00Z.
  At 08:30Z that cooldown had **not** elapsed. **Verified**.
- Docs PR #2047 is **ready** (`isDraft=false`) despite the Cursor event title
  “Draft pull request created” — same 0gd class as product salvage, but it was
  not converted back to draft. **Verified**.

### Risk / impact / root cause

The Stage 2 authority gap is **systemic**: the contract forbids Stage 2 merge,
calibration forbids Stage 3 merge, and Stage 1 inventory does not include
replacement PRs that never received `item_key`s. Tested salvage therefore
cannot reach `TERMINAL` without a human. Isolated process excellence (0gd,
pytest, path discipline) does not fix that exit-criteria hole.

---

## 6. Stage 3 Findings

### Successes

- First live calibration after bootstrap; increment **only** via
  `kind: CALIBRATION` event; still `REPORT_ONLY`. **Verified**.
- 11 live reconciliations, **0 SHA drift** vs ledger for those keys; live `gh`
  heads still match. **Verified**.
- ACK then HANDOFF on processed items. **Verified** (run record).
- Close-candidates #673/#705 → `STAGE1_INTAKE` without closing. **Verified**.
- Five one-question packets (cap 5) for irreducible canonical/platform/sticky
  questions; did not packet routine remainder. **Strongly Inferred** (URLs
  present; bodies not fetched).
- Created complete Stage 2 work item `s2-20260820-pc-2041-docs-markers` for
  draft pc#2041 instead of a prose reminder. #2041 still OPEN draft head
  `2facd5bddc67`. **Verified**.
- Did not autonomously close SENSITIVE sticky Hydro #523. **Verified**.
- Did not recreate rpce salvage on Linux. **Verified**.
- Zero product mutations. **Verified**.

### Failures / underperformance

- **Did not ingest #543/#708 as ledger items** after observing them. That is
  the handoff the completion spec already describes (“Reconcile the draft, its
  provenance…”) but the run treated them as extras. **Verified**.
- **Processed 11/82** owned items (cap 20). 71 remain `STAGE3_RECONCILIATION`.
  Calibration success does not mean backlog ownership is current. **Verified**.
- **Continuity from main, not same-day unmerged records.** Stage 3 therefore
  could have missed Stage 1 15:00 specifics if the ledger CAS had failed; it
  luckily had rev 6. **Verified**.
- **Calibration 1/7 does not prove bounded-completion safety.** The run
  produced ledger progress (work item + close-candidates + packets) so the
  increment matches the written rule. It does **not** exercise merge
  predicates. **Verified**.
- Docs PR #2048 ready, not draft. **Verified**.
- Cloud pre-commit hook aborted on a secret label containing a space; session
  claimed a `printenv` / `make cursor-cloud-hooks` fix. **Strongly Inferred**
  (session; not reproduced here).

### Risk / impact / root cause

Stage 3 behaved as a coordinator under `REPORT_ONLY`, which is correct, but
coordination without replacement-PR ledger keys cannot complete salvage. Root
cause is schema/practice (no mandatory replacement item), not a rogue merge.

Notion packet SLA / whether a human answered: **Unverified**.

---

## 7. Cross-Stage Patterns and Edge Cases

| Pattern | Evidence | Confidence |
| ------- | -------- | ---------- |
| Unresolved / repeatedly deferred | 71 `STAGE3_RECONCILIATION`; 35 `REVIEW_SECURITY`; hydro validate_data.py Sentinel cluster still open | Verified |
| Duplicate / overlapping work | ctrld #1165 vs #1202; seatek #693 vs #692; hydro #535 vs #543; rpce #247 vs #271 | Verified live OPEN |
| Stale-SHA decisions | 0 SHA drift on the 11 Stage 3 keys; hydro #535 base moved on main without allowed-path overlap | Verified / Strongly Inferred |
| Handoff without acknowledgement | Stage 1 listed ACK `pending`; Stage 2/3 ACK’d latest projected HANDOFF for processed items | Verified |
| Work that cannot reach terminal | Salvage drafts #543/#708; docs PRs #2044/#2047/#2048 on Trunk; human `feat/`/`fix/` | Verified |
| REPORT_ONLY / capacity starvation | S3 11/82; S2 leftover #1161; S1 15 rpce unowned; calib 1/7 | Verified |
| Human PRs permanently exempt | Five `feat/`/`fix/` still OPEN; by design. Residual risk if a bot uses those prefixes without two signals | Verified |
| Stage 2 salvage PRs no stage can merge | #543, #708 not in ledger; S3 REPORT_ONLY; S2 must not merge | Verified |
| Stage 3 duplicating earlier analysis | Mostly reused ledger + live `gh`; did **not** re-open salvage branches. Under-ingested replacements rather than re-analyzing | Verified |
| Docs-run records off main | #2044/#2047/#2048 OPEN MERGEABLE ready; later stages read main `tasks/*-session-reports.md` | Verified |
| Event title vs live draft bit | Cursor `pr_created` title “Draft pull request created” for #2044/#2047/#2048; live `isDraft=false` | Verified |
| Open count 104 → 126 | Intake record vs `gh pr list` at cutoff | Verified |
| Close cooldown clock | #673/#705 close after **2026-08-21T19:20:00Z** (not elapsed at 08:30Z). Three zero-diffs already eligible for next Stage 1 | Verified |

Claim check against the originating task (treat as claims, not facts):

| Claim | Result |
| ----- | ------ |
| Starting backlog ~104 | **Verified** (Stage 1 record). Now 126 open. |
| Stage 1: 50 new BOT; skip 34 SHA; 5 human; docs #2044 | **Verified** |
| Stage 2: max 5 work items; CAS 5→6; originals unchanged; #2047 | **Verified** |
| Stage 3: first live calib; #2048; CAS 6→7 blobs `5c433bf…`→`d441c22…`; `evt-s3-20260820-calibration`; 1/7; REPORT_ONLY | **Verified** |
| 11 reconciliations, 0 SHA drift | **Verified** for the 11 keys vs live heads |
| Close-candidates Seatek #673, #705 | **Verified** `STAGE1_INTAKE`; still OPEN |
| Work item `s2-20260820-pc-2041-docs-markers` | **Verified** in runtime YAML; #2041 still draft |
| Notion packets hydro 535/543, ctrld 1165/1202, seatek 693/692, rpce 247/271, hydro 523 | **Strongly Inferred** (URLs + run record; bodies unread) |

---

## 8. Structural Gaps

1. **Entry/exit for salvage replacements.** Opening a draft is not an exit.
   Missing: ledger `item_key` for `owner/repo#replacement@head_sha`, provenance
   to original, and a named merger.
2. **Merge authority split.** Stage 1 = routine merger; Stage 2 = builder;
   Stage 3 = post-calibration completer. No path during `REPORT_ONLY` except
   human. Docs PRs on `TRUNK_QUEUE` share the hole.
3. **Continuity plane assumes main.** Run records on unmerged PRs are invisible
   to `last three records on main`. Ledger CAS partially compensated this run.
4. **Overflow / lease.** Inventory 50 and salvage 5 and reconcile 20 have no
   overflow queue, no item lease, no retry/cooldown beyond expiry timestamps.
   Unowned rpce siblings prove it.
5. **HITL packets** have URLs and expiry (`2026-08-27T19:20:00Z`) but no SLA
   owner in-repo and no “packet unanswered → escalate” automation.
6. **Replacement vs original close.** Spec already says Stage 1 may close
   superseded non-security after cooldown. Stage 3 routed #705 to Stage 1 with
   canonical #708, but #708 is not an inventory item, so Stage 1 may close the
   original while the replacement stays ownerless.
7. **Platform capability.** Linux cloud cannot salvage `repoprompt-ce`. No skip
   rule in config; each run rediscovers `HOLD_PLATFORM`.
8. **Work-item path freshness.** `#1161` `allowed_paths: display.py` stale
   after module split. No mandatory live-path refresh before recover.
9. **Calibration metric.** `successful_run_count` measures report completeness,
   not terminal rate, SHA freshness of the untouched 71, or salvage-merge lag.
10. **Emergency stop / rollback.** Ledger rollback conditions exist; no
    documented “disable all three automations” runbook besides Dashboard
    disable + `REVOKED`.
11. **ACK protocol vs operator UX.** Pending ACKs on Stage 1 look like failed
    handoffs even when Stage 2 later ACK’d.
12. **Identity residual.** Ordinary `feat/`/`fix/` stay HUMAN — correct, but a
    determined bot can hide as a human prefix if it lacks two signals.

---

## 9. Prioritized Action Plan

### P0 — Salvage-output merge authority (separation of duties preserved)

**Change:** Normative contract + stage specs + prompts (this PR). No Stage 2
merge. No calibration reset (`pr-lifecycle-v1.4` unchanged).

| Step | Owner | Acceptance |
| ---- | ----- | ---------- |
| Stage 2 CAS-writes a **new ledger item** for each replacement PR (`item_key` = `owner/repo#N@head_sha`) with provenance URLs, `replacement_of`, labels `salvage` + original key | Stage 2 | Validator still passes; #543/#708-class drafts appear as items on next CAS |
| Stage 1 **re-ingests** those items (and any open PR labeled salvage/provenance) into inventory even if draft | Stage 1 | Next cron inventories #543/#708 |
| During `REPORT_ONLY`, Stage 1 may routine-merge a salvage replacement only if every existing routine predicate passes **and** the item is BOT, non-sensitive, checks green, provenance complete. Draft is not a merge blocker when GitHub allows merging drafts; do not mark ready as a *shortcut* around failed predicates | Stage 1 | At least one routine salvage reaches `TERMINAL` without Stage 2 merging |
| After `APPROVED`, Stage 3 may merge salvage drafts only after an **independent** predicate re-read (already in completion spec § Eligible merge) | Stage 3 | No merge from salvage session |
| Human may merge salvage drafts at any time | Maintainer | Documented HITL fallback |

**Test:** unit/docs review only this change. Next live Stage 2 must show a
replacement `item_key` in the ledger export. Next Stage 1 record must list that
key. Do not CAS-write the runtime ledger from a docs PR (lesson 0gc).

**Migration:** no schema bump required if provenance lives in existing
`changed_paths` / `evidence_urls` / `next_action` fields. Optional later:
`replacement_pr` on the original item (schema + validator tests).

### P0 — Continuity reads include unmerged same-day run-record PRs

**Change:** Every stage reads the latest open docs PR / branch for its own and
upstream stage records, not only `main` `tasks/*-session-reports.md`.

**Acceptance:** Stage 3 identity block cites `#2044` / `#2047` (or the day’s
heads) when those PRs are open.

**Owner:** all three stage specs + prompts.

### P1 — Close cooldown-expired `CLOSE_NONSECURITY_NOOP`

**Change:** Stage 1 must consume `STAGE1_INTAKE` close-candidates whose cooldown
elapsed and whose head SHA + zero-diff/supersession evidence still match.

**Acceptance:** After the next 15:00 run, rpce#270, seatek#704, series#403 are
`CLOSED_NOOP` or the run record explains SHA/diff change. Do not close
esp#1504 before 2026-08-21T13:11:16Z. Do not close #673/#705 before
2026-08-21T19:20:00Z.

**Owner:** Stage 1.

### P1 — Inventory overflow

**Change:** Record uninventoried in-scope BOT PRs as `NOT_RUN` overflow keys
(or a compact overflow list in the run record **and** ledger) so they are not
invisible.

**Acceptance:** The 15 rpce siblings appear as owned `NOT_RUN` / Stage 1
backlog, not “forgotten.”

### P1 — Docs-record lineage on personal-config

**Change:** Keep one squashable docs lineage (lesson 0fk class: #2016 CONFLICTING
plus #2044/#2047/#2048). Human or Stage 1 Trunk-queue a docs-only audit PR after
review. Do not stack a fourth overlapping `tasks/*-session-reports.md` PR
without rebasing.

**Acceptance:** Operators can read yesterday’s Stage 1/2/3 records from `main`.

### P1 — rpce / Swift platform skip

**Change:** Config: `platform: macos-required` (or equivalent hold) for
`repoprompt-ce` salvage tests. Stage 2 must `HOLD_PLATFORM` **before** copying
files, not after a failed `make guardrails`.

**Acceptance:** Next Stage 2 run does not dirty a local rpce tree; packet or
skip only.

### P2 — Work-item path refresh

Live-stat allowed paths against current `main` before recover; if a path is
gone, fail-closed to Stage 3 with `HOLD_EVIDENCE` rather than expanding scope
(0fv).

### P2 — Metrics

Track terminal rate, salvage-merge lag, overflow count, packet age — not only
`successful_run_count`.

### P2 — Optional schema

Add `replacement_item_key` / `replaced_item_key` pair to
`schemas/pr-lifecycle-ledger.schema.json` with validator tests. Not in this
docs PR.

---

## 10. Documentation or Configuration Changes

Implemented in the same branch as this retrospective (no `policy_revision`
bump; calibration 1/7 must not reset):

| Path | Change |
| ---- | ------ |
| `docs/pr-lifecycle-pipeline-run-retro-2026-08-20.md` | This audit |
| `docs/automated-pr-lifecycle.md` | Salvage-output merge authority; continuity of unmerged run records; cap text 50/20 |
| `docs/automated-pr-review-agent.md` | Re-ingest salvage replacements; fix Scheduling cap; expired close-candidates |
| `docs/automated-pr-salvage-agent.md` | Ledger item for replacement PRs; re-read `isDraft` (0gd); stale allowed_paths |
| `docs/automated-pr-completion-agent.md` | Ingest observed salvage drafts as items; do not leave extras |
| `docs/cursor-automations/three-stage-pr-lifecycle.md` | Handoff of salvage drafts; merger is Stage 1 or post-calib Stage 3 or human |
| `docs/cursor-automations/prompts/daily-pr-*.md` | Matching prompt sentences |
| `AGENTS.md` | Operational salvage-merge note in stacked-PR / salvage bullets. **Not** Learned* |
| `tasks/lessons.md` | 0gd, 0ge, 0gf, 0gi |
| `tasks/todo.md` | This plan’s checkboxes |

Not changed: runtime ledger, identity allowlist, sensitive taxonomy, JSON
schema, GitHub Actions, Endor.

---

## 11. Proposed Target-State Workflow

```text
Stage 1 (15:00)  inventory (50) including salvage-labeled + overflow
                 ├── routine BOT non-sensitive → squash / Trunk / close
                 ├── bounded mechanical → complete Stage 2 work item
                 └── else → Stage 3
Stage 2 (17:00)  recover (5) from trusted main
                 ├── tested draft + ledger ITEM for the replacement
                 │     next_owner = stage1 (routine) or stage3 (canonical/security)
                 └── failed / HOLD_PLATFORM → Stage 3 (no branch)
Stage 3 (19:00)  REPORT_ONLY until 7 successful + human APPROVED
                 ├── ingest any salvage draft missing from ledger
                 ├── close-candidate → Stage 1 (cooldown)
                 ├── mechanical remainder → Stage 2 work item
                 ├── irreducible → one-question packet
                 └── after APPROVED: merge salvage drafts only after independent predicates
Human            merge salvage drafts during REPORT_ONLY; answer packets;
                 never expect Stage 2 to merge
```

Separation of duties: **builder ≠ merger**. Stage 2 never gains approve/merge.
Stage 1 remains the only pre-calibration autonomous merger, and only for
routine BOT work.

---

## 12. Open Questions and HITL Decisions

1. **Should Stage 1 merge salvage drafts during REPORT_ONLY**, or only humans,
   until calibration completes? Recommendation: Stage 1 routine-only, human
   for anything `HOLD_CANONICAL` (Hydro #543 is in that bucket). **Needs HITL.**
2. **Hydro #535 vs #543:** Dependabot lock + salvage CI pin. Packet
   `https://app.notion.com/p/3c27419416de81239945fe67878eda2e`. **Needs HITL.**
3. **ctrld #1165 vs #1202:** recommended narrower #1165 in Stage 3 record.
   Packet `…/3c27419416de81caad68ea4c89a29d63`. **Needs HITL.**
4. **Seatek #693 vs #692:** recommended #693 POSIXct; #692 CONFLICTING + journal.
   Packet `…/3c27419416de8120a9cec293ee73236c`. **Needs HITL.**
5. **rpce macOS runner** for #247/#271. Packet
   `…/3c27419416de811faef5f096aac6512d`. **Needs HITL** (platform spend).
6. **Hydro #523** sticky SENSITIVE vs merged #536. Packet
   `…/3c27419416de81c99db3da826729474c`. **Needs HITL** (do not auto-close
   sticky).
7. **Docs PR stack** #2016/#2044/#2047/#2048: squash-one lineage vs leave until
   Trunk? **Needs HITL** (personal-config merge method).
8. **Give Stage 3 merge during calibration?** **No.** Do not weaken
   `REPORT_ONLY`.
9. **Give Stage 2 merge?** **No.** Hard boundary.
10. **Bump policy to v1.5** for replacement-item schema? Defer until validator
    tests exist; this clarification stays v1.4 so calibration 1/7 survives.

---

## Appendix A — Live SHA corroboration (2026-08-21T08:30Z)

| PR | Live head (12) | State |
| -- | -------------- | ----- |
| hydro #536 | `3a63ebb016ae` | MERGED squash `226f97b63030` |
| hydro #535 | `118f9ca67550` | OPEN MERGEABLE |
| hydro #543 | `2af2758598d8` | OPEN draft MERGEABLE |
| hydro #523 | `a845bfdbb51b` | OPEN MERGEABLE |
| seatek #701 | (merged) | MERGED 03:29Z `85ea23de1e1c` |
| seatek #673 | `e2da9d736fd3` | OPEN MERGEABLE |
| seatek #705 | `c4d07fa12213` | OPEN MERGEABLE |
| seatek #708 | `a458455faf31` | OPEN draft MERGEABLE |
| seatek #693 | `dd62586806b5` | OPEN MERGEABLE |
| seatek #692 | `6bac9d59986c` | OPEN CONFLICTING |
| ctrld #1161 | `1b7811646f19` | OPEN CONFLICTING |
| ctrld #1165 | `de77774551ba` | OPEN MERGEABLE |
| ctrld #1202 | `4b10bd631026` | OPEN MERGEABLE |
| rpce #247 | `b3a5b0c760ec` | OPEN CONFLICTING |
| rpce #271 | `fc9f84652beb` | OPEN MERGEABLE |
| pc #2041 | `2facd5bddc67` | OPEN draft MERGEABLE |
| pc #2044 | `4d604a5afaaa` | OPEN ready MERGEABLE |
| pc #2047 | `ef79b711b952` | OPEN ready MERGEABLE |
| pc #2048 | `dec01fcda62f` | OPEN ready MERGEABLE |

Open counts at cutoff: pc 29, ctrld 12, esp 7, hydro 16, Seatek 29, series 5,
rpce 28. **Total 126.**

## Appendix B — ELIR

PURPOSE: Evidence-rich audit of the 2026-08-20 first live three-stage PR
pipeline run, plus v1.4 clarifications so salvage drafts can reach a merger
without giving Stage 2 merge authority.
SECURITY: No auth/payment/schema/ledger CAS from this docs PR; no secrets;
Stage 2 remains draft-only; sticky security and human PRs stay non-autonomous.
FAILS IF: Operators treat calibration 1/7 as merge permission, or Stage 2 is
given merge to “fix” the authority gap.
VERIFY: Ledger rev 7 blob `d441c22e…`; hydro #536 squash `226f97b6…`; #543/#708
still draft; #2044/#2047/#2048 still open.
MAINTAIN: Next Stage 2 must ledger replacement PRs; next Stage 1 must close
elapsed zero-diffs and re-ingest salvage drafts.

═══ ELIR (quick) ═══
PURPOSE: First-live-run audit + salvage-output merger clarification (v1.4).
SECURITY: Stage 2 still cannot merge; no ledger CAS from docs.
FAILS IF: Salvage drafts stay unledgered, so no stage can complete them.
VERIFY: Live `gh` table in Appendix A vs runtime ledger rev 7.
MAINTAIN: Builder ≠ merger; Stage 1 re-ingests salvage items.
