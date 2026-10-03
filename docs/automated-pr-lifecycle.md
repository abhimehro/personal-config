# Automated PR Lifecycle Contract

**Version:** 1.2

This contract is the shared operating model for the Automated PR Review Agent,
Automated PR Salvage & Recovery Agent, and Automated PR Completion Agent. The
three agents are complementary. They must not repeat an unchanged analysis or
leave an item without an owner.

## Lifecycle principle

Every in-scope PR must have either a terminal disposition or a single current
owner. A terminal disposition is `MERGED_ROUTINE`, `MERGED_BOUNDED_COMPLETION`,
`CLOSED_NOOP`, `CLOSED_DUPLICATE`, `CLOSED_STALE`, `CLOSED_SUPERSEDED`,
`HUMAN_REJECTED`, or `HUMAN_DEFERRED`. A **guardrail outcome** is intermediate
eligibility evidence, not a terminal disposition.

Every nonterminal item must carry immutable base and head SHA anchors, a risk
class, one guardrail outcome, a safe default, the next owner, and a bounded next
action. A base or head SHA change invalidates prior evidence and returns the
item to Stage 1 intake.

| Stage | Name       | Owns                                | May do                                                                                                                                                          | Must hand off                                                                                                 |
| ----- | ---------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 1     | Review     | New and invalidated inventory items | Routine approve, squash-merge, close, and narrowly mechanical repair when every routine predicate passes                                                        | Mechanical recovery to Stage 2; security, policy, platform, canonical, or evidence holds to Stage 3           |
| 2     | Salvage    | Bounded mechanical recovery         | Open or update a focused **draft** replacement with required tests and provenance                                                                               | Draft completion, rejected recovery, unavailable platform, or unresolved decision to Stage 3                  |
| 3     | Completion | All remaining nonterminal entries   | Reconcile live state, prevent duplication, create decision packets, and, only after approved calibration, complete qualified non-security work under a hard cap | SHA drift to Stage 1; mechanical recovery to Stage 2; irreducible policy/security decision to the human inbox |

Automated routine approval is a policy-authorized throughput control, not an
independent human security review. Security-sensitive and ordinary
human-authored PRs never become routine merge or close candidates.

## Canonical records and repository authority

| Record                     | Location                                                                                        | Writer                                                                  | Purpose                                                                                                    |
| -------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Runtime lifecycle ledger   | `automation/pr-lifecycle-ledger:pr-lifecycle-ledger.yaml` after separately authorized bootstrap | The stage that currently owns the item through a revision-checked event | Current state, SHA anchors, evidence, next action, handoff history, calibration, and merge-method registry |
| Main-branch ledger pointer | `tasks/pr-lifecycle-ledger.yaml`                                                                | Maintainer only during bootstrap                                        | Non-authoritative retrieval/bootstrap metadata, never live calibration state                               |
| Review run record          | `tasks/review-session-reports.md`                                                               | Stage 1 only                                                            | Append-only inventory and routine-disposition audit                                                        |
| Salvage run record         | `tasks/salvage-session-reports.md`                                                              | Stage 2 only                                                            | Append-only recovery and draft-provenance audit                                                            |
| Completion run record      | `tasks/completion-session-reports.md`                                                           | Stage 3 only                                                            | Append-only reconciliation, packet, and bounded-completion audit                                           |
| Lessons                    | `tasks/lessons.md`                                                                              | Any stage, through an append-only entry                                 | Reusable routing or verification rules, not raw logs or speculation                                        |

The runtime ledger is the only source of an item's current owner. A run report
is evidence of what a stage did; it cannot silently transfer ownership. A stage
must never edit another stage's run report. The Git-native write,
compare-and-swap, runtime capability, inventory-exclusion, and bootstrap
protocol is normative in
[PR Lifecycle Runtime Ledger](pr-lifecycle-runtime-ledger.md).

