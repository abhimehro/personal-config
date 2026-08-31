# PR lifecycle burndown and Stage 2 starvation — 2026-08-30

Evidence-first. Does not rewrite the 2026-08-20 retrospective or the 2026-08-26
throughput diagnosis. Policy revision stays `pr-lifecycle-v1.4`. Stage 2 still
never merges. Grok Bot **PR Desk** remains read-only.

## Named root cause

**The daily drain cap equals arrivals, and Stage 2 is starved of work items, so
open-PR count oscillates near 200.**

Two mechanisms, both observed:

1. **Cap-equals-arrivals.** After #2098, Stage 1 spends **20/20** product
   mutations every run and grades **PASS**. About 14–20 new PRs arrive per day.
   Net change is about **−6 to 0** open PRs/day. That cannot clear a ~200
   backlog in an acceptable time.
2. **Upstream Stage 2 work-item starvation.** Stage 2 empty-intake is specified
   success. After 2026-08-22, Stages 1 and 3 stopped creating complete Stage 2
   work items. CONFLICTING BOT PRs with unique remaining source therefore never
   enter the MERGEABLE pool, so the 20 (now 40) merge slots cannot touch them.

#2098 fixed SHA_MATCH skip of MERGEABLE green BOT. It did **not** raise the
drain cap and it **forbade** Stage 2 from inventing recoveries without feeding
it work items. Both gaps remain in live runs through 2026-08-29.

## Burndown math (direct evidence)

| When | Open PRs (seven repos) | Stage 1 product mutations | Stage 2 | Notes |
| --- | ---: | --- | --- | --- |
| 2026-08-21 | 126 | low | drafts | Pre-#2098 growth |
| 2026-08-26 | 198–200 | 8/20 (underused) | EMPTY_INTAKE | SHA_MATCH skip 180 |
| 2026-08-27 | 211 | 20/20 | EMPTY_INTAKE | #2098 live |
| 2026-08-28 | 208 | 20/20 (7 squash, 12 close, 1 fail) | EMPTY_INTAKE | PASS; 0 Stage 2 WI |
| 2026-08-29 15:00 | 211 → 191 in-run | 20/20 (9 squash, 11 close) | EMPTY_INTAKE (rev 29) | PASS; 0 Stage 2 WI |
| 2026-08-30 ~12:00 UTC | **205** | Stage 1 not yet fired (cron 15:00) | still 0 WI | Live `gh pr list` |

Overnight 2026-08-29 15:00 → 2026-08-30 12:00: 191 → 205 is **+14 arrivals**
after a −20 drain. Arrivals ≈ **14–20/day**. Drain at 20/day ≈ keeps pace.

Live GitHub 2026-08-30 (DIRECT, `gh pr list` + status rollup):

| Bucket | Count | Who can act |
| --- | ---: | --- |
| Open PRs | 205 | — |
| BOT-ish ready MERGEABLE + green | 57 | Stage 1 merge |
| BOT-ish ready UNKNOWN + green | 37 | Stage 1 after readable checks |
| BOT-ish ready MERGEABLE + failing checks | 19 | Stage 2 if mechanical; else hold |
| BOT-ish ready CONFLICTING | 47 | Stage 2 if salvage-eligible; else canonical-pick / sticky |
| HUMAN (ready+draft) | ~42 | Never auto-merge |
| Ledger `REVIEW_SECURITY` nonterminal | 115 | Human / packet |

**Drainable automation stock** (not the whole 205): roughly **90–130** BOT PRs
that are MERGEABLE-green or salvage-eligible CONFLICTING. The rest is HUMAN,
sticky security, lockfile/major-dep `HOLD_CONTRACT`, or Swift `HOLD_PLATFORM`.
Automation must not pretend it can drive open PRs to zero.

Steady-state if nothing else changes:

```text
Δopen ≈ arrivals − stage1_mutations − stage3_completions
      ≈ 16           − 20                 − 0
      ≈ −4 / day
205 / 4 ≈ 50 days  (and the floor of sticky/HUMAN is never reached that way
                    because CONFLICTING stock never becomes MERGEABLE)
```

Target after this change (declared **before** live cron proof):

```text
Δopen ≈ 16 − 40 (Stage 1) − up to 5 (Stage 3 overflow completions)
      ≈ −24 to −29 / day on drainable stock
MERGEABLE-green BOT (~94) clears in ~4 days if arrivals stay ~16
CONFLICTING salvage-eligible (~12–37) converts at up to 5 drafts/day, then
  merges from Stage 1/3 the next day
Floor (HUMAN + sticky security + Swift-on-Linux) remains until a human acts
```

## Stage 2 starvation (direct evidence)

Live ledger `automation/pr-lifecycle-ledger` rev **30** (blob
`3195cb0724d4bc98b2f7ff69d1d4a3b4f669a3d7`):

