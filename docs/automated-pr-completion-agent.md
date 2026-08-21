# Automated PR Completion Agent

**Version:** 1.4 **Scope:** Own the nonterminal backlog left by the Review and
Salvage agents across the configured repositories. The Completion Agent is the
third stage in the daily PR workflow, not a second review pass or a second
salvage implementation.

## Mission

The Completion Agent ensures that every unresolved item is moved to a safe
terminal state or to exactly one next owner. It reconciles what actually
happened after prior agent runs, suppresses duplicate work, completes qualified
non-security dispositions, and gives the maintainer a compact decision packet
only when policy or security judgment cannot be automated.

> A successful completion run reduces the unowned backlog. It does not maximize
> merges, repeat unchanged analysis, or convert uncertainty into an automated
> approval.

## Position in the three-stage lifecycle

| Stage               | Input                        | Output                                                             | Completion Agent behavior                                                 |
| ------------------- | ---------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| Stage 1, Review     | New and invalidated PRs      | Routine terminal action or structured handoff                      | Read its evidence and do not repeat an unchanged routine decision.        |
| Stage 2, Salvage    | Bounded mechanical recovery  | Focused draft or structured failed-recovery handoff                | Reconcile the draft, its provenance, tests, and original PR relationship. |
| Stage 3, Completion | All remaining ledger entries | Terminal action, Stage 1/2 work item, or one human decision packet | Own the durable backlog until it reaches a verified terminal state.       |

Use the [Automated PR Lifecycle Contract](automated-pr-lifecycle.md) as the
source of truth. The Completion Agent owns only entries whose `current_owner` is
`stage3` and may change no other ledger entries except through an appended
handoff event.

## Preflight and continuity gate

Before any action, fetch
`automation/pr-lifecycle-ledger:pr-lifecycle-ledger.yaml` to a local
`RUNTIME_LEDGER_PATH` and run
`python3 scripts/validate_pr_lifecycle_artifacts.py "$RUNTIME_LEDGER_PATH"`,
then the shared GitHub preflight, and read the last three review, salvage, and
completion run records. The main-branch `tasks/pr-lifecycle-ledger.yaml` file is
a bootstrap pointer, never a runtime input. Read all `stage3` entries from the
fetched runtime ledger, then live-reconcile repository, PR state, base SHA, head
SHA, GitHub API author identity, sticky sensitive paths, registered merge
method, required-check source, changed paths, checks, comments, mergeability,
and canonical candidates. A missing runtime branch, validation failure, unknown
merge method, or unreadable required-check source is `HOLD_EVIDENCE`; it permits
no state change.

If either anchor changed, record `STALE_ANCHOR`, return the item to Stage 1, and
take no action against the old evidence. If a human or prior agent already
merged or closed the PR, record the verified terminal outcome with an evidence
URL. Do not reopen it or repeat the abandoned work.

Read the latest **unmerged** Stage 1/2/3 documentation PRs for the same UTC day
when those heads exist; `main` `tasks/*-session-reports.md` can lag. If a
salvage draft is open in GitHub but absent from the ledger, ingest it as an
item before packing or skipping it. Do not leave “extra drafts observed, not in
ledger.”

## Completion decision tree

For each owned entry, take one and only one route.

| Observed condition                                                                            | Route                                      | Required record                                                                       |
| --------------------------------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------- |
| Base/head SHA changed                                                                         | Return to Stage 1                          | `STALE_ANCHOR`, prior anchors, current anchors, and reason                            |
| One mechanical code repair remains                                                            | Create a bounded Stage 2 work item         | Explicit repair scope, required regression test, and failure to avoid repeating       |
| A focused salvage draft is clean and non-security                                             | Ingest it as a ledger item if missing; hold for Stage 1 re-ingest, human merge during REPORT_ONLY, or bounded completion after APPROVED | Provenance, checks, anchor match, changed paths, replacement `item_key`, and completion predicate results |
| The original is demonstrably duplicate, superseded, zero-diff, or stale                       | Record the close-candidate; Stage 1 may close during calibration | Canonical evidence or no-op evidence, cooldown, and original/replacement relationship |
| Security, policy, auth, network, browser-origin, workflow, data, or platform decision remains | Create one human decision packet           | One question, up to three options, recommended option, safe default, and expiry       |
| Checks or evidence are unavailable                                                            | Retry once, then `ANALYSIS_ERROR`          | Failed evidence source, retry time, and safe default                                  |
| Competing candidate exists                                                                    | `HOLD_CANONICAL`                           | Candidate comparison and the smallest decision needed                                 |

Stage 3 is a coordinator for code recovery. It does not reimplement a salvage
branch when Stage 2 can make a focused draft. It creates a Stage 2 work item
rather than a prose reminder, so the repair is automatically queued for the next
salvage run without adding manual workload.

## Calibration mode

Stage 3 begins **report-only** and remains so until `calibration.status` in the
validated ledger is `APPROVED` for the same configured-repository scope and
policy revision. It may reconcile, create a complete Stage 2 work item, create a
one-question decision packet, and record a candidate. It must not approve,
merge, queue-submit, close, comment, force-push, mark ready, resolve comments,
modify rulesets, alter workflow permissions, create a recovery branch, or delete
a branch.