The three `docs/automated-pr-*.md` specifications and this lifecycle contract
are the authoritative Cursor-facing PR-automation documents in this repository.
The `.agents` directory supplies generic skills and has no PR-specific review,
salvage, or completion asset in the current default branch. It must not override
this lifecycle without an explicit policy revision.

## Normative ledger and legal transitions

`schemas/pr-lifecycle-ledger.schema.json` is the normative machine-readable
schema. `scripts/validate_pr_lifecycle_artifacts.py` must pass before an
automation reads or writes the runtime ledger. The validator rejects duplicate
YAML mapping keys, unknown fields, duplicate item/event/idempotency keys,
invalid anchors, invalid URLs/timestamps, invalid transition state/owner pairs,
illegal transitions, projection disagreement, invalid terminal ownership,
missing calibration fields, invalid Stage 2 work items, and an export whose
authority does not match its stage. Any failure is `ANALYSIS_ERROR`; no action
may follow. A main-branch bootstrap pointer is not a valid runtime-ledger input.

The unique item key is `owner/repository#PR@head_sha`. Each entry has an integer
`revision`; a state transition increments it by exactly one. Nonterminal legal
states are `STAGE1_INTAKE`, `STAGE2_QUEUED`, `STAGE2_ACTIVE`,
`STAGE3_RECONCILIATION`, and `WAITING_HUMAN`. The only terminal state is
`TERMINAL`, which must have one terminal disposition and `current_owner: none`,
`next_owner: none`.

| From state              | Legal destination                                                     | Owner rule                                                                                                                  |
| ----------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `STAGE1_INTAKE`         | `TERMINAL`, `STAGE2_QUEUED`, `STAGE3_RECONCILIATION`                  | Stage 1 may act only on identity-verified bot routine work; all other nonterminal work receives one handoff.                |
| `STAGE2_QUEUED`         | `STAGE2_ACTIVE`, `STAGE3_RECONCILIATION`                              | Stage 2 accepts only a complete, unexpired work item. Invalid or stale work returns to Stage 1 or Stage 3 without a branch. |
| `STAGE2_ACTIVE`         | `STAGE3_RECONCILIATION`                                               | Stage 2 ends with a tested draft or structured failed-recovery handoff.                                                     |
| `STAGE3_RECONCILIATION` | `STAGE1_INTAKE`, `STAGE2_QUEUED`, `WAITING_HUMAN`, `TERMINAL`         | Stage 3 reconciles every remainder and acts only in approved bounded-completion mode.                                       |
| `WAITING_HUMAN`         | `STAGE1_INTAKE`, `STAGE2_QUEUED`, `STAGE3_RECONCILIATION`, `TERMINAL` | A human decision or new immutable evidence must define the next route.                                                      |

### Atomic, idempotent handoff protocol

1. The sending stage reads the item revision and creates one projected `HANDOFF`
   event with a unique `event_id`, `item_key`, from/to lifecycle state and
   matching from/to owner, `expected_item_revision`, resulting revision, and
   idempotency key `(item_key, event_id)`.
2. It applies the event only if the stored item revision equals
   `expected_item_revision`; the projection, owner, next action, and revision
   update occur in the same committed ledger edit.
3. A receiver is ineligible until the event projection exists. On receipt it
   appends an `ACKNOWLEDGEMENT` receipt with `parent_event_id` set to the
   handoff ID before processing. Receipts do not increment revision or mutate
   the projected state; the original transition remains `PROJECTED` forever.
4. Replaying the same event is a no-op. A competing writer with a stale expected
   revision loses, records `ANALYSIS_ERROR`, and re-reads the ledger instead of
   clobbering.
5. If a write is interrupted, a later run validates the ledger. A present event
   without the matching projected item state is recorded with a `CANCELLATION`
   receipt and reissued from fresh evidence; a projected event without
   acknowledgement remains owned by the sender until acknowledged. A
   cancellation is a receipt, not a backdoor state change.