| Field | Value |
| --- | --- |
| Items | 299 |
| `stage2_work_items` | **[]** |
| `current_owner: stage2` | **0** |
| `STAGE2_QUEUED` / `STAGE2_ACTIVE` | **0** |
| Owners | stage3 118, none/TERMINAL 92, human 77, stage1 12, **stage2 0** |
| Last `to_owner=stage2` productive CAS | **2026-08-22T17:20Z** (esp #1515 draft) |

Stage 2 EMPTY_INTAKE: 2026-08-24, 25, 26, 27, 28, **29** (docs lineage
[#2117](https://github.com/abhimehro/personal-config/pull/2117)).

Join of live CONFLICTING ready BOT-ish PRs to the ledger (DIRECT): **37** are
not `REVIEW_SECURITY` and not sticky except `generated_output`. **12** Stage-3
or human items already have `next_action` “Recover unique source only on a new
focused draft” and **no** Stage 2 work item. The monitor classifier on this
same ledger (rev 30) reports **`salvage_eligible=24`**, `stage2_work_items=0`,
exit **2**. That is a handoff failure, not a lack of salvage work. The extra
12 beyond recover-unique are other mechanical `HOLD_CONTRACT` /
`HOLD_EVIDENCE` next_actions (wrap, lint/import, conflict markers, DIRTY
unique remaining).

Dashboard 2026-08-30 (DIRECT `cursor-cloud-get-automation`): Stage 1
`77c168e0-…` **enabled**, Stage 2 `3e537981-…` **enabled**, Stage 3 calibration
`d9d2c058-…` **disabled**. Completion UUID is still **not** recorded in-repo
(INSUFFICIENT: inferred live from 08-27/28/29 bounded-completion records).

## Why 20/day cannot dent 200

#2098 made Stage 1 *use* the 20 slots. Using them fully is necessary and
insufficient.

- Inventory cap **50** with action cap **20** leaves **161** SHA_MATCH overflow
  on 08-29. Most overflow is MERGEABLE green BOT that would have been merged if
  slots existed.
- Throughput FAIL only fires when net open BOT **grew** and slots were unused.
  20/20 + slight decline = **PASS** while the backlog stays ~200.
- “Spend merges and closes first” plus 20/20 means Stage 1 never queues a Stage
  2 work item. Queuing a WI was not distinguished from a product mutation.
- Stage 3 is told both to bounce executable work to Stage 1 **and** to spend
  five completion actions. Bounce won. 08-28: **0/5** completion actions.
  Those five actions are authorized drain sitting idle while Stage 1 is full.

Raising Stage 2 utilization with fake recoveries would not reduce open PRs.
Salvage drafts that Stage 1/3 can merge **do**. MERGEABLE green BOT that Stage
1 overflowed and Stage 3 bounced **also** do, if Stage 3 completes them.

## Previously attempted approaches (do not reintroduce)

| Attempt | Expected | Actual | Why it failed |
| --- | --- | --- | --- |
| Stage 3 REPORT_ONLY calibration | Safe then complete | Parking lot; 0 S2 WIs counted as calibration success | Packets/owner-change satisfied the OR-list |
| SHA_MATCH skip unchanged SHA | Avoid re-work | 180/198 skipped | Unchanged ≠ done |
| Dump HOLD_CANONICAL on Stage 3 | Completion decides | Stage 3 cannot auto-act on clusters | Wrong owner |
| Empty-intake stop (#2098) | Stop Stage 2 theater | Stage 2 idle forever | Treated symptom; forbade self-feed |
| Canonical-pick + green HOLD_PLATFORM merge at Stage 1 (#2098) | Drain MERGEABLE BOT | 211→208 then 211→191→205; Stage 2 still 0 | Correct for MERGEABLE; does not feed salvage; 20-cap still equals arrivals |
| Stage 3 bounce to Stage 1 (#2098) | Unstick parked executable | 6 bounces 08-27; 0 S2 WIs; 0/5 completions 08-28 | Bounce competed with completion **and** WI creation and won |
| HOLD_PLATFORM as Stage 1 merge block | Avoid broken Swift salvage | Zero rpce merges until 0gu | Salvage-only hold was right; using it as a merge block was not — **do not revert 0gu** |
| Stage 2 invent recoveries from remainder markdown | Keep Stage 2 busy | Forbidden | Unscoped drafts — **do not re-enable inventing** |
| Docs Trunk as throughput PASS | Green sessions | Backlog grew | #2098 partially fixed; still PASS at 20/20 with 0 S2 WI |

## What this change does

Does **not** bump `policy_revision` / `prompt_revision` /
`sensitive_path_taxonomy_revision`. Raising Stage 1 volume of **already
authorized** routine merge/close is not a new action type and **must not**
reset calibration to `REPORT_ONLY`.

1. **Stage 1 cap 50/20 → 80/40.** Inventory must grow with the action cap or
   the extra slots starve. Expected drain ≈ 40 − arrivals, not 20 − arrivals.
2. **Queuing a complete Stage 2 work item is ledger CAS bookkeeping**, not a
   product mutation. Stage 1 can spend 40 merge/close **and** queue up to 5
   salvage WIs.
3. **SHA_MATCH reselect** includes salvage-eligible CONFLICTING/DIRTY/red-CI
   BOT **after** merge/close/canonical-pick, to create WIs, not to merge dirty
   PRs.
4. **Operational definition of salvage-eligible** (contract). Mechanical
   `HOLD_CONTRACT` / `HOLD_EVIDENCE` (unique-source rebase, wrap, lint, import,
   conflict markers; `generated_output` only or empty sticky paths) → Stage 2
   WI when `current_owner` is `stage1` or `stage3`. Sticky
   lockfile/workflow/auth/secrets → Stage 3 / human. Linux Swift
   `HOLD_PLATFORM` and WAITING_HUMAN stay not queued. Classifier expansion
   (`NOT_RUN` + more mechanical patterns) can raise the eligible count on the
   same ledger revision; that is expected, not a monitor bug.
5. **Stage 1 FAIL** if salvage-eligible BOT items exist and this run queued
   zero Stage 2 WIs while Stage 2 would empty-intake. Keep the existing FAIL
   (net open BOT grew **and** unused product slots).
6. **Stage 3 completes Stage 1 overflow.** Do **not** bounce MERGEABLE green
   BOT that Stage 1 overflowed this UTC day. Spend the five completion actions
   on those. Bounce remains for canonical-pick clusters that Stage 1 owns.
   Mechanical remainder → complete Stage 2 WI, never WAITING_HUMAN with
   “recover via draft” and no WI.
7. **Stage 2** still stops on true empty intake and still does **not** invent
   recoveries. If salvage-eligible items exist, label
   `EMPTY_INTAKE_STARVATION` for PR Desk, then stop.
8. **PR Desk** Health line flags `Stage 2 EMPTY_INTAKE while salvage-eligible > 0`
   and unused Stage 1 product slots while MERGEABLE green BOT remain. Read-only.
9. **Monitor** `scripts/pr_lifecycle_pipeline_health.py` exits 2 on starvation.

## Success criteria (declared before live cron)

In-session (this PR): contract tests; monitor exit 2 on current live ledger
(starvation is true today); salvage-eligible count ≥ 1 on that ledger.

After Dashboard paste, over **three consecutive UTC cron days**:

| Criterion | Pass | Fail |
| --- | --- | --- |
| Stage 1 product mutations | 30–40/day when MERGEABLE green BOT remain | ≤20 while ≥30 MERGEABLE green BOT sit open |
| Net seven-repo open PRs | Decline ≥ 15/day while drainable stock remains | Oscillate within ±10 of 200 |
| Stage 2 | 1–5 complete WIs or tested drafts/failed-recovery records on days salvage-eligible ≥ 1 | EMPTY_INTAKE while salvage-eligible ≥ 1 |
| Stage 3 completion actions | ≥ 1 overflow merge/close on days Stage 1 hit 40/40 and MERGEABLE overflow remains | 0/5 while bouncing MERGEABLE green to Stage 1 |
| HANDOFF `to_owner=stage2` | At least one after 08-22 drought | Still none |
| Safeguards | 0 HUMAN / `REVIEW_SECURITY` auto-merge; Stage 2 never merges | Any such action |
| PR Desk | Read-only; health flags starvation | Writes or orchestration |
| Manual HITL | One Dashboard paste | Daily routing intervention |

Live burndown **cannot** be proven in one agent session. Cron is 15:00 / 17:00 /
19:00 UTC. This session supplies tests, the monitor, and a live-ledger
classifier. Three cron days after paste are the remaining proof.

## Rollback

1. Revert this PR (or paste the previous prompts).
2. Restore `stage_caps` to 50/20 in `tasks/pr-review-agent.config.yaml` and
   `scripts/pr_lifecycle_config.py`.
3. Do **not** set calibration to `REPORT_ONLY` unless a real identity/taxonomy/
   merge-method/action-type change occurred.
4. Keep Stage 2 empty-intake / do-not-invent; keep SHA_MATCH reselect of
   MERGEABLE green; keep HOLD_PLATFORM salvage-only for GitHub-green BOT.

## Assumptions

- Arrivals stay ~14–20 BOT PRs/day (observed 08-27–30). If arrivals jump to 40,
  even a 40-cap only keeps pace; re-measure before raising again.
- Dashboard paste happens after merge. Git-only prompt changes do not move
  cron.
- Completion automation UUID remains unrecorded (INSUFFICIENT).
- How many of the 37 CONFLICTING mechanical-ish PRs survive canonical-pick as
  keepers is INFERRED until Stage 1 runs the new reselect. The 12
  recover-unique `next_action` items are DIRECT salvage-eligible.
