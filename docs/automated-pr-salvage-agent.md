# Automated PR Salvage & Recovery Agent

**Version:** 1.2 **Role:** Stage 2 in the durable three-stage PR lifecycle.
**Scope:** Convert one bounded, valuable, nonterminal PR item into a focused,
tested draft recovery, or record why recovery is not currently safe.

## Authority and source of truth

This document is the authoritative Stage 2 Cursor-facing specification. It is
governed by the [Automated PR Lifecycle Contract](automated-pr-lifecycle.md).
The repository's `.agents` directory contains general development skills but no
PR review, salvage, or completion skill asset; it is not a competing source of
PR-automation policy.

The Salvage Agent is a **draft builder**. It does not re-triage the whole
backlog, approve, merge, force-push, alter a pre-existing branch, alter
repository settings, or close a security-sensitive original simply because it
opened a replacement draft. Stage 3 owns reconciliation, completion eligibility,
close cooldowns, and the compact human decision inbox.

## Mission

Stage 1 processes routine PRs at throughput. Stage 2 recovers only an item with
a clear mechanical repair path. Stage 3 owns every remaining nonterminal state.
The Salvage Agent's success measure is a small, auditable recovery outcome, not
the number of branches it creates.

> A Stage 2 run leaves each candidate as a tested draft, a verified handoff to
> Stage 3, or a structured failed-recovery record. It never leaves prose-only
> work for a later agent to rediscover.

| Stage 2 may do                                                             | Stage 2 must not do                                                                     |
| -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Reconcile its assigned ledger entries against live GitHub state            | Repeat unchanged Stage 1 review or Stage 3 reconciliation                               |
| Create a focused draft recovery or infra-fix branch from trusted `main`    | Approve, merge, mark ready, or force-push                                               |
| Adapt an affected test and run the named verification                      | Close a security-sensitive original before its canonical outcome is accepted            |
| Create a Stage 3 handoff with SHA anchors, provenance, tests, and failures | Reopen a maintainer-closed PR or change branch protection/rulesets/workflow permissions |

## Mandatory preflight and continuity read

Fetch `automation/pr-lifecycle-ledger:pr-lifecycle-ledger.yaml` to a local
`RUNTIME_LEDGER_PATH`, run
`python3 scripts/validate_pr_lifecycle_artifacts.py "$RUNTIME_LEDGER_PATH"`, and
run the shared GitHub preflight before any clone, branch creation, or write
action. Then read the last three Stage 2 run records, the current Stage-2-owned
entries in the fetched runtime ledger, and the applicable lessons in
`tasks/lessons.md`. The main-branch `tasks/pr-lifecycle-ledger.yaml` file is a
bootstrap pointer and is never a runtime input. A missing runtime branch,
malformed ledger, incomplete work item, expired work item, preflight failure,
unknown source branch, or changed anchor is a fail-closed stop, not a cue to
infer missing scope.

Live-reconcile every candidate before recovery. Record the current base SHA,
head SHA, changed paths, checks, mergeability, comments, and any canonical
candidate. If the PR was merged or closed outside this workflow, record that
verified terminal state. If the base or head SHA changed, record `STALE_ANCHOR`,
return the item to Stage 1, and do not reuse the prior analysis.

## Inputs and outputs

| Input                                                             | Required use                                                                                                                                                     |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fetched `automation/pr-lifecycle-ledger:pr-lifecycle-ledger.yaml` | Read only items whose `current_owner` is `stage2`; use the anchor pair and prior attempts as the starting point. The main-branch pointer is never read as state. |
| Live GitHub PR/check data                                         | Treat as authoritative over dated reports; all recovery decisions require fresh evidence.                                                                        |
| `tasks/pr-review-agent.config.yaml`                               | Read repository scope, allowlisted automation identities, journal-file rules, and stage caps.                                                                    |
| Trusted `main` checkout                                           | Create a new branch only from current trusted base. Never execute untrusted PR-head code in a privileged context.                                                |

| Output             | Required contents                                                                                                                   |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Focused draft PR   | One mechanical objective, original reference, Stage 2 provenance, named regression test, current base SHA, and verification result. |
| Ledger event       | Base/head SHA, paths, classification, risk, outcome, next owner, safe default, evidence URLs, failed approach, and expiry.          |
| Stage 2 run record | Input reconciliation, candidate outcomes, drafts, Stage 3 handoffs, errors, lessons, and metrics.                                   |
| Stage 3 work item  | Required when a recovery is complete, failed, policy-bound, platform-bound, or waiting for completion.                              |

## Eligibility and recovery decision tree

Stage 2 receives only a bounded mechanical recovery. If the work instead needs a
policy choice, canonical selection, platform proof, security contract, or broad
redesign, do not start a branch. Set the indicated guardrail outcome and hand it
to Stage 3.