The full required item, event, calibration, import, and Stage 2 work-item fields
are defined in the schema and illustrated in
`tasks/pr-lifecycle-ledger.example.yaml`. Unknown fields are invalid rather than
silently accepted.

## Guardrail outcomes

Use the exact outcome values below in ledger events and run records.

| Outcome                  | Meaning                                                  | Default owner                            |
| ------------------------ | -------------------------------------------------------- | ---------------------------------------- |
| `PASS_ROUTINE`           | All routine execution predicates are complete            | Stage 1 or approved Stage 3 completion   |
| `REVIEW_SECURITY`        | A security result needs an explicit human decision       | Human inbox                              |
| `HOLD_CONTRACT`          | A policy, behavior, or security contract is undefined    | Stage 3, then human inbox                |
| `HOLD_EVIDENCE`          | Checks, tests, overlap, or artifacts are insufficient    | Stage 3 reconciliation                   |
| `HOLD_PLATFORM`          | Target platform proof is unavailable                     | Stage 3 reconciliation                   |
| `HOLD_CANONICAL`         | Competing candidate or source overlap is unresolved      | Stage 3 reconciliation                   |
| `CLOSE_NONSECURITY_NOOP` | A non-security close candidate has evidence and cooldown | Stage 3 completion after calibration     |
| `ANALYSIS_ERROR`         | The agent could not obtain reliable evidence             | Stage 3 with one retry, then human inbox |
| `NOT_RUN`                | The item has not received the required stage             | Stage 1                                  |

## Identity and sticky sensitivity rules

An agent must classify authorship only from GitHub API `login` and `app_slug`.
The only automated identity set is the versioned `bot_authors` list in
`tasks/pr-review-agent.config.yaml`. Branch names, titles, bodies, comments, or
review history cannot establish bot authorship. `UNKNOWN` is treated as `HUMAN`
for every autonomous mutation.

The sensitive-path taxonomy includes workflows and permissions, secrets,
authentication and authorization, deployment and infrastructure, lockfiles and
major dependencies, security configuration, database migrations, network/browser
origins, shell execution, file-read/write boundaries, generated output, public
API contracts, and destructive data actions. A sensitive classification is
sticky until a human records an explicit policy revision. A change to identity
policy or taxonomy invalidates calibration.

## Continuity and self-healing rules

Before acting, every stage reads its last three run records and all currently
owned ledger entries. It must record meaningful actions, results, failed
approaches, changed assumptions, and one reusable lesson only when that lesson
changes future routing, testing, or safety behavior.

Runs are idempotent by `repository#pr@head_sha`. An unchanged item with an
unexpired next action is not re-investigated. The system must detect PRs
resolved outside the workflow, rejected salvage drafts, missing canonical
candidates, or stale SHA anchors and update the ledger instead of reopening old
work or repeating an unsuccessful approach.

Routine evidence expires after seven days. A deterministic retry is allowed
once. Repeated unexplained failure, absent audit evidence, or an unexpected
security/human classification routes to `ANALYSIS_ERROR` and stops automated
state changes for that item.

Each item report is mandatory, not narrative-optional. It records repository,
PR, ledger key, observed and ledger anchors, owner before/after, GitHub
identity, classification, risk, guardrail outcome, changed paths, evidence URLs,
proposed/actual action, mode, audit-record ID, retries/errors, correctness
assessment during calibration, final observed result, next owner/action, expiry,
and provenance/canonical relationship. The stage run template is a required
wrapper around these per-item records.

## Calibration and bounded completion

The `calibration` object in the ledger scopes completion authority to a named
policy revision and repository scope. It begins `REPORT_ONLY`, requires seven
successful runs, records representative
identity/risk/merge-method/required-check coverage, and may change to `APPROVED`
only with a dated human approver, evidence URL, scope, policy revision, and
rollback conditions. A successful calibration run has a valid ledger, complete
mandatory records for every processed item, fresh anchors and readable
required-check sources for every candidate, no prohibited mutation attempt, and
no `ANALYSIS_ERROR`. A zero-eligible-item run counts only after live
reconciliation of all Stage-3-owned items.

