# PR Lifecycle Revision Checklist

**Applies to:** `personal-config` PR #2026, merged. **Purpose:** This records
the implementation and re-review evidence for the maintainer-designated blocking
review and the subsequent authorized runtime reconciliation. It is not a blanket
authorization for Stage 3 bounded completion.

## Preserved authority model

The revision must retain the parts of the reviewed design that already match
maintainer intent. **Stage 1** remains the evidence-complete routine executor
for bot-authored, non-sensitive PRs. **Stage 2** remains a draft-only recovery
builder. **Stage 3** remains report-only during a durable calibration gate and
becomes a bounded non-security completion layer only after recorded approval.
Security-sensitive and ordinary human-authored PRs never enter an automated
merge or close path.

|  # | Blocking requirement                                                        | Required artifact or change                                                                                                                                                                    | Validation evidence                                    | Status                 |
| -: | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ---------------------- |
|  1 | Keep Stage 1 routine approve, merge, and close authority.                   | Stage 1 prompt/export preserves `prComment.allowApprove: true`, limits action to identity-verified bot routine work, and uses the repository merge-method registry.                            | Export validation plus prompt predicates.              | Implemented, validated |
|  2 | Keep Stage 2 draft-only and remove approval/reviewer-request capability.    | Stage 2 prompt/export includes no approval or reviewer-request action, accepts only complete Stage 2 work items, and creates drafts/candidates only.                                           | Export action-set validation.                          | Implemented, validated |
|  3 | Make Stage 3 a calibrated completion layer, not a permanent third reviewer. | Separate calibration and post-calibration prompts/exports; durable approval, rollback, reset, scope, and success-count rules.                                                                  | Calibration schema and transition validation.          | Implemented, validated |
|  4 | Provide a normative machine-readable ledger schema.                         | JSON Schema, validated YAML ledger, complete terminal/nonterminal/event/calibration/Stage 2-work-item examples, and fail-closed validator.                                                     | Validator success and malformed-fixture failure.       | Implemented, validated |
|  5 | Make handoffs atomic, idempotent, and revision-checked.                     | Event ID, expected revision, acknowledgement, idempotency key, compare-and-swap semantics, and interrupted-write recovery procedure.                                                           | Lifecycle transition and duplicate-event fixtures.     | Implemented, validated |
|  6 | Persist calibration state and reset rules.                                  | Schema fields for scope, policy revision, approval, representative coverage, resets, revocation, and action authority.                                                                         | Calibration fixture and validator.                     | Implemented, validated |
|  7 | Supply paste-ready Cursor prompts and actual-surface exports.               | Four prompt files, four exports, dashboard create/update checklist, UTC and America/Chicago time note, environment, actions, memory, rollback, and drift check.                                | JSON parse and prompt/export consistency validation.   | Implemented, validated |
|  8 | Define the Stage 2 work-item schema.                                        | Immutable source anchors, allowed/prohibited paths, test command/result, acceptance criteria, provenance, expiry, attempts, owner, and history.                                                | Complete example and validator.                        | Implemented, validated |
|  9 | Use GitHub identity classification and sticky sensitive paths.              | Versioned bot identities, ambiguous-is-human rule, sensitive-path taxonomy, sticky security classification, and calibration invalidation rule.                                                 | Prompt and schema validation.                          | Implemented, validated |
| 10 | Restore or map deleted salvage procedures.                                  | Trigger, source intake, stale-state handling, trusted-base setup, journal safety, bounded recovery, infra diagnosis, branch/provenance, retries, and rejection procedure.                      | Procedure crosswalk in Stage 2 specification.          | Implemented, validated |
| 11 | Make historical import reproducible and rerunnable.                         | File globs, precedence, deterministic mapping, anchor handling, import ID/event, idempotency, no-longer-open PR handling, and evidence-only rule.                                              | Historical-import procedure and fixture.               | Implemented, validated |
| 12 | Require completion and continuity reporting fields.                         | Mandatory per-item report template with anchors, ownership, identity, classification, audit/action count, live evidence, correctness assessment, outcome, and next state.                      | Template validation.                                   | Implemented, validated |
| 13 | Namespace shared memory behind the continuity plane.                        | `memoryEnabled: true` in all reference exports, documented as a namespaced cache that cannot override ledger/run records/lessons.                                                              | Export and prompt assertions.                          | Implemented, validated |
| 14 | Make the merge path match each repository.                                  | Merge-method registry declares Trunk, merge queue, direct squash, or unknown; required-check source and unreadable-config hold; audited approval/merge outcomes.                               | Registry validation and completion predicate.          | Implemented, validated |
| 15 | Preserve Dashboard MCP inventory while enforcing stage authority.           | Documentation records the live prompt-referenced MCP group and broader Dashboard inventory without treating visible tools as authority; stage prompts retain all security and mutation limits. | Dashboard reconciliation and prompt/export validation. | Implemented, validated |
| 16 | Fix review-spec numbering and scheduled-automation contradiction.           | Review specification uses sequential numbering, maps legacy statuses, and identifies the 15:00/17:00/19:00 UTC Cursor runs as the lifecycle; upstream 06:00/08:00/08:15 tasks are inputs only. | Documentation lint and Dashboard reconciliation.       | Implemented, validated |

## Re-review gate

Every row must be marked **Implemented** only after its named artifact is
present and the stated validation evidence is recorded. A passing documentation
check is not evidence that the Cursor Dashboard runtime matches the checked-in
source. The Dashboard is canonical and must be read before an export is changed;
the reconciled checked-in artifact then records the verified Dashboard state and
its fingerprint in the next runtime-ledger event.

## Enforcement-layer follow-up

