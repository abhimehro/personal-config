# Automated PR Lifecycle Contract

**Version:** 1.0

This contract is the shared operating model for the Automated PR Review Agent, Automated PR Salvage & Recovery Agent, and Automated PR Completion Agent. The three agents are complementary. They must not repeat an unchanged analysis or leave an item without an owner.

## Lifecycle principle

Every in-scope PR must have either a terminal disposition or a single current owner. A terminal disposition is `MERGED_ROUTINE`, `MERGED_BOUNDED_COMPLETION`, `CLOSED_NOOP`, `CLOSED_DUPLICATE`, `CLOSED_STALE`, `CLOSED_SUPERSEDED`, `HUMAN_REJECTED`, or `HUMAN_DEFERRED`.

Every nonterminal item must carry immutable base and head SHA anchors, a risk class, one guardrail outcome, a safe default, the next owner, and a bounded next action. A base or head SHA change invalidates prior evidence and returns the item to Stage 1 intake.

| Stage | Name | Owns | May do | Must hand off |
|---|---|---|---|---|
| 1 | Review | New and invalidated inventory items | Routine approve, squash-merge, close, and narrowly mechanical repair when every routine predicate passes | Mechanical recovery to Stage 2; security, policy, platform, canonical, or evidence holds to Stage 3 |
| 2 | Salvage | Bounded mechanical recovery | Open or update a focused **draft** replacement with required tests and provenance | Draft completion, rejected recovery, unavailable platform, or unresolved decision to Stage 3 |
| 3 | Completion | All remaining nonterminal entries | Reconcile live state, prevent duplication, create decision packets, and, only after approved calibration, complete qualified non-security work under a hard cap | SHA drift to Stage 1; mechanical recovery to Stage 2; irreducible policy/security decision to the human inbox |

Automated routine approval is a policy-authorized throughput control, not an independent human security review. Security-sensitive and ordinary human-authored PRs never become routine merge or close candidates.

## Canonical records and repository authority

| Record | Location | Writer | Purpose |
|---|---|---|---|
| Lifecycle ledger | `tasks/pr-lifecycle-ledger.yaml` | The stage that currently owns the item | Current state, SHA anchors, evidence, next action, and handoff history |
| Review run record | `tasks/review-session-reports.md` | Stage 1 only | Append-only inventory and routine-disposition audit |
| Salvage run record | `tasks/salvage-session-reports.md` | Stage 2 only | Append-only recovery and draft-provenance audit |
| Completion run record | `tasks/completion-session-reports.md` | Stage 3 only | Append-only reconciliation, packet, and bounded-completion audit |
| Lessons | `tasks/lessons.md` | Any stage, through an append-only entry | Reusable routing or verification rules, not raw logs or speculation |

The ledger is the only source of an item's current owner. A run report is evidence of what a stage did; it cannot silently transfer ownership. Each stage may modify only ledger entries it owns, then append a handoff event. A stage must never edit another stage's run report.

The three `docs/automated-pr-*.md` specifications and this lifecycle contract are the authoritative Cursor-facing PR-automation documents in this repository. The `.agents` directory supplies generic skills and has no PR-specific review, salvage, or completion asset in the current default branch. It must not override this lifecycle without an explicit policy revision.

## Required handoff record

Every handoff must include `key`, `repository`, `pr`, `url`, `base_sha`, `head_sha`, `author_type`, `classification`, `risk_class`, `guardrail_outcome`, `current_owner`, `next_owner`, `safe_default`, `next_action`, `evidence_urls`, `changed_paths`, `attempts`, and `updated_at_utc`.

The handoff is invalid if any required field is unknown. The receiving stage must live-reconcile the PR before it acts. It must record `STALE_ANCHOR` and return the item to Stage 1 rather than acting against stale evidence.

## Guardrail outcomes

Use the exact outcome values below in ledger events and run records.

| Outcome | Meaning | Default owner |
|---|---|---|
| `PASS_ROUTINE` | All routine execution predicates are complete | Stage 1 or approved Stage 3 completion |
| `REVIEW_SECURITY` | A security result needs an explicit human decision | Human inbox |
| `HOLD_CONTRACT` | A policy, behavior, or security contract is undefined | Stage 3, then human inbox |
| `HOLD_EVIDENCE` | Checks, tests, overlap, or artifacts are insufficient | Stage 3 reconciliation |
| `HOLD_PLATFORM` | Target platform proof is unavailable | Stage 3 reconciliation |
| `HOLD_CANONICAL` | Competing candidate or source overlap is unresolved | Stage 3 reconciliation |
| `CLOSE_NONSECURITY_NOOP` | A non-security close candidate has evidence and cooldown | Stage 3 completion after calibration |
| `ANALYSIS_ERROR` | The agent could not obtain reliable evidence | Stage 3 with one retry, then human inbox |
| `NOT_RUN` | The item has not received the required stage | Stage 1 |

## Continuity and self-healing rules

Before acting, every stage reads its last three run records and all currently owned ledger entries. It must record meaningful actions, results, failed approaches, changed assumptions, and one reusable lesson only when that lesson changes future routing, testing, or safety behavior.

Runs are idempotent by `repository#pr@head_sha`. An unchanged item with an unexpired next action is not re-investigated. The system must detect PRs resolved outside the workflow, rejected salvage drafts, missing canonical candidates, or stale SHA anchors and update the ledger instead of reopening old work or repeating an unsuccessful approach.

Routine evidence expires after seven days. A deterministic retry is allowed once. Repeated unexplained failure, absent audit evidence, or an unexpected security/human classification routes to `ANALYSIS_ERROR` and stops automated state changes for that item.

## Decision packets

Stage 3 may create a decision packet only for an irreducible human choice. One packet contains one question, up to three mutually exclusive options, a recommended option, a safe default, immutable anchors, evidence links, prohibited-condition results, and an expiry. No packet may be used as an approval, merge authorization, or substitute for a defined policy.

## Scheduling and bounded concurrency

The standard daily order is Stage 1 at `0 13 * * *`, Stage 2 at `0 17 * * *`, and Stage 3 at `15 21 * * *`. Only one run per stage may execute at once. The default per-run caps are 20 Stage 1 items, five Stage 2 recovery candidates, 20 Stage 3 reconciliations, five human decision cards, and, after explicit calibration approval, five Stage 3 completion or closure actions.

## Migration

Historical `open_followups`, `remainder`, `ESCALATE`, and `DEFER` records are evidence only. The first Stage 3 calibration run must import them into the ledger after live PR reconciliation. It must not infer a current owner from prose alone.

## Related specifications

- [Automated PR Review & Consolidation Agent](automated-pr-review-agent.md)
- [Automated PR Salvage & Recovery Agent](automated-pr-salvage-agent.md)
- [Automated PR Completion Agent](automated-pr-completion-agent.md)
