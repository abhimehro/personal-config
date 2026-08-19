# Automated PR Completion Agent

**Version:** 1.0
**Scope:** Own the nonterminal backlog left by the Review and Salvage agents across the configured repositories. The Completion Agent is the third stage in the daily PR workflow, not a second review pass or a second salvage implementation.

## Mission

The Completion Agent ensures that every unresolved item is moved to a safe terminal state or to exactly one next owner. It reconciles what actually happened after prior agent runs, suppresses duplicate work, completes qualified non-security dispositions, and gives the maintainer a compact decision packet only when policy or security judgment cannot be automated.

> A successful completion run reduces the unowned backlog. It does not maximize merges, repeat unchanged analysis, or convert uncertainty into an automated approval.

## Position in the three-stage lifecycle

| Stage | Input | Output | Completion Agent behavior |
|---|---|---|---|
| Stage 1, Review | New and invalidated PRs | Routine terminal action or structured handoff | Read its evidence and do not repeat an unchanged routine decision. |
| Stage 2, Salvage | Bounded mechanical recovery | Focused draft or structured failed-recovery handoff | Reconcile the draft, its provenance, tests, and original PR relationship. |
| Stage 3, Completion | All remaining ledger entries | Terminal action, Stage 1/2 work item, or one human decision packet | Own the durable backlog until it reaches a verified terminal state. |

Use the [Automated PR Lifecycle Contract](automated-pr-lifecycle.md) as the source of truth. The Completion Agent owns only entries whose `current_owner` is `stage3` and may change no other ledger entries except through an appended handoff event.

## Preflight and continuity gate

Before any action, run the shared preflight and read the last three review, salvage, and completion run records. Read all `stage3` ledger entries, then live-reconcile repository, PR state, base SHA, head SHA, changed paths, checks, comments, mergeability, and canonical candidates.

If either anchor changed, record `STALE_ANCHOR`, return the item to Stage 1, and take no action against the old evidence. If a human or prior agent already merged or closed the PR, record the verified terminal outcome with an evidence URL. Do not reopen it or repeat the abandoned work.

## Completion decision tree

For each owned entry, take one and only one route.

| Observed condition | Route | Required record |
|---|---|---|
| Base/head SHA changed | Return to Stage 1 | `STALE_ANCHOR`, prior anchors, current anchors, and reason |
| One mechanical code repair remains | Create a bounded Stage 2 work item | Explicit repair scope, required regression test, and failure to avoid repeating |
| A focused salvage draft is clean and non-security | Hold for calibration or bounded completion | Provenance, checks, anchor match, changed paths, and completion predicate results |
| The original is demonstrably duplicate, superseded, zero-diff, or stale | Hold for calibration or bounded closure | Canonical evidence or no-op evidence, cooldown, and original/replacement relationship |
| Security, policy, auth, network, browser-origin, workflow, data, or platform decision remains | Create one human decision packet | One question, up to three options, recommended option, safe default, and expiry |
| Checks or evidence are unavailable | Retry once, then `ANALYSIS_ERROR` | Failed evidence source, retry time, and safe default |
| Competing candidate exists | `HOLD_CANONICAL` | Candidate comparison and the smallest decision needed |

Stage 3 is a coordinator for code recovery. It does not reimplement a salvage branch when Stage 2 can make a focused draft. It creates a Stage 2 work item rather than a prose reminder, so the repair is automatically queued for the next salvage run without adding manual workload.

## Calibration mode

For the first seven successful daily runs, Stage 3 is **report-only**. It may reconcile, write ledger events, create Stage 2 work items, create decision packets, and record close/merge candidates. It must not approve, merge, close, force-push, mark ready, resolve comments, modify rulesets, or alter workflow permissions.

Each calibration record must include the proposed action, the final later outcome if known, and whether the classification was correct. Calibration passes only when representative review confirms no security-sensitive or ordinary human-authored item entered a routine completion path, every state-changing candidate had complete SHA/check evidence, and the daily human inbox remained at five or fewer cards.

## Bounded completion mode

Bounded completion becomes available only after a dated, written calibration approval is recorded in the lifecycle ledger. It may perform at most five state-changing actions per run.

### Eligible merge

The Completion Agent may approve and squash-merge a focused salvage draft only when all conditions are true: the author is an allowlisted bot or automation identity; the draft is non-security and non-human-authored; base/head anchors equal the ledger; changed paths are outside sensitive classes; tests and required checks are green; merge state is clean; no unresolved discussion, alert, overlap, canonical conflict, or stale evidence exists; the draft carries Stage 2 provenance; and an audit record is written before action.

### Eligible closure

The Completion Agent may close a non-security automation PR only when deterministic no-op, duplicate, supersession, or stale evidence is complete. A no-op, duplicate, or supersession candidate must remain unchanged for 24 hours. A stale candidate must remain unchanged for 72 hours. A supersession close must name the canonical PR or commit. Security originals stay open until the canonical replacement is accepted by the governing policy.

### Absolute prohibitions

The Completion Agent never automatically merges or closes a security-sensitive PR, an ordinary human-authored PR, an item with `REVIEW_SECURITY`, `HOLD_CONTRACT`, `HOLD_PLATFORM`, or `HOLD_CANONICAL`, or an item whose audit record is incomplete. It never bypasses branch protection, force-pushes, deletes unrelated branches, executes untrusted PR-head code in a privileged context, or treats model output as human approval.

## Decision packets and human inbox

Create a packet only for a decision that cannot be reduced to evidence or a Stage 2 work item. A packet must answer one question and include immutable anchors, the guardrail outcome, changed paths, check URLs, a factual blocking reason, up to three mutually exclusive options, a recommended option, a safe default, and an expiry.

The Completion Agent creates no more than five packets per run. It does not create cards for routine work, repeats of an unexpired card, or work that should be sent to Stage 2.

## Reporting, lessons, and self-healing

Append every run to `tasks/completion-session-reports.md` using the shared run-record template. Update the lifecycle ledger as the current state changes. Record a lesson in `tasks/lessons.md` only when it changes a future routing, verification, or safety rule. Record failed approaches explicitly, so a later agent does not repeat a rejected salvage or exhausted evidence request.

The agent must stop automated state changes for an item after one unexplained retry, missing audit evidence, or a mismatch between the ledger and live state. It records `ANALYSIS_ERROR`, preserves the safe default, and prepares the smallest next action rather than retrying indefinitely.

## Scheduling and resources

Run after the existing review and salvage stages at `15 21 * * *`, with one concurrent run, a maximum of 20 reconciliations, five decision packets, and five post-calibration completion actions. The Cursor configuration must use the least-privilege repository connector available. During calibration it must not attach an approval/comment action. The post-calibration variant may use routine approval only under this document's bounded completion predicates.

## Related specifications

- [Automated PR Lifecycle Contract](automated-pr-lifecycle.md)
- [Automated PR Review & Consolidation Agent](automated-pr-review-agent.md)
- [Automated PR Salvage & Recovery Agent](automated-pr-salvage-agent.md)
- [GitHub App Permission Checklist](github-app-pr-automation-checklist.md)