The approved enforcement follow-up is implemented in source on this draft
branch. It adds enforcement, test, and CI coverage without creating a data
branch, changing a Cursor Dashboard automation, approving, merging, closing, or
otherwise mutating any PR.

| Follow-up                                  | Source implementation                                                                                                                                                                            | Validation evidence                                                                                                                                                                                                         | Runtime status                                                          |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| A1, Git-native ledger write path           | `docs/pr-lifecycle-runtime-ledger.md`; active main-branch bootstrap pointer; explicit Contents API CAS rules; inventory exclusion; capability hold behavior.                                     | Pointer validation, fetched runtime-ledger validation, and stale-CAS rejection.                                                                                                                                             | **Active:** Contents API bootstrap authorized and verified.             |
| A2, CodeScene refactor                     | Validator split into parsing/schema, configuration/export, ledger cross-record, and thin orchestration modules.                                                                                  | Ruff, Bandit, Radon, focused regression suite, fixture validation, prompt/export drift check, and `make test-quick` pass locally; the hosted `CodeScene Code Health Review (main)` passed for enforcement commit `e84816a`. | Source complete, hosted quality gate verified.                          |
| B1-B2, URL/schema/calibration enforcement  | JSON Schema plus cross-record validation for complete HTTPS URLs, timestamps, terminal ownership, projection continuity, current-policy calibration events, and seven-run approval.              | Twelve focused regression tests and `PR_LIFECYCLE_VALID`.                                                                                                                                                                   | Source complete.                                                        |
| B3-B4, pointer/registry/config correctness | Runtime pointer validation, legacy-key rejection, exact stage caps/schedules/authorities, verified-zero required-check proof, and dated read-only discovery evidence for all seven repositories. | Fixture validation and targeted regression tests.                                                                                                                                                                           | Active ledger read is available through the selected Contents API path. |
| C, Cursor transition and drift safety      | Runtime-ledger prompt preamble, prompt/export synchronization, Dashboard reconciliation, and mutually exclusive Stage 3 transition/rollback steps.                                               | `CURSOR_EXPORT_PROMPTS_MATCH`, export validation, and Dashboard readback.                                                                                                                                                   | Stage 3 variants disabled for controlled manual testing.                |
| D, trusted-base enforcement                | `Code Quality` CI job installs the pinned schema dependency and runs artifact validation, prompt/export sync, and focused lifecycle tests before the broader suite.                              | Workflow review and local command parity.                                                                                                                                                                                   | Active when this source reaches the trusted base.                       |

The broad `make test-all` suite passes. The unrelated
`tests/test_controld_manager.sh` false positive was repaired in the test harness
by replacing pipefail-sensitive `echo | grep -q` assertions with equivalent Bash
here-string checks. The Control D runtime behavior was not changed. The
lifecycle smoke suite and focused enforcement suite also pass.

## Schema v1.2 and final evidence corrections

The current re-review head is `1efd36d`. Schema v1.2 is implemented before any
runtime-ledger bootstrap: transition events are append-only `HANDOFF`, `IMPORT`,
and `TERMINAL` records with explicit lifecycle states and one-revision
increments; `ACKNOWLEDGEMENT` and `CANCELLATION` are append-only receipts with
`parent_event_id`, unchanged revision, and unchanged projected state. Terminal
items require a final `TERMINAL` transition, revision at least one, `none/none`
ownership, and a matching disposition. The illustrative ledger validates under
v1.2.

The active lifecycle configuration now requires the fetched-ledger invocation
`python3 scripts/validate_pr_lifecycle_artifacts.py "$RUNTIME_LEDGER_PATH"`; the
configuration validator rejects the former argument-less form, and a focused
regression test covers that rejection. The Stage 2 fixture uses the same
command.

The verified-zero registry was corrected separately from the schema change.
`abhimehro/personal-config` remains `VERIFIED` only because the authoritative
branch-protection endpoint was read at `2026-08-19T12:52:18Z` and recorded a
disabled-protection response, while the ruleset endpoint returned no rulesets.
The remaining six repositories were then read from their authoritative
branch-protection and ruleset endpoints at `2026-08-19T13:04:17Z`. `ctrld-sync`,
`email-security-pipeline`, `Seatek_Analysis`,
`Hydrograph_Versus_Seatek_Sensors_Project`, and
`series_correction_project_updated` have no required-status-check rule in their
active rulesets and are now `VERIFIED` with evidence-backed zero required
checks. `repoprompt-ce` is `VERIFIED` with nonzero requirements for CodeQL code
scanning and code quality, so its `required_checks_verified_zero` remains false.
No merge path is inferred beyond these recorded settings.

| Evidence item                      | Result                                                                                                                                                                                                   |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused lifecycle regression suite | 20 tests passed, including stale-command rejection and pending-hold coverage.                                                                                                                            |
| Full local validation              | Ruff, Bandit, fixture validation, prompt/export synchronization, `make test-quick`, and `make test-all` passed, with 480 repository tests passing.                                                       |
| Hosted quality gate                | `CodeScene Code Health Review (main)` passed on the preceding schema-v1.2 quality head and on current evidence remediation head `1efd36d`.                                                               |
| Authoritative registry refresh     | Branch-protection and full ruleset definitions were read for the six remaining repositories. The explicit stale-command regression `test_active_config_requires_fetched_runtime_ledger_argument` passed. |
| Runtime and governance             | The authorized ledger bootstrap and read/CAS verification completed; Dashboard settings are maintainer-controlled, with no product-PR mutation performed by this reconciliation.                         |

These records are implementation and re-review evidence only. They do not
authorize merge, dashboard activation, or runtime-ledger bootstrap; each remains
a separate human decision.
