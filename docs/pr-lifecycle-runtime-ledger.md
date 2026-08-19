# PR Lifecycle Runtime Ledger

## Status and Authority

This document defines the **runtime** storage model for the lifecycle ledger.
The separately authorized bootstrap is complete: the orphan branch
`automation/pr-lifecycle-ledger` contains the v1.2 baseline and manifest, and
the selected primitive is `github_contents_api`. This document does not itself
grant an automation permission or replace a live Dashboard configuration.

The checked-in `tasks/pr-lifecycle-ledger.yaml` file on `main` is a
**non-authoritative bootstrap pointer** once this model is activated. It must
never be read as runtime calibration state. The only runtime ledger is
`pr-lifecycle-ledger.yaml` on the dedicated orphan data branch
`automation/pr-lifecycle-ledger`.

| Record                  | Canonical location after bootstrap                                                                   | Authority                                                                                   |
| ----------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Runtime ledger          | `automation/pr-lifecycle-ledger:pr-lifecycle-ledger.yaml`                                            | Current items, events, calibration, Stage 2 work items, imports, and merge-method registry. |
| Main-branch pointer     | `tasks/pr-lifecycle-ledger.yaml`                                                                     | Bootstrap metadata and retrieval instructions only, never runtime state.                    |
| Schema and validator    | `main:schemas/pr-lifecycle-ledger.schema.json` and `main:scripts/validate_pr_lifecycle_artifacts.py` | Reviewed structure and fail-closed validation rules.                                        |
| Run records and lessons | `main:tasks/*.md`                                                                                    | Append-only evidence and reusable lessons, never an ownership projection.                   |

The branch is deliberately orphaned so ledger reads do not pull the `main`
history. Because the active deletion rule applies to all branches, the name and
layout must be confirmed before bootstrap; routine actors do not delete or
rename this branch.

## Bootstrap Manifest and Selected Write Primitive

Before any stage is enabled against the runtime ledger, the maintainer records a
bootstrap manifest in the runtime ledger containing the branch name, schema
revision, selected write primitive, credential evidence, permission scope,
activation timestamp, and rollback contact.

Exactly one primitive is selected for a run. Agents must not switch primitives
mid-run.

| Primitive                       | Preconditions                                                                      | Compare-and-swap anchor                                 | Use when                                                                           |
| ------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Git fast-forward transaction    | Runtime has repository Git credentials and may write only the data branch.         | Observed remote ref SHA plus `ledger_revision`.         | The runtime can fetch and push the orphan branch directly.                         |
| GitHub Contents API transaction | Runtime lacks usable Git credentials but has scoped Contents API write permission. | Observed ledger-file blob `sha` plus `ledger_revision`. | A conditional file update is available; a stale blob SHA is treated as a conflict. |

The selected primitive and its evidence are part of every stage run record. An
absent, ambiguous, or untested write primitive is `HOLD_PLATFORM`; it never
counts as a successful calibration run.

## Git Fast-Forward Transaction

The Git transaction is intentionally narrow:

1. Fetch `automation/pr-lifecycle-ledger` and record its remote ref SHA.
2. Read the runtime ledger, validate it, and confirm the owned item's `revision`
   equals the handoff/event's expected revision.
3. Rebuild exactly one owned item projection plus its event(s), validate the
   complete ledger, and create one signed-by-runtime audit commit.
4. Push only by ordinary fast-forward.
5. If the push is rejected as non-fast-forward, treat it as a stale CAS result.
   Fetch, rebuild from the new ref, revalidate, and retry once at most.

The transaction may **fetch, rebuild, validate, commit, retry once, and
plain-fast-forward push**. It must not invoke `pull`, `rebase`, `merge`,
`--force`, or `--force-with-lease`. A normal fast-forward push is sufficient
ref-level CAS for append-only ledger writes; a merge-based recovery would
silently defeat the ledger's stale-revision guarantee.

## Contents API Transaction

When the selected primitive is the Contents API, the stage reads the current
runtime ledger file and records its blob `sha`. It validates and rebuilds the
same bounded projection, then writes using that exact blob SHA precondition. A
stale-SHA conflict is a CAS loss. The stage re-reads, revalidates, and retries
once at most. It never creates a working-tree merge, force-updates a ref, or
bypasses the data branch.

## Stage Eligibility, Inventory Exclusion, and Recovery

Stages must fetch and validate the runtime ledger before intake. They consume
the data branch directly. Ledger-only commits are not pull requests, are not
source candidates, and are excluded from Stage 1 product-PR inventory by branch
and path policy.

| Condition                                            | Required outcome                                                                                                   |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Data branch or file is missing before bootstrap      | `HOLD_PLATFORM`; report one bootstrap prerequisite.                                                                |
| Read, schema, or cross-record validation fails       | `ANALYSIS_ERROR`; perform no lifecycle action.                                                                     |
| CAS conflict persists after one rebuild              | `ANALYSIS_ERROR`; leave the item unchanged and emit evidence for the next run.                                     |
| Git credentials unavailable                          | Use Contents API only if the recorded API primitive and scope are proven; otherwise `HOLD_PLATFORM`.               |
| Existing dashboard stage is enabled before bootstrap | Do not apply ledger-read-required exports; retain the existing dashboard state and raise one rollout prerequisite. |

No calibration event, state transition, closure candidate, approval, merge, or
completion action may follow a failed runtime-ledger read or write.

## Rollout Sequence

The authorized bootstrap created and seeded the orphan data branch, validated the
Contents API read/write primitive, recorded its manifest, and proved the
main-branch pointer cannot be used as runtime state. Stage 1 and Stage 2 may
read the active ledger only through the recorded primitive. Both Stage 3 variants
are currently disabled for controlled manual testing; after the test, enable only
the report-only calibration variant. The post-calibration completion variant
remains disabled until the ledger contains the approved seven-run record and a
dated written approval.
