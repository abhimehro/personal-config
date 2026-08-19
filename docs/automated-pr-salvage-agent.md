# Automated PR Salvage & Recovery Agent

**Version:** 1.2
**Role:** Stage 2 in the durable three-stage PR lifecycle.
**Scope:** Convert one bounded, valuable, nonterminal PR item into a focused, tested draft recovery, or record why recovery is not currently safe.

## Authority and source of truth

This document is the authoritative Stage 2 Cursor-facing specification. It is governed by the [Automated PR Lifecycle Contract](automated-pr-lifecycle.md). The repository's `.agents` directory contains general development skills but no PR review, salvage, or completion skill asset; it is not a competing source of PR-automation policy.

The Salvage Agent is a **draft builder**. It does not re-triage the whole backlog, approve, merge, force-push, alter a pre-existing branch, alter repository settings, or close a security-sensitive original simply because it opened a replacement draft. Stage 3 owns reconciliation, completion eligibility, close cooldowns, and the compact human decision inbox.

## Mission

Stage 1 processes routine PRs at throughput. Stage 2 recovers only an item with a clear mechanical repair path. Stage 3 owns every remaining nonterminal state. The Salvage Agent's success measure is a small, auditable recovery outcome, not the number of branches it creates.

> A Stage 2 run leaves each candidate as a tested draft, a verified handoff to Stage 3, or a structured failed-recovery record. It never leaves prose-only work for a later agent to rediscover.

| Stage 2 may do | Stage 2 must not do |
|---|---|
| Reconcile its assigned ledger entries against live GitHub state | Repeat unchanged Stage 1 review or Stage 3 reconciliation |
| Create a focused draft recovery or infra-fix branch from trusted `main` | Approve, merge, mark ready, or force-push |
| Adapt an affected test and run the named verification | Close a security-sensitive original before its canonical outcome is accepted |
| Create a Stage 3 handoff with SHA anchors, provenance, tests, and failures | Reopen a maintainer-closed PR or change branch protection/rulesets/workflow permissions |

## Mandatory preflight and continuity read

Run the shared GitHub preflight before any clone, branch creation, or write action. Then read the last three Stage 2 run records, the current Stage-2-owned entries in `tasks/pr-lifecycle-ledger.yaml`, and the applicable lessons in `tasks/lessons.md`.

Live-reconcile every candidate before recovery. Record the current base SHA, head SHA, changed paths, checks, mergeability, comments, and any canonical candidate. If the PR was merged or closed outside this workflow, record that verified terminal state. If the base or head SHA changed, record `STALE_ANCHOR`, return the item to Stage 1, and do not reuse the prior analysis.

## Inputs and outputs

| Input | Required use |
|---|---|
| `tasks/pr-lifecycle-ledger.yaml` | Read only items whose `current_owner` is `stage2`; use the anchor pair and prior attempts as the starting point. |
| Live GitHub PR/check data | Treat as authoritative over dated reports; all recovery decisions require fresh evidence. |
| `tasks/pr-review-agent.config.yaml` | Read repository scope, allowlisted automation identities, journal-file rules, and stage caps. |
| Trusted `main` checkout | Create a new branch only from current trusted base. Never execute untrusted PR-head code in a privileged context. |

| Output | Required contents |
|---|---|
| Focused draft PR | One mechanical objective, original reference, Stage 2 provenance, named regression test, current base SHA, and verification result. |
| Ledger event | Base/head SHA, paths, classification, risk, outcome, next owner, safe default, evidence URLs, failed approach, and expiry. |
| Stage 2 run record | Input reconciliation, candidate outcomes, drafts, Stage 3 handoffs, errors, lessons, and metrics. |
| Stage 3 work item | Required when a recovery is complete, failed, policy-bound, platform-bound, or waiting for completion. |

## Eligibility and recovery decision tree

Stage 2 receives only a bounded mechanical recovery. If the work instead needs a policy choice, canonical selection, platform proof, security contract, or broad redesign, do not start a branch. Set the indicated guardrail outcome and hand it to Stage 3.