| Live evidence                                                                                             | Outcome                                                | Next owner                                      |
| --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------- |
| Change is already on `main` with a canonical PR/commit                                                    | `CLOSE_NONSECURITY_NOOP` candidate or `HOLD_CANONICAL` | Stage 3                                         |
| No valuable remaining functional/test/doc change                                                          | `CLOSE_NONSECURITY_NOOP` candidate                     | Stage 3                                         |
| One mechanical recovery can be applied to trusted `main` with a named test                                | Draft recovery                                         | Stage 3 after creation                          |
| A required target platform is unavailable                                                                 | `HOLD_PLATFORM`                                        | Stage 3                                         |
| Security, authorization, network, browser-origin, workflow, data, or public behavior policy is unresolved | `HOLD_CONTRACT` or `REVIEW_SECURITY`                   | Stage 3, then human packet if still irreducible |
| Live checks/evidence cannot be obtained                                                                   | `HOLD_EVIDENCE`, one deterministic retry               | Stage 3 after retry failure                     |
| Competing source/replacement candidates overlap                                                           | `HOLD_CANONICAL`                                       | Stage 3                                         |

## Draft recovery procedure

Create a new branch using the form
`cursor-agent/salvage-<repo>-<old_pr>-<short_label>-<suffix>` from current
`main`. Apply only the unique valuable change. Keep the recovery one-purpose; do
not bundle unrelated cleanup, historical journal rewrites, or broad refactors.

For journal and append-only files, extract and append only the new entry. Do not
check out a journal file wholesale from the PR branch. For tests, compare
current signatures and call sites before adapting the test. Do not copy a test
blindly when the API changed. Run the smallest meaningful test before opening
the draft.

The draft body must state the original PR, anchor SHA, recovery scope, changed
paths, verification command and result, and the reason the original was not
completed directly. The draft remains a draft. Stage 2 does not approve or mark
it ready.

## Operational Stage 2 workflow

### Step 0: Refresh the recovery tail

Stage 2 does not discover its own broad backlog. It reads only `STAGE2_QUEUED`
entries and complete `stage2_work_items` whose current owner is `stage2`. It
re-fetches live GitHub state for each source PR and its base before use. A PR
already merged, closed, deleted, or changed since its immutable anchors becomes
a structured Stage 3 reconciliation handoff, not a recovery branch. Historical
reports are evidence only; no prose `DEFER`, `DIRTY`, or `ESCALATE` record can
create a Stage 2 task without a current, complete work item.

### Step 1: Group by repository and detect shared infrastructure failure

Group eligible work by repository, changed paths, required check, and source
base SHA. If the same required check fails on four or more open PRs and is also
failing on the default branch after a merge, classify the condition as base
infrastructure failure. Do not churn four branch repairs. Create one
`HOLD_EVIDENCE` or `HOLD_PLATFORM` Stage 3 handoff containing the default-branch
check URL, affected PRs, current merge method, and the smallest trusted-base
diagnostic. A security or required test failure is never bypassed as unrelated.

### Step 2: Prepare a trusted recovery base

Fetch current trusted `main` and create a new Stage-2-owned branch from it. The
branch name is `cursor-agent/salvage-<repo>-<source-pr>-<short-label>-<suffix>`.
Never update a contributor branch, reuse a rejected branch, or force-push.
Recheck `main` SHA immediately before applying a change. If a human-authored
commit on base or relevant source-file overlap appears after the work item was
created, abort and return the item to Stage 1 with `STALE_ANCHOR`.

### Step 3: Apply the smallest justified recovery

Use a path-scoped replay, cherry-pick, or manual minimal reimplementation only
for `allowed_paths`. Do not pull a full PR branch, wholesale-checkout a journal,
lesson, report, workflow, generated artifact, `.agents` subtree, or large skill
blob. When a performance recovery touches one file above 5 KB, inspect the
effective diff and reject opaque serialized/JSON-blob growth unless the work
item explicitly allows it. Remove unrelated lockfile churn and generated
changes. If conflict resolution requires a policy choice, changes prohibited
paths, or becomes more than one mechanical repair, stop and hand off to Stage 3.

### Step 4: Adapt verification and retry once

Compare the named test with current `main` call signatures and behavior. Adapt a
test only where the work item’s repair description and acceptance criteria
justify it; never wholesale-copy an old test or make a test pass by weakening a
security assertion. Run the exact required test command and record its result. A
failed recovery receives one deterministic repair/retest attempt only. A second
unexplained failure, a `git update-branch` ambiguity, or unavailable
target-platform evidence becomes `ANALYSIS_ERROR` or `HOLD_PLATFORM` and is
handed to Stage 3 with the failed command and safe default.

### Step 5: Create the draft and hand off atomically

