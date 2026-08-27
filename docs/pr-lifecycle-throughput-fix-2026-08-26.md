# PR lifecycle throughput diagnosis — 2026-08-26

Evidence-first. Does not rewrite the 2026-08-20 first-live-run retrospective.
Policy revision stays `pr-lifecycle-v1.4`. Stage 2 still never merges.

## Objective vs observed

The three-stage pipeline exists to **drain** bot-authored PRs. After Stage 3
and later refinements, open PRs grew:

| When | Open PRs (seven-repo) | Notes |
| ---- | --------------------: | ----- |
| 2026-08-21 cutoff | 126 | First post-Stage-3 days |
| 2026-08-23 | 150 | Stage 1: 1 squash + 1 Trunk docs + 1 close |
| 2026-08-24 | 163 | 1 squash + 1 Trunk docs + 2 closes |
| 2026-08-25 | 185 | 0 squash + 1 Trunk docs + 3 closes |
| 2026-08-26 15:00 | 198 | 0 squash + 1 Trunk docs + 3 closes; SHA_MATCH skip **180** |
| 2026-08-26 evening | **200** | 128 MERGEABLE non-draft; ~182 botish |

Arrival is ~12–20 BOT PRs/day. Drain is ~1 product merge + ~3 zero-diff closes.
Net growth is structural, not a missed 20-action cap: Stage 1 used **8/20**
actions on 2026-08-26 and marked throughput **PASS**.

## Where the pipeline stalls

1. **SHA_MATCH skip is the throughput killer.** Unchanged-SHA items are treated
   as done. The 18 NEW items are mostly overlap twins → `HOLD_CANONICAL` or
   `REVIEW_SECURITY` → Stage 3. Next day SHA still matches → skip forever.
2. **HOLD_CANONICAL clusters are dumped on Stage 3.** The review spec already
   says keep one PR per group and close the others. Cron prompts routed every
   cluster to Stage 3 instead.
3. **Stage 3 was a parking lot.** `REPORT_ONLY` cannot merge. It incremented
   calibration with packets and close-candidates. Maintainer HITL grew.
4. **HOLD_PLATFORM misapplied to Stage 1 merge.** Lesson 0gi: Linux cannot
   *salvage* Swift. Stage 1 treated GitHub-green `repoprompt-ce` BOT PRs as
   platform holds. Zero rpce merges since 2026-08-20.
5. **`.jules/` journals counted as sticky `generated_output`.** Bolt PRs that
   also touch real source never merge. Journal overlap is lesson 0cs.
6. **Stage 2 empty-intake theater.** After the first salvage, Stage 1 queues 0.
   Stage 2 still burns a session to write “empty intake.”
7. **Success metric is wrong.** PASS at 1 docs Trunk merge while open PRs grew
   13. Bookkeeping (CAS + docs PR) was counted toward the 20-action cap.

Live ledger after approval (rev 23): 241 items; **0** Stage 2 work items;
nonterminal mass is Stage 3 `REVIEW_SECURITY` (58), `HOLD_CANONICAL` (36),
`HOLD_CONTRACT` (34), plus WAITING_HUMAN. That is parking, not drain. Canonical-pick
and SHA_MATCH reselect are what move the MERGEABLE BOT subset.

## Stage 3 calibration — approved

| Check | Result |
| ----- | ------ |
| Successful `CALIBRATION` events | 7 (`evt-s3-20260820-calibration` … `evt-s3-20260826-calibration`); each `successful: true`, `ACKNOWLEDGED` |
| `successful_run_count` | 7 of 7 |
| `policy_revision` | `pr-lifecycle-v1.4` |
| Prior status | `REPORT_ONLY`, `approved_by: null` |
| Human approval | Maintainer Abhi Mehrotra (`abhimehro`), 2026-08-26, this session |
| Live Dashboard | Calibration automation `d9d2c058-9c42-11f1-ba66-0e7d0216e441` is still **enabled**; cron will keep report-only until that is disabled and the completion prompt is pasted |

Approving calibration **without** the Stage 1 drain still cannot clear
`HOLD_CANONICAL` / sticky / HUMAN items (Stage 3 must not auto-act on those).
Bounded completion adds five qualified non-security actions/day. Stage 1
canonical-pick and SHA_MATCH reselect are what drain the MERGEABLE BOT backlog.

## What this change does

- Stage 1 reselects SHA_MATCH-executable work and canonical-picks BOT clusters.
- `HOLD_PLATFORM` is salvage-only; GitHub-green BOT PRs merge at Stage 1.
- `.jules/` journal alone is not sticky.
- Product-mutation cap excludes ledger CAS and docs lineage.
- Throughput FAIL if net open BOT PRs grew and unused product slots remained.
- Stage 2 empty intake: short record and stop.
- Stage 3 bounces executable clusters to Stage 1; packets stay irreducible.
- Runtime ledger `calibration.status` → `APPROVED` via Contents API CAS
  (`automation/pr-lifecycle-ledger` commit
  `2f024d1f659fa8d8cd5b8bf76d40d90da3505b23`, ledger rev 23). Dashboard: disable
  calibration automation, enable completion, **paste** the updated prompts or
  cron keeps the old behavior.

## What this does not do

- Stage 2 still never merges, approves, closes, or requests review.
- HUMAN and sticky security (workflows, secrets, auth, lockfiles/major deps)
  still never auto-merge.
- `policy_revision` / `prompt_revision` / taxonomy revision stay `v1.4` /
  `2026-08-19` so the seven calibration events remain valid.
- No new `stage_caps` YAML keys (validator `require_exact_stage_caps`).