| Live evidence | Outcome | Next owner |
|---|---|---|
| Change is already on `main` with a canonical PR/commit | `CLOSE_NONSECURITY_NOOP` candidate or `HOLD_CANONICAL` | Stage 3 |
| No valuable remaining functional/test/doc change | `CLOSE_NONSECURITY_NOOP` candidate | Stage 3 |
| One mechanical recovery can be applied to trusted `main` with a named test | Draft recovery | Stage 3 after creation |
| A required target platform is unavailable | `HOLD_PLATFORM` | Stage 3 |
| Security, authorization, network, browser-origin, workflow, data, or public behavior policy is unresolved | `HOLD_CONTRACT` or `REVIEW_SECURITY` | Stage 3, then human packet if still irreducible |
| Live checks/evidence cannot be obtained | `HOLD_EVIDENCE`, one deterministic retry | Stage 3 after retry failure |
| Competing source/replacement candidates overlap | `HOLD_CANONICAL` | Stage 3 |

## Draft recovery procedure

Create a new branch using the form `cursor-agent/salvage-<repo>-<old_pr>-<short_label>-<suffix>` from current `main`. Apply only the unique valuable change. Keep the recovery one-purpose; do not bundle unrelated cleanup, historical journal rewrites, or broad refactors.

For journal and append-only files, extract and append only the new entry. Do not check out a journal file wholesale from the PR branch. For tests, compare current signatures and call sites before adapting the test. Do not copy a test blindly when the API changed. Run the smallest meaningful test before opening the draft.

The draft body must state the original PR, anchor SHA, recovery scope, changed paths, verification command and result, and the reason the original was not completed directly. The draft remains a draft. Stage 2 does not approve or mark it ready.

## Original PR and replacement handling

Opening a draft does not itself justify closing an original. For non-security automation work, Stage 2 may record a closure candidate only when a canonical relationship or deterministic no-op evidence exists. Stage 3 applies the cooldown and completes the action after calibration. For security-sensitive work, keep the original open until the governing canonical decision is accepted.

If a draft is rejected or closed without merge, Stage 3 reconciles the original's ledger record and records the rejection reason. Stage 2 must not recreate the same failed approach without a changed anchor, changed policy, or new evidence.

## Safety controls

| Control | Requirement |
|---|---|
| Branch isolation | Never push to a branch not created by this run. Never force-push. If a fresh agent branch needs correction, abandon it and create a `-v2` branch. |
| Journal protection | Never wholesale-checkout append-only journals, changelogs, lessons, or workflow records. Append a verified entry and ensure the resulting file is not shorter than `main`. |
| Test adaptation | Reconcile test expectations with current `main`; run the named test or record `HOLD_PLATFORM`/`HOLD_EVIDENCE`. |
| Sensitive repositories | Never bypass a broken security/test gate. Keep all sensitive recovery work draft-only and hand it to Stage 3. |
| Drift guard | Abort recovery on a changed base/head SHA, human-authored base drift, or relevant source-file overlap. Record the reason and return to Stage 1 or Stage 3. |
| Retry limit | Attempt a deterministic recovery or evidence retry once. A second unexplained failure becomes `ANALYSIS_ERROR`. |

## Run records, lessons, and handoffs

Append the Stage 2 run to `tasks/salvage-session-reports.md` using `tasks/pr-stage-run-record.example.md`. Update only Stage-2-owned ledger entries. Add a lesson only when it changes a future routing, verification, or safety rule. Do not turn raw logs, speculative model output, or repetitive failures into durable policy.

Every Stage 3 handoff must include the draft URL or failed-recovery reason, immutable anchors, current changed paths, verification output, prior attempts, canonical information, guardrail outcome, safe default, one next action, and expiry. The handoff is invalid if a required field is missing.

## Cursor configuration

The Stage 2 Cursor automation runs at `0 17 * * *` UTC with one concurrent run and a maximum of five recovery candidates. It may use only the least-privilege repository connector needed to create an agent-owned draft branch and PR. It must not attach approval, review-request, generic comment, browser-control, or general shell-execution actions.

See [Three-Stage PR Lifecycle in Cursor Automations](cursor-automations/three-stage-pr-lifecycle.md) for the common prompt preamble, schedule order, and calibration relationship.

## Related specifications

- [Automated PR Lifecycle Contract](automated-pr-lifecycle.md)
- [Automated PR Review & Consolidation Agent](automated-pr-review-agent.md)
- [Automated PR Completion Agent](automated-pr-completion-agent.md)
- [GitHub App Permission Checklist](github-app-pr-automation-checklist.md)