Completion approval automatically resets to `REPORT_ONLY` when the policy
revision, prompt, identity allowlist, sensitive taxonomy, attached
permission/action scope, required-check source, or repository merge method
changes. A human may set `REVOKED` at any time; a revoked or invalidated record
permits no bounded state change. Only an `APPROVED` record with the current
policy revision authorizes Stage 3’s five-action non-security completion cap.

## Repository merge methods and required checks

Every configured repository has a `repository_merge_methods` record with an
evidence URL, observation timestamp, discovery status, and explicit hold reason
where discovery is incomplete. `method` is `TRUNK_QUEUE`, `GITHUB_SQUASH`,
`GITHUB_MERGE_QUEUE`, or `UNKNOWN`; the required-check source is `TRUNK`, GitHub
rulesets, GitHub branch protection, or unknown. `UNKNOWN`, an unreadable source,
or an ambiguous empty response is `HOLD_EVIDENCE`, never an inferred green
check. An empty `required_checks` list is eligible only when
`required_checks_verified_zero: true` records that a successfully read
authoritative source explicitly requires zero checks.

For `abhimehro/personal-config`, the current method is `TRUNK_QUEUE`. Approval
and queue submission are separate audited actions and both count toward Stage
3’s five-action cap. The second action may occur only after re-reading every
completion predicate. Approval-success/queue-failure stops the item with an
error record. Merge-success/branch-delete-failure is a non-blocking follow-up.
Failed attempts and retries count against the cap.

## Decision packets

Stage 3 may create a decision packet only for an irreducible human choice. One
packet contains one question, up to three mutually exclusive options, a
recommended option, a safe default, immutable anchors, evidence links,
prohibited-condition results, and an expiry. No packet may be used as an
approval, merge authorization, or substitute for a defined policy.

## Scheduling and bounded concurrency

The standard daily order is Stage 1 at `0 13 * * *`, Stage 2 at `0 17 * * *`,
and Stage 3 at `15 21 * * *`. Only one run per stage may execute at once. The
default per-run caps are 20 Stage 1 items, five Stage 2 recovery candidates, 20
Stage 3 reconciliations, five human decision cards, and, after explicit
calibration approval, five Stage 3 completion or closure actions.

## Historical import procedure

Historical import is a rerunnable, idempotent evidence operation. Stage 3 scans
`tasks/pr-review-*.md`, `tasks/review-session-reports.md`,
`tasks/salvage-session-reports.md`, `tasks/completion-session-reports.md`,
`tasks/handoff.md`, and `tasks/pr-escalation-salvage-plan.md` in this precedence
order: current ledger, terminal GitHub state, newest dated run record, explicit
handoff, then older snapshot. It fingerprints each source and writes an `IMPORT`
event with a stable `import_id`; a matching `(source_path, fingerprint)` is
skipped on rerun.

Map legacy `ESCALATE` to `REVIEW_SECURITY` or `HOLD_CONTRACT` and Stage 3,
`DEFER` to Stage 2 only if one complete mechanical repair exists otherwise Stage
3, `DIRTY` to Stage 2 only with a work item otherwise Stage 3, `UNSTABLE` to
`HOLD_EVIDENCE`, and close values to the documented terminal disposition only
after live verification. A record lacking immutable anchors remains
`EVIDENCE_ONLY`; it becomes actionable only after GitHub live reconciliation.
Deleted, merged, or closed PRs are imported as evidence with their observed
terminal state, never resurrected.

## Related specifications

- [Automated PR Review & Consolidation Agent](automated-pr-review-agent.md)
- [Automated PR Salvage & Recovery Agent](automated-pr-salvage-agent.md)
- [Automated PR Completion Agent](automated-pr-completion-agent.md)