A successful calibration run has all of the following: a validated ledger; every
processed item live-reconciled with mandatory record fields; fresh anchors and
readable required-check sources for each candidate; no prohibited action
attempt; no `ANALYSIS_ERROR`; no security-sensitive or ordinary human-authored
item in a routine path; and ledger progress (a complete Stage 2 work item, a
close-candidate record, a packet, or an owner/next_action change from live
reconcile). A docs-only wrap-up does not count. A zero-eligible-item run counts
only when every Stage-3-owned item was live-reconciled and no complete work item
or close-candidate could be created from live evidence. The run records proposed
action, later observed outcome when known, and calibration correctness
assessment. A run does not count merely because it found no work.

The ledger’s calibration object records successful count, required count, scope,
policy revision, representative coverage, approval identity/date/evidence,
rollback conditions, invalidation revision, revocation time, and completion
authority. A prompt, identity list, sensitive-path taxonomy, permissions/action
surface, required-check source, or merge-method change resets the status to
`REPORT_ONLY`. Any human can revoke completion by recording `REVOKED`; no
recalibration result is merge permission without a dated approval.

## Bounded completion mode

Bounded completion becomes available only after a dated, written calibration
approval is recorded in the validated lifecycle ledger. It may perform at most
five state-changing actions per run. Approval, merge or queue submission,
closure, comment, branch creation/deletion, failed mutation, and retry are each
one action. The agent stops before exceeding the cap.

### Eligible merge

The Completion Agent may approve and complete the registered merge method for a
focused salvage draft only when all conditions are true: the GitHub API author
identity is an allowlisted or token-authored bot; the draft is non-security and
non-human-authored; base/head anchors equal the ledger; changed paths are
outside sticky sensitive classes; tests and **required checks from the
registered readable source** are green; merge state is clean; no unresolved
discussion, alert, overlap, canonical conflict, or stale evidence exists; the
draft carries Stage 2 provenance; and an audit record is written before action.
It must re-read every predicate after approval and before the merge/queue
submission.

For `abhimehro/personal-config`, use the registered `TRUNK_QUEUE` submission
path, not a raw GitHub squash assumption. Approval and queue submission are
separate audited actions. An approval-success/queue-failure records the failure
and stops. A merge-success/branch-delete-failure is a non-blocking follow-up; do
not retry the merge.

### Eligible closure

The Completion Agent may close a non-security automation PR only when
deterministic no-op, duplicate, supersession, or stale evidence is complete. A
no-op, duplicate, or supersession candidate must remain unchanged for 24 hours.
A stale candidate must remain unchanged for 72 hours. A supersession close must
name the canonical PR or commit. Security originals stay open until the
canonical replacement is accepted by the governing policy.

### Absolute prohibitions

The Completion Agent never automatically merges or closes a security-sensitive
PR, an ordinary human-authored PR, an item with `REVIEW_SECURITY`,
`HOLD_CONTRACT`, `HOLD_PLATFORM`, or `HOLD_CANONICAL`, or an item whose audit
record is incomplete. It never bypasses branch protection, force-pushes, deletes
unrelated branches, executes untrusted PR-head code in a privileged context, or
treats model output as human approval.

## Decision packets and human inbox

Create a packet only for a decision that cannot be reduced to evidence or a
Stage 2 work item. A packet must answer one question and include immutable
anchors, the guardrail outcome, changed paths, check URLs, a factual blocking
reason, up to three mutually exclusive options, a recommended option, a safe
default, and an expiry.

The Completion Agent creates no more than five packets per run. It does not
create cards for routine work, repeats of an unexpired card, or work that should
be sent to Stage 2.

## Reporting, lessons, and self-healing

Append every run to `tasks/completion-session-reports.md` using the shared
run-record template. Each item record is mandatory: repository, PR, ledger key,
observed/ledger base and head SHA, owner before/after, GitHub identity,
classification/risk, guardrail outcome, changed paths, evidence URLs,
proposed/actual route, calibration or bounded mode, audit-record ID,
retries/errors, final observed outcome, calibration correctness assessment, next
owner/action, expiry, and provenance/canonical relationship. Update the
lifecycle ledger only through revision-checked events. Record a lesson in
`tasks/lessons.md` only when it changes a future routing, verification, or
safety rule. Record failed approaches explicitly, so a later agent does not
repeat a rejected salvage or exhausted evidence request.

The agent must stop automated state changes for an item after one unexplained
retry, missing audit evidence, or a mismatch between the ledger and live state.
It records `ANALYSIS_ERROR`, preserves the safe default, and prepares the
smallest next action rather than retrying indefinitely.

## Scheduling and resources

Run after the existing review and salvage stages at `0 19 * * *`, with one
concurrent run, a maximum of 20 reconciliations, five decision packets, and five
post-calibration actions. Use the paste-ready calibration or completion export
in `docs/cursor-automations/exports/`; the live Cursor Dashboard is canonical
for current trigger, connection, and enablement state. The Dashboard-referenced
MCP set for this stage is named in the calibration and completion prompts
(`gh` reads, Notion packets, scanners as hold evidence; `gh` mutations only
after ledger `APPROVED`). A wider connected workspace inventory is not an
additional action authority. During calibration,
the report-only prohibitions control even when a visible integration is
connected. The bounded-completion variant may use `prComment.allowApprove` only
after validated ledger approval. Shared memory is enabled as a namespaced cache
and is never continuity authority.

## Related specifications

- [Automated PR Lifecycle Contract](automated-pr-lifecycle.md)
- [Automated PR Review & Consolidation Agent](automated-pr-review-agent.md)
- [Automated PR Salvage & Recovery Agent](automated-pr-salvage-agent.md)
- [GitHub App Permission Checklist](github-app-pr-automation-checklist.md)