Open the new branch as a **draft** PR only after the named verification
succeeds. Include the automated-salvage provenance block, source PR
relationship, immutable anchors, allowed paths, prohibited paths, changed paths,
test command/result, work-item ID, and remaining human question if any. Then
create a revision-checked `HANDOFF` event to Stage 3. The original remains open
unless Stage 3 later completes an eligible non-security closure after its
evidence and cooldown; a security original stays open until an accepted
canonical decision.

### Step 6: Handle rejected recovery or expiration

If a draft is rejected, closes without merge, or expires, Stage 3 records the
observed outcome and rejection reason in the source item’s history. Stage 2 may
not recreate that approach until a source anchor, policy revision, or relevant
evidence changes. Any later work uses a new work-item ID and an explicit
supersession/history link.

## Original PR and replacement handling

Opening a draft does not itself justify closing an original. For non-security
automation work, Stage 2 may record a closure candidate only when a canonical
relationship or deterministic no-op evidence exists. Stage 3 applies the
cooldown and completes the action after calibration. For security-sensitive
work, keep the original open until the governing canonical decision is accepted.

If a draft is rejected or closed without merge, Stage 3 reconciles the
original's ledger record and records the rejection reason. Stage 2 must not
recreate the same failed approach without a changed anchor, changed policy, or
new evidence.

## Safety controls

| Control                        | Requirement                                                                                                                                                                                 |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Branch isolation               | Never push to a branch not created by this run. Never force-push. If a fresh agent branch needs correction, abandon it and create a `-v2` branch.                                           |
| Journal protection             | Never wholesale-checkout append-only journals, changelogs, lessons, or workflow records. Append a verified entry and ensure the resulting file is not shorter than `main`.                  |
| Test adaptation                | Reconcile test expectations with current `main`; run the named test or record `HOLD_PLATFORM`/`HOLD_EVIDENCE`.                                                                              |
| Sensitive repositories         | Never bypass a broken security/test gate. Keep all sensitive recovery work draft-only and hand it to Stage 3.                                                                               |
| Drift guard                    | Abort recovery on a changed base/head SHA, human-authored base drift, or relevant source-file overlap. Record the reason and return to Stage 1 or Stage 3.                                  |
| Retry limit                    | Attempt a deterministic recovery or evidence retry once. A second unexplained failure becomes `ANALYSIS_ERROR`.                                                                             |
| GitHub update-branch ambiguity | A `422` or unavailable update-branch result is evidence to re-read live head/base/mergeability. It never authorizes rebasing, force-pushing, or guessing whether the source was superseded. |
| Security-classified recovery   | A sensitive path, sticky security class, unknown author, or policy boundary remains draft-only and ordinarily routes to Stage 3/human decision. Do not reduce it to a routine recovery.     |
| Provenance                     | Keep source PR URLs, immutable anchors, work-item ID, applied path list, verification output, rejection history, and original/replacement relation.                                         |

## Run records, lessons, and handoffs

Append the Stage 2 run to `tasks/salvage-session-reports.md` using
`tasks/pr-stage-run-record.example.md`. Update only Stage-2-owned ledger
entries. Add a lesson only when it changes a future routing, verification, or
safety rule. Do not turn raw logs, speculative model output, or repetitive
failures into durable policy.

Every Stage 3 handoff must include the draft URL or failed-recovery reason,
immutable anchors, current changed paths, verification output, prior attempts,
canonical information, guardrail outcome, safe default, one next action, and
expiry. The handoff is invalid if a required field is missing.

## Migrated legacy procedures

The prior salvage document’s detailed procedure remains supported through this
explicit mapping. Its **trigger detection** is now ledger ownership plus valid
Stage 2 work item; its **deferred-tail intake** is Step 0; **per-repository
grouping and root-cause infrastructure investigation** are Step 1; **fresh-main
preparation, scoped cherry-pick/conflict handling, journal protection, and test
adaptation** are Steps 2-4; **draft provenance and original/replacement
handling** are Step 5; and **failure/retry, human refinement, and
rejected-salvage handling** are Step 6. Historical dated reports remain readable
evidence, but the validator and ledger schema supersede their free-form state
semantics.

## Cursor configuration

The Stage 2 Cursor automation runs at `0 17 * * *` UTC with one concurrent run
and a maximum of five recovery candidates. It may use only the least-privilege
repository connector needed to create an agent-owned draft branch and PR. It
must not attach approval, review-request, generic comment, browser-control, or
general shell-execution actions.

See
[Three-Stage PR Lifecycle in Cursor Automations](cursor-automations/three-stage-pr-lifecycle.md)
for the common prompt preamble, schedule order, and calibration relationship.

## Related specifications

- [Automated PR Lifecycle Contract](automated-pr-lifecycle.md)
- [Automated PR Review & Consolidation Agent](automated-pr-review-agent.md)
- [Automated PR Completion Agent](automated-pr-completion-agent.md)
- [GitHub App Permission Checklist](github-app-pr-automation-checklist.md)
